# -*- coding: utf-8 -*-

from datetime import datetime, timedelta, time

from dateutil.relativedelta import relativedelta

import pytz

from odoo import fields, http
from odoo.http import request


class UserActivityDashboardController(http.Controller):
    @http.route('/gesys_control/user_activity_data', type='jsonrpc', auth='user')
    def user_activity_data(self, period='day', date_anchor=None):
        env = request.env
        base_date = fields.Date.from_string(date_anchor) if date_anchor else fields.Date.context_today(env.user)
        config = env['gesys_control.config'].sudo().get_config(ensure_setup=False)
        tz_name = config.timezone or env.user.tz or 'UTC'

        if period == 'week':
            start_date = base_date - relativedelta(days=base_date.weekday())
            end_date = start_date + relativedelta(days=7)
            group_field = 'action_weekday'
            buckets = ['1', '2', '3', '4', '5']
            labels = ['Lun', 'Mar', 'Mie', 'Jue', 'Vie']
        elif period == 'month':
            start_date = base_date.replace(day=1)
            end_date = start_date + relativedelta(months=1)
            group_field = 'action_day_of_month'
            total_days = (end_date - start_date).days
            buckets = list(range(1, total_days + 1))
            labels = [str(day) for day in buckets]
        else:
            start_date = base_date
            end_date = start_date + relativedelta(days=1)
            group_field = 'action_hour'
            buckets = list(range(0, 24))
            labels = [str(hour) for hour in buckets]

        tz = pytz.timezone(tz_name)
        start_local = tz.localize(datetime.combine(start_date, time.min))
        end_local = tz.localize(datetime.combine(end_date, time.min))
        start_dt = start_local.astimezone(pytz.utc).replace(tzinfo=None)
        end_dt = end_local.astimezone(pytz.utc).replace(tzinfo=None)

        users = env['res.users'].search([('active', '=', True)], order='name')
        user_ids = users.ids

        domain = [
            ('action_date', '>=', fields.Datetime.to_string(start_dt)),
            ('action_date', '<', fields.Datetime.to_string(end_dt)),
            ('user_id', 'in', user_ids),
        ]

        if period == 'week':
            domain.append((group_field, 'in', buckets))

        groups = env['gesys_control.user_action'].read_group(
            domain,
            ['id:count'],
            ['user_id', group_field],
            lazy=False
        )

        counts = {}
        for group in groups:
            user_value = group.get('user_id')
            bucket_value = group.get(group_field)
            if not user_value or bucket_value is False:
                continue
            user_id = user_value[0]
            counts[(user_id, bucket_value)] = group.get('__count', 0)

        data = []
        work_schedule_enabled = bool(getattr(config, 'work_schedule_enabled', False))
        for user in users:
            series = [counts.get((user.id, bucket), 0) for bucket in buckets]
            out_of_schedule = self._compute_out_of_schedule_for_user(
                config, user, period, base_date, start_date, buckets
            )
            data.append({
                'id': user.id,
                'name': user.display_name,
                'data': series,
                'out_of_schedule': out_of_schedule,
            })

        return {
            'labels': labels,
            'users': data,
            'work_schedule_enabled': work_schedule_enabled,
        }

    def _compute_out_of_schedule_for_user(self, config, user, period, base_date, start_date, buckets):
        """Retorna lista de bool: True = fuera de horario, False = en horario.
        Usa horario del usuario si gesys_work_schedule_override, sino el general.
        """
        if not getattr(config, 'work_schedule_enabled', False):
            return [False] * len(buckets)

        # Horario por usuario (anula el general) o general
        if getattr(user, 'gesys_work_schedule_override', False):
            days_str = getattr(user, 'gesys_work_schedule_days', None) or '1,2,3,4,5'
            start_h = float(getattr(user, 'gesys_work_schedule_start', 8) or 8)
            end_h = float(getattr(user, 'gesys_work_schedule_end', 18) or 18)
        else:
            days_str = getattr(config, 'work_schedule_days', None) or '1,2,3,4,5'
            start_h = float(getattr(config, 'work_schedule_start', 8) or 8)
            end_h = float(getattr(config, 'work_schedule_end', 18) or 18)

        try:
            work_days = set(
                int(x.strip()) for x in days_str.split(',')
                if x.strip().isdigit()
            )
        except (ValueError, AttributeError):
            work_days = {1, 2, 3, 4, 5}

        result = []
        if period == 'day':
            # buckets = [0,1,...,23] (horas)
            # weekday: 0=Mon, 6=Sun -> iso: 1=Mon, 7=Sun
            weekday = base_date.isoweekday()
            if weekday not in work_days:
                return [True] * 24
            for hour in buckets:
                h = int(hour) if isinstance(hour, (int, float)) else int(hour)
                result.append(h < start_h or h >= end_h)
        elif period == 'week':
            # buckets = ['1','2','3','4','5'] (Lun-Vie)
            for b in buckets:
                wd = int(b) if isinstance(b, int) else int(str(b).strip())
                result.append(wd not in work_days)
        else:
            # period == 'month': buckets = [1,2,...,31] (días del mes)
            for day_num in buckets:
                d = int(day_num) if isinstance(day_num, int) else int(day_num)
                try:
                    dt = start_date + timedelta(days=d - 1)
                    weekday = dt.isoweekday()
                    result.append(weekday not in work_days)
                except (ValueError, OverflowError):
                    result.append(True)
        return result
