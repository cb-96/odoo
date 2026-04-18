import json
from types import SimpleNamespace
from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase

from odoo.addons.sports_federation_import_tools.controllers.integration_api import (
    FederationIntegrationApi,
)


class TestIntegrationApi(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.controller = FederationIntegrationApi()
        cls.contract = cls.env.ref(
            "sports_federation_import_tools.federation_integration_contract_finance_event"
        )
        cls.inbound_contract = cls.env.ref(
            "sports_federation_import_tools.federation_integration_contract_clubs_csv"
        )
        cls.partner = cls.env["federation.integration.partner"].create(
            {
                "name": "API Partner",
                "code": "API_PARTNER",
            }
        )
        cls.env["federation.integration.partner.contract"].create(
            {
                "partner_id": cls.partner.id,
                "contract_id": cls.contract.id,
            }
        )
        cls.env["federation.integration.partner.contract"].create(
            {
                "partner_id": cls.partner.id,
                "contract_id": cls.inbound_contract.id,
            }
        )
        cls.raw_token = cls.partner._issue_auth_token()

    def _make_request(self, headers=None, params=None, json_payload=None):
        return SimpleNamespace(
            httprequest=SimpleNamespace(
                headers=headers or {},
                get_json=lambda silent=True: json_payload,
            ),
            params=params or {},
            env=self.env,
        )

    def test_get_credentials_accepts_custom_headers(self):
        request_stub = self._make_request(
            headers={
                "X-Federation-Partner-Code": self.partner.code,
                "X-Federation-Partner-Token": self.raw_token,
            }
        )

        with patch(
            "odoo.addons.sports_federation_import_tools.controllers.integration_api.request",
            request_stub,
        ):
            partner_code, token = self.controller._get_credentials()

        self.assertEqual(partner_code, self.partner.code)
        self.assertEqual(token, self.raw_token)

    def test_get_credentials_accepts_bearer_authorization(self):
        request_stub = self._make_request(
            headers={
                "X-Federation-Partner-Code": self.partner.code,
                "Authorization": f"Bearer {self.raw_token}",
            }
        )

        with patch(
            "odoo.addons.sports_federation_import_tools.controllers.integration_api.request",
            request_stub,
        ):
            partner_code, token = self.controller._get_credentials()

        self.assertEqual(partner_code, self.partner.code)
        self.assertEqual(token, self.raw_token)

    def test_get_credentials_rejects_query_string_credentials(self):
        request_stub = self._make_request(
            params={
                "partner_code": self.partner.code,
                "access_token": self.raw_token,
            }
        )

        with patch(
            "odoo.addons.sports_federation_import_tools.controllers.integration_api.request",
            request_stub,
        ), self.assertRaises(AccessError):
            self.controller._get_credentials()

    def test_get_credentials_rejects_mixed_header_and_query_credentials(self):
        request_stub = self._make_request(
            headers={
                "X-Federation-Partner-Code": self.partner.code,
                "X-Federation-Partner-Token": self.raw_token,
            },
            params={
                "access_token": "leaked-token",
            },
        )

        with patch(
            "odoo.addons.sports_federation_import_tools.controllers.integration_api.request",
            request_stub,
        ), self.assertRaises(AccessError):
            self.controller._get_credentials()

    def test_contracts_route_returns_401_for_query_string_credentials(self):
        request_stub = self._make_request(
            params={
                "partner_code": self.partner.code,
                "access_token": self.raw_token,
            }
        )

        with patch(
            "odoo.addons.sports_federation_import_tools.controllers.integration_api.request",
            request_stub,
        ):
            response = self.controller.integration_contracts()

        self.assertEqual(response.status_code, 401)
        payload = json.loads(response.get_data(as_text=True))
        self.assertEqual(payload["error_code"], "access_denied")
        self.assertIn("headers only", payload["error"])

    def test_inbound_route_returns_400_for_disallowed_payload_extension(self):
        request_stub = self._make_request(
            headers={
                "X-Federation-Partner-Code": self.partner.code,
                "X-Federation-Partner-Token": self.raw_token,
            },
            json_payload={
                "filename": "clubs.json",
                "payload_base64": "bmFtZTtjb2RlClN0YWdlZCBDbHViO1NDMDAx",
            },
        )

        with patch(
            "odoo.addons.sports_federation_import_tools.controllers.integration_api.request",
            request_stub,
        ):
            response = self.controller.integration_stage_inbound_delivery(
                self.inbound_contract.code
            )

        self.assertEqual(response.status_code, 400)
        payload = json.loads(response.get_data(as_text=True))
        self.assertEqual(payload["error_code"], "data_validation")
        self.assertIn("extensions", payload["error"])