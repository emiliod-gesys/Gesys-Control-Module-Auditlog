# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import logging
import unicodedata

_logger = logging.getLogger(__name__)


class UserAction(models.Model):
    _name = 'gesys_control.user_action'
    _description = 'User Action'
    _order = 'action_date desc, id desc'
    _rec_name = 'action_type'
    
    # Prevenir creación manual - solo se puede crear mediante log_action
    _check_company_auto = True

    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        ondelete='cascade',
        default=lambda self: self.env.user
    )
    
    action_type = fields.Selection(
        selection=[
            ('create', 'Creation'),
            ('read', 'Read'),
            ('write', 'Update'),
            ('delete', 'Deletion'),
            ('validate', 'Validation'),
            ('post', 'Post'),
            ('cancel', 'Cancel'),
            ('unlink', 'Delete'),
            ('action_post', 'Post'),
            ('action_cancel', 'Cancel'),
            ('button_validate', 'Validate'),
            ('action_draft', 'Draft'),
            ('first_login_day', 'First Login of the Day'),
            ('purge_all', 'Delete All'),
            ('export', 'Export'),
            ('import', 'Import'),
            ('print', 'Print'),
            ('email', 'Email'),
            ('report', 'Report'),
            ('button', 'Button'),
            ('other', 'Other'),
        ],
        string='Action Type',
        required=True,
        default='other'
    )
    
    action_type_display = fields.Char(
        string='Action Type (Display)',
        compute='_compute_action_type_display',
        store=True
    )
    
    model_name = fields.Char(
        string='Model',
        required=True,
        index=True
    )
    
    model_description = fields.Char(
        string='Model Description',
        compute='_compute_model_description',
        store=True
    )
    
    record_id = fields.Integer(
        string='Record ID',
        index=True
    )
    
    record_name = fields.Char(
        string='Record Name',
        compute='_compute_record_name',
        store=False
    )

    record_name_cached = fields.Char(
        string='Record Name (Saved)',
        compute='_compute_record_name_cached',
        store=True,
        index=True
    )

    record_name_simple = fields.Char(
        string='Record Name (Simple)',
        compute='_compute_record_name_simple',
        store=True,
        index=True
    )

    search_text = fields.Char(
        string='Text',
        help='Virtual field for combined searches.',
        search='_search_text'
    )
    
    action_description = fields.Text(
        string='Description',
        required=True
    )

    action_method = fields.Char(
        string='Method/Button'
    )

    changed_fields = fields.Text(
        string='Changed fields'
    )

    old_values = fields.Text(
        string='Old values'
    )

    new_values = fields.Text(
        string='New values'
    )

    action_description_display = fields.Text(
        string='Description (Display)',
        compute='_compute_action_description_display',
        store=False
    )
    
    action_date = fields.Datetime(
        string='Date',
        required=True,
        default=fields.Datetime.now,
        index=True
    )
    
    action_date_only = fields.Date(
        string='Date (Only)',
        compute='_compute_action_date_only',
        store=True,
        index=True
    )

    action_hour = fields.Integer(
        string='Hour',
        compute='_compute_action_time_parts',
        store=True,
        index=True
    )

    action_weekday = fields.Selection(
        selection=[
            ('1', 'Monday'),
            ('2', 'Tuesday'),
            ('3', 'Wednesday'),
            ('4', 'Thursday'),
            ('5', 'Friday'),
            ('6', 'Saturday'),
            ('7', 'Sunday'),
        ],
        string='Weekday',
        compute='_compute_action_time_parts',
        store=True,
        index=True
    )

    action_day_of_month = fields.Integer(
        string='Day of Month',
        compute='_compute_action_time_parts',
        store=True,
        index=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    
    ip_address = fields.Char(
        string='IP Address'
    )

    http_request_path = fields.Char(
        string='HTTP Path',
        help='HTTP request path that originated the action'
    )

    http_session_id = fields.Char(
        string='HTTP Session',
        index=True,
        help='User session ID'
    )

    line_ids = fields.One2many(
        'gesys_control.user_action_line',
        'user_action_id',
        string='Change Lines'
    )

    is_protected = fields.Boolean(
        string='Protected',
        default=False,
        index=True
    )
    
    @api.depends('action_type')
    def _compute_action_type_display(self):
        """Compute display label for action type."""
        for record in self:
            translations = {
                'create': 'Creation',
                'read': 'Read',
                'write': 'Update',
                'delete': 'Deletion',
                'validate': 'Validation',
                'post': 'Post',
                'cancel': 'Cancel',
                'unlink': 'Delete',
                'action_post': 'Post',
                'action_cancel': 'Cancel',
                'button_validate': 'Validate',
                'action_draft': 'Draft',
                'first_login_day': 'First Login of the Day',
                'purge_all': 'Delete All',
                'export': 'Export',
                'import': 'Import',
                'print': 'Print',
                'email': 'Email',
                'report': 'Report',
                'button': 'Button',
                'other': 'Other',
            }
            
            record.action_type_display = translations.get(
                record.action_type, record.action_type
            )
    
    @api.depends('model_name')
    def _compute_model_description(self):
        """Obtener descripción del modelo"""
        for record in self:
            if record.model_name:
                try:
                    model_obj = self.env[record.model_name]
                    model_description = model_obj._description if hasattr(model_obj, '_description') else record.model_name
                    record.model_description = model_description
                except:
                    record.model_description = record.model_name
            else:
                record.model_description = False
    
    def _compute_record_name(self):
        """Obtener nombre del registro si existe"""
        for record in self:
            if record.model_name and record.record_id:
                try:
                    model_obj = self.env[record.model_name]
                    res_record = model_obj.browse(record.record_id)
                    if res_record.exists():
                        record.record_name = res_record.display_name or res_record.name or f"ID: {record.record_id}"
                    else:
                        record.record_name = record.record_name_cached or f"[Eliminado] ID: {record.record_id}"
                except:
                    record.record_name = record.record_name_cached or f"ID: {record.record_id}"
            else:
                record.record_name = False

    @api.depends('model_name', 'record_id')
    def _compute_record_name_cached(self):
        """Guardar nombre del registro para busquedas."""
        for record in self:
            record.record_name_cached = record._get_record_display_name(
                record.model_name, record.record_id
            )

    @api.depends('model_name', 'record_id')
    def _compute_record_name_simple(self):
        """Guardar nombre simple del registro para busquedas."""
        for record in self:
            record.record_name_simple = record._get_record_simple_name(
                record.model_name, record.record_id
            )

    def _get_record_display_name(self, model_name, record_id):
        """Resolver nombre del registro para cache."""
        if not model_name or not record_id:
            return False
        try:
            model_obj = self.env[model_name]
            res_record = model_obj.browse(record_id)
            if res_record.exists():
                return res_record.display_name or res_record.name or f"ID: {record_id}"
        except Exception:
            pass
        return f"ID: {record_id}"

    def _get_record_simple_name(self, model_name, record_id):
        """Resolver nombre simple del registro para cache."""
        if not model_name or not record_id:
            return False
        try:
            model_obj = self.env[model_name]
            res_record = model_obj.browse(record_id)
            if res_record.exists():
                return res_record.name or res_record.display_name or f"ID: {record_id}"
        except Exception:
            pass
        return f"ID: {record_id}"
    
    @api.depends('action_date')
    def _compute_action_date_only(self):
        """Extraer solo la fecha sin hora"""
        for record in self:
            if record.action_date:
                record.action_date_only = fields.Date.from_string(record.action_date)
            else:
                record.action_date_only = False

    @api.depends('action_date')
    def _compute_action_time_parts(self):
        """Extraer hora, día de semana y día de mes en zona horaria configurada"""
        tz_name = self.env['gesys_control.config'].get_config().timezone or self.env.user.tz or 'UTC'
        for record in self:
            if record.action_date:
                local_dt = fields.Datetime.context_timestamp(
                    record.with_context(tz=tz_name),
                    record.action_date
                )
                record.action_hour = local_dt.hour
                record.action_weekday = str(local_dt.weekday() + 1)
                record.action_day_of_month = local_dt.day
            else:
                record.action_hour = False
                record.action_weekday = False
                record.action_day_of_month = False
    
    @api.model_create_multi
    def create(self, vals_list):
        """
        Sobrescribir create para prevenir creación manual.
        Solo permitir creación mediante log_action() con contexto especial.
        """
        # Verificar si viene del método log_action (contexto especial)
        if not self.env.context.get('gesys_control_allow_create'):
            # Si alguien intenta crear manualmente desde la interfaz, bloquearlo
            _logger.warning("Blocked manual action creation attempt. Only automatic actions are allowed.")
            raise UserError(_('Actions cannot be created manually. They are logged automatically by the system.'))
        
        return super().create(vals_list)
    
    @api.model
    def log_action(self, action_type, model_name, record_id, description, user_id=None, ip_address=None,
                   protected=False, action_method=None, changed_fields=None, old_values=None, new_values=None,
                   http_request_path=None, http_session_id=None, line_vals=None):
        """
        Método helper para registrar una acción.
        Este es el único método permitido para crear acciones.
        """
        description = self._sanitize_description(description)
        # Evitar duplicados (misma acción en ventana de 2 segundos)
        try:
            last = self.search([
                ('user_id', '=', user_id or self.env.user.id),
                ('model_name', '=', model_name),
                ('record_id', '=', record_id or False),
                ('action_type', '=', action_type),
                ('action_method', '=', action_method or False),
                ('action_description', '=', description),
            ], order='action_date desc, id desc', limit=1)
            if last:
                delta = fields.Datetime.now() - last.action_date
                if delta.total_seconds() <= 2:
                    return last
        except Exception:
            pass

        vals = {
            'action_type': action_type,
            'model_name': model_name,
            'record_id': record_id,
            'action_description': description,
            'user_id': user_id or self.env.user.id,
            'action_date': fields.Datetime.now(),
            'company_id': self.env.company.id,
            'ip_address': ip_address or self.env.context.get('ip_address'),
            'is_protected': protected,
            'action_method': action_method,
            'changed_fields': changed_fields,
            'old_values': old_values,
            'new_values': new_values,
            'http_request_path': http_request_path or self.env.context.get('http_request_path'),
            'http_session_id': http_session_id or self.env.context.get('http_session_id'),
        }
        try:
            with self.env.cr.savepoint():
                rec = self.with_context(gesys_control_allow_create=True).create(vals)
                if line_vals and rec:
                    if 'gesys_control.user_action_line' in self.env:
                        self.env['gesys_control.user_action_line'].sudo().create([
                            dict(v, user_action_id=rec.id) for v in line_vals
                        ])
                return rec
        except Exception as e:
            _logger.debug("Error al crear registro de auditoria: %s", e)
            return self.env['gesys_control.user_action']

    def unlink(self):
        """Evitar borrar acciones protegidas o de Borrado Total."""
        protected = self.filtered(lambda r: r.is_protected or r.action_type == 'purge_all')
        if protected:
            raise UserError(_('Protected actions and Delete All actions cannot be removed.'))
        return super().unlink()

    @api.model
    def _sanitize_description(self, description):
        """Quitar tildes y caracteres problemáticos para impresión."""
        if not description:
            return ''
        if not isinstance(description, str):
            description = str(description)
        normalized = unicodedata.normalize('NFD', description)
        return ''.join(char for char in normalized if unicodedata.category(char) != 'Mn')

    @api.depends('action_description')
    def _compute_action_description_display(self):
        """Mostrar descripción sin tildes en la vista."""
        for record in self:
            record.action_description_display = self._sanitize_description(record.action_description)

    @api.model
    def _search_text(self, operator, value):
        """Buscar en descripcion y nombre del registro guardado."""
        if not value:
            return []
        allowed_ops = {'ilike', 'like', '=ilike', '=like', '=', '!=', 'not ilike', 'not like'}
        op = operator if operator in allowed_ops else 'ilike'
        return ['|', ('record_name_cached', op, value),
                '|', ('record_name_simple', op, value), ('action_description', op, value)]
    
    def action_view_record(self):
        """Abrir el registro relacionado"""
        self.ensure_one()
        if not self.model_name or not self.record_id:
            raise UserError(_('No related record available.'))
        
        try:
            return {
                'type': 'ir.actions.act_window',
                'name': self.record_name or self.model_description,
                'res_model': self.model_name,
                'res_id': self.record_id,
                'view_mode': 'form',
                'target': 'current',
            }
        except:
            raise UserError(_('Cannot open the record. It may have been deleted.'))
    
    def name_get(self):
        """Nombre a mostrar en la vista"""
        result = []
        for record in self:
            name = f"[{record.action_type_display or record.action_type}] {record.model_description or record.model_name}"
            if record.record_name:
                name += f" - {record.record_name}"
            result.append((record.id, name))
        return result
