/** @odoo-module */

import { Component, onMounted, onPatched, onWillStart, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { loadJS } from "@web/core/assets";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

const CHART_COLORS = [
    "rgb(31, 119, 180)",
    "rgb(255, 127, 14)",
    "rgb(44, 160, 44)",
    "rgb(214, 39, 40)",
    "rgb(148, 103, 189)",
    "rgb(140, 86, 75)",
    "rgb(227, 119, 194)",
    "rgb(127, 127, 127)",
    "rgb(188, 189, 34)",
    "rgb(23, 190, 207)",
];

export class StatisticsDashboard extends Component {
    setup() {
        this.state = useState({
            period: "day",
            date: this._getTodayString(),
            data: {
                labels: [],
                by_type: [],
                by_user: [],
                by_model: [],
                trend: [],
                total: 0,
            },
            loading: true,
        });
        this.chartTrendRef = useRef("chartTrend");
        this.chartByTypeRef = useRef("chartByType");
        this.chartByUserRef = useRef("chartByUser");
        this.chartByModelRef = useRef("chartByModel");
        this._charts = [];

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            await this._loadData();
        });

        onMounted(() => this._renderCharts());
        onPatched(() => this._renderCharts());
    }

    _getTodayString() {
        // Usar fecha local del navegador (no UTC) para evitar desfase de día.
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, "0");
        const day = String(now.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    onReportClick() {
        const pathname = window.location.pathname;
        const base = pathname.includes("/web") ? pathname.split("/web")[0] || "" : "";
        const url = `${window.location.origin}${base}/gesys_control/report_excel?period=${this.state.period}&date_anchor=${this.state.date}`;
        window.open(url, "_blank");
    }

    async onPeriodChange(ev) {
        this.state.period = ev.target.value;
        await this._loadData();
    }

    async onDateChange(ev) {
        this.state.date = ev.target.value || this._getTodayString();
        await this._loadData();
    }

    async _loadData() {
        this.state.loading = true;
        const result = await rpc("/gesys_control/statistics_data", {
            period: this.state.period,
            date_anchor: this.state.date,
        });
        this.state.data = {
            labels: result.labels || [],
            by_type: result.by_type || [],
            by_user: result.by_user || [],
            by_model: result.by_model || [],
            trend: result.trend || [],
            total: result.total ?? 0,
        };
        this.state.loading = false;
    }

    _destroyCharts() {
        for (const chart of this._charts) {
            if (chart && chart.destroy) {
                chart.destroy();
            }
        }
        this._charts = [];
    }

    _renderCharts() {
        this._destroyCharts();
        const { labels, by_type, by_user, by_model, trend } = this.state.data;

        const trendEl = this.chartTrendRef.el;
        if (trendEl && labels.length) {
            const chart = new Chart(trendEl.getContext("2d"), {
                type: "line",
                data: {
                    labels,
                    datasets: [{
                        label: _t("Acciones"),
                        data: trend,
                        borderColor: CHART_COLORS[0],
                        backgroundColor: "rgba(31, 119, 180, 0.15)",
                        fill: true,
                        pointRadius: 2,
                        tension: 0.2,
                    }],
                },
                options: {
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { maxRotation: 0 } },
                        y: { beginAtZero: true, ticks: { precision: 0 } },
                    },
                },
            });
            this._charts.push(chart);
        }

        const byTypeEl = this.chartByTypeRef.el;
        if (byTypeEl && by_type.length) {
            const chart = new Chart(byTypeEl.getContext("2d"), {
                type: "bar",
                data: {
                    labels: by_type.map((d) => d.label),
                    datasets: [{
                        label: _t("Cantidad"),
                        data: by_type.map((d) => d.count),
                        backgroundColor: CHART_COLORS.slice(0, by_type.length),
                    }],
                },
                options: {
                    maintainAspectRatio: false,
                    indexAxis: "y",
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { beginAtZero: true, ticks: { precision: 0 } },
                    },
                },
            });
            this._charts.push(chart);
        }

        const byUserEl = this.chartByUserRef.el;
        if (byUserEl && by_user.length) {
            const chart = new Chart(byUserEl.getContext("2d"), {
                type: "bar",
                data: {
                    labels: by_user.map((d) => d.label),
                    datasets: [{
                        label: _t("Acciones"),
                        data: by_user.map((d) => d.count),
                        backgroundColor: CHART_COLORS[1],
                    }],
                },
                options: {
                    maintainAspectRatio: false,
                    indexAxis: "y",
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { beginAtZero: true, ticks: { precision: 0 } },
                    },
                },
            });
            this._charts.push(chart);
        }

        const byModelEl = this.chartByModelRef.el;
        if (byModelEl && by_model.length) {
            const chart = new Chart(byModelEl.getContext("2d"), {
                type: "bar",
                data: {
                    labels: by_model.map((d) => d.label),
                    datasets: [{
                        label: _t("Acciones"),
                        data: by_model.map((d) => d.count),
                        backgroundColor: CHART_COLORS[2],
                    }],
                },
                options: {
                    maintainAspectRatio: false,
                    indexAxis: "y",
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { beginAtZero: true, ticks: { precision: 0 } },
                    },
                },
            });
            this._charts.push(chart);
        }
    }

    get emptyMessage() {
        return _t("Cargando...");
    }
}

StatisticsDashboard.template = "gesys_control_statistics_dashboard";

registry.category("actions").add("gesys_control_statistics_dashboard", StatisticsDashboard);
