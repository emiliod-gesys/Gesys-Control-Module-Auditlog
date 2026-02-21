# -*- coding: utf-8 -*-

from odoo import models, api
import logging
import json

_logger = logging.getLogger(__name__)


def _get_http_context(env):
    """Obtener path y sesion HTTP si hay request."""
    try:
        from odoo.http import request
        if request and hasattr(request, 'httprequest') and request.httprequest:
            path = getattr(request.httprequest, 'path', None) or ''
            sid = getattr(request.session, 'sid', None) if request.session else None
            return {'http_request_path': path, 'http_session_id': str(sid) if sid else None}
    except Exception:
        pass
    return {}


def _get_tracking_user_id(env):
    """Resolver el usuario real que debe registrarse."""
    if not env.user:
        return False
    if env.su:
        uid = env.context.get('uid')
        if uid and uid != 1:
            return uid
        return False
    return env.user.id


# Interceptar las operaciones base del ORM para TODOS los modelos
# Model es la clase base que todos los modelos de Odoo heredan
Model = models.Model  # Acceder a través del módulo models
_original_create = Model.create
_original_write = Model.write
_original_unlink = Model.unlink
_original_read = Model.read
_original_export_data = getattr(Model, 'export_data', None)


def _serialize_value(record, field_name):
    field = record._fields.get(field_name)
    if not field:
        return None
    value = record[field_name]
    try:
        if field.type == 'many2one':
            return {'id': value.id, 'name': value.display_name} if value else False
        if field.type in ('one2many', 'many2many'):
            ids = value.ids if value else []
            return ids if len(ids) <= 20 else {'count': len(ids)}
        if field.type == 'binary':
            return '[binary]'
        return value
    except Exception:
        return None


def _track_action_universal(self, action_type, description=None, action_method=None,
                            changed_fields=None, old_values=None, new_values=None, line_vals=None):
    """
    M?todo helper universal para registrar una acci?n en cualquier modelo
    """
    try:
        # Verificar si el m?dulo est? instalado
        if 'gesys_control.user_action' not in self.env:
            return
        if self.env.context.get('gesys_control_skip_tracking'):
            return
        
        user_id = _get_tracking_user_id(self.env)
        if not user_id:
            return
        
        # No rastrear acciones en modelos de control (evitar loops)
        if self._name.startswith('gesys_control.'):
            return
        
        # Excluir modelos que empiezan con "bus" (sistema de mensajería/navegación)
        if self._name.startswith('bus.'):
            return
        
        # Excluir modelos del sistema que no son ?tiles rastrear
        excluded_models = [
            'ir.model', 'ir.model.fields', 'ir.model.data', 'ir.model.access',
            'ir.ui.view', 'ir.actions.act_window', 'ir.actions.server',
            'ir.attachment', 'ir.logging', 'ir.config_parameter',
            'ir.sequence', 'ir.sequence.date_range', 'res.users.log',
            'mail.message', 'mail.followers', 'mail.channel', 'mail.activity',
            'mail.tracking.value',
            'res.lang', 'ir.translation', 'res.currency', 'res.currency.rate',
            'ir.module.module', 'ir.module.module.dependency',
            'base.automation', 'base.automation.trigger',
            'bus.presence',  # User Presence - solo navegación, genera mucho volumen
            'account.move.line',  # Evitar ruido por líneas contables
            'stock.move', 'stock.move.line', 'stock.picking', 'stock.quant', 'stock.valuation.layer',
            'pos.order', 'pos.order.line', 'pos.payment',
            'pos_preparation_display.order', 'pos_preparation_display.orderline',
        ]
        
        if self._name in excluded_models:
            return

        # Reglas: excluir usuario segun config (evitar recursion si tabla no existe)
        if 'gesys_control.rule' in self.env:
            try:
                with self.env.cr.savepoint():
                    rule = self.env['gesys_control.rule'].sudo().search([
                        ('model_id.model', '=', self._name), ('active', '=', True)
                    ], limit=1)
                    if rule and user_id in rule.users_to_exclude_ids.ids:
                        return
            except Exception:
                pass

        # Resolver ID del registro antes de construir la descripcion
        record_id = self.id if hasattr(self, 'id') and isinstance(self.id, int) else False

        # Generar descripci?n si no se proporciona
        if not description:
            model_name = self._name
            model_description = getattr(self, '_description', None) or model_name
            record_name = getattr(self, 'display_name', None)
            
            # Excluir modelos cuya descripción sea "User Presence"
            if model_description and 'User Presence' in str(model_description):
                return
            
            if action_type == 'create':
                description = f"Creacion de {model_description}"
            elif action_type == 'write':
                description = f"Modificacion de {model_description}"
            elif action_type == 'delete' or action_type == 'unlink':
                description = f"Eliminacion de {model_description}"
            elif action_type == 'validate' or action_type == 'post':
                description = f"Validacion/Publicacion de {model_description}"
            elif action_type == 'cancel':
                description = f"Cancelacion de {model_description}"
            else:
                description = f"Accion en {model_description}"

            if record_name:
                description = f"{description} - {record_name} (ID: {record_id})"
        
        ip_address = self.env.context.get('ip_address')
        http_ctx = _get_http_context(self.env)

        if record_id:
            self.env['gesys_control.user_action'].sudo().with_context(**http_ctx).log_action(
                action_type=action_type,
                model_name=self._name,
                record_id=record_id,
                description=description,
                user_id=user_id,
                ip_address=ip_address,
                action_method=action_method,
                changed_fields=changed_fields,
                old_values=old_values,
                new_values=new_values,
                line_vals=line_vals,
            )
    except Exception as e:
        # No queremos que el rastreo rompa las operaciones normales
        _logger.debug(f"Error al rastrear acci?n universal en {getattr(self, '_name', 'unknown')}: {e}")


@api.model_create_multi
def _patched_create(self, vals_list):
    """Versi?n parcheada de create que agrega tracking universal"""
    # Saltar para res.users.log - evita race con registry durante login
    if self._name == 'res.users.log':
        return _original_create(self, vals_list)

    records = _original_create(self, vals_list)
    
    # Rastrear creaci?n para cada registro creado
    for record in records:
        try:
            _track_action_universal(record, 'create')
        except Exception:
            pass  # Ignorar errores de tracking
    
    return records


def _patched_write(self, vals):
    """Versi?n parcheada de write que agrega tracking universal"""
    if not vals:
        return _original_write(self, vals)

    # Saltar tracking para account.move - evita InFailedSqlTransaction al registrar pagos
    if self._name == 'account.move':
        return _original_write(self, vals)

    ignored_fields = {
        '__last_update', 'write_date', 'write_uid', 'create_date', 'create_uid',
        'message_ids', 'message_follower_ids', 'message_main_attachment_id',
        'message_attachment_count', 'activity_ids', 'activity_user_id',
        'activity_type_id', 'activity_summary', 'activity_exception_decoration',
        'activity_exception_icon', 'website_message_ids', 'display_name',
        'parent_path'
    }

    is_settings = self._name == 'res.config.settings'
    fields_to_track = [k for k in vals.keys() if k not in ignored_fields]
    if is_settings and not fields_to_track:
        fields_to_track = list(vals.keys())

    # Regla: campos a excluir (evitar recursion si tabla rule no existe)
    exclude_field_names = set()
    if 'gesys_control.rule' in self.env:
        try:
            with self.env.cr.savepoint():
                rule = self.env['gesys_control.rule'].sudo().search([
                    ('model_id.model', '=', self._name), ('active', '=', True)
                ], limit=1)
                if rule and rule.fields_to_exclude_ids:
                    exclude_field_names = set(rule.fields_to_exclude_ids.mapped('name'))
        except Exception:
            pass
    if exclude_field_names:
        fields_to_track = [f for f in fields_to_track if f not in exclude_field_names]

    fast_mode = False
    if 'gesys_control.config' in self.env:
        try:
            with self.env.cr.savepoint():
                config = self.env['gesys_control.config'].get_config(ensure_setup=False)
                fast_mode = getattr(config, 'log_mode', 'full') == 'fast'
        except Exception:
            pass

    old_values_by_id = {}
    if fields_to_track and not fast_mode:
        for record in self:
            old_values_by_id[record.id] = {
                f: _serialize_value(record, f) for f in fields_to_track if f in record._fields
            }

    result = _original_write(self, vals)

    if result and fields_to_track:
        for record in self:
            try:
                if fast_mode:
                    old_vals = {f: None for f in fields_to_track}
                    new_vals = {f: vals.get(f) for f in fields_to_track}
                    changes = {f: {'old': None, 'new': new_vals[f]} for f in fields_to_track}
                else:
                    old_vals = old_values_by_id.get(record.id, {})
                    if is_settings:
                        new_vals = {f: vals.get(f) for f in fields_to_track}
                    else:
                        new_vals = {f: _serialize_value(record, f) for f in fields_to_track if f in record._fields}
                    changes = {f: {'old': old_vals.get(f), 'new': new_vals.get(f)}
                               for f in new_vals.keys()
                               if old_vals.get(f) != new_vals.get(f)}
                    if is_settings and not changes:
                        changes = {f: {'old': old_vals.get(f), 'new': new_vals.get(f)} for f in new_vals.keys()}
                if not changes:
                    continue
                changed_fields = ', '.join(changes.keys())
                model_description = getattr(record, '_description', None) or record._name
                record_name = getattr(record, 'display_name', None)
                summary_parts = []
                for idx, (field, diff) in enumerate(changes.items()):
                    if idx >= 3:
                        break
                    summary_parts.append(f"{field}: {diff.get('old')} -> {diff.get('new')}")
                summary = '; '.join(summary_parts)
                description = f"Modificacion de {model_description}"
                if record_name:
                    description += f" - {record_name} (ID: {record.id})"
                if summary:
                    description += f" | Cambios: {summary}"
                line_vals = [
                    {'field_name': f, 'old_value_text': str(d.get('old') or ''),
                     'new_value_text': str(d.get('new') or '')}
                    for f, d in changes.items()
                ]
                _track_action_universal(
                    record,
                    'write',
                    description=description,
                    changed_fields=changed_fields,
                    old_values=json.dumps({k: v['old'] for k, v in changes.items()}, default=str),
                    new_values=json.dumps({k: v['new'] for k, v in changes.items()}, default=str),
                    line_vals=line_vals,
                )
            except Exception:
                pass

    return result


def _patched_read(self, fields=None, load='_classic_read'):
    """Parche para registrar lecturas (opcional)."""
    result = _original_read(self, fields=fields, load=load)
    try:
        if self.env.context.get('gesys_control_skip_tracking'):
            return result
        if 'gesys_control.user_action' not in self.env or 'gesys_control.config' not in self.env:
            return result
        config = None
        log_read_enabled = False
        try:
            with self.env.cr.savepoint():
                # ensure_setup=False: evitar writes (sync grupo) durante reads
                config = self.env['gesys_control.config'].get_config(ensure_setup=False)
                log_read_enabled = bool(config and getattr(config, 'log_read', False))
        except Exception:
            return result
        if not log_read_enabled:
            return result
        user_id = _get_tracking_user_id(self.env)
        if not user_id or not self.ids:
            return result
        if self._name.startswith('gesys_control.') or self._name.startswith('bus.'):
            return result
        excluded = {
            'ir.model', 'ir.model.fields', 'ir.model.data', 'ir.model.access',
            'ir.ui.view', 'ir.actions.act_window', 'mail.message', 'bus.presence',
            'res.lang', 'ir.translation', 'res.currency', 'res.currency.rate',
        }
        if self._name in excluded:
            return result
        if len(self) > 10:
            return result
        if 'gesys_control.rule' in self.env:
            try:
                with self.env.cr.savepoint():
                    rule = self.env['gesys_control.rule'].sudo().search([
                        ('model_id.model', '=', self._name), ('active', '=', True)
                    ], limit=1)
                    if rule and user_id in rule.users_to_exclude_ids.ids:
                        return result
            except Exception:
                return result
        model_desc = getattr(self, '_description', None) or self._name
        for rec in self:
            if not isinstance(rec.id, int):
                continue
            desc = f"Lectura de {model_desc}"
            try:
                disp = rec.display_name
                if disp:
                    desc += f" - {disp} (ID: {rec.id})"
            except Exception:
                desc += f" (ID: {rec.id})"
            http_ctx = _get_http_context(self.env)
            self.env['gesys_control.user_action'].sudo().with_context(**http_ctx).log_action(
                action_type='read',
                model_name=self._name,
                record_id=rec.id,
                description=desc,
                user_id=user_id,
            )
    except Exception as e:
        _logger.debug(f"Error al rastrear read en {getattr(self, '_name', '?')}: {e}")
    return result


def _patched_unlink(self):
    """Versi?n parcheada de unlink que agrega tracking universal"""
    # Rastrear eliminaci?n ANTES de eliminar (para tener el ID)
    for record in self:
        try:
            _track_action_universal(record, 'delete')
        except Exception:
            pass  # Ignorar errores de tracking
    
    return _original_unlink(self)


def _track_export_action(self):
    """Registrar exportaciones desde cualquier modelo."""
    try:
        if 'gesys_control.user_action' not in self.env:
            return
        if self.env.context.get('gesys_control_skip_tracking'):
            return
        user_id = _get_tracking_user_id(self.env)
        if not user_id:
            return
        if self._name.startswith('gesys_control.') or self._name.startswith('bus.'):
            return
        excluded_models = {
            'ir.model', 'ir.model.fields', 'ir.model.data', 'ir.model.access',
            'ir.ui.view', 'ir.actions.act_window', 'ir.actions.server',
            'ir.attachment', 'ir.logging', 'ir.config_parameter',
            'ir.sequence', 'ir.sequence.date_range', 'res.users.log',
            'mail.message', 'mail.followers', 'mail.channel', 'mail.activity',
            'mail.tracking.value',
            'res.lang', 'ir.translation', 'res.currency', 'res.currency.rate',
            'ir.module.module', 'ir.module.module.dependency',
            'base.automation', 'base.automation.trigger',
            'bus.presence',
            'account.move.line',
            'stock.move', 'stock.move.line', 'stock.picking', 'stock.quant', 'stock.valuation.layer',
            'pos.order', 'pos.order.line', 'pos.payment',
            'pos_preparation_display.order', 'pos_preparation_display.orderline',
        }
        if self._name in excluded_models:
            return

        model_description = getattr(self, '_description', None) or self._name
        record_count = len(self)
        record_id = self.id if record_count == 1 else False
        description = f"Exportacion de {model_description} - registros: {record_count}"
        if record_id and getattr(self, 'display_name', None):
            description = f"{description} - {self.display_name}"
        http_ctx = _get_http_context(self.env)
        self.env['gesys_control.user_action'].sudo().with_context(**http_ctx).log_action(
            action_type='export',
            model_name=self._name,
            record_id=record_id,
            description=description,
            user_id=user_id,
            ip_address=self.env.context.get('ip_address'),
        )
    except Exception as e:
        _logger.debug(f"Error al rastrear exportacion en {getattr(self, '_name', 'unknown')}: {e}")


def _patched_export_data(self, fields_to_export, *args, **kwargs):
    """Parche para registrar exportaciones."""
    result = _original_export_data(self, fields_to_export, *args, **kwargs)
    try:
        _track_export_action(self)
    except Exception:
        pass
    return result


# Aplicar parches a nivel del ORM base - esto intercepta TODOS los modelos
# Solo se aplica si el m?dulo est? instalado
try:
    Model.create = _patched_create
    Model.write = _patched_write
    Model.unlink = _patched_unlink
    Model.read = _patched_read
    if _original_export_data:
        Model.export_data = _patched_export_data
    _logger.info("Tracking universal aplicado a nivel del ORM base")
except Exception as e:
    _logger.error(f"Error al aplicar tracking universal: {e}")
