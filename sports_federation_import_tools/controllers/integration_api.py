import csv
import io
import json
import logging

from odoo import http
from odoo.addons.sports_federation_base.exceptions import AttachmentScanVerificationError
from odoo.addons.sports_federation_base.models.failure_feedback import build_failure_feedback
from odoo.exceptions import AccessError, ValidationError
from odoo.http import Response, request


_logger = logging.getLogger(__name__)


class FederationIntegrationApi(http.Controller):
    def _json_response(self, payload, status=200, headers=None):
        """Handle JSON response."""
        return Response(
            json.dumps(payload),
            status=status,
            content_type="application/json; charset=utf-8",
            headers=headers or [],
        )

    def _json_error_response(self, status, error=None, detail=None, default_category="unexpected_bug"):
        """Return a typed JSON error payload with sanitized operator detail."""
        failure_category, operator_message = build_failure_feedback(
            error=error,
            detail=detail,
            default_category=default_category,
        )
        return self._json_response(
            {
                "error": operator_message,
                "error_code": failure_category,
            },
            status=status,
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

    def _get_remote_addr(self):
        """Return the best-effort caller IP for integration throttling."""
        headers = getattr(request.httprequest, "headers", {}) or {}
        forwarded_for = (headers.get("X-Forwarded-For") or "").split(",", 1)[0].strip()
        remote_addr = forwarded_for or (getattr(request.httprequest, "remote_addr", "") or "").strip()
        return remote_addr or "unknown"

    def _get_rate_limit_subject(self):
        """Key partner traffic by partner code, then fall back to caller IP."""
        headers = getattr(request.httprequest, "headers", {}) or {}
        partner_code = (headers.get("X-Federation-Partner-Code") or "").strip()
        if partner_code:
            return f"partner:{partner_code}"
        return f"ip:{self._get_remote_addr()}"

    def _rate_limit_response(self, scope):
        """Return a 429 response when the caller exceeds the route limit."""
        decision = request.env["federation.request.rate.limit"].sudo().consume(
            scope,
            self._get_rate_limit_subject(),
        )
        if decision["allowed"]:
            return False
        return self._json_response(
            {
                "error": f"Too many requests. Retry after {decision['retry_after']} seconds.",
                "error_code": "retryable_delivery",
            },
            status=429,
            headers=[("Retry-After", str(decision["retry_after"]))],
        )

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
        blocked_response = self._rate_limit_response("integration_contracts")
        if blocked_response:
            return blocked_response
        try:
            partner, _subscription = self._authenticate()
        except (AccessError, ValidationError) as error:
            return self._json_error_response(status=401, error=error)

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
        blocked_response = self._rate_limit_response("integration_finance_events")
        if blocked_response:
            return blocked_response
        try:
            partner, _subscription = self._authenticate(contract_code="finance_event_v1")
        except (AccessError, ValidationError) as error:
            return self._json_error_response(status=401, error=error)

        FinanceEvent = request.env.get("federation.finance.event")
        if FinanceEvent is None:
            return self._json_error_response(
                status=404,
                detail="The finance export contract is not available in this database.",
                default_category="configuration_error",
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
        blocked_response = self._rate_limit_response("integration_inbound_deliveries")
        if blocked_response:
            return blocked_response
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
            return self._json_error_response(status=401, error=error)
        except ValidationError as error:
            return self._json_error_response(status=400, error=error)
        except AttachmentScanVerificationError as error:
            return self._json_error_response(
                status=503,
                error=error,
                default_category="retryable_delivery",
            )
        except Exception as error:
            _logger.exception("Inbound delivery staging failed for contract %s", contract_code)
            return self._json_error_response(status=500, error=error)

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