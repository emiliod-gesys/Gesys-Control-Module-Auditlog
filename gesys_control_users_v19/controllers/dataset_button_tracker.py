# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import logging

try:
    from odoo.addons.web.controllers import dataset as dataset_controller
    BaseDataset = getattr(dataset_controller, "Dataset", None) or getattr(dataset_controller, "DataSet", None)
except Exception:
    dataset_controller = None
    BaseDataset = None

_logger = logging.getLogger(__name__)


if BaseDataset:
    class DatasetButtonTracker(BaseDataset):
        """Interceptar botones para registrar acciones de usuario."""

        @http.route([
            '/web/dataset/call_button',
            '/web/dataset/call_button/<string:model>/<string:method>',
        ], type='jsonrpc', auth='user')
        def call_button(self, model=None, method=None, args=None, kwargs=None):
            args = args or []
            kwargs = kwargs or {}
            result = super().call_button(model, method, args, kwargs)
            try:
                env = request.env
                if 'gesys_control.user_action' not in env:
                    return result
                if env.context.get('gesys_control_skip_tracking'):
                    return result

                excluded_models = {
                    'ir.model', 'ir.model.fields', 'ir.model.data', 'ir.model.access',
                    'ir.ui.view', 'ir.actions.act_window', 'ir.actions.server',
                    'ir.attachment', 'ir.logging', 'ir.config_parameter',
                    'ir.sequence', 'ir.sequence.date_range', 'res.users.log',
                    'mail.message', 'mail.followers', 'mail.channel', 'mail.activity',
                    'res.lang', 'ir.translation', 'res.currency', 'res.currency.rate',
                    'ir.module.module', 'ir.module.module.dependency',
                    'base.automation', 'base.automation.trigger',
                    'bus.presence',
                    'account.move.line',
                    'stock.move', 'stock.move.line', 'stock.picking', 'stock.quant', 'stock.valuation.layer',
                    'pos.order', 'pos.order.line', 'pos.payment',
                    'pos_preparation_display.order', 'pos_preparation_display.orderline',
                }
                if model.startswith('gesys_control.') or model.startswith('bus.') or model in excluded_models:
                    return result

                # args usually: [record_ids], sometimes [[record_ids], ...]
                record_ids = []
                if args and isinstance(args[0], (list, tuple)):
                    record_ids = list(args[0])

                model_description = model
                if model in env:
                    model_description = env[model]._description or model

                description = f"Boton {method} en {model_description}"
                user_id = env.user.id
                ip_address = env.context.get('ip_address')
                http_ctx = {}
                try:
                    if request and hasattr(request, 'httprequest') and request.httprequest:
                        http_ctx['http_request_path'] = getattr(request.httprequest, 'path', '') or ''
                        sid = getattr(request.session, 'sid', None) if request.session else None
                        http_ctx['http_session_id'] = str(sid) if sid else None
                except Exception:
                    pass

                if record_ids:
                    for rec_id in record_ids:
                        env['gesys_control.user_action'].sudo().with_context(**http_ctx).log_action(
                            action_type='button',
                            model_name=model,
                            record_id=rec_id,
                            description=description,
                            user_id=user_id,
                            ip_address=ip_address,
                            action_method=method,
                        )
                else:
                    env['gesys_control.user_action'].sudo().with_context(**http_ctx).log_action(
                        action_type='button',
                        model_name=model,
                        record_id=False,
                        description=description,
                        user_id=user_id,
                        ip_address=ip_address,
                        action_method=method,
                    )
            except Exception as exc:
                _logger.debug("Error al rastrear botón %s en %s: %s", method, model, exc)
            return result
else:
    _logger.warning("Dataset controller no disponible; tracking de botones desactivado")
