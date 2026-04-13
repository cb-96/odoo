from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FederationFinanceEvent(models.Model):
    _name = "federation.finance.event"
    _description = "Federation Finance Event"
    _order = "create_date desc"

    HANDOFF_STATE_SELECTION = [
        ("pending_export", "Pending Export"),
        ("exported", "Exported"),
        ("reconciled", "Reconciled"),
        ("closed", "Closed"),
    ]
    EXPORT_SCHEMA_VERSION = "finance_event_v1"

    name = fields.Char(required=True)
    fee_type_id = fields.Many2one(
        "federation.fee.type",
        required=True,
        ondelete="restrict",
    )
    event_type = fields.Selection(
        [
            ("charge", "Charge"),
            ("credit", "Credit"),
            ("reimbursement", "Reimbursement"),
        ],
        required=True,
    )
    amount = fields.Monetary(
        currency_field="currency_id",
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("settled", "Settled"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
    )
    source_model = fields.Char(required=True)
    source_res_id = fields.Integer(required=True)
    partner_id = fields.Many2one(
        "res.partner",
        ondelete="set null",
    )
    club_id = fields.Many2one(
        "federation.club",
        ondelete="set null",
    )
    player_id = fields.Many2one(
        "federation.player",
        ondelete="set null",
    )
    referee_id = fields.Many2one(
        "federation.referee",
        ondelete="set null",
    )
    invoice_ref = fields.Char()
    external_ref = fields.Char()
    notes = fields.Text()
    handoff_state = fields.Selection(
        HANDOFF_STATE_SELECTION,
        default="pending_export",
        required=True,
    )
    export_schema_version = fields.Char(
        default=EXPORT_SCHEMA_VERSION,
        required=True,
        readonly=True,
    )
    accounting_batch_ref = fields.Char()
    reconciliation_ref = fields.Char()
    closure_note = fields.Text()
    exported_on = fields.Datetime(readonly=True)
    exported_by_id = fields.Many2one("res.users", readonly=True)
    reconciled_on = fields.Datetime(readonly=True)
    reconciled_by_id = fields.Many2one("res.users", readonly=True)
    closed_on = fields.Datetime(readonly=True)
    closed_by_id = fields.Many2one("res.users", readonly=True)

    _fee_source_unique = models.Constraint('unique (fee_type_id, source_model, source_res_id)', 'A finance event already exists for this fee type and source record.')

    @api.constrains("amount")
    def _check_amount(self):
        for record in self:
            if record.amount < 0:
                raise ValidationError("Amount must be >= 0.")

    @api.constrains("source_model")
    def _check_source_model(self):
        for record in self:
            if not record.source_model:
                raise ValidationError("Source model must not be empty.")

    @api.constrains("source_res_id")
    def _check_source_res_id(self):
        for record in self:
            if record.source_res_id <= 0:
                raise ValidationError("Source res ID must be > 0.")

    def action_confirm(self):
        for record in self:
            if record.state != "draft":
                raise ValidationError("Only draft events can be confirmed.")
            record.write({"state": "confirmed"})
            record.flush_recordset()
            Dispatcher = record.env.get("federation.notification.dispatcher")
            if Dispatcher is not None:
                Dispatcher.send_finance_event_confirmed(record)

    def action_settle(self):
        for record in self:
            if record.state != "confirmed":
                raise ValidationError("Only confirmed events can be settled.")
            record.write({"state": "settled"})
            record.flush_recordset()

    def action_cancel(self):
        for record in self:
            if record.state == "settled":
                raise ValidationError("Settled events cannot be cancelled.")
            record.write(
                {
                    "state": "cancelled",
                    "handoff_state": "closed",
                    "closed_on": fields.Datetime.now(),
                    "closed_by_id": self.env.user.id,
                }
            )
            record.flush_recordset()

    def action_mark_exported(self):
        for record in self:
            if record.state not in ("confirmed", "settled"):
                raise ValidationError(
                    "Only confirmed or settled finance events can be exported."
                )
            if record.handoff_state == "closed":
                raise ValidationError("Closed handoff records cannot be exported again.")
            record.write(
                {
                    "handoff_state": "exported",
                    "exported_on": fields.Datetime.now(),
                    "exported_by_id": self.env.user.id,
                }
            )
            record.flush_recordset()

    def action_mark_reconciled(self):
        for record in self:
            if record.state != "settled":
                raise ValidationError(
                    "Only settled finance events can be marked as reconciled."
                )
            if record.handoff_state not in ("exported", "reconciled"):
                raise ValidationError(
                    "Mark the event as exported before reconciling it with the accounting system."
                )
            record.write(
                {
                    "handoff_state": "reconciled",
                    "reconciled_on": fields.Datetime.now(),
                    "reconciled_by_id": self.env.user.id,
                }
            )
            record.flush_recordset()

    def action_close_handoff(self):
        for record in self:
            if record.state != "settled":
                raise ValidationError(
                    "Only settled finance events can close the accounting handoff."
                )
            if record.handoff_state != "reconciled":
                raise ValidationError(
                    "Reconcile the event before closing the accounting handoff."
                )
            record.write(
                {
                    "handoff_state": "closed",
                    "closed_on": fields.Datetime.now(),
                    "closed_by_id": self.env.user.id,
                }
            )
            record.flush_recordset()

    @api.model
    def _build_external_ref(self, source_record, fee_type):
        fee_code = (fee_type.code or str(fee_type.id)).upper()
        model_token = source_record._name.replace(".", "_")
        return f"{fee_code}-{model_token}-{source_record.id}"

    @api.model
    def _prepare_from_source_vals(
        self,
        source_record,
        fee_type,
        amount=None,
        event_type="charge",
        partner=None,
        note=None,
        extra_vals=None,
    ):
        if amount is None:
            amount = fee_type.default_amount

        vals = {
            "name": f"{fee_type.name} - {source_record.name if hasattr(source_record, 'name') else source_record.id}",
            "fee_type_id": fee_type.id,
            "event_type": event_type,
            "amount": amount,
            "currency_id": fee_type.currency_id.id or self.env.company.currency_id.id,
            "source_model": source_record._name,
            "source_res_id": source_record.id,
            "partner_id": partner.id if partner else False,
            "external_ref": self._build_external_ref(source_record, fee_type),
            "export_schema_version": self.EXPORT_SCHEMA_VERSION,
            "notes": note,
        }

        # Try to set related fields if available on source_record
        if source_record._name == "federation.club":
            vals["club_id"] = source_record.id
        elif hasattr(source_record, "club_id") and source_record.club_id:
            vals["club_id"] = source_record.club_id.id
        if source_record._name == "federation.player":
            vals["player_id"] = source_record.id
        elif hasattr(source_record, "player_id") and source_record.player_id:
            vals["player_id"] = source_record.player_id.id
        if source_record._name == "federation.referee":
            vals["referee_id"] = source_record.id
        elif hasattr(source_record, "referee_id") and source_record.referee_id:
            vals["referee_id"] = source_record.referee_id.id

        if extra_vals:
            for key, value in extra_vals.items():
                if key in self._fields:
                    vals[key] = value

        return vals

    @api.model
    def ensure_from_source(
        self,
        source_record,
        fee_type,
        amount=None,
        event_type="charge",
        partner=None,
        note=None,
        extra_vals=None,
        update_existing=False,
    ):
        existing = self.search(
            [
                ("fee_type_id", "=", fee_type.id),
                ("source_model", "=", source_record._name),
                ("source_res_id", "=", source_record.id),
            ],
            limit=1,
        )
        vals = self._prepare_from_source_vals(
            source_record,
            fee_type,
            amount=amount,
            event_type=event_type,
            partner=partner,
            note=note,
            extra_vals=extra_vals,
        )

        if existing:
            if update_existing and existing.state in ("draft", "cancelled"):
                update_vals = {}
                for field_name in (
                    "name",
                    "amount",
                    "currency_id",
                    "partner_id",
                    "club_id",
                    "player_id",
                    "referee_id",
                    "external_ref",
                    "notes",
                ):
                    value = vals.get(field_name)
                    existing_value = existing[field_name]
                    if self._fields[field_name].type == "many2one":
                        existing_value = existing_value.id
                    if value not in (False, None, "") and existing_value != value:
                        update_vals[field_name] = value
                if existing.state == "cancelled":
                    update_vals.update(
                        {
                            "state": "draft",
                            "handoff_state": "pending_export",
                            "closed_on": False,
                            "closed_by_id": False,
                        }
                    )
                if update_vals:
                    existing.write(update_vals)
            elif not existing.external_ref and vals.get("external_ref"):
                existing.external_ref = vals["external_ref"]
            return existing

        return self.create(vals)

    @api.model
    def get_handoff_export_headers(self):
        return [
            "Schema Version",
            "Event ID",
            "Name",
            "State",
            "Handoff State",
            "Event Type",
            "Amount",
            "Currency",
            "Fee Type",
            "Accounting Batch Ref",
            "Reconciliation Ref",
            "Invoice Ref",
            "External Ref",
            "Source Model",
            "Source Record ID",
            "Partner",
            "Club",
            "Player",
            "Referee",
            "Exported On",
            "Reconciled On",
            "Closed On",
            "Closure Note",
        ]

    def get_handoff_export_row(self):
        self.ensure_one()
        return [
            self.export_schema_version,
            self.id,
            self.name,
            self.state,
            self.handoff_state,
            self.event_type,
            self.amount,
            self.currency_id.name if self.currency_id else "",
            self.fee_type_id.code if self.fee_type_id else "",
            self.accounting_batch_ref or "",
            self.reconciliation_ref or "",
            self.invoice_ref or "",
            self.external_ref or "",
            self.source_model,
            self.source_res_id,
            self.partner_id.display_name if self.partner_id else "",
            self.club_id.name if self.club_id else "",
            self.player_id.display_name if self.player_id else "",
            self.referee_id.display_name if self.referee_id else "",
            fields.Datetime.to_string(self.exported_on) if self.exported_on else "",
            fields.Datetime.to_string(self.reconciled_on) if self.reconciled_on else "",
            fields.Datetime.to_string(self.closed_on) if self.closed_on else "",
            self.closure_note or "",
        ]

    @api.model
    def create_from_source(
        self,
        source_record,
        fee_type,
        amount=None,
        event_type="charge",
        partner=None,
        note=None,
        extra_vals=None,
    ):
        """Helper to create finance event from a source record.

        Args:
            source_record: The record that triggers this finance event.
            fee_type: federation.fee.type record.
            amount: Optional amount override; defaults to fee_type.default_amount.
            event_type: "charge", "credit", or "reimbursement".
            partner: Optional res.partner record.
            note: Optional notes.

        Returns:
            The created federation.finance.event record.
        """
        return self.create(
            self._prepare_from_source_vals(
                source_record,
                fee_type,
                amount=amount,
                event_type=event_type,
                partner=partner,
                note=note,
                extra_vals=extra_vals,
            )
        )