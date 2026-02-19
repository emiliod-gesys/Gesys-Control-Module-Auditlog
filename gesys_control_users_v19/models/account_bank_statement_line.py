# -*- coding: utf-8 -*-

from xmlrpc.client import MAXINT

from odoo import api, fields, models


class AccountBankStatementLine(models.Model):
    """
    Extensión para corregir AttributeError en cierre de POS:
    'bool' object has no attribute 'strftime'

    Ocurre cuando st_line.date es False durante el cierre de sesión POS
    (al crear account.move.line para combine_cash_receivable_lines).
    El método estándar _compute_internal_index asume que date siempre es
    un objeto fecha, pero en ciertos flujos puede ser False.
    """

    _inherit = 'account.bank.statement.line'

    @api.depends('date', 'sequence')
    def _compute_internal_index(self):
        """
        Sobrescrito para evitar AttributeError cuando date es False o bool.
        Compatible con Odoo 17, 18 y 19.
        """
        for st_line in self.filtered(lambda line: line._origin.id):
            date_val = st_line.date
            # Evitar strftime sobre bool/False (común durante cierre POS)
            if date_val and hasattr(date_val, 'strftime'):
                st_line.internal_index = (
                    f'{date_val.strftime("%Y%m%d")}'
                    f'{MAXINT - st_line.sequence:0>10}'
                    f'{st_line._origin.id:0>10}'
                )
            else:
                # Fallback: usar fecha de hoy para no bloquear el flujo
                fallback_date = fields.Date.context_today(self)
                st_line.internal_index = (
                    f'{fallback_date.strftime("%Y%m%d")}'
                    f'{MAXINT - st_line.sequence:0>10}'
                    f'{st_line._origin.id:0>10}'
                )
