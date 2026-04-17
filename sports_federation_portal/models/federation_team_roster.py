from odoo import _, api, models
from odoo.exceptions import AccessError, ValidationError


class FederationTeamRoster(models.Model):
    _inherit = "federation.team.roster"

    @api.model
    def _portal_get_scope_domain(self, user=None):
        """Return the exact roster domain the portal user may see.

        Team-specific assignments take precedence, club assignments widen the
        scope, and users with no roster authority get an explicit false domain
        instead of an accidental full-table search.
        """
        user = user or self.env.user
        club_scope = user.portal_club_scope_ids
        team_scope = user.portal_team_scope_ids
        if team_scope and club_scope:
            return ["|", ("team_id", "in", team_scope.ids), ("club_id", "in", club_scope.ids)]
        if team_scope:
            return [("team_id", "in", team_scope.ids)]
        represented_clubs = user.represented_club_ids
        if represented_clubs:
            return [("club_id", "in", represented_clubs.ids)]
        return [("id", "=", False)]

    @api.model
    def _portal_get_represented_clubs(self, user=None):
        """Resolve represented clubs through the shared privilege boundary.

        The read is elevated so controllers can reuse the result for ownership
        checks while keeping create and write attribution tied to the portal
        user.
        """
        user = user or self.env.user
        return self.env["federation.portal.privilege"].elevate(
            self.env["federation.club.representative"],
            user=user,
        )._get_clubs_for_user(user=user)

    @api.model
    def _portal_get_confirmed_registrations(self, user=None):
        """Return confirmed season registrations inside the caller's roster scope.

        Unscoped users receive an empty recordset so portal pages can render a
        safe empty state without leaking registrations from other clubs.
        """
        user = user or self.env.user
        scope_domain = self._portal_get_scope_domain(user=user)
        if scope_domain == [("id", "=", False)]:
            return self.env["federation.season.registration"]
        return (
            self.env["federation.season.registration"]
            .with_user(user)
            .sudo()
            .search(
                scope_domain + [("state", "=", "confirmed")],
                order="season_id desc, team_id, id desc",
            )
        )

    def _portal_get_confirmed_registration(self, user=None):
        """Return the confirmed season registration that authorizes portal edits.

        Match-day and roster changes stay blocked until the team has a
        confirmed registration for the same season.
        """
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

    @api.model
    def _portal_get_preferred_roster_for_tournament(self, tournament, team, user=None):
        """Choose the roster the portal should treat as the team's active baseline.

        Competition-specific active rosters win first, then generic active
        season rosters, then the latest fallback roster if no active option
        exists.
        """
        user = user or self.env.user
        tournament.ensure_one()
        team.ensure_one()

        scope_domain = self._portal_get_scope_domain(user=user)
        if scope_domain == [("id", "=", False)]:
            return self.browse([])

        domain = scope_domain + [("team_id", "=", team.id)]
        if tournament.season_id:
            domain.append(("season_id", "=", tournament.season_id.id))

        rosters = self.with_user(user).sudo().search(domain, order="id desc")
        if not rosters:
            return rosters

        if tournament.competition_id:
            competition_rosters = rosters.filtered(
                lambda roster: roster.competition_id == tournament.competition_id
            )
            picked = self._portal_pick_preferred_roster(competition_rosters)
            if picked:
                return picked

        generic_rosters = rosters.filtered(lambda roster: not roster.competition_id)
        picked = self._portal_pick_preferred_roster(generic_rosters)
        return picked or self._portal_pick_preferred_roster(rosters)

    @api.model
    def _portal_pick_preferred_roster(self, rosters):
        """Prefer active rosters because portal match-day flows assume readiness.

        If no active roster exists, the newest remaining roster is returned so
        the portal can still guide operators toward the current fallback.
        """
        active_rosters = rosters.filtered(lambda roster: roster.status == "active")
        return active_rosters[:1] or rosters[:1]

    def _portal_assert_manage_access(self, user=None):
        """Enforce portal ownership before any roster write or state transition.

        Team-level assignments may manage only their own team. Whole-club roles
        may manage club rosters, but only after the team's season registration
        has been confirmed.
        """
        user = user or self.env.user
        club_scope = user.portal_club_scope_ids
        team_scope = user.portal_team_scope_ids
        represented_clubs = user.represented_club_ids
        if not represented_clubs and not team_scope:
            raise AccessError(
                _("You are not assigned as a club representative.")
            )
        for record in self:
            if record.team_id in team_scope:
                continue
            if club_scope and record.club_id in club_scope:
                continue
            if not team_scope and record.club_id in represented_clubs:
                continue
            if record.club_id not in represented_clubs:
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
        """Reuse an existing portal roster before creating a new season baseline.

        The portal first looks for a roster already linked to the confirmed
        registration, then falls back to the latest generic roster for the same
        team and season.
        """
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
        """Create or reuse the roster that a confirmed registration should edit.

        Ownership is checked against represented clubs first. Existing rosters
        are linked back to the confirmed registration when that can be done
        without mutating a match-day locked record.
        """
        user = user or self.env.user
        PortalPrivilege = self.env["federation.portal.privilege"]
        season_registration = PortalPrivilege.elevate(season_registration, user=user)
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
                PortalPrivilege.portal_write(
                    roster,
                    {"season_registration_id": season_registration.id},
                    user=user,
                )
            return roster

        return PortalPrivilege.portal_create(
            self,
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
            },
            user=user,
        )

    @api.model
    def _portal_prepare_roster_write_values(self, values=None):
        """Normalize editable roster fields before the portal privilege write.

        Blank strings are stripped so the portal does not persist whitespace-only
        values as intentional operator input.
        """
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
        return prepared

    def _portal_update_roster(self, values=None, user=None):
        """Apply portal-safe roster edits after ownership and status checks.

        Closed rosters stay immutable from the portal, even for valid club
        representatives, so match-day history is not rewritten after closure.
        """
        user = user or self.env.user
        self._portal_assert_manage_access(user=user)
        closed_rosters = self.filtered(lambda roster: roster.status == "closed")
        if closed_rosters:
            raise ValidationError(
                _("Closed rosters cannot be edited in the portal.")
            )

        prepared = self._portal_prepare_roster_write_values(values=values)
        if not prepared:
            return False
        return self.env["federation.portal.privilege"].portal_write(
            self,
            prepared,
            user=user,
        )

    def _portal_action_activate(self, user=None):
        """Activate rosters through the shared privilege boundary after access checks."""
        user = user or self.env.user
        self._portal_assert_manage_access(user=user)
        return self.env["federation.portal.privilege"].portal_call(
            self,
            "action_activate",
            user=user,
        )

    def _portal_action_set_draft(self, user=None):
        """Move rosters back to draft when the caller still owns the record."""
        user = user or self.env.user
        self._portal_assert_manage_access(user=user)
        return self.env["federation.portal.privilege"].portal_call(
            self,
            "action_set_draft",
            user=user,
        )

    def _portal_action_close(self, user=None):
        """Close rosters through the portal boundary so the write stays attributable."""
        user = user or self.env.user
        self._portal_assert_manage_access(user=user)
        return self.env["federation.portal.privilege"].portal_call(
            self,
            "action_close",
            user=user,
        )


class FederationTeamRosterLine(models.Model):
    _inherit = "federation.team.roster.line"

    @api.model
    def _portal_get_available_players(self, roster, user=None):
        """Return only players the caller may legally add to the selected roster.

        Team-scoped users are constrained to players already linked to that
        team, while club-scoped users may also pick club players not yet linked
        to the team.
        """
        user = user or self.env.user
        roster._portal_assert_manage_access(user=user)
        if roster.team_id in user.portal_team_scope_ids and roster.club_id not in user.portal_club_scope_ids:
            domain = [
                ("team_ids", "in", roster.team_id.ids),
                ("active", "=", True),
            ]
        else:
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
        """Return licenses that match the roster club, season, and optional player."""
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
    def _portal_resolve_line_player(self, roster, values=None, user=None, player=None):
        """Resolve and authorize the player referenced by a portal roster edit.

        New line creation may choose a player from the form payload, while line
        edits keep the existing player pinned and only validate that the record
        still exists.
        """
        user = user or self.env.user
        values = values or {}
        selected_from_form = player is None

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

        if selected_from_form:
            if roster.team_id in user.portal_team_scope_ids and roster.club_id not in user.portal_club_scope_ids:
                if roster.team_id not in player.team_ids:
                    raise ValidationError(
                        _("You can only roster players already assigned to the selected team.")
                    )
            elif player.club_id != roster.club_id and roster.team_id not in player.team_ids:
                raise ValidationError(
                    _("You can only roster players who belong to your club.")
                )

        return player

    @api.model
    def _portal_resolve_line_license(self, roster, player, license_id=None, user=None):
        """Resolve an optional license and ensure it matches the roster context.

        Portal edits may only attach licenses for the same player, club, and
        season so operators cannot cross-link external registration records.
        """
        user = user or self.env.user
        license_record = self.env["federation.player.license"]
        if not license_id:
            return license_record

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
        return license_record

    @api.model
    def _portal_prepare_line_values(self, roster, values=None, user=None, player=None):
        """Normalize a portal roster-line payload before create or update.

        The resulting values are safe to persist through the shared portal
        privilege boundary because player scope, license scope, and allowed
        status transitions are validated first.
        """
        user = user or self.env.user
        values = values or {}
        player = self._portal_resolve_line_player(
            roster,
            values=values,
            user=user,
            player=player,
        )
        license_record = self._portal_resolve_line_license(
            roster,
            player,
            license_id=values.get("license_id"),
            user=user,
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
        """Create a roster line only after the roster and payload pass portal checks."""
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
        return self.env["federation.portal.privilege"].portal_create(
            self,
            prepared,
            user=user,
        )

    def _portal_update_line(self, values=None, user=None):
        """Update roster lines without allowing player swaps or closed-roster edits."""
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
            self.env["federation.portal.privilege"].portal_write(
                line,
                prepared,
                user=user,
            )
        return True

    def _portal_delete_line(self, user=None):
        """Delete roster lines only while the owning roster remains editable."""
        user = user or self.env.user
        self.mapped("roster_id")._portal_assert_manage_access(user=user)
        if any(line.roster_id.status == "closed" for line in self):
            raise ValidationError(
                _("Closed rosters cannot be edited in the portal.")
            )
        return self.env["federation.portal.privilege"].portal_call(
            self,
            "unlink",
            user=user,
        )