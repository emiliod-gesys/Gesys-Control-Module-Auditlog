# -*- coding: utf-8 -*-

from datetime import datetime, time, timedelta
import logging
import pytz

from odoo import api, fields, models, registry

_logger = logging.getLogger(__name__)


class ResUsersLoginTracker(models.Model):
    _inherit = 'res.users'

    @classmethod
    def _login(cls, db, *args, **kwargs):
        """Compatibilidad con firmas antiguas y nuevas."""
        user_agent_env = kwargs.get('user_agent_env')
        uid = False
        if args and isinstance(args[0], dict):
            # Firma nueva: _login(db, credential, user_agent_env=None)
            credential = args[0]
            uid = super()._login(db, credential, user_agent_env=user_agent_env)
        else:
            # Firma antigua: _login(db, login, password, user_agent_env=None)
            login = args[0] if len(args) > 0 else kwargs.get('login')
            password = args[1] if len(args) > 1 else kwargs.get('password')
            uid = super()._login(db, login, password, user_agent_env=user_agent_env)
        if uid:
            try:
                reg = registry(db)
                with reg.cursor() as cr:
                    env = api.Environment(cr, uid, {'uid': uid})
                    cls._log_first_login_of_day(env, uid)
                    cr.commit()
            except Exception as e:
                _logger.warning(f"Error al registrar primer ingreso del día: {e}")
        return uid

    @classmethod
    def _log_first_login_of_day(cls, env, uid):
        if 'gesys_control.user_action' not in env:
            return

        user = env['res.users'].browse(uid)
        config = env['gesys_control.config'].sudo().get_config()
        tz_name = config.timezone or user.tz or 'UTC'
        tz = pytz.timezone(tz_name)

        now_utc = fields.Datetime.now()
        local_now = fields.Datetime.context_timestamp(user.with_context(tz=tz_name), now_utc)
        local_date = local_now.date()

        start_local = tz.localize(datetime.combine(local_date, time.min))
        end_local = start_local + timedelta(days=1)
        start_dt = start_local.astimezone(pytz.utc).replace(tzinfo=None)
        end_dt = end_local.astimezone(pytz.utc).replace(tzinfo=None)

        exists = env['gesys_control.user_action'].sudo().search_count([
            ('user_id', '=', uid),
            ('action_type', '=', 'first_login_day'),
            ('action_date', '>=', fields.Datetime.to_string(start_dt)),
            ('action_date', '<', fields.Datetime.to_string(end_dt)),
        ], limit=1)

        if exists:
            return

        env['gesys_control.user_action'].sudo().log_action(
            action_type='first_login_day',
            model_name='res.users',
            record_id=uid,
            description=f"Primer ingreso del día - {user.display_name}",
            user_id=uid,
        )
