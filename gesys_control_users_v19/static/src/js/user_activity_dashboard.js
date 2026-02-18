/** @odoo-module */

import { Component, onMounted, onPatched, onWillStart, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { loadJS } from "@web/core/assets";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

export class UserActivityDashboard extends Component {
    setup() {
        this.state = useState({
            period: "day",
            date: this._getTodayString(),
            labels: [],
            users: [],
            work_schedule_enabled: false,
            loading: true,
        });
        this.rootRef = useRef("dashboardRoot");
        this._charts = new Map();

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            await this._loadData();
        });

        onMounted(() => this._renderCharts());
        onPatched(() => this._renderCharts());
    }

    _getTodayString() {
        // Usar fecha local del navegador (no UTC) para alinear con el día de trabajo del usuario.
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, "0");
        const day = String(now.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
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
        const result = await rpc("/gesys_control/user_activity_data", {
            period: this.state.period,
            date_anchor: this.state.date,
        });
        this.state.labels = result.labels || [];
        this.state.users = result.users || [];
        this.state.work_schedule_enabled = result.work_schedule_enabled || false;
        this.state.loading = false;
    }

    _destroyCharts() {
        for (const chart of this._charts.values()) {
            if (chart && chart.destroy) {
                chart.destroy();
            }
        }
        this._charts.clear();
    }

    _renderCharts() {
        this._destroyCharts();
        const root = this.rootRef.el;
        if (!root) {
            return;
        }
        const labels = this.state.labels || [];
        root.querySelectorAll("canvas[data-user-id]").forEach((canvas) => {
            const userId = Number(canvas.dataset.userId);
            const user = this.state.users.find((item) => item.id === userId);
            if (!user) {
                return;
            }
            const outOfSchedule = user.out_of_schedule || [];
            const pointBg = labels.map((_, i) =>
                outOfSchedule[i] ? "#dc3545" : "rgba(31, 119, 180, 0.8)"
            );
            const pointBorder = labels.map((_, i) =>
                outOfSchedule[i] ? "#dc3545" : "#1f77b4"
            );
            const chart = new Chart(canvas.getContext("2d"), {
                type: "line",
                data: {
                    labels,
                    datasets: [
                        {
                            label: user.name,
                            data: user.data || [],
                            borderColor: "#1f77b4",
                            backgroundColor: "rgba(31, 119, 180, 0.15)",
                            fill: true,
                            pointRadius: 3,
                            pointBackgroundColor: pointBg,
                            pointBorderColor: pointBorder,
                            tension: 0.2,
                        },
                    ],
                },
                options: {
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                    },
                    scales: {
                        x: {
                            ticks: { maxRotation: 0 },
                        },
                        y: {
                            beginAtZero: true,
                            ticks: { precision: 0 },
                        },
                    },
                },
            });
            this._charts.set(userId, chart);
        });
    }

    get emptyMessage() {
        if (this.state.loading) {
            return _t("Cargando...");
        }
        return _t("Sin datos para mostrar");
    }
}

UserActivityDashboard.template = "gesys_control_user_activity_dashboard";

registry.category("actions").add("gesys_control_user_activity_dashboard", UserActivityDashboard);
