import logging
from odoo import models

_logger = logging.getLogger(__name__)


class CompetitionEngineService(models.AbstractModel):
    _name = "federation.competition.engine.service"
    _description = "Competition Engine Service"

    def generate_round_robin_schedule(self, tournament, stage, participants, options):
        """Delegate to round-robin service."""
        service = self.env["federation.round.robin.service"]
        return service.generate(tournament, stage, participants, options)

    def generate_knockout_bracket(self, tournament, stage, participants, options):
        """Delegate to knockout service."""
        service = self.env["federation.knockout.service"]
        return service.generate(tournament, stage, participants, options)

    def generate_standings(self, tournament, stage=None, group=None):
        """
        Compute standings - extension point for future implementation.
        """
        _logger.info(
            "Standings called for tournament %s (stage: %s, group: %s)",
            tournament.name if tournament else "N/A",
            stage.name if stage else "N/A",
            group.name if group else "N/A",
        )
        raise NotImplementedError("Standings computation not yet implemented.")
