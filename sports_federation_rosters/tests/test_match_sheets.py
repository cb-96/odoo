from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestMatchSheets(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.club = cls.env["federation.club"].create({
            "name": "Test Club",
            "code": "TEST",
        })
        cls.team_home = cls.env["federation.team"].create({
            "name": "Home Team",
            "club_id": cls.club.id,
            "code": "HT",
        })
        cls.team_away = cls.env["federation.team"].create({
            "name": "Away Team",
            "club_id": cls.club.id,
            "code": "AT",
        })
        cls.season = cls.env["federation.season"].create({
            "name": "Test Season",
            "code": "TS2024",
            "date_start": "2024-01-01",
            "date_end": "2024-12-31",
        })
        cls.tournament = cls.env["federation.tournament"].create({
            "name": "Test Tournament",
            "code": "TTOUR",
            "season_id": cls.season.id,
            "date_start": "2024-01-01",
        })
        cls.match = cls.env["federation.match"].create({
            "tournament_id": cls.tournament.id,
            "home_team_id": cls.team_home.id,
            "away_team_id": cls.team_away.id,
            "date_scheduled": "2024-06-15 15:00:00",
        })
        cls.player1 = cls.env["federation.player"].create({
            "name": "Player One",
            "first_name": "Player",
            "last_name": "One",
        })
        cls.player2 = cls.env["federation.player"].create({
            "name": "Player Two",
            "first_name": "Player",
            "last_name": "Two",
        })

    def test_create_match_sheet(self):
        """Test basic match sheet creation."""
        sheet = self.env["federation.match.sheet"].create({
            "name": "Home Sheet",
            "match_id": self.match.id,
            "team_id": self.team_home.id,
            "side": "home",
        })
        self.assertTrue(sheet.id)
        self.assertEqual(sheet.state, "draft")
        self.assertEqual(sheet.match_id, self.match)
        self.assertEqual(sheet.team_id, self.team_home)

    def test_match_sheet_unique_per_match_team_side(self):
        """Test that only one match sheet per match/team/side combination exists."""
        # Create first sheet
        self.env["federation.match.sheet"].create({
            "name": "Home Sheet",
            "match_id": self.match.id,
            "team_id": self.team_home.id,
            "side": "home",
        })
        
        # Try to create duplicate - should fail
        with self.assertRaises(Exception):
            self.env["federation.match.sheet"].create({
                "name": "Duplicate Home Sheet",
                "match_id": self.match.id,
                "team_id": self.team_home.id,
                "side": "home",
            })

    def test_match_sheet_side_team_consistency(self):
        """Test that home/away side must match match teams."""
        # Test home side with wrong team
        with self.assertRaises(ValidationError):
            self.env["federation.match.sheet"].create({
                "name": "Wrong Home Sheet",
                "match_id": self.match.id,
                "team_id": self.team_away.id,
                "side": "home",
            })
        
        # Test away side with wrong team
        with self.assertRaises(ValidationError):
            self.env["federation.match.sheet"].create({
                "name": "Wrong Away Sheet",
                "match_id": self.match.id,
                "team_id": self.team_home.id,
                "side": "away",
            })
        
        # Test correct home side
        home_sheet = self.env["federation.match.sheet"].create({
            "name": "Correct Home Sheet",
            "match_id": self.match.id,
            "team_id": self.team_home.id,
            "side": "home",
        })
        self.assertEqual(home_sheet.team_id, self.match.home_team_id)
        
        # Test correct away side
        away_sheet = self.env["federation.match.sheet"].create({
            "name": "Correct Away Sheet",
            "match_id": self.match.id,
            "team_id": self.team_away.id,
            "side": "away",
        })
        self.assertEqual(away_sheet.team_id, self.match.away_team_id)

    def test_match_sheet_line_unique_player(self):
        """Test that a player cannot appear twice on same match sheet."""
        sheet = self.env["federation.match.sheet"].create({
            "name": "Test Sheet",
            "match_id": self.match.id,
            "team_id": self.team_home.id,
            "side": "home",
        })
        
        # Create first line
        self.env["federation.match.sheet.line"].create({
            "match_sheet_id": sheet.id,
            "player_id": self.player1.id,
        })
        
        # Try to create duplicate - should fail
        with self.assertRaises(Exception):
            self.env["federation.match.sheet.line"].create({
                "match_sheet_id": sheet.id,
                "player_id": self.player1.id,
            })

    def test_match_sheet_line_starter_substitute_validation(self):
        """Test that a player cannot be both starter and substitute."""
        sheet = self.env["federation.match.sheet"].create({
            "name": "Test Sheet",
            "match_id": self.match.id,
            "team_id": self.team_home.id,
            "side": "home",
        })
        
        # Test invalid combination
        with self.assertRaises(ValidationError):
            self.env["federation.match.sheet.line"].create({
                "match_sheet_id": sheet.id,
                "player_id": self.player1.id,
                "is_starter": True,
                "is_substitute": True,
            })