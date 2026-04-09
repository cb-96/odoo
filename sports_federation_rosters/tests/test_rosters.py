from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestRosters(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.club = cls.env["federation.club"].create({
            "name": "Test Club",
            "code": "TEST",
        })
        cls.team = cls.env["federation.team"].create({
            "name": "Test Team",
            "club_id": cls.club.id,
            "code": "TT",
        })
        cls.season = cls.env["federation.season"].create({
            "name": "Test Season",
            "code": "TS2024",
            "date_start": "2024-01-01",
            "date_end": "2024-12-31",
        })
        cls.competition = cls.env["federation.competition"].create({
            "name": "Test Competition",
            "code": "TC",
        })
        cls.player1 = cls.env["federation.player"].create({
            "name": "Player One",
            "first_name": "Player",
            "last_name": "One",
            "gender": "male",
        })
        cls.player2 = cls.env["federation.player"].create({
            "name": "Player Two",
            "first_name": "Player",
            "last_name": "Two",
            "gender": "male",
        })

    def test_create_roster(self):
        """Test basic roster creation."""
        roster = self.env["federation.team.roster"].create({
            "name": "Test Roster",
            "team_id": self.team.id,
            "season_id": self.season.id,
            "competition_id": self.competition.id,
        })
        self.assertTrue(roster.id)
        self.assertEqual(roster.status, "draft")
        self.assertEqual(roster.team_id, self.team)
        self.assertEqual(roster.season_id, self.season)

    def test_roster_team_season_registration_consistency(self):
        """Test that season registration must match team and season."""
        registration = self.env["federation.season.registration"].create({
            "name": "Test Registration",
            "team_id": self.team.id,
            "season_id": self.season.id,
        })
        
        # Create roster with matching registration - should work
        roster = self.env["federation.team.roster"].create({
            "name": "Test Roster",
            "team_id": self.team.id,
            "season_id": self.season.id,
            "season_registration_id": registration.id,
        })
        self.assertEqual(roster.season_registration_id, registration)
        
        # Create another team and season to test mismatch
        other_team = self.env["federation.team"].create({
            "name": "Other Team",
            "club_id": self.club.id,
            "code": "OT",
        })
        other_season = self.env["federation.season"].create({
            "name": "Other Season",
            "code": "OS2024",
            "date_start": "2024-01-01",
            "date_end": "2024-12-31",
        })
        
        # Test team mismatch
        with self.assertRaises(ValidationError):
            self.env["federation.team.roster"].create({
                "name": "Bad Roster Team",
                "team_id": other_team.id,
                "season_id": self.season.id,
                "season_registration_id": registration.id,
            })
        
        # Test season mismatch
        with self.assertRaises(ValidationError):
            self.env["federation.team.roster"].create({
                "name": "Bad Roster Season",
                "team_id": self.team.id,
                "season_id": other_season.id,
                "season_registration_id": registration.id,
            })

    def test_roster_line_unique_player_constraint(self):
        """Test that a player cannot have duplicate roster lines with same date_from."""
        roster = self.env["federation.team.roster"].create({
            "name": "Test Roster",
            "team_id": self.team.id,
            "season_id": self.season.id,
        })
        
        # Create first line
        self.env["federation.team.roster.line"].create({
            "roster_id": roster.id,
            "player_id": self.player1.id,
            "date_from": "2024-01-01",
        })
        
        # Try to create duplicate - should fail
        with self.assertRaises(Exception):
            self.env["federation.team.roster.line"].create({
                "roster_id": roster.id,
                "player_id": self.player1.id,
                "date_from": "2024-01-01",
            })

    def test_single_active_captain_constraint(self):
        """Test that only one active captain is allowed per roster."""
        roster = self.env["federation.team.roster"].create({
            "name": "Test Roster",
            "team_id": self.team.id,
            "season_id": self.season.id,
        })
        
        # Create first captain
        self.env["federation.team.roster.line"].create({
            "roster_id": roster.id,
            "player_id": self.player1.id,
            "is_captain": True,
            "status": "active",
        })
        
        # Try to create second captain - should fail
        with self.assertRaises(ValidationError):
            self.env["federation.team.roster.line"].create({
                "roster_id": roster.id,
                "player_id": self.player2.id,
                "is_captain": True,
                "status": "active",
            })

    def test_roster_line_date_validation(self):
        """Test that date_to cannot be before date_from."""
        roster = self.env["federation.team.roster"].create({
            "name": "Test Roster",
            "team_id": self.team.id,
            "season_id": self.season.id,
        })
        
        # Test invalid dates
        with self.assertRaises(ValidationError):
            self.env["federation.team.roster.line"].create({
                "roster_id": roster.id,
                "player_id": self.player1.id,
                "date_from": "2024-12-31",
                "date_to": "2024-01-01",
            })

    def test_roster_line_rejects_gender_mismatch(self):
        """Players cannot be added to a single-gender team with the wrong gender."""
        female_team = self.env["federation.team"].create({
            "name": "Female Team",
            "club_id": self.club.id,
            "code": "FT",
            "gender": "female",
        })
        male_player = self.env["federation.player"].create({
            "first_name": "Male",
            "last_name": "Player",
            "gender": "male",
        })
        roster = self.env["federation.team.roster"].create({
            "name": "Female Team Roster",
            "team_id": female_team.id,
            "season_id": self.season.id,
        })

        with self.assertRaises(ValidationError):
            self.env["federation.team.roster.line"].create({
                "roster_id": roster.id,
                "player_id": male_player.id,
            })