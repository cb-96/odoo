from odoo.tests import TransactionCase


class TestReporting(TransactionCase):
    """Test cases for reporting module."""

    @classmethod
    def setUpClass(cls):
        """Set up shared test data for the test case."""
        super().setUpClass()
        # Create test club
        cls.club = cls.env["federation.club"].create({
            "name": "Test Club",
            "code": "TC001",
        })
        # Create test season
        cls.season = cls.env["federation.season"].create({
            "name": "Test Season",
            "code": "TS2024",
            "date_start": "2024-09-01",
            "date_end": "2025-06-30",
        })
        # Create test referee
        cls.referee = cls.env["federation.referee"].create({
            "name": "Test Referee",
            "email": "referee@example.com",
        })
        # Create test fee type
        cls.fee_type = cls.env["federation.fee.type"].create({
            "name": "Test Fee",
            "code": "TESTFEE",
            "category": "registration",
            "default_amount": 100.00,
        })

    def test_participation_report_has_rows(self):
        """Test that participation report returns data."""
        report = self.env["federation.report.participation"]
        # Ensure view is created
        report.init()
        # Search should work
        rows = report.search([])
        self.assertIsNotNone(rows)

    def test_officiating_report_has_rows(self):
        """Test that officiating report returns data."""
        report = self.env["federation.report.officiating"]
        # Ensure view is created
        report.init()
        # Search should work
        rows = report.search([])
        self.assertIsNotNone(rows)

    def test_compliance_report_has_rows(self):
        """Test that compliance report returns data."""
        report = self.env["federation.report.compliance"]
        # Ensure view is created
        report.init()
        # Search should work
        rows = report.search([])
        self.assertIsNotNone(rows)

    def test_finance_report_has_rows(self):
        """Test that finance report returns data."""
        report = self.env["federation.report.finance"]
        # Ensure view is created
        report.init()
        # Search should work
        rows = report.search([])
        self.assertIsNotNone(rows)