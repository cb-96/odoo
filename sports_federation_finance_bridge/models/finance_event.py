from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FederationFinanceEvent(models.Model):
    _name = "federation.finance.event"
    _description = "Federation Finance Event"
    _order = "create_date desc"

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

    _sql_constraints = [
        (
            "unique_finance_event",
            "UNIQUE(fee_type_id, source_model, source_res_id)",
            "A finance event already exists for this fee type and source record.",
        ),
    ]

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
            record.state = "confirmed"

    def action_settle(self):
        for record in self:
            if record.state != "confirmed":
                raise ValidationError("Only confirmed events can be settled.")
            record.state = "settled"

    def action_cancel(self):
        for record in self:
            if record.state == "settled":
                raise ValidationError("Settled events cannot be cancelled.")
            record.state = "cancelled"

    @api.model
    def create_from_source(
        self, source_record, fee_type, amount=None, event_type="charge", partner=None, note=None
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
            "notes": note,
        }

        # Try to set related fields if available on source_record
        if hasattr(source_record, "club_id") and source_record.club_id:
            vals["club_id"] = source_record.club_id.id
        if hasattr(source_record, "player_id") and source_record.player_id:
            vals["player_id"] = source_record.player_id.id
        if hasattr(source_record, "referee_id") and source_record.referee_id:
            vals["referee_id"] = source_record.referee_id.id

        return self.create(vals)