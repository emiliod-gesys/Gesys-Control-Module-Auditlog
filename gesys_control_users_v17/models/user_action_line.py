# -*- coding: utf-8 -*-

from odoo import models, fields


class UserActionLine(models.Model):
    _name = 'gesys_control.user_action_line'
    _description = 'Change Line (Modified field)'

    user_action_id = fields.Many2one(
        'gesys_control.user_action',
        string='Action',
        required=True,
        ondelete='cascade',
        index=True
    )
    action_date = fields.Datetime(
        string='Date and Time',
        related='user_action_id.action_date',
        store=False,
        readonly=True
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        related='user_action_id.user_id',
        store=False,
        readonly=True
    )
    field_name = fields.Char(string='Field')
    old_value_text = fields.Text(string='Old Value')
    new_value_text = fields.Text(string='New Value')
