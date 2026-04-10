from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestParticipantReadiness(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.club = cls.env["federation.club"].create({
            "name": "Participant Ready Club",
            "code": "PRC1",
        })
        cls.team = cls.env["federation.team"].create({
            "name": "Participant Ready Team",
            "club_id": cls.club.id,
            "code": "PRT1",
        })
        cls.season = cls.env["federation.season"].create({
            "name": "Participant Ready Season",
            "code": "PRS1",
            "date_start": "2025-01-01",
            "date_end": "2025-12-31",
        })
        cls.rule_set = cls.env["federation.rule.set"].create({
            "name": "Participant Ready Rules",
            "code": "PRR1",
            "squad_min_size": 1,
        })
        cls.env["federation.eligibility.rule"].create({
            "rule_set_id": cls.rule_set.id,
            "name": "Active License Required",
            "eligibility_type": "license_valid",
        })
        cls.tournament = cls.env["federation.tournament"].create({
            "name": "Participant Ready Tournament",
            "code": "PRT-TOUR",
            "season_id": cls.season.id,
            "date_start": "2025-06-01",
            "rule_set_id": cls.rule_set.id,
        })
        cls.player = cls.env["federation.player"].create({
            "first_name": "Eligible",
            "last_name": "Player",
            "gender": "male",
        })

    def test_participant_confirm_requires_ready_active_roster(self):
        participant = self.env["federation.tournament.participant"].create({
            "tournament_id": self.tournament.id,
            "team_id": self.team.id,
        })

        self.assertFalse(participant.ready_for_confirmation)
        self.assertIn("Create and activate a team roster", participant.confirmation_feedback)
        with self.assertRaises(ValidationError):
            participant.action_confirm()

    def test_participant_confirm_succeeds_with_ready_roster(self):
        roster = self.env["federation.team.roster"].create({
            "name": "Participant Ready Roster",
            "team_id": self.team.id,
            "season_id": self.season.id,
            "rule_set_id": self.rule_set.id,
        })
        license_record = self.env["federation.player.license"].create({
            "name": "LIC-PARTICIPANT-1",
            "player_id": self.player.id,
            "season_id": self.season.id,
            "club_id": self.club.id,
            "issue_date": "2025-01-01",
            "expiry_date": "2025-12-31",
            "state": "active",
        })
        self.env["federation.team.roster.line"].create({
            "roster_id": roster.id,
            "player_id": self.player.id,
            "license_id": license_record.id,
        })
        roster.action_activate()

        participant = self.env["federation.tournament.participant"].create({
            "tournament_id": self.tournament.id,
            "team_id": self.team.id,
        })
        participant.action_confirm()

        self.assertTrue(participant.ready_for_confirmation)
        self.assertEqual(participant.state, "confirmed")