import csv
import io
import json

from odoo import http
from odoo.exceptions import AccessError, ValidationError
from odoo.http import Response, request


class FederationIntegrationApi(http.Controller):
    def _json_response(self, payload, status=200):
        """Handle JSON response."""
        return Response(
            json.dumps(payload),
            status=status,
            content_type="application/json; charset=utf-8",
        )

    def _get_bearer_token(self, headers):
        """Extract a bearer token from the authorization header."""
        authorization = (headers.get("Authorization") or "").strip()
        if not authorization:
            return ""

        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise AccessError("Authorization headers must use the Bearer scheme.")
        return token.strip()

    def _get_credentials(self):
        """Return credentials."""
        headers = request.httprequest.headers
        if request.params.get("partner_code") or request.params.get("access_token"):
            raise AccessError("Partner credentials must be supplied via request headers only.")
        partner_code = (headers.get("X-Federation-Partner-Code") or "").strip()
        token = (headers.get("X-Federation-Partner-Token") or "").strip()
        if not token:
            token = self._get_bearer_token(headers)
        if not partner_code or not token:
            raise AccessError("Partner code and token are required in request headers.")
        return partner_code, token

    def _authenticate(self, contract_code=None):
        """Handle authenticate."""
        partner_code, token = self._get_credentials()
        return request.env["federation.integration.partner"].sudo().authenticate_partner(
            partner_code,
            token,
            contract_code=contract_code,
        )

    @http.route(
        ["/integration/v1/contracts"],
        type="http",
        auth="public",
        website=False,
        methods=["GET"],
        csrf=False,
    )
    def integration_contracts(self, **kw):
        """Handle integration contracts."""
        try:
            partner, _subscription = self._authenticate()
        except (AccessError, ValidationError) as error:
            return self._json_response({"error": str(error)}, status=401)

        subscriptions = partner.subscription_ids.filtered(
            lambda line: line.state == "active" and line.contract_id.active
        )
        return self._json_response(
            {
                "partner": {
                    "code": partner.code,
                    "name": partner.name,
                },
                "contracts": [
                    line.contract_id.build_manifest_payload(subscription=line)
                    for line in subscriptions
                ],
            }
        )

    @http.route(
        ["/integration/v1/outbound/finance/events"],
        type="http",
        auth="public",
        website=False,
        methods=["GET"],
        csrf=False,
    )
    def integration_finance_events(self, **kw):
        """Handle integration finance events."""
        try:
            partner, _subscription = self._authenticate(contract_code="finance_event_v1")
        except (AccessError, ValidationError) as error:
            return self._json_response({"error": str(error)}, status=401)

        FinanceEvent = request.env.get("federation.finance.event")
        if FinanceEvent is None:
            return self._json_response(
                {"error": "The finance export contract is not available in this database."},
                status=404,
            )

        events = FinanceEvent.sudo().search([], order="create_date desc, id desc")
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(FinanceEvent.get_handoff_export_headers())
        for event in events:
            writer.writerow(event.get_handoff_export_row())

        return Response(
            output.getvalue(),
            content_type="text/csv; charset=utf-8",
            headers=[
                ("Content-Disposition", 'attachment; filename="finance_events_partner_handoff.csv"'),
                ("X-Federation-Contract", "finance_event_v1"),
                ("X-Federation-Contract-Version", FinanceEvent.EXPORT_SCHEMA_VERSION),
                ("X-Federation-Partner-Code", partner.code),
            ],
        )

    @http.route(
        ["/integration/v1/inbound/<string:contract_code>/deliveries"],
        type="http",
        auth="public",
        website=False,
        methods=["POST"],
        csrf=False,
    )
    def integration_stage_inbound_delivery(self, contract_code, **kw):
        """Handle integration stage inbound delivery."""
        try:
            partner, subscription = self._authenticate(contract_code=contract_code)
            payload = request.httprequest.get_json(silent=True) or {}
            if not isinstance(payload, dict):
                raise ValidationError("Inbound delivery requests must use a JSON object body.")

            delivery = request.env["federation.integration.delivery"].sudo().stage_partner_delivery(
                partner=partner,
                contract=subscription.contract_id,
                filename=(payload.get("filename") or "").strip(),
                payload_base64=(payload.get("payload_base64") or "").strip(),
                content_type=(payload.get("content_type") or "").strip() or False,
                notes=(payload.get("notes") or "").strip() or False,
                source_reference=(payload.get("source_reference") or "").strip() or False,
            )
        except AccessError as error:
            return self._json_response({"error": str(error)}, status=401)
        except ValidationError as error:
            return self._json_response({"error": str(error)}, status=400)

        return self._json_response(
            {
                "delivery": {
                    "id": delivery.id,
                    "name": delivery.name,
                    "partner_code": delivery.partner_id.code,
                    "contract_code": delivery.contract_id.code,
                    "state": delivery.state,
                    "filename": delivery.filename,
                    "payload_checksum": delivery.payload_checksum,
                    "route_hint": delivery.contract_id.route_hint,
                }
            },
            status=201,
        )