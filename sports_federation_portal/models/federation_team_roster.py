from odoo import _, api, models
from odoo.exceptions import AccessError, ValidationError


class FederationTeamRoster(models.Model):
    _inherit = "federation.team.roster"

    @api.model
    def _portal_get_represented_clubs(self, user=None):
        user = user or self.env.user
        return (
            self.env["federation.club.representative"]
            .with_user(user)
            .sudo()
            ._get_clubs_for_user(user=user)
        )

    @api.model
    def _portal_get_confirmed_registrations(self, user=None):
        user = user or self.env.user
        clubs = self._portal_get_represented_clubs(user=user)
        if not clubs:
            return self.env["federation.season.registration"]
        return (
            self.env["federation.season.registration"]
            .with_user(user)
            .sudo()
            .search(
                [
                    ("club_id", "in", clubs.ids),
                    ("state", "=", "confirmed"),
                ],
                order="season_id desc, team_id, id desc",
            )
        )

    def _portal_get_confirmed_registration(self, user=None):
        self.ensure_one()
        user = user or self.env.user
        if self.season_registration_id and self.season_registration_id.state == "confirmed":
            return self.season_registration_id
        return (
            self.env["federation.season.registration"]
            .with_user(user)
            .sudo()
            .search(
                [
                    ("team_id", "=", self.team_id.id),
                    ("season_id", "=", self.season_id.id),
                    ("state", "=", "confirmed"),
                ],
                order="id desc",
                limit=1,
            )
        )

    def _portal_assert_manage_access(self, user=None):
        user = user or self.env.user
        clubs = self._portal_get_represented_clubs(user=user)
        if not clubs:
            raise AccessError(
                _("You are not assigned as a club representative.")
            )
        for record in self:
            if record.club_id not in clubs:
                raise AccessError(
                    _("You can only manage rosters for your own club.")
                )
            if not record._portal_get_confirmed_registration(user=user):
                raise ValidationError(
                    _(
                        "This roster can only be managed in the portal after the team's season registration has been confirmed."
                    )
                )
        return True

    @api.model
    def _portal_get_primary_roster_for_registration(self, season_registration, user=None):
        user = user or self.env.user
        season_registration.ensure_one()
        roster = (
            self.with_user(user)
            .sudo()
            .search(
                [("season_registration_id", "=", season_registration.id)],
                order="id desc",
                limit=1,
            )
        )
        if roster:
            return roster
        return (
            self.with_user(user)
            .sudo()
            .search(
                [
                    ("team_id", "=", season_registration.team_id.id),
                    ("season_id", "=", season_registration.season_id.id),
                    ("competition_id", "=", False),
                ],
                order="id desc",
                limit=1,
            )
        )

    @api.model
    def _portal_create_roster_for_registration(self, season_registration, user=None):
        user = user or self.env.user
        season_registration = season_registration.with_user(user).sudo()
        clubs = self._portal_get_represented_clubs(user=user)
        if season_registration.club_id not in clubs:
            raise AccessError(
                _("You can only create rosters for your own club.")
            )
        if season_registration.state != "confirmed":
            raise ValidationError(
                _(
                    "A roster can only be created after the season registration has been confirmed."
                )
            )

        roster = self._portal_get_primary_roster_for_registration(
            season_registration, user=user
        )
        if roster:
            if not roster.season_registration_id and not roster.match_day_locked:
                roster.with_user(user).sudo().write(
                    {"season_registration_id": season_registration.id}
                )
            return roster

        return self.with_user(user).sudo().create(
            {
                "name": _("%(team)s - %(season)s Roster")
                % {
                    "team": season_registration.team_id.display_name,
                    "season": season_registration.season_id.display_name,
                },
                "team_id": season_registration.team_id.id,
                "season_id": season_registration.season_id.id,
                "season_registration_id": season_registration.id,
                "valid_from": season_registration.season_id.date_start or False,
                "valid_to": season_registration.season_id.date_end or False,
            }
        )

    def _portal_update_roster(self, values=None, user=None):
        user = user or self.env.user
        self._portal_assert_manage_access(user=user)
        closed_rosters = self.filtered(lambda roster: roster.status == "closed")
        if closed_rosters:
            raise ValidationError(
                _("Closed rosters cannot be edited in the portal.")
            )

        values = values or {}
        prepared = {}
        if "name" in values:
            name = (values.get("name") or "").strip()
            if not name:
                raise ValidationError(_("Roster name is required."))
            prepared["name"] = name
        if "valid_from" in values:
            prepared["valid_from"] = values.get("valid_from") or False
        if "valid_to" in values:
            prepared["valid_to"] = values.get("valid_to") or False
        if "notes" in values:
            prepared["notes"] = (values.get("notes") or "").strip() or False
        if not prepared:
            return False
        return self.with_user(user).sudo().write(prepared)

    def _portal_action_activate(self, user=None):
        user = user or self.env.user
        self._portal_assert_manage_access(user=user)
        return self.with_user(user).sudo().action_activate()

    def _portal_action_set_draft(self, user=None):
        user = user or self.env.user
        self._portal_assert_manage_access(user=user)
        return self.with_user(user).sudo().action_set_draft()

    def _portal_action_close(self, user=None):
        user = user or self.env.user
        self._portal_assert_manage_access(user=user)
        return self.with_user(user).sudo().action_close()


class FederationTeamRosterLine(models.Model):
    _inherit = "federation.team.roster.line"

    @api.model
    def _portal_get_available_players(self, roster, user=None):
        user = user or self.env.user
        roster._portal_assert_manage_access(user=user)
        domain = [
            "|",
            ("club_id", "=", roster.club_id.id),
            ("team_ids", "in", roster.team_id.ids),
            ("active", "=", True),
        ]
        if roster.team_id.gender in ("male", "female"):
            domain.append(("gender", "=", roster.team_id.gender))
        return (
            self.env["federation.player"]
            .with_user(user)
            .sudo()
            .search(domain, order="last_name, first_name, id")
        )

    @api.model
    def _portal_get_available_licenses(self, roster, user=None, player=None):
        user = user or self.env.user
        roster._portal_assert_manage_access(user=user)
        domain = [
            ("club_id", "=", roster.club_id.id),
            ("season_id", "=", roster.season_id.id),
        ]
        if player:
            domain.append(("player_id", "=", player.id))
        return (
            self.env["federation.player.license"]
            .with_user(user)
            .sudo()
            .search(domain, order="player_id, issue_date desc, id desc")
        )

    @api.model
    def _portal_prepare_line_values(self, roster, values=None, user=None, player=None):
        user = user or self.env.user
        values = values or {}
        selected_player = not bool(player)

        if not player:
            player_id = values.get("player_id")
            if not player_id:
                raise ValidationError(_("Select a player."))
            try:
                player_id = int(player_id)
            except (TypeError, ValueError) as exc:
                raise ValidationError(_("Select a valid player.")) from exc
            player = (
                self.env["federation.player"]
                .with_user(user)
                .sudo()
                .browse(player_id)
            )

        if not player.exists():
            raise ValidationError(_("Select a valid player."))

        if selected_player and player.club_id != roster.club_id and roster.team_id not in player.team_ids:
            raise ValidationError(
                _("You can only roster players who belong to your club.")
            )

        license_id = values.get("license_id")
        license_record = self.env["federation.player.license"]
        if license_id:
            try:
                license_id = int(license_id)
            except (TypeError, ValueError) as exc:
                raise ValidationError(_("Select a valid license.")) from exc
            license_record = (
                self.env["federation.player.license"]
                .with_user(user)
                .sudo()
                .browse(license_id)
            )
            if (
                not license_record.exists()
                or license_record.player_id != player
                or license_record.club_id != roster.club_id
                or license_record.season_id != roster.season_id
            ):
                raise ValidationError(
                    _(
                        "The selected license must belong to the chosen player, your club, and the roster season."
                    )
                )

        status = values.get("status") or "active"
        if status != "active":
            raise ValidationError(
                _(
                    "Portal roster editing only supports active roster lines. Remove a player from the roster if they should no longer be available."
                )
            )

        return {
            "player_id": player.id,
            "status": status,
            "jersey_number": (values.get("jersey_number") or "").strip() or False,
            "is_captain": bool(values.get("is_captain")),
            "is_vice_captain": bool(values.get("is_vice_captain")),
            "license_id": license_record.id or False,
            "date_from": values.get("date_from") or False,
            "date_to": values.get("date_to") or False,
            "notes": (values.get("notes") or "").strip() or False,
        }

    @api.model
    def _portal_create_line(self, roster, values=None, user=None):
        user = user or self.env.user
        roster._portal_assert_manage_access(user=user)
        if roster.status == "closed":
            raise ValidationError(
                _("Closed rosters cannot be edited in the portal.")
            )
        prepared = self._portal_prepare_line_values(
            roster, values=values, user=user
        )
        prepared["roster_id"] = roster.id
        return self.with_user(user).sudo().create(prepared)

    def _portal_update_line(self, values=None, user=None):
        user = user or self.env.user
        self.mapped("roster_id")._portal_assert_manage_access(user=user)
        if any(line.roster_id.status == "closed" for line in self):
            raise ValidationError(
                _("Closed rosters cannot be edited in the portal.")
            )
        for line in self:
            prepared = self._portal_prepare_line_values(
                line.roster_id,
                values=values,
                user=user,
                player=line.player_id,
            )
            line.with_user(user).sudo().write(prepared)
        return True

    def _portal_delete_line(self, user=None):
        user = user or self.env.user
        self.mapped("roster_id")._portal_assert_manage_access(user=user)
        if any(line.roster_id.status == "closed" for line in self):
            raise ValidationError(
                _("Closed rosters cannot be edited in the portal.")
            )
        return self.with_user(user).sudo().unlink()