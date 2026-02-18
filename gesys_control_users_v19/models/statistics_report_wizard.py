# -*- coding: utf-8 -*-

from datetime import datetime, time
from dateutil.relativedelta import relativedelta
import pytz

from odoo import api, fields, models


class StatisticsReportWizard(models.TransientModel):
    _name = 'gesys_control.statistics_report_wizard'
    _description = 'Asistente para reportes PDF de estadísticas'

    period = fields.Selection([
        ('day', 'Día'),
        ('week', 'Semana'),
        ('month', 'Mes'),
    ], string='Period', required=True, default='day')
    date_anchor = fields.Date(string='Date', required=True, default=fields.Date.context_today)

    def get_report_data(self):
        """Obtener datos para el reporte (misma lógica que statistics_data)."""
        self.ensure_one()
        env = self.env
        base_date = self.date_anchor
        config = env['gesys_control.config'].sudo().get_config(ensure_setup=False)
        tz_name = getattr(config, 'timezone', None) or env.user.tz or 'UTC'

        if self.period == 'week':
            start_date = base_date - relativedelta(days=base_date.weekday())
            end_date = start_date + relativedelta(days=7)
            group_field = 'action_weekday'
            buckets = ['1', '2', '3', '4', '5', '6', '7']
            labels = ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom']
        elif self.period == 'month':
            start_date = base_date.replace(day=1)
            end_date = start_date + relativedelta(months=1)
            group_field = 'action_day_of_month'
            total_days = (end_date - start_date).days
            buckets = [str(d) for d in range(1, total_days + 1)]
            labels = buckets
        else:
            start_date = base_date
            end_date = start_date + relativedelta(days=1)
            group_field = 'action_hour'
            buckets = [str(h) for h in range(24)]
            labels = buckets

        tz = pytz.timezone(tz_name)
        start_local = tz.localize(datetime.combine(start_date, time.min))
        end_local = tz.localize(datetime.combine(end_date, time.min))
        start_dt = start_local.astimezone(pytz.utc).replace(tzinfo=None)
        end_dt = end_local.astimezone(pytz.utc).replace(tzinfo=None)

        domain = [
            ('action_date', '>=', fields.Datetime.to_string(start_dt)),
            ('action_date', '<', fields.Datetime.to_string(end_dt)),
        ]
        if self.period == 'week':
            domain.append((group_field, 'in', buckets))

        Action = env['gesys_control.user_action']

        by_type = Action.read_group(domain, ['id:count'], ['action_type'], lazy=False)
        by_type_data = [{'label': g['action_type'] or 'other', 'count': g['__count']} for g in by_type]

        by_user = Action.read_group(domain, ['id:count'], ['user_id'], lazy=False)
        by_user_sorted = sorted(by_user, key=lambda x: x.get('__count', 0), reverse=True)[:15]
        by_user_data = []
        for g in by_user_sorted:
            uid = g.get('user_id')
            if uid:
                by_user_data.append({'label': uid[1], 'count': g['__count']})

        by_model = Action.read_group(domain, ['id:count'], ['model_name'], lazy=False)
        by_model_sorted = sorted(by_model, key=lambda x: x.get('__count', 0), reverse=True)[:15]
        by_model_data = [{'label': g['model_name'] or '-', 'count': g['__count']} for g in by_model_sorted]

        trend = Action.read_group(domain, ['id:count'], [group_field], lazy=False)
        trend_map = {str(g.get(group_field)): g['__count'] for g in trend if g.get(group_field) is not False}
        trend_data = [{'label': labels[i], 'count': trend_map.get(b, 0)} for i, b in enumerate(buckets)]

        total = Action.search_count(domain)

        period_label = {'day': 'Día', 'week': 'Semana', 'month': 'Mes'}.get(self.period, self.period)
        return {
            'period_label': period_label,
            'date_from': start_date,
            'date_to': end_date - relativedelta(days=1) if self.period != 'day' else start_date,
            'total': total,
            'by_type': by_type_data,
            'by_user': by_user_data,
            'by_model': by_model_data,
            'trend': trend_data,
        }

    def action_report_activity(self):
        return self.env.ref('gesys_control_users_v19.action_report_activity_summary').report_action(self)

    def action_report_executive(self):
        return self.env.ref('gesys_control_users_v19.action_report_executive_summary').report_action(self)

    def action_report_by_user(self):
        return self.env.ref('gesys_control_users_v19.action_report_by_user').report_action(self)
