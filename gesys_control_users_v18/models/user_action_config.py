# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import ast
import pytz
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class UserActionConfig(models.Model):
    _name = 'gesys_control.config'
    _description = 'Control Module Configuration'
    _rec_name = 'display_name'
    
    @api.model
    def default_get(self, fields_list):
        """Asegurar que siempre haya valores por defecto"""
        res = super().default_get(fields_list)
        if self.env.context.get('gesys_control_skip_config_defaults'):
            res.update({
                'auto_delete_enabled': False,
                'delete_frequency': 'never',
                'timezone': self._default_timezone(),
                'allowed_user_ids': self._default_allowed_users(),
                'log_read': False,
                'log_mode': 'full',
                'ui_language_mode': 'en_US',
            })
            return res
        try:
            config = self.search([], limit=1)
        except Exception:
            config = self.env['gesys_control.config']
        if config:
            lang_mode = getattr(config, 'ui_language_mode', 'en_US')
            if lang_mode in ('es_GT', 'es_ES'):
                lang_mode = 'es'
            if lang_mode not in ('en_US', 'es'):
                lang_mode = 'en_US'
            res.update({
                'auto_delete_enabled': config.auto_delete_enabled or False,
                'delete_frequency': config.delete_frequency or 'never',
                'timezone': config.timezone or self._default_timezone(),
                'allowed_user_ids': [(6, 0, config.allowed_user_ids.ids)],
                'log_read': getattr(config, 'log_read', False),
                'log_mode': getattr(config, 'log_mode', 'full'),
                'ui_language_mode': lang_mode,
                'work_schedule_enabled': getattr(config, 'work_schedule_enabled', False),
                'work_schedule_days': getattr(config, 'work_schedule_days', '1,2,3,4,5'),
                'work_schedule_start': getattr(config, 'work_schedule_start', 8.0),
                'work_schedule_end': getattr(config, 'work_schedule_end', 18.0),
            })
        else:
            res.update({
                'auto_delete_enabled': False,
                'delete_frequency': 'never',
                'timezone': self._default_timezone(),
                'allowed_user_ids': self._default_allowed_users(),
                'log_read': False,
                'log_mode': 'full',
                'ui_language_mode': 'en_US',
                'work_schedule_enabled': False,
                'work_schedule_days': '1,2,3,4,5',
                'work_schedule_start': 8.0,
                'work_schedule_end': 18.0,
            })
        return res
    
    @api.model_create_multi
    def create(self, vals_list):
        """Sobrescribir create para asegurar que solo haya un registro (singleton)"""
        records = self.env['gesys_control.config']
        for vals in vals_list:
            try:
                existing = self.search([], limit=1)
            except Exception:
                existing = self.env['gesys_control.config']
            if existing:
                existing.write(vals)
                records |= existing
            else:
                rec = super().create([vals])
                records |= rec
        if records:
            try:
                records._ensure_allowed_users()
                records._safe_apply_ui_language_to_actions()
            except Exception:
                pass
        return records
    
    def write(self, vals):
        """Sobrescribir write para asegurar que se guarden los cambios y actualizar traducciones"""
        result = super().write(vals)
        if 'timezone' in vals:
            try:
                actions = self.env['gesys_control.user_action'].search([])
                actions._recompute_fields(['action_hour', 'action_weekday', 'action_day_of_month'])
            except Exception:
                _logger.warning("No se pudo recalcular los campos de tiempo para las acciones.")
        if 'allowed_user_ids' in vals:
            self._ensure_allowed_users()
        if 'ui_language_mode' in vals:
            self._safe_apply_ui_language_to_actions()
        return result
    
    def action_load_config(self):
        """Método para asegurar que siempre se muestre el singleton cuando se abre desde la vista"""
        config = self.env['gesys_control.config'].get_config()
        # Si estamos en una acción de ventana, devolver el ID del singleton
        if config:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Configuration'),
                'res_model': 'gesys_control.config',
                'res_id': config.id,
                'view_mode': 'form',
                'target': 'current',
                'context': config._get_module_lang_action_context({}),
            }
        return False
    
    display_name = fields.Char(
        string='Configuration',
        compute='_compute_display_name',
        store=False
    )
    
    auto_delete_enabled = fields.Boolean(
        string='Enable Automatic Cleanup',
        default=False,
        help='If enabled, old records are removed automatically'
    )

    allowed_user_ids = fields.Many2many(
        'res.users',
        string='Users with module access',
        domain=[('share', '=', False)],
        help='Users allowed to access the Control module.'
    )

    timezone = fields.Selection(
        selection=lambda self: [(tz, tz) for tz in pytz.common_timezones],
        string='Time Zone',
        default=lambda self: self._default_timezone(),
        help='Time zone used for activity charts.'
    )
    
    delete_frequency = fields.Selection(
        selection=[
            ('never', 'Do not delete records'),
            ('5min', 'Delete records older than 5 minutes'),
            ('48h', 'Delete records older than 48 hours'),
            ('week', 'Delete records older than 1 week'),
            ('month', 'Delete records older than 1 month'),
            ('3months', 'Delete records older than 3 months'),
            ('6months', 'Delete records older than 6 months'),
            ('year', 'Delete records older than 1 year'),
        ],
        string='Cleanup records older than',
        default='never',
        required=True,
        help='Records older than the selected period are removed'
    )
    
    log_read = fields.Boolean(
        string='Log read operations',
        default=False,
        compute='_compute_log_options',
        inverse='_inverse_log_options',
        store=False,
        help='Log when a user opens/reads a record (can generate high volume)'
    )
    log_mode = fields.Selection(
        selection=[
            ('full', 'Full (before/after diff)'),
            ('fast', 'Fast (sent values only)'),
        ],
        string='Log mode',
        default='full',
        compute='_compute_log_options',
        inverse='_inverse_log_options',
        store=False,
        help='Full: more details but slower. Fast: only sent values.'
    )
    ui_language_mode = fields.Selection(
        selection=[
            ('en_US', 'English'),
            ('es', 'Spanish'),
        ],
        string='Module Interface Language',
        default='en_US',
        help='Select the interface language used by this module.'
    )

    def _get_param(self, key, default):
        try:
            return self.env['ir.config_parameter'].sudo().get_param(key, default)
        except Exception:
            return default

    def _set_param(self, key, value):
        try:
            self.env['ir.config_parameter'].sudo().set_param(key, value)
        except Exception:
            pass

    @api.depends()
    def _compute_log_options(self):
        for rec in self:
            rec.log_read = rec._get_param('gesys_control.log_read', 'false') == 'true'
            rec.log_mode = rec._get_param('gesys_control.log_mode', 'full') or 'full'

    def _inverse_log_options(self):
        for rec in self:
            rec._set_param('gesys_control.log_read', 'true' if rec.log_read else 'false')
            rec._set_param('gesys_control.log_mode', rec.log_mode or 'full')

    # Horario laboral general (para resaltar acciones fuera de horario)
    work_schedule_enabled = fields.Boolean(
        string='Enable working schedule',
        default=False,
        help='If enabled, out-of-schedule actions are highlighted in red in User Activity.'
    )
    work_schedule_days = fields.Char(
        string='Working days',
        default='1,2,3,4,5',
        help='Weekdays: 1=Monday, 7=Sunday. Comma separated. Example: 1,2,3,4,5 (Mon-Fri)'
    )
    work_schedule_start = fields.Float(
        string='Start time',
        default=8.0,
        help='Start time in 24h format (e.g. 8.0 = 08:00, 8.5 = 08:30)'
    )
    work_schedule_end = fields.Float(
        string='End time',
        default=18.0,
        help='End time in 24h format (e.g. 18.0 = 18:00)'
    )

    delete_frequency_display = fields.Char(
        string='Cleanup records older than',
        compute='_compute_delete_frequency_display',
        store=False
    )

    storage_usage_display = fields.Char(
        string='Storage usage',
        compute='_compute_storage_usage',
        help='Disk space used by Actions and Change Lines'
    )

    def _compute_storage_usage(self):
        for rec in self:
            rec.storage_usage_display = rec._get_storage_usage_display()

    def _get_storage_usage_display(self):
        """Obtener uso de espacio en disco de las tablas de auditoría."""
        try:
            cr = self.env.cr
            tables = ['gesys_control_user_action', 'gesys_control_user_action_line']
            total = 0
            for tbl in tables:
                cr.execute(
                    "SELECT pg_total_relation_size(%s)",
                    (tbl,)
                )
                row = cr.fetchone()
                if row and row[0]:
                    total += row[0]
            size_str = '0 B'
            if total > 0:
                for unit, div in [('GB', 1024**3), ('MB', 1024**2), ('KB', 1024)]:
                    if total >= div:
                        size_str = f'{total / div:.2f} {unit}'
                        break
                else:
                    size_str = f'{total} B'
            actions = self.env['gesys_control.user_action'].search_count([])
            lines = self.env['gesys_control.user_action_line'].search_count([])
            return f'{size_str} ({actions:,} acciones, {lines:,} líneas)'
        except Exception as e:
            _logger.debug("Error obteniendo uso de espacio: %s", e)
            return '-'
    
    last_cleanup_date = fields.Datetime(
        string='Last Cleanup',
        help='Date of the last automatic cleanup execution'
    )
    
    next_cleanup_date = fields.Datetime(
        string='Next Cleanup',
        compute='_compute_next_cleanup_date',
        store=False
    )
    
    @api.depends()
    def _compute_display_name(self):
        """Calcular nombre display"""
        for record in self:
            record.display_name = 'Control Configuration'
    
    def _compute_delete_frequency_display(self):
        """Calcular display de frecuencia"""
        for record in self:
            translations = {
                'never': 'Do not delete records',
                '5min': 'Delete records older than 5 minutes',
                '48h': 'Delete records older than 48 hours',
                'week': 'Delete records older than 1 week',
                'month': 'Delete records older than 1 month',
                '3months': 'Delete records older than 3 months',
                '6months': 'Delete records older than 6 months',
                'year': 'Delete records older than 1 year',
            }
            record.delete_frequency_display = translations.get(
                record.delete_frequency, record.delete_frequency
            )
    
    @api.depends('auto_delete_enabled', 'delete_frequency', 'last_cleanup_date')
    def _compute_next_cleanup_date(self):
        """Calcular próxima fecha de limpieza"""
        for record in self:
            if not record.auto_delete_enabled or record.delete_frequency == 'never':
                record.next_cleanup_date = False
                return
            
            base_date = record.last_cleanup_date or fields.Datetime.now()
            
            frequency_delta = {
                '5min': timedelta(minutes=5),
                '48h': timedelta(hours=48),
                'week': timedelta(days=7),
                'month': timedelta(days=30),
                '3months': timedelta(days=90),
                '6months': timedelta(days=180),
                'year': timedelta(days=365),
            }
            
            delta = frequency_delta.get(record.delete_frequency, timedelta(days=0))
            record.next_cleanup_date = base_date + delta
    
    def _get_config_fallback(self):
        """Configuración por defecto en memoria cuando falla el acceso a BD."""
        return self.new({
            'auto_delete_enabled': False,
            'delete_frequency': 'never',
            'timezone': self._default_timezone(),
            'allowed_user_ids': self._default_allowed_users(),
            'log_read': False,
            'log_mode': 'full',
            'ui_language_mode': 'en_US',
            'work_schedule_enabled': False,
            'work_schedule_days': '1,2,3,4,5',
            'work_schedule_start': 8.0,
            'work_schedule_end': 18.0,
        })

    @api.model
    def get_config(self, ensure_setup=True):
        """Obtener o crear la configuración (singleton).
        ensure_setup: si False, no ejecuta _ensure_allowed_users ni _ensure_cleanup_cron
        (útil cuando solo se necesita consultar log_read/log_mode, evita writes durante reads).
        """
        # Evitar recursión: si ya estamos dentro de get_config, devolver fallback
        if self.env.context.get('gesys_control_get_config_guard'):
            return self.sudo()._get_config_fallback()
        self = self.with_context(gesys_control_get_config_guard=True)
        try:
            config = self.sudo().search([], limit=1)
            if not config:
                config = self.with_context(gesys_control_skip_config_defaults=True).sudo().create({
                    'auto_delete_enabled': False,
                    'delete_frequency': 'never',
                    'timezone': self._default_timezone(),
                    'allowed_user_ids': self._default_allowed_users(),
                    'log_read': False,
                    'log_mode': 'full',
                    'ui_language_mode': 'en_US',
                })
            if ensure_setup:
                try:
                    config._ensure_allowed_users()
                    config._ensure_cleanup_cron()
                    config._safe_apply_ui_language_to_actions()
                except Exception as setup_err:
                    _logger.debug(
                        "get_config: no se pudo asegurar usuarios/cron (schema/permisos). %s",
                        setup_err
                    )
            return config
        except Exception as e:
            _logger.warning(
                "No se pudo cargar gesys_control.config (schema desactualizado). "
                "Usando configuración por defecto. Error: %s", e
            )
            return self.sudo()._get_config_fallback()

    def _default_timezone(self):
        company_tz = self.env.company.partner_id.tz
        return company_tz or self.env.user.tz or 'UTC'

    def _default_allowed_users(self):
        # Solo usuarios internos (share=False) para evitar conflicto de tipo de usuario
        return [(6, 0, self.env['res.users'].search([('share', '=', False)]).ids)]

    def _ensure_allowed_users(self):
        """Asegurar que admin siempre tenga acceso y sincronizar grupo."""
        admin_group = self.env.ref('base.group_system').sudo()
        admin_users = admin_group.users
        for record in self:
            if not record.allowed_user_ids:
                record.with_context(gesys_control_skip_tracking=True).sudo().allowed_user_ids = [
                    (6, 0, self.env['res.users'].search([('share', '=', False)]).ids)
                ]
            else:
                # Sanear configuraciones antiguas: quitar portal/public del listado permitido.
                internal_allowed = record.allowed_user_ids.filtered(lambda u: not u.share)
                if internal_allowed != record.allowed_user_ids:
                    record.with_context(gesys_control_skip_tracking=True).sudo().allowed_user_ids = [
                        (6, 0, internal_allowed.ids)
                    ]
            missing_admins = admin_users - record.allowed_user_ids
            if missing_admins:
                record.with_context(gesys_control_skip_tracking=True).sudo().allowed_user_ids = [
                    (4, user.id) for user in missing_admins
                ]
        self._sync_access_group()

    def _sync_access_group(self):
        """Asignar grupo de acceso a usuarios permitidos."""
        group = self.env.ref('gesys_control_users_v18.group_gesys_control_user').sudo().with_context(
            gesys_control_skip_tracking=True
        )
        group_user = self.env.ref('base.group_user').sudo()
        group_portal = self.env.ref('base.group_portal').sudo()
        group_public = self.env.ref('base.group_public').sudo()
        user_type_groups = group_user | group_portal | group_public

        def _has_user_type_conflict(user):
            return len(user.groups_id & user_type_groups) > 1

        def _can_receive_internal_access(user):
            """El grupo del módulo implica base.group_user (interno).
            Si el usuario tiene tipo portal/public, agregarlo provocará conflicto.
            """
            current_types = user.groups_id & user_type_groups
            if group_portal in current_types or group_public in current_types:
                return False
            return True

        for record in self:
            # Evitar asignar este grupo a portal/public para no romper la validación
            # de "un solo tipo de usuario" en Odoo.
            allowed = record.allowed_user_ids.filtered(lambda u: not u.share)
            admins = self.env.ref('base.group_system').users
            allowed = (allowed | admins).filtered(lambda u: not u.share)

            # Sincronización diferencial para no tocar usuarios con conflicto de tipo:
            # en producción puede existir data histórica inconsistente.
            current_users = group.users
            to_add = allowed - current_users
            to_remove = current_users - allowed

            # Solo agregar a usuarios compatibles con tipo interno.
            safe_to_add = to_add.filtered(
                lambda u: (not _has_user_type_conflict(u)) and _can_receive_internal_access(u)
            )
            safe_to_remove = to_remove.filtered(lambda u: not _has_user_type_conflict(u))

            # Escribir en comandos unitarios para evitar que un usuario inválido
            # haga fallar toda la sincronización.
            for user in safe_to_add:
                try:
                    group.write({'users': [(4, user.id)]})
                except Exception as err:
                    _logger.warning(
                        "gesys_control: no se pudo agregar usuario %s al grupo de control: %s",
                        user.id, err
                    )
            for user in safe_to_remove:
                try:
                    group.write({'users': [(3, user.id)]})
                except Exception as err:
                    _logger.warning(
                        "gesys_control: no se pudo quitar usuario %s del grupo de control: %s",
                        user.id, err
                    )

            skipped = (to_add - safe_to_add) | (to_remove - safe_to_remove)
            if skipped:
                _logger.warning(
                    "gesys_control: se omitio sincronizar usuarios con conflicto de tipo (interno/portal/public): %s",
                    skipped.ids
                )

    def _get_effective_module_lang(self, user=None):
        """Resolve module language according to configuration."""
        self.ensure_one()
        mode = self.ui_language_mode or 'en_US'
        if mode == 'en_US':
            return 'en_US'
        if mode in ('es', 'es_GT', 'es_ES'):
            # Usar un idioma español válido e instalado en la BD.
            lang_codes = self.env['res.lang'].sudo().search([
                ('active', '=', True),
                ('code', '=like', 'es_%'),
            ], order='code')
            if lang_codes:
                return lang_codes[0].code
            # Fallback seguro: no forzar idioma inválido.
            return self.env.user.lang or 'en_US'
        return 'en_US'

    def _get_module_lang_action_context(self, base_context=None, user=None):
        """Return action context with optional lang override."""
        self.ensure_one()
        context = dict(base_context or {})
        context['lang'] = self._get_effective_module_lang(user=user)
        return context

    def _apply_ui_language_to_actions(self):
        """Apply language override and visible labels for module navigation."""
        for record in self:
            lang_key = 'es' if record._get_effective_module_lang() != 'en_US' else 'en'

            action_xmlids = [
                'gesys_control_users_v18.action_user_action_all',
                'gesys_control_users_v18.action_user_action_by_employee',
                'gesys_control_users_v18.action_user_action_line',
                'gesys_control_users_v18.action_user_action_rule',
                'gesys_control_users_v18.action_user_activity',
                'gesys_control_users_v18.action_statistics_report_wizard',
                'gesys_control_users_v18.action_user_activity_dashboard',
                'gesys_control_users_v18.action_statistics_dashboard',
            ]
            for xmlid in action_xmlids:
                action = self.env.ref(xmlid, raise_if_not_found=False)
                if not action or not hasattr(action, 'context'):
                    continue

                raw_context = action.context or '{}'
                try:
                    parsed = ast.literal_eval(raw_context) if isinstance(raw_context, str) else dict(raw_context)
                    base_context = parsed if isinstance(parsed, dict) else {}
                except Exception:
                    base_context = {}

                new_context = record._get_module_lang_action_context(base_context)
                action.sudo().with_context(gesys_control_skip_tracking=True).write({
                    'context': repr(new_context)
                })

            # Keep module navigation labels aligned with selected module language.
            menu_name_map = {
                'gesys_control_users_v18.menu_control_root': {'en': 'Control', 'es': 'Control'},
                'gesys_control_users_v18.menu_control_user_actions': {'en': 'User Actions', 'es': 'Acciones de Usuarios'},
                'gesys_control_users_v18.menu_control_by_employee': {'en': 'Actions by Employee', 'es': 'Acciones por Empleado'},
                'gesys_control_users_v18.menu_control_log_lines': {'en': 'Change Lines', 'es': 'Lineas de cambio'},
                'gesys_control_users_v18.menu_control_user_activity': {'en': 'User Activity', 'es': 'Actividad Usuarios'},
                'gesys_control_users_v18.menu_control_statistics': {'en': 'Statistics', 'es': 'Estadisticas'},
                'gesys_control_users_v18.menu_control_rules': {'en': 'Rules', 'es': 'Reglas'},
                'gesys_control_users_v18.menu_control_config': {'en': 'Configuration', 'es': 'Configuracion'},
            }
            action_name_map = {
                'gesys_control_users_v18.action_user_action_all': {'en': 'User Actions', 'es': 'Acciones de Usuarios'},
                'gesys_control_users_v18.action_user_action_by_employee': {'en': 'Actions by Employee', 'es': 'Acciones por Empleado'},
                'gesys_control_users_v18.action_user_action_line': {'en': 'Change Lines', 'es': 'Lineas de cambio'},
                'gesys_control_users_v18.action_user_action_rule': {'en': 'Audit Rules', 'es': 'Reglas de auditoria'},
                'gesys_control_users_v18.action_user_activity': {'en': 'User Activity', 'es': 'Actividad Usuarios'},
                'gesys_control_users_v18.action_statistics_report_wizard': {'en': 'Statistics Report', 'es': 'Informe de estadisticas'},
                'gesys_control_users_v18.action_user_activity_dashboard': {'en': 'User Activity', 'es': 'Actividad Usuarios'},
                'gesys_control_users_v18.action_statistics_dashboard': {'en': 'Statistics', 'es': 'Estadisticas'},
                'gesys_control_users_v18.action_user_action_config_server': {'en': 'Configuration', 'es': 'Configuracion'},
            }

            for xmlid, labels in menu_name_map.items():
                menu = self.env.ref(xmlid, raise_if_not_found=False)
                if menu:
                    name = labels.get(lang_key) or labels.get('en')
                    if name and menu.name != name:
                        menu.sudo().with_context(gesys_control_skip_tracking=True).write({'name': name})

            for xmlid, labels in action_name_map.items():
                action = self.env.ref(xmlid, raise_if_not_found=False)
                if action:
                    name = labels.get(lang_key) or labels.get('en')
                    if name and action.name != name:
                        action.sudo().with_context(gesys_control_skip_tracking=True).write({'name': name})

            # Apply visible text swap in the configuration form itself.
            config_view = self.env.ref('gesys_control_users_v18.view_user_action_config_form', raise_if_not_found=False)
            if config_view and config_view.arch_db:
                text_map = {
                    'Control Configuration': 'Configuracion de Control',
                    'Information': 'Informacion',
                    'User Control module configuration': 'Configuracion del modulo Control de Usuarios',
                    'Module Interface Language': 'Idioma de la Interfaz del Modulo',
                    'Time Zone': 'Huso Horario',
                    'Cleanup records older than': 'Limpieza de registros mayores de',
                    'Storage usage': 'Uso de espacio',
                    'Space used by Actions and Change Lines. Updated when opening configuration.': 'Espacio ocupado por Acciones y Lineas de cambio. Se actualiza al abrir la configuracion.',
                    'Automatic Record Cleanup': 'Borrado Automatico de Registros',
                    'Delete Records Now': 'Borrar Registros Ahora',
                    'Enable Automatic Cleanup': 'Activar Borrado Automatico',
                    'If automatic cleanup is enabled, old records are removed based on selected frequency.': 'Si activa el borrado automatico, los registros antiguos se eliminaran segun la frecuencia seleccionada.',
                    'Cleanup runs automatically using a scheduled job.': 'El borrado se ejecuta automaticamente mediante un trabajo programado.',
                    'Once deleted, records cannot be recovered.': 'Una vez eliminados, los registros no se pueden recuperar.',
                    'Working schedule': 'Horario laboral',
                    'In User Activity, out-of-schedule actions are shown in red.': 'En Actividad de usuarios, las acciones fuera de horario se muestran en rojo.',
                    'Users can define their own schedule in their profile (Working schedule tab), which overrides the general one.': 'Los usuarios pueden definir su propio horario en su ficha (pestana Horario laboral), que anula el general.',
                    'Audit options': 'Opciones de auditoria',
                    'Warning:': 'Atencion:',
                    'Read logging can generate high volume.': 'Registrar lecturas puede generar mucho volumen.',
                    'Module Access': 'Acceso al Modulo',
                    'Note:': 'Nota:',
                    'Administrators always keep access.': 'Los administradores siempre tendran acceso.',
                    'Delete ALL': 'Borrar TODO',
                }

                arch_db = config_view.arch_db
                if lang_key == 'es':
                    for en_text, es_text in text_map.items():
                        arch_db = arch_db.replace(en_text, es_text)
                else:
                    for en_text, es_text in text_map.items():
                        arch_db = arch_db.replace(es_text, en_text)

                if arch_db != config_view.arch_db:
                    config_view.sudo().with_context(gesys_control_skip_tracking=True).write({
                        'arch_db': arch_db
                    })

            # Apply language on module field labels to avoid mixed list/form headers.
            field_label_map = {
                ('gesys_control.user_action', 'action_date'): {'en': 'Date', 'es': 'Fecha'},
                ('gesys_control.user_action', 'user_id'): {'en': 'User', 'es': 'Usuario'},
                ('gesys_control.user_action', 'action_type_display'): {'en': 'Action Type (Display)', 'es': 'Tipo de Acción (Display)'},
                ('gesys_control.user_action', 'model_description'): {'en': 'Model Description', 'es': 'Descripción del Modelo'},
                ('gesys_control.user_action', 'record_name'): {'en': 'Record Name', 'es': 'Nombre del Registro'},
                ('gesys_control.user_action', 'record_name_simple'): {'en': 'Record Name (Simple)', 'es': 'Nombre del Registro (Simple)'},
                ('gesys_control.user_action', 'action_description_display'): {'en': 'Description (Display)', 'es': 'Descripción (Display)'},
                ('gesys_control.user_action', 'changed_fields'): {'en': 'Changed fields', 'es': 'Campos cambiados'},
                ('gesys_control.user_action', 'action_method'): {'en': 'Method/Button', 'es': 'Método/Botón'},
                ('gesys_control.user_action', 'company_id'): {'en': 'Company', 'es': 'Compañía'},
                ('gesys_control.user_action_line', 'action_date'): {'en': 'Date and Time', 'es': 'Fecha y Hora'},
                ('gesys_control.user_action_line', 'user_id'): {'en': 'User', 'es': 'Usuario'},
                ('gesys_control.user_action_line', 'user_action_id'): {'en': 'Action', 'es': 'Acción'},
                ('gesys_control.user_action_line', 'field_name'): {'en': 'Field', 'es': 'Campo'},
                ('gesys_control.user_action_line', 'old_value_text'): {'en': 'Old Value', 'es': 'Valor Anterior'},
                ('gesys_control.user_action_line', 'new_value_text'): {'en': 'New Value', 'es': 'Valor Nuevo'},
                ('gesys_control.config', 'ui_language_mode'): {'en': 'Module Interface Language', 'es': 'Idioma de la Interfaz del Módulo'},
                ('gesys_control.config', 'timezone'): {'en': 'Time Zone', 'es': 'Huso Horario'},
                ('gesys_control.config', 'auto_delete_enabled'): {'en': 'Enable Automatic Cleanup', 'es': 'Activar Borrado Automático'},
                ('gesys_control.config', 'delete_frequency'): {'en': 'Cleanup records older than', 'es': 'Limpieza de registros mayores de'},
                ('gesys_control.config', 'work_schedule_enabled'): {'en': 'Enable working schedule', 'es': 'Activar horario laboral'},
                ('gesys_control.config', 'log_read'): {'en': 'Log read operations', 'es': 'Registrar lecturas'},
                ('gesys_control.config', 'log_mode'): {'en': 'Log mode', 'es': 'Modo de registro'},
                ('gesys_control.config', 'allowed_user_ids'): {'en': 'Users with module access', 'es': 'Usuarios con acceso al módulo'},
            }
            Fields = self.env['ir.model.fields'].sudo()
            for (model_name, field_name), labels in field_label_map.items():
                field_rec = Fields.search([('model', '=', model_name), ('name', '=', field_name)], limit=1)
                if not field_rec:
                    continue
                label = labels.get(lang_key) or labels.get('en')
                if label and field_rec.field_description != label:
                    field_rec.with_context(gesys_control_skip_tracking=True).write({
                        'field_description': label
                    })

    def _safe_apply_ui_language_to_actions(self):
        """Best-effort wrapper: language sync must never break web_save."""
        try:
            # If transaction is already aborted (e.g., serialization conflict), skip.
            self.env.cr.execute("SELECT 1")
        except Exception as tx_err:
            _logger.warning(
                "gesys_control: skip ui language sync due transaction state: %s",
                tx_err
            )
            return

        try:
            with self.env.cr.savepoint():
                self._apply_ui_language_to_actions()
        except Exception as sync_err:
            _logger.warning(
                "gesys_control: ui language sync failed (non-blocking): %s",
                sync_err
            )

    def _ensure_cleanup_cron(self):
        """Asegurar frecuencia del cron de limpieza (5 minutos)."""
        try:
            cron = self.env.ref('gesys_control_users_v18.ir_cron_cleanup_old_actions').sudo().with_context(
                gesys_control_skip_tracking=True
            )
            cron.write({
                'interval_number': 5,
                'interval_type': 'minutes',
                'active': True,
                'numbercall': -1,
                'nextcall': fields.Datetime.now(),
            })
        except Exception:
            _logger.warning("No se pudo actualizar el cron de limpieza automática.")
    
    def cleanup_old_records(self):
        """
        Ejecutar limpieza de registros antiguos según configuración.
        Borra solo los registros cuya fecha (action_date) sea anterior a la fecha límite
        calculada según la frecuencia configurada.
        """
        config = self.get_config()
        
        if not config.auto_delete_enabled or config.delete_frequency == 'never':
            return {
                'deleted_count': 0,
                'cutoff_date': None,
            }
        
        # Calcular fecha límite según frecuencia
        # La lógica es: borrar registros que tengan más de X días desde su creación
        now = fields.Datetime.now()
        frequency_delta = {
            '5min': timedelta(minutes=5),
            '48h': timedelta(hours=48),
            'week': timedelta(days=7),
            'month': timedelta(days=30),
            '3months': timedelta(days=90),
            '6months': timedelta(days=180),
            'year': timedelta(days=365),
        }
        
        delta = frequency_delta.get(config.delete_frequency, timedelta(days=0))
        cutoff_date = now - delta
        
        # Buscar registros antiguos (cuya fecha de acción sea anterior a la fecha límite)
        # Esto significa que solo se borran los registros que cumplan el tiempo configurado
        old_actions = self.env['gesys_control.user_action'].sudo().search([
            ('action_date', '<', cutoff_date),
            ('is_protected', '=', False),
        ])
        
        count = len(old_actions)
        if count > 0:
            old_actions.unlink()
            _logger.info(f"Limpieza automática: Se eliminaron {count} registros anteriores a {cutoff_date}")
        
        # Actualizar fecha de última limpieza (solo si hay registro persistido)
        if config.ids:
            config.sudo().write({'last_cleanup_date': now})
        
        return {
            'deleted_count': count,
            'cutoff_date': cutoff_date,
        }

    def cleanup_old_records_manual(self):
        """Limpieza manual según el tiempo seleccionado (sin depender del toggle)."""
        config = self.get_config()
        if config.delete_frequency == 'never':
            return {
                'deleted_count': 0,
                'cutoff_date': None,
            }
        self.env['gesys_control.user_action'].sudo().log_action(
            action_type='purge_all',
            model_name='gesys_control.user_action',
            record_id=False,
            description=f"Limpieza manual por periodo ejecutada por {self.env.user.display_name}",
            user_id=self.env.user.id,
            protected=True,
        )
        now = fields.Datetime.now()
        frequency_delta = {
            '5min': timedelta(minutes=5),
            '48h': timedelta(hours=48),
            'week': timedelta(days=7),
            'month': timedelta(days=30),
            '3months': timedelta(days=90),
            '6months': timedelta(days=180),
            'year': timedelta(days=365),
        }
        delta = frequency_delta.get(config.delete_frequency, timedelta(days=0))
        cutoff_date = now - delta
        old_actions = self.env['gesys_control.user_action'].sudo().search([
            ('action_date', '<', cutoff_date),
            ('is_protected', '=', False),
        ])
        count = len(old_actions)
        if count > 0:
            old_actions.unlink()
            _logger.info(f"Limpieza manual: Se eliminaron {count} registros anteriores a {cutoff_date}")
        if config.ids:
            config.sudo().write({'last_cleanup_date': now})
        return {
            'deleted_count': count,
            'cutoff_date': cutoff_date,
        }

    def action_open_purge_all_wizard(self):
        """Abrir asistente para borrado total."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Delete All Actions',
            'res_model': 'gesys_control.purge_actions_wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': self.env.ref('gesys_control_users_v18.view_purge_actions_wizard_form').id,
            'context': {'default_config_id': self.id},
        }

    def action_print_manual_es(self):
        """Abrir reporte PDF del manual en español."""
        self.ensure_one()
        return self.env.ref('gesys_control_users_v18.action_report_user_manual_es').report_action(self)

    def action_print_manual_en(self):
        """Abrir reporte PDF del manual en inglés."""
        self.ensure_one()
        return self.env.ref('gesys_control_users_v18.action_report_user_manual_en').report_action(self)

    def purge_all_actions(self):
        """Borrar todas las acciones no protegidas y registrar el evento."""
        config = self.get_config()
        env = self.env
        description = f"Borrado total de acciones ejecutado por {env.user.display_name}"
        env['gesys_control.user_action'].sudo().log_action(
            action_type='purge_all',
            model_name='gesys_control.user_action',
            record_id=False,
            description=description,
            user_id=env.user.id,
            protected=True,
        )
        old_actions = env['gesys_control.user_action'].sudo().search([
            ('is_protected', '=', False),
        ])
        count = len(old_actions)
        if count:
            old_actions.unlink()
        if config.ids:
            config.sudo().write({'last_cleanup_date': fields.Datetime.now()})
        return count
    
    
