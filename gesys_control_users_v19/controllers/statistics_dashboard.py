# -*- coding: utf-8 -*-

import io
from datetime import datetime, time

from dateutil.relativedelta import relativedelta

import pytz

from odoo import fields, http
from odoo.http import request, content_disposition


class StatisticsDashboardController(http.Controller):
    @http.route('/gesys_control/statistics_data', type='jsonrpc', auth='user')
    def statistics_data(self, period='day', date_anchor=None):
        env = request.env
        base_date = fields.Date.from_string(date_anchor) if date_anchor else fields.Date.context_today(env.user)
        config = env['gesys_control.config'].sudo().get_config(ensure_setup=False)
        tz_name = getattr(config, 'timezone', None) or env.user.tz or 'UTC'

        if period == 'week':
            start_date = base_date - relativedelta(days=base_date.weekday())
            end_date = start_date + relativedelta(days=7)
            group_field = 'action_weekday'
            buckets = ['1', '2', '3', '4', '5', '6', '7']
            labels = ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom']
        elif period == 'month':
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
        if period == 'week':
            domain.append((group_field, 'in', buckets))

        Action = env['gesys_control.user_action']

        # 1. Acciones por tipo (bar)
        by_type = Action.read_group(domain, ['id:count'], ['action_type'], lazy=False)
        by_type_data = [{'label': g['action_type'] or 'other', 'count': g['__count']} for g in by_type]

        # 2. Top usuarios (bar)
        by_user = Action.read_group(domain, ['id:count'], ['user_id'], lazy=False)
        by_user_sorted = sorted(by_user, key=lambda x: x.get('__count', 0), reverse=True)[:10]
        by_user_data = []
        for g in by_user_sorted:
            uid = g.get('user_id')
            if uid:
                by_user_data.append({'id': uid[0], 'label': uid[1], 'count': g['__count']})

        # 3. Top modelos (bar)
        by_model = Action.read_group(domain, ['id:count'], ['model_name'], lazy=False)
        by_model_sorted = sorted(by_model, key=lambda x: x.get('__count', 0), reverse=True)[:10]
        by_model_data = [{'label': g['model_name'] or '-', 'count': g['__count']} for g in by_model_sorted]

        # 4. Tendencia (line) - total por bucket, mismo formato que Actividad
        trend = Action.read_group(domain, ['id:count'], [group_field], lazy=False)
        trend_map = {str(g.get(group_field)): g['__count'] for g in trend if g.get(group_field) is not False}
        trend_data = [trend_map.get(b, 0) for b in buckets]

        # 5. KPIs
        total = Action.search_count(domain)

        return {
            'labels': labels,
            'by_type': by_type_data,
            'by_user': by_user_data,
            'by_model': by_model_data,
            'trend': trend_data,
            'total': total,
        }

    def _get_report_data_for_period(self, period, date_anchor):
        """Obtener datos del reporte para un período."""
        env = request.env
        if not date_anchor:
            date_anchor = fields.Date.context_today(env.user)
        base_date = fields.Date.from_string(str(date_anchor)) if isinstance(date_anchor, str) else date_anchor
        config = env['gesys_control.config'].sudo().get_config(ensure_setup=False)
        tz_name = getattr(config, 'timezone', None) or env.user.tz or 'UTC'

        if period == 'week':
            start_date = base_date - relativedelta(days=base_date.weekday())
            end_date = start_date + relativedelta(days=7)
            group_field = 'action_weekday'
            buckets = ['1', '2', '3', '4', '5', '6', '7']
            labels = ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom']
        elif period == 'month':
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
        if period == 'week':
            domain.append((group_field, 'in', buckets))

        Action = env['gesys_control.user_action']

        by_type = Action.read_group(domain, ['id:count'], ['action_type'], lazy=False)
        by_type_data = [{'label': g['action_type'] or 'other', 'count': g['__count']} for g in by_type]

        by_user = Action.read_group(domain, ['id:count'], ['user_id'], lazy=False)
        by_user_sorted = sorted(by_user, key=lambda x: x.get('__count', 0), reverse=True)[:15]
        by_user_data = [{'label': g['user_id'][1], 'count': g['__count']} for g in by_user_sorted if g.get('user_id')]

        by_model = Action.read_group(domain, ['id:count'], ['model_name'], lazy=False)
        by_model_sorted = sorted(by_model, key=lambda x: x.get('__count', 0), reverse=True)[:15]
        by_model_data = [{'label': g['model_name'] or '-', 'count': g['__count']} for g in by_model_sorted]

        trend = Action.read_group(domain, ['id:count'], [group_field], lazy=False)
        trend_map = {str(g.get(group_field)): g['__count'] for g in trend if g.get(group_field) is not False}
        trend_data = [{'label': labels[i], 'count': trend_map.get(b, 0)} for i, b in enumerate(buckets)]

        total = Action.search_count(domain)
        period_label = {'day': 'Día', 'week': 'Semana', 'month': 'Mes'}.get(period, period)
        return {
            'period_label': period_label,
            'date_from': start_date,
            'date_to': end_date - relativedelta(days=1) if period != 'day' else start_date,
            'total': total,
            'by_type': by_type_data,
            'by_user': by_user_data,
            'by_model': by_model_data,
            'trend': trend_data,
        }

    @http.route('/gesys_control/report_excel', type='http', auth='user')
    def report_excel(self, period='day', date_anchor=None, **kw):
        """Generar reporte Excel con los filtros actuales del dashboard."""
        try:
            import xlsxwriter
        except ImportError:
            return request.make_response(
                'El módulo xlsxwriter no está instalado. Ejecute: pip install xlsxwriter',
                status=500,
                headers=[('Content-Type', 'text/plain')],
            )
        if not date_anchor:
            date_anchor = fields.Date.context_today(request.env.user)
        data = self._get_report_data_for_period(period, date_anchor)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        bold = workbook.add_format({'bold': True})
        header = workbook.add_format({'bold': True, 'bg_color': '#4472C4', 'font_color': 'white'})

        # Layout horizontal: 4 tablas en 2x2 (columnas 0, 4, 8, 12)
        sheet = workbook.add_worksheet('Estadísticas')
        col_offsets = [0, 4, 8, 12]

        # Encabezado común (primera fila)
        sheet.merge_range(0, 0, 0, 15, 'Reporte de Actividad - Control de Usuarios', bold)
        sheet.write(1, 0, f"Período: {data['period_label']} | Fecha: {data['date_from']}")
        sheet.write(2, 0, f"Total acciones: {data['total']}")
        start_row = 4

        def write_table(col, title, headers, rows):
            r = start_row
            sheet.write(r, col, title, bold)
            r += 1
            sheet.write(r, col, headers[0], header)
            sheet.write(r, col + 1, headers[1], header)
            r += 1
            for row in rows:
                sheet.write(r, col, row['label'])
                sheet.write(r, col + 1, row['count'])
                r += 1
            return r

        write_table(col_offsets[0], 'Por tipo de acción', ('Tipo', 'Cantidad'), data['by_type'])
        write_table(col_offsets[1], 'Top usuarios', ('Usuario', 'Acciones'), data['by_user'])
        write_table(col_offsets[2], 'Top modelos', ('Modelo', 'Acciones'), data['by_model'])
        write_table(col_offsets[3], 'Tendencia', ('Bucket', 'Cantidad'), data['trend'])

        workbook.close()
        output.seek(0)
        filename = 'Control_%s.xlsx' % date_anchor
        return request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(filename)),
            ],
        )
