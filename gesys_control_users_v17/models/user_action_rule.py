# -*- coding: utf-8 -*-

from odoo import models, fields


class UserActionRule(models.Model):
    _name = 'gesys_control.rule'
    _description = 'Audit rule per model'

    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        ondelete='cascade',
        index=True
    )
    model_name = fields.Char(related='model_id.model', readonly=True)
    users_to_exclude_ids = fields.Many2many(
        'res.users',
        string='Users to exclude',
        help='Actions from these users are not logged for this model'
    )
    fields_to_exclude_ids = fields.Many2many(
        'ir.model.fields',
        string='Fields to exclude',
        domain="[('model_id', '=', model_id)]",
        help='Changes on these fields are not logged'
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('model_uniq', 'unique(model_id)', 'A rule for this model already exists.')
    ]
