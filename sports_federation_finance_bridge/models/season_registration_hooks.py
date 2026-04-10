from odoo import api, models


class FederationSeasonRegistrationFinanceHooks(models.Model):
    _inherit = "federation.season.registration"

    @api.model_create_multi
    def create(self, vals_list):
        registrations = super().create(vals_list)
        registrations.filtered(lambda rec: rec.state == "confirmed")._ensure_registration_finance_event()
        return registrations

    def write(self, vals):
        should_create_events = vals.get("state") == "confirmed"
        res = super().write(vals)
        if should_create_events:
            self.filtered(lambda rec: rec.state == "confirmed")._ensure_registration_finance_event()
        return res

    def _ensure_registration_finance_event(self):
        finance_event_model = self.env["federation.finance.event"]
        for registration in self:
            fee_type = registration._get_registration_fee_type()
            existing_event = finance_event_model.search(
                [
                    ("fee_type_id", "=", fee_type.id),
                    ("source_model", "=", registration._name),
                    ("source_res_id", "=", registration.id),
                ],
                limit=1,
            )
            if existing_event:
                continue

            partner = False
            if "partner_id" in registration._fields:
                partner = registration.partner_id

            finance_event_model.create_from_source(
                registration,
                fee_type,
                event_type="charge",
                partner=partner,
                note=(
                    "Auto: season registration confirmed for "
                    f"{registration.team_id.display_name} in {registration.season_id.display_name}"
                ),
            )

    def _get_registration_fee_type(self):
        self.ensure_one()
        fee_type = self.env["federation.fee.type"].search(
            [("code", "=", "season_registration")],
            limit=1,
        )
        if fee_type:
            return fee_type

        return self.env["federation.fee.type"].create(
            {
                "name": "Season Registration Fee",
                "code": "season_registration",
                "category": "registration",
                "default_amount": 0.0,
                "currency_id": self.env.company.currency_id.id,
            }
        )