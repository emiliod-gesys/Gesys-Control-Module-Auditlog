# -*- coding: utf-8 -*-

from datetime import timedelta
import logging

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class UserActionPurgeWizard(models.TransientModel):
    _name = 'gesys_control.purge_actions_wizard'
    _description = 'Asistente de Borrado Total de Acciones'

    config_id = fields.Many2one('gesys_control.config', required=True)

    def action_confirm_purge(self):
        """Confirmar borrado total con espera obligatoria de 5 segundos."""
        self.ensure_one()
        create_date = self.create_date or fields.Datetime.now()
        if fields.Datetime.now() < create_date + timedelta(seconds=5):
            raise UserError('Debe esperar al menos 5 segundos para confirmar el borrado total.')

        try:
            count = self.config_id.purge_all_actions()
            _logger.info(f"Borrado total ejecutado. Registros eliminados: {count}")
        except Exception as e:
            _logger.error(f"Error en borrado total: {e}")
            raise

        return {'type': 'ir.actions.act_window_close'}
