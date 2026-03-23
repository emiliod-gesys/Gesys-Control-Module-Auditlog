# -*- coding: utf-8 -*-

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    # Horario laboral por usuario (anula el horario general cuando está activo)
    gesys_work_schedule_override = fields.Boolean(
        string='Usar horario laboral propio',
        default=False,
        help='Si está activo, usa el horario de este usuario en lugar del horario general.'
    )
    gesys_work_schedule_days = fields.Char(
        string='Working Days',
        default='1,2,3,4,5',
        help='1=Lun, 7=Dom. Separados por coma. Ej: 1,2,3,4,5 (Lun-Vie)'
    )
    gesys_work_schedule_start = fields.Float(
        string='Start Time',
        default=8.0,
        help='Hora en 24h (ej: 8.0 = 08:00)'
    )
    gesys_work_schedule_end = fields.Float(
        string='End Time',
        default=18.0,
        help='Hora en 24h (ej: 18.0 = 18:00)'
    )
