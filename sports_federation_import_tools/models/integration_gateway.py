import base64
import binascii
import hashlib
import hmac
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
        """Return whether the record is available."""
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
        """Build manifest payload."""
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

    TOKEN_HASH_PREFIX = "pbkdf2_sha256"
    TOKEN_HASH_ROUNDS = 390000
    TOKEN_SALT_BYTES = 16

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    contact_partner_id = fields.Many2one("res.partner", ondelete="set null")
    auth_token = fields.Char(copy=False, readonly=True)
    auth_token_last4 = fields.Char(readonly=True, copy=False)
    token_last_rotated_on = fields.Datetime(readonly=True)
    token_rotation_required = fields.Boolean(readonly=True, default=False, copy=False)
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

    def _register_hook(self):
        """Migrate legacy plaintext tokens into hashed storage."""
        result = super()._register_hook()
        self._migrate_plaintext_tokens()
        return result

    @api.model
    def _generate_auth_token(self):
        """Handle generate auth token."""
        return secrets.token_urlsafe(24)

    @api.model
    def _auth_token_is_hashed(self, stored_token):
        """Return whether a stored token already uses the hash format."""
        return bool(stored_token and stored_token.startswith(f"{self.TOKEN_HASH_PREFIX}$"))

    @api.model
    def _hash_auth_token(self, token, salt=None, rounds=None):
        """Hash a raw token before persisting it."""
        if not token:
            raise ValidationError("Integration tokens cannot be empty.")
        salt = salt or secrets.token_hex(self.TOKEN_SALT_BYTES)
        rounds = rounds or self.TOKEN_HASH_ROUNDS
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            token.encode("utf-8"),
            salt.encode("utf-8"),
            rounds,
        )
        encoded_digest = base64.urlsafe_b64encode(digest).decode("ascii")
        return f"{self.TOKEN_HASH_PREFIX}${rounds}${salt}${encoded_digest}"

    @api.model
    def _verify_stored_auth_token(self, stored_token, candidate_token):
        """Verify a candidate token against the stored representation."""
        if not stored_token or not candidate_token:
            return False
        if not self._auth_token_is_hashed(stored_token):
            return hmac.compare_digest(stored_token, candidate_token)

        try:
            _prefix, rounds, salt, encoded_digest = stored_token.split("$", 3)
            rounds = int(rounds)
        except (TypeError, ValueError):
            return False

        digest = hashlib.pbkdf2_hmac(
            "sha256",
            candidate_token.encode("utf-8"),
            salt.encode("utf-8"),
            rounds,
        )
        candidate_digest = base64.urlsafe_b64encode(digest).decode("ascii")
        return hmac.compare_digest(candidate_digest, encoded_digest)

    @api.model
    def _prepare_auth_token_values(self, token, rotation_required=False, mark_rotated=True):
        """Build storage values for a raw token."""
        values = {
            "auth_token": self._hash_auth_token(token),
            "auth_token_last4": token[-4:] if len(token) >= 4 else token,
            "token_rotation_required": rotation_required,
        }
        if mark_rotated:
            values["token_last_rotated_on"] = fields.Datetime.now()
        return values

    def _issue_auth_token(self, rotation_required=False):
        """Generate, hash, persist, and return a new raw token."""
        self.ensure_one()
        raw_token = self._generate_auth_token()
        self.write(
            self._prepare_auth_token_values(
                raw_token,
                rotation_required=rotation_required,
                mark_rotated=True,
            )
        )
        return raw_token

    @api.model
    def _migrate_plaintext_tokens(self):
        """Hash legacy plaintext tokens and flag them for scheduled rotation."""
        partners = self.sudo().with_context(active_test=False).search([
            ("auth_token", "!=", False),
        ])
        for partner in partners:
            if partner._auth_token_is_hashed(partner.auth_token):
                continue
            partner.write(
                partner._prepare_auth_token_values(
                    partner.auth_token,
                    rotation_required=True,
                    mark_rotated=False,
                )
            )

    @api.model_create_multi
    def create(self, vals_list):
        """Create records with module-specific defaults and side effects."""
        prepared_vals_list = []
        for vals in vals_list:
            prepared_vals = dict(vals)
            raw_token = prepared_vals.get("auth_token")
            if raw_token and not self._auth_token_is_hashed(raw_token):
                prepared_vals.update(
                    self._prepare_auth_token_values(
                        raw_token,
                        rotation_required=bool(prepared_vals.get("token_rotation_required", False)),
                        mark_rotated=True,
                    )
                )
            prepared_vals_list.append(prepared_vals)
        return super().create(prepared_vals_list)

    def write(self, vals):
        """Hash any raw tokens before they are persisted."""
        prepared_vals = dict(vals)
        raw_token = prepared_vals.get("auth_token")
        if raw_token and not self._auth_token_is_hashed(raw_token):
            prepared_vals.update(
                self._prepare_auth_token_values(
                    raw_token,
                    rotation_required=bool(prepared_vals.get("token_rotation_required", False)),
                    mark_rotated=True,
                )
            )
        return super().write(prepared_vals)

    def action_rotate_token(self):
        """Execute the rotate token action."""
        self.ensure_one()
        if not self.env.user.has_group("sports_federation_base.group_federation_manager"):
            raise AccessError("Only federation managers can rotate integration tokens.")

        raw_token = self._issue_auth_token(rotation_required=False)
        wizard = self.env["federation.integration.partner.token.wizard"].create(
            {
                "partner_id": self.id,
                "issued_token": raw_token,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": "Partner Token",
            "res_model": wizard._name,
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def _get_subscription(self, contract_code):
        """Return subscription."""
        self.ensure_one()
        return self.subscription_ids.filtered(
            lambda line: line.contract_id.code == contract_code and line.state == "active"
        )[:1]

    @api.model
    def authenticate_partner(self, partner_code, token, contract_code=None):
        """Handle authenticate partner."""
        partner = self.sudo().search(
            [
                ("code", "=", partner_code),
                ("active", "=", True),
            ],
            limit=1,
        )
        if not partner or not partner._verify_stored_auth_token(partner.auth_token, token):
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
        """Handle mark used."""
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
        """Compute name."""
        for record in self:
            parts = [
                record.partner_id.name or "Partner",
                record.contract_id.code or "contract",
                record.filename or "delivery",
            ]
            record.name = " - ".join(parts)

    @api.constrains("contract_id")
    def _check_contract_direction(self):
        """Validate contract direction."""
        for record in self:
            if record.contract_id.direction != "inbound":
                raise ValidationError("Only inbound contracts can be staged as deliveries.")
            if not record.contract_id.import_template_id:
                raise ValidationError("Inbound contracts must be linked to an import template.")

    @api.model
    def stage_partner_delivery(
        self,
        partner,
        contract,
        filename,
        payload_base64,
        content_type=None,
        notes=None,
        source_reference=None,
    ):
        """Handle stage partner delivery."""
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

        upload = self.env["federation.attachment.policy"].validate_upload(
            "integration_inbound_csv",
            filename,
            payload,
            mimetype=content_type,
        )
        checksum = upload["checksum"]
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
                "name": upload["filename"],
                "datas": payload_base64,
                "res_model": delivery._name,
                "res_id": delivery.id,
                "mimetype": upload["mimetype"],
            }
        )
        delivery.write({"attachment_id": attachment.id})
        return delivery

    def action_open_import_wizard(self):
        """Execute the open import wizard action."""
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
        """Execute the cancel action."""
        self.write({"state": "cancelled"})

    def action_mark_previewed(self, wizard):
        """Execute the mark previewed action."""
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
        """Execute the mark awaiting approval action."""
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
        """Execute the mark approved action."""
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
        """Execute the mark processed action."""
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
        """Execute the mark failed action."""
        self.ensure_one()
        values = {
            "state": "failed",
        }
        if message:
            values["result_message"] = message
        if job:
            values["governance_job_id"] = job.id
        self.write(values)