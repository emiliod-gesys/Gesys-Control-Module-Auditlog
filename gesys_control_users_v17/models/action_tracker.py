# -*- coding: utf-8 -*-

from odoo import models, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


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


def _log_action(env, action_type, model_name, record_id, description):
    """Loguear una acción de forma segura."""
    if 'gesys_control.user_action' not in env:
        return
    if env.context.get('gesys_control_skip_tracking'):
        return
    user_id = _get_tracking_user_id(env)
    if not user_id:
        return
    ip_address = env.context.get('ip_address')
    try:
        with env.cr.savepoint():
            env['gesys_control.user_action'].sudo().log_action(
                action_type=action_type,
                model_name=model_name,
                record_id=record_id,
                description=description,
                user_id=user_id,
                ip_address=ip_address,
            )
    except Exception as e:
        _logger.debug("Error al registrar accion %s en %s: %s", action_type, model_name, e)


class ActionTrackerMixin(models.AbstractModel):
    """
    Mixin para rastrear acciones de usuarios automรกticamente.
    Heredar este mixin en modelos que quieran rastrear acciones.
    """
    _name = 'gesys_control.action_tracker.mixin'
    _description = 'Mixin para Rastreo de Acciones'
    
    def _track_action(self, action_type, description=None, record_id=None):
        """
        Mรฉtodo helper para registrar una acciรณn
        
        :param action_type: Tipo de acciรณn (create, write, delete, validate, etc.)
        :param description: Descripciรณn opcional de la acciรณn
        :param record_id: ID del registro (por defecto usa self.id)
        """
        try:
            # Verificar si el mรณdulo estรก instalado
            if 'gesys_control.user_action' not in self.env:
                return  # No registrar acciones del sistema
            
            record_id = record_id or (self.id if isinstance(self.id, int) else False)
            
            if not description:
                model_description = self._description or self._name
                record_name = self.display_name if hasattr(self, 'display_name') else ''
                if action_type == 'create':
                    description = f"Creacion de {model_description}"
                elif action_type == 'write':
                    description = f"Modificacion de {model_description}"
                elif action_type == 'delete' or action_type == 'unlink':
                    description = f"Eliminacion de {model_description}"
                elif action_type == 'validate':
                    description = f"Validacion de {model_description}"
                elif action_type == 'post' or action_type == 'action_post':
                    description = f"Publicacion de {model_description}"
                elif action_type == 'cancel' or action_type == 'action_cancel':
                    description = f"Cancelacion de {model_description}"
                else:
                    description = f"Accion en {model_description}"

                if record_name:
                    description = f"{description} - {record_name} (ID: {record_id})"
            
            _log_action(self.env, action_type, self._name, record_id, description)
        except Exception as e:
            # No queremos que el rastreo rompa las operaciones normales
            _logger.warning(f"Error al rastrear acciรณn: {e}")
    
    @api.model_create_multi
    def create(self, vals_list):
        """Interceptar creaciรณn de registros"""
        records = super().create(vals_list)
        
        for record in records:
            record._track_action('create', description=f"Creaciรณn de {record._description or record._name}")
        
        return records
    
    def write(self, vals):
        """Interceptar modificaciรณn de registros"""
        result = super().write(vals)
        
        if result:
            for record in self:
                record._track_action('write', description=f"Modificaciรณn de {record._description or record._name}")
        
        return result
    
    def unlink(self):
        """Interceptar eliminaciรณn de registros"""
        for record in self:
            record._track_action('unlink', description=f"Eliminaciรณn de {record._description or record._name}")
        
        return super().unlink()

    def _get_tracking_user_id(self):
        """Resolver el usuario real que debe registrarse."""
        return _get_tracking_user_id(self.env)


class AccountMoveTracker(models.Model):
    """Heredar account.move para rastrear acciones importantes"""
    _inherit = 'account.move'
    
    def _track_account_action(self, action_type, description):
        """Helper para rastrear acciones de account.move"""
        try:
            if 'gesys_control.user_action' not in self.env:
                return
            for record in self:
                _log_action(self.env, action_type, record._name, record.id, description)
        except Exception as e:
            _logger.warning(f"Error al rastrear acciรณn de account.move: {e}")
    
    def action_post(self):
        """Interceptar publicaciรณn de asientos"""
        result = super().action_post()
        
        for move in self:
            move._track_account_action('post', f"Publicaciรณn de Asiento {move.name}")
        
        return result
    
    def button_draft(self):
        """Interceptar cambio a borrador"""
        result = super().button_draft()
        
        for move in self:
            move._track_account_action('action_draft', f"Asiento {move.name} cambiado a borrador")
        
        return result
    
    def button_cancel(self):
        """Interceptar cancelaciรณn"""
        result = super().button_cancel()
        
        for move in self:
            move._track_account_action('cancel', f"Cancelaciรณn de Asiento {move.name}")
        
        return result


class AccountPaymentTracker(models.Model):
    """Heredar account.payment para rastrear acciones"""
    _inherit = 'account.payment'
    
    def _track_payment_action(self, action_type, description):
        """Helper para rastrear acciones de account.payment"""
        try:
            if 'gesys_control.user_action' not in self.env:
                return
            for record in self:
                _log_action(self.env, action_type, record._name, record.id, description)
        except Exception as e:
            _logger.warning(f"Error al rastrear acciรณn de account.payment: {e}")
    
    def action_post(self):
        """Interceptar publicaciรณn de pagos"""
        result = super().action_post()
        
        for payment in self:
            payment._track_payment_action('post', f"Publicaciรณn de Pago {payment.name}")
        
        return result
    
    def action_draft(self):
        """Interceptar cambio a borrador"""
        result = super().action_draft()
        
        for payment in self:
            payment._track_payment_action('action_draft', f"Pago {payment.name} cambiado a borrador")
        
        return result
    
    def action_cancel(self):
        """Interceptar cancelaciรณn"""
        result = super().action_cancel()
        
        for payment in self:
            payment._track_payment_action('cancel', f"Cancelaciรณn de Pago {payment.name}")
        
        return result


# NOTA: Las herencias de sale.order, purchase.order y pos.session se eliminaron
# porque causaban errores si esos módulos no estaban instalados.
# El tracking universal (universal_tracker.py) ya captura automáticamente
# todas las acciones (create, write, delete) de TODOS los modelos, incluyendo
# estos si están instalados.
#
# Si necesitas tracking específico para acciones especiales como action_confirm,
# button_confirm, etc., puedes agregar estas dependencias al manifest:
# 'depends': ['base', 'mail', 'account', 'sale', 'purchase', 'point_of_sale']


class ProductProductTracker(models.Model):
    """Heredar product.product para rastrear creaciรณn y eliminaciรณn"""
    _inherit = 'product.product'
    
    def _track_product_action(self, action_type, description):
        """Helper para rastrear acciones de product.product"""
        try:
            if 'gesys_control.user_action' not in self.env:
                return
            for record in self:
                _log_action(self.env, action_type, record._name, record.id, description)
        except Exception as e:
            _logger.warning(f"Error al rastrear acciรณn de product.product: {e}")
    
    @api.model_create_multi
    def create(self, vals_list):
        """Interceptar creaciรณn de productos"""
        records = super().create(vals_list)
        
        for record in records:
            record._track_product_action('create', f"Creaciรณn de Producto {record.name or record.default_code or 'Sin nombre'}")
        
        return records
    
    def unlink(self):
        """Interceptar eliminaciรณn de productos"""
        for record in self:
            record._track_product_action('delete', f"Eliminaciรณn de Producto {record.name or record.default_code or 'Sin nombre'}")
        
        return super().unlink()


class ProductTemplateTracker(models.Model):
    """Heredar product.template para rastrear creaciรณn y eliminaciรณn"""
    _inherit = 'product.template'
    
    def _track_template_action(self, action_type, description):
        """Helper para rastrear acciones de product.template"""
        try:
            if 'gesys_control.user_action' not in self.env:
                return
            for record in self:
                _log_action(self.env, action_type, record._name, record.id, description)
        except Exception as e:
            _logger.warning(f"Error al rastrear acciรณn de product.template: {e}")

    @api.model_create_multi
    def create(self, vals_list):
        """Interceptar creaciรณn de plantillas de producto"""
        records = super().create(vals_list)
        
        for record in records:
            record._track_template_action('create', f"Creaciรณn de Plantilla de Producto {record.name or 'Sin nombre'}")
        
        return records
    
    def unlink(self):
        """Interceptar eliminaciรณn de plantillas de producto"""
        for record in self:
            record._track_template_action('delete', f"Eliminaciรณn de Plantilla de Producto {record.name or 'Sin nombre'}")
        
        return super().unlink()


class IrActionsReportTracker(models.Model):
    """Rastrear impresión/generación de reportes."""
    _inherit = 'ir.actions.report'

    def report_action(self, docids, data=None, config=True):
        result = super().report_action(docids, data=data, config=config)
        try:
            self._track_report_action(docids)
        except Exception as e:
            _logger.warning(f"Error al rastrear impresión de reporte: {e}")
        return result

    def _track_report_action(self, docids):
        model_name = self.model or 'ir.actions.report'
        model_description = model_name
        if model_name in self.env:
            model_description = self.env[model_name]._description or model_name
        report_name = self.name or self.report_name or model_description
        description = f"Impresion de reporte {report_name}"

        docid_list = []
        if docids:
            if isinstance(docids, (list, tuple, set)):
                docid_list = list(docids)
            else:
                docid_list = [docids]

        if docid_list:
            for docid in docid_list:
                _log_action(self.env, 'print', model_name, docid, description)
        else:
            _log_action(self.env, 'print', model_name, False, description)


class MailComposeMessageTracker(models.TransientModel):
    """Rastrear envío de correos desde el asistente."""
    _inherit = 'mail.compose.message'

    def action_send_mail(self):
        result = super().action_send_mail()
        self._track_email_action()
        return result

    def send_mail(self, *args, **kwargs):
        result = super().send_mail(*args, **kwargs)
        self._track_email_action()
        return result

    def _track_email_action(self):
        model_name = getattr(self, 'model', None) or self.env.context.get('active_model')
        record_id = getattr(self, 'res_id', None) or self.env.context.get('active_id')
        model_description = model_name
        if model_name and model_name in self.env:
            model_description = self.env[model_name]._description or model_name
        description = f"Envio de correo en {model_description}"
        _log_action(self.env, 'email', model_name or self._name, record_id or False, description)


class MailTemplateTracker(models.Model):
    """Rastrear envío de correos desde plantillas."""
    _inherit = 'mail.template'

    def send_mail(self, res_id, force_send=False, raise_exception=False, email_values=None):
        result = super().send_mail(res_id, force_send=force_send, raise_exception=raise_exception, email_values=email_values)
        self._track_template_email(res_id)
        return result

    def _track_template_email(self, res_id):
        model_name = self.model or self._name
        model_description = model_name
        if model_name in self.env:
            model_description = self.env[model_name]._description or model_name
        description = f"Envio de correo (plantilla) en {model_description}"
        _log_action(self.env, 'email', model_name, res_id or False, description)


class BaseImportImportTracker(models.TransientModel):
    """Rastrear importaciones."""
    _inherit = 'base_import.import'

    def execute_import(self, *args, **kwargs):
        result = super().execute_import(*args, **kwargs)
        self._track_import(args, kwargs)
        return result

    def do(self, *args, **kwargs):
        result = super().do(*args, **kwargs)
        self._track_import(args, kwargs)
        return result

    def _track_import(self, args, kwargs):
        model_name = getattr(self, 'res_model', None) or getattr(self, 'model', None) or self._name
        model_description = model_name
        if model_name in self.env:
            model_description = self.env[model_name]._description or model_name
        row_count = None
        data = kwargs.get('data') or kwargs.get('rows')
        if data is None and len(args) >= 2 and isinstance(args[1], list):
            data = args[1]
        if isinstance(data, list):
            row_count = len(data)
        description = f"Importacion a {model_description}"
        if row_count is not None:
            description = f"{description} - filas: {row_count}"
        _log_action(self.env, 'import', model_name, False, description)


class SaleOrderTracker(models.Model):
    """Rastrear cancelación de órdenes de venta."""
    _inherit = 'sale.order'

    def action_cancel(self):
        result = super().action_cancel()
        for order in self:
            description = f"Cancelacion de Orden de Venta {order.name}"
            _log_action(self.env, 'cancel', order._name, order.id, description)
        return result


class PurchaseOrderTracker(models.Model):
    """Rastrear cancelación de órdenes de compra."""
    _inherit = 'purchase.order'

    def button_cancel(self):
        result = super().button_cancel()
        for order in self:
            description = f"Cancelacion de Orden de Compra {order.name}"
            _log_action(self.env, 'cancel', order._name, order.id, description)
        return result


# PosSessionTracker eliminado - usar tracking universal
