import base64
import binascii
import hashlib
import secrets

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class FederationIntegrationContract(models.Model):
    _name = "federation.integration.contract"
    _description = "Federation Integration Contract"
    _order = "direction, code"

    DIRECTION_SELECTION = [
        ("outbound", "Outbound"),
        ("inbound", "Inbound"),
    ]
    TRANSPORT_SELECTION = [
        ("json", "JSON"),
        ("csv", "CSV"),
        ("file", "File"),
    ]
    DEPRECATION_STAGE_SELECTION = [
        ("active", "Active"),
        ("deprecated", "Deprecated"),
        ("sunset", "Sunset"),
    ]

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    version = fields.Char(required=True)
    direction = fields.Selection(DIRECTION_SELECTION, required=True)
    transport = fields.Selection(TRANSPORT_SELECTION, required=True)
    route_hint = fields.Char()
    description = fields.Text()
    required_module = fields.Char(
        help="Optional module name that must be installed before this contract is operational.",
    )
    import_template_id = fields.Many2one(
        "federation.import.template",
        ondelete="set null",
    )
    deprecation_stage = fields.Selection(
        DEPRECATION_STAGE_SELECTION,
        required=True,
        default="active",
    )
    replacement_contract_id = fields.Many2one(
        "federation.integration.contract",
        ondelete="set null",
    )
    sunset_on = fields.Date()
    active = fields.Boolean(default=True)
    subscription_ids = fields.One2many(
        "federation.integration.partner.contract",
        "contract_id",
    )

    _code_unique = models.Constraint(
        "UNIQUE(code)",
        "Integration contract codes must be unique.",
    )

    def _is_available(self):
        self.ensure_one()
        if not self.required_module:
            return True
        return bool(
            self.env["ir.module.module"].sudo().search_count(
                [
                    ("name", "=", self.required_module),
                    ("state", "=", "installed"),
                ],
                limit=1,
            )
        )

    def build_manifest_payload(self, subscription=None):
        self.ensure_one()
        payload = {
            "code": self.code,
            "name": self.name,
            "version": self.version,
            "direction": self.direction,
            "transport": self.transport,
            "route_hint": self.route_hint,
            "description": self.description or "",
            "deprecation_stage": self.deprecation_stage,
            "sunset_on": fields.Date.to_string(self.sunset_on) if self.sunset_on else None,
            "replacement_contract": self.replacement_contract_id.code if self.replacement_contract_id else None,
            "available": self._is_available(),
        }
        if subscription:
            payload["subscription_state"] = subscription.state
            payload["last_used_on"] = (
                fields.Datetime.to_string(subscription.last_used_on)
                if subscription.last_used_on
                else None
            )
        return payload


class FederationIntegrationPartner(models.Model):
    _name = "federation.integration.partner"
    _description = "Federation Integration Partner"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    contact_partner_id = fields.Many2one("res.partner", ondelete="set null")
    auth_token = fields.Char(required=True, copy=False, readonly=True)
    token_last_rotated_on = fields.Datetime(readonly=True)
    last_request_on = fields.Datetime(readonly=True)
    active = fields.Boolean(default=True)
    notes = fields.Text()
    subscription_ids = fields.One2many(
        "federation.integration.partner.contract",
        "partner_id",
    )
    delivery_ids = fields.One2many(
        "federation.integration.delivery",
        "partner_id",
    )

    _code_unique = models.Constraint(
        "UNIQUE(code)",
        "Integration partner codes must be unique.",
    )

    @api.model
    def _generate_auth_token(self):
        return secrets.token_urlsafe(24)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("auth_token", self._generate_auth_token())
            vals.setdefault("token_last_rotated_on", fields.Datetime.now())
        return super().create(vals_list)

    def action_rotate_token(self):
        for record in self:
            record.write(
                {
                    "auth_token": self._generate_auth_token(),
                    "token_last_rotated_on": fields.Datetime.now(),
                }
            )

    def _get_subscription(self, contract_code):
        self.ensure_one()
        return self.subscription_ids.filtered(
            lambda line: line.contract_id.code == contract_code and line.state == "active"
        )[:1]

    @api.model
    def authenticate_partner(self, partner_code, token, contract_code=None):
        partner = self.sudo().search(
            [
                ("code", "=", partner_code),
                ("active", "=", True),
            ],
            limit=1,
        )
        if not partner or partner.auth_token != token:
            raise AccessError("Invalid partner credentials.")

        partner.write({"last_request_on": fields.Datetime.now()})
        subscription = False
        if contract_code:
            subscription = partner._get_subscription(contract_code)
            if not subscription:
                raise AccessError("The partner is not subscribed to this contract.")
            subscription.mark_used()
        return partner, subscription


class FederationIntegrationPartnerContract(models.Model):
    _name = "federation.integration.partner.contract"
    _description = "Federation Integration Partner Contract"
    _order = "partner_id, contract_id"

    STATE_SELECTION = [
        ("active", "Active"),
        ("suspended", "Suspended"),
        ("deprecated", "Deprecated"),
    ]

    partner_id = fields.Many2one(
        "federation.integration.partner",
        required=True,
        ondelete="cascade",
    )
    contract_id = fields.Many2one(
        "federation.integration.contract",
        required=True,
        ondelete="cascade",
    )
    state = fields.Selection(STATE_SELECTION, required=True, default="active")
    notes = fields.Text()
    last_used_on = fields.Datetime(readonly=True)
    direction = fields.Selection(related="contract_id.direction", readonly=True)
    version = fields.Char(related="contract_id.version", readonly=True)
    route_hint = fields.Char(related="contract_id.route_hint", readonly=True)

    _partner_contract_unique = models.Constraint(
        "UNIQUE(partner_id, contract_id)",
        "A partner can only subscribe to a contract once.",
    )

    def mark_used(self):
        self.write({"last_used_on": fields.Datetime.now()})


class FederationIntegrationDelivery(models.Model):
    _name = "federation.integration.delivery"
    _description = "Federation Integration Delivery"
    _order = "received_on desc, id desc"

    STATE_SELECTION = [
        ("staged", "Staged"),
        ("previewed", "Previewed"),
        ("awaiting_approval", "Awaiting Approval"),
        ("approved", "Approved"),
        ("processed", "Processed"),
        ("processed_with_errors", "Processed With Errors"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    RECEIVED_VIA_SELECTION = [
        ("api", "Partner API"),
        ("manual", "Manual"),
    ]

    name = fields.Char(compute="_compute_name", store=True)
    partner_id = fields.Many2one(
        "federation.integration.partner",
        required=True,
        ondelete="restrict",
    )
    contract_id = fields.Many2one(
        "federation.integration.contract",
        required=True,
        ondelete="restrict",
    )
    import_template_id = fields.Many2one(
        "federation.import.template",
        related="contract_id.import_template_id",
        store=True,
        readonly=True,
    )
    governance_job_id = fields.Many2one(
        "federation.import.job",
        ondelete="set null",
        readonly=True,
    )
    attachment_id = fields.Many2one(
        "ir.attachment",
        ondelete="set null",
        readonly=True,
    )
    filename = fields.Char(required=True)
    payload_checksum = fields.Char(required=True, readonly=True)
    source_reference = fields.Char()
    state = fields.Selection(STATE_SELECTION, required=True, default="staged", readonly=True)
    received_via = fields.Selection(RECEIVED_VIA_SELECTION, required=True, default="api")
    received_on = fields.Datetime(required=True, default=fields.Datetime.now, readonly=True)
    previewed_on = fields.Datetime(readonly=True)
    approved_on = fields.Datetime(readonly=True)
    processed_on = fields.Datetime(readonly=True)
    line_count = fields.Integer(readonly=True)
    success_count = fields.Integer(readonly=True)
    error_count = fields.Integer(readonly=True)
    result_message = fields.Text(readonly=True)
    verification_summary = fields.Text(readonly=True)
    notes = fields.Text()

    @api.depends("partner_id", "contract_id", "filename")
    def _compute_name(self):
        for record in self:
            parts = [
                record.partner_id.name or "Partner",
                record.contract_id.code or "contract",
                record.filename or "delivery",
            ]
            record.name = " - ".join(parts)

    @api.constrains("contract_id")
    def _check_contract_direction(self):
        for record in self:
            if record.contract_id.direction != "inbound":
                raise ValidationError("Only inbound contracts can be staged as deliveries.")
            if not record.contract_id.import_template_id:
                raise ValidationError("Inbound contracts must be linked to an import template.")

    @api.model
    def stage_partner_delivery(self, partner, contract, filename, payload_base64, notes=None, source_reference=None):
        if not partner:
            raise ValidationError("Select a partner before staging an inbound delivery.")
        if not contract or contract.direction != "inbound":
            raise ValidationError("The selected contract does not accept inbound deliveries.")
        if not filename:
            raise ValidationError("Inbound deliveries require a filename.")
        if not payload_base64:
            raise ValidationError("Inbound deliveries require a base64-encoded payload.")

        try:
            payload = base64.b64decode(payload_base64, validate=True)
        except (binascii.Error, ValueError) as error:
            raise ValidationError("Inbound payload must be valid base64-encoded content.") from error

        checksum = hashlib.sha256(payload).hexdigest()
        existing = self.sudo().search(
            [
                ("partner_id", "=", partner.id),
                ("contract_id", "=", contract.id),
                ("payload_checksum", "=", checksum),
                ("state", "in", ("staged", "previewed", "awaiting_approval", "approved")),
            ],
            limit=1,
        )
        if existing:
            return existing

        delivery = self.sudo().create(
            {
                "partner_id": partner.id,
                "contract_id": contract.id,
                "filename": filename,
                "payload_checksum": checksum,
                "source_reference": source_reference,
                "notes": notes,
            }
        )
        attachment = self.env["ir.attachment"].sudo().create(
            {
                "name": filename,
                "datas": payload_base64,
                "res_model": delivery._name,
                "res_id": delivery.id,
                "mimetype": "text/csv",
            }
        )
        delivery.write({"attachment_id": attachment.id})
        return delivery

    def action_open_import_wizard(self):
        self.ensure_one()
        if self.state == "cancelled":
            raise ValidationError("Cancelled deliveries cannot be reopened in the import pipeline.")
        if not self.attachment_id or not self.attachment_id.datas:
            raise ValidationError("The staged delivery does not have an attached payload.")
        if not self.import_template_id:
            raise ValidationError("This delivery is not linked to an import template.")

        wizard_model = self.import_template_id.wizard_model
        wizard_env = self.env.get(wizard_model)
        if wizard_env is None:
            raise ValidationError("The import wizard for this delivery is not available.")

        wizard = wizard_env.create(
            {
                "template_id": self.import_template_id.id,
                "upload_file": self.attachment_id.datas,
                "upload_filename": self.filename,
                "dry_run": True,
                "integration_delivery_id": self.id,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": "Preview Partner Delivery",
            "res_model": wizard_model,
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_mark_previewed(self, wizard):
        wizard.ensure_one()
        self.ensure_one()
        self.write(
            {
                "state": "previewed",
                "previewed_on": fields.Datetime.now(),
                "line_count": wizard.line_count,
                "success_count": wizard.success_count,
                "error_count": wizard.error_count,
                "result_message": wizard.result_message,
            }
        )

    def action_mark_awaiting_approval(self, job):
        job.ensure_one()
        self.ensure_one()
        self.write(
            {
                "state": "awaiting_approval",
                "governance_job_id": job.id,
                "verification_summary": job.verification_summary,
            }
        )

    def action_mark_approved(self, job):
        job.ensure_one()
        self.ensure_one()
        self.write(
            {
                "state": "approved",
                "governance_job_id": job.id,
                "approved_on": fields.Datetime.now(),
                "verification_summary": job.verification_summary,
            }
        )

    def action_mark_processed(self, job):
        job.ensure_one()
        self.ensure_one()
        self.write(
            {
                "state": "processed" if job.state == "completed" else "processed_with_errors",
                "governance_job_id": job.id,
                "processed_on": fields.Datetime.now(),
                "line_count": job.line_count,
                "success_count": job.success_count,
                "error_count": job.error_count,
                "result_message": job.execution_result_message or job.preview_result_message,
                "verification_summary": job.verification_summary,
            }
        )

    def action_mark_failed(self, message=None, job=None):
        self.ensure_one()
        values = {
            "state": "failed",
        }
        if message:
            values["result_message"] = message
        if job:
            values["governance_job_id"] = job.id
        self.write(values)