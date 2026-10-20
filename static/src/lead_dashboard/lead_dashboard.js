/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

export class CrmLeadAnalyticsDashboard extends Component {
    static template = "diyacrm.CrmLeadAnalyticsDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.dailyChartRef = useRef("dailyChart");
        this.monthlyChartRef = useRef("monthlyChart");
        this.sourceChartRef = useRef("sourceChart");

        this.dailyChartInstance = null;
        this.monthlyChartInstance = null;
        this.sourceChartInstance = null;

        this.state = useState({
            loading: true,
            datePreset: "all",
            dateFrom: "",
            dateTo: "",
            companyFilter: "all",
            kpi: {
                total: 0,
                active: 0,
                lost: 0,
                won: 0,
                repeat: 0,
                repeat_leads: 0,
                fresh_cost: 0,
                repeat_cost: 0,
                total_cost: 0,
                conversion_pct: 0,
                repeat_lead_ids: [],
            },
            source_data: [],
            company_data: [],
            stage_funnel: [],
            daily_trend: [],
            monthly_trend: [],
            companies: [],
        });

        onWillStart(async () => {
            try {
                if (typeof window.Chart === "undefined") {
                    await loadJS("https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js");
                }
            } catch (e) {
                console.warn("Chart.js load warning:", e);
            }
            await this.loadData();
        });

        onMounted(() => {
            this.renderCharts();
        });
    }

    // ── Date presets ──────────────────────────────────────────────────────
    get today() {
        return new Date().toISOString().split("T")[0];
    }

    setPreset(preset) {
        const today = new Date();
        const fmt = (d) => d.toISOString().split("T")[0];
        let from = "", to = "";

        if (preset === "today") {
            from = fmt(today); to = fmt(today);
        } else if (preset === "week") {
            const mon = new Date(today);
            mon.setDate(today.getDate() - today.getDay() + 1);
            from = fmt(mon); to = fmt(today);
        } else if (preset === "month") {
            from = fmt(new Date(today.getFullYear(), today.getMonth(), 1)); to = fmt(today);
        } else if (preset === "quarter") {
            const q = Math.floor(today.getMonth() / 3);
            from = fmt(new Date(today.getFullYear(), q * 3, 1)); to = fmt(today);
        } else if (preset === "year") {
            from = fmt(new Date(today.getFullYear(), 0, 1)); to = fmt(today);
        }
        // "all" = empty dates
        this.state.datePreset = preset;
        this.state.dateFrom = from;
        this.state.dateTo = to;
        this.loadData();
    }

    async onDateFromChange(ev) {
        this.state.dateFrom = ev.target.value;
        this.state.datePreset = "custom";
        if (this.state.dateTo) await this.loadData();
    }

    async onDateToChange(ev) {
        this.state.dateTo = ev.target.value;
        this.state.datePreset = "custom";
        if (this.state.dateFrom) await this.loadData();
    }

    async onCompanyChange(ev) {
        this.state.companyFilter = ev.target.value;
        await this.loadData();
    }

    // ── Data loading ──────────────────────────────────────────────────────
    async loadData() {
        this.state.loading = true;
        try {
            const res = await this.orm.call("crm.lead", "get_lead_dashboard_data", [], {
                date_from: this.state.dateFrom || false,
                date_to: this.state.dateTo || false,
                company_id: this.state.companyFilter || "all",
            });
            if (res) {
                this.state.kpi = res.kpi;
                this.state.source_data = res.source_data;
                this.state.company_data = res.company_data;
                this.state.stage_funnel = res.stage_funnel;
                this.state.daily_trend = res.daily_trend;
                this.state.monthly_trend = res.monthly_trend;
                if (res.companies && res.companies.length > 0) {
                    this.state.companies = res.companies;
                }
            }
        } catch (err) {
            console.error("Lead Analytics Dashboard load error:", err);
            this.notification.add("Could not load dashboard data: " + (err.message || err), { type: "danger" });
        } finally {
            this.state.loading = false;
            setTimeout(() => this.renderCharts(), 100);
        }
    }

    // ── Chart rendering ───────────────────────────────────────────────────
    renderCharts() {
        this.renderDailyChart();
        this.renderMonthlyChart();
        this.renderSourceChart();
    }

    renderDailyChart() {
        const canvas = this.dailyChartRef.el;
        if (!canvas || typeof window.Chart === "undefined") return;
        if (this.dailyChartInstance) { this.dailyChartInstance.destroy(); }

        const data = this.state.daily_trend.slice(-60); // last 60 days
        this.dailyChartInstance = new window.Chart(canvas, {
            type: "line",
            data: {
                labels: data.map(d => d.date),
                datasets: [{
                    label: "Leads Per Day",
                    data: data.map(d => d.count),
                    borderColor: "#4361ee",
                    backgroundColor: "rgba(67,97,238,0.12)",
                    fill: true,
                    tension: 0.4,
                    pointRadius: data.length < 30 ? 4 : 2,
                    pointHoverRadius: 6,
                    borderWidth: 2,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: (items) => "Date: " + items[0].label,
                            label: (item) => "Leads: " + item.raw,
                        },
                    },
                },
                scales: {
                    x: { ticks: { maxTicksLimit: 12, font: { size: 11 } } },
                    y: { beginAtZero: true, ticks: { stepSize: 1 } },
                },
            },
        });
    }

    renderMonthlyChart() {
        const canvas = this.monthlyChartRef.el;
        if (!canvas || typeof window.Chart === "undefined") return;
        if (this.monthlyChartInstance) { this.monthlyChartInstance.destroy(); }

        const data = this.state.monthly_trend.slice(-18); // last 18 months
        const colors = data.map((_, i) => `hsl(${210 + i * 12}, 70%, 55%)`);

        this.monthlyChartInstance = new window.Chart(canvas, {
            type: "bar",
            data: {
                labels: data.map(d => d.label),
                datasets: [{
                    label: "Leads Per Month",
                    data: data.map(d => d.count),
                    backgroundColor: colors,
                    borderRadius: 6,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: { label: (item) => "Leads: " + item.raw } },
                },
                scales: {
                    x: { ticks: { font: { size: 11 } } },
                    y: { beginAtZero: true, ticks: { stepSize: 1 } },
                },
            },
        });
    }

    renderSourceChart() {
        const canvas = this.sourceChartRef.el;
        if (!canvas || typeof window.Chart === "undefined") return;
        if (this.sourceChartInstance) { this.sourceChartInstance.destroy(); }

        const top = this.state.source_data.slice(0, 10);
        const palette = [
            "#4361ee","#3a0ca3","#7209b7","#f72585","#4cc9f0",
            "#06d6a0","#ffd166","#ef476f","#118ab2","#073b4c"
        ];

        this.sourceChartInstance = new window.Chart(canvas, {
            type: "doughnut",
            data: {
                labels: top.map(s => s.source),
                datasets: [{
                    data: top.map(s => s.total),
                    backgroundColor: palette.slice(0, top.length),
                    hoverOffset: 8,
                    borderWidth: 2,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "right", labels: { font: { size: 12 }, padding: 12 } },
                    tooltip: {
                        callbacks: {
                            label: (item) => {
                                const d = top[item.dataIndex];
                                return [`Leads: ${d.total}`, `Active: ${d.active}`, `Lost: ${d.lost}`, `Won: ${d.won}`, `Repeat Hits: ${d.repeat || 0}`];
                            },
                        },
                    },
                },
            },
        });
    }

    // ── Formatters ────────────────────────────────────────────────────────
    fmt_inr(val) {
        const n = Number(val) || 0;
        if (n >= 10000000) return "₹" + (n / 10000000).toFixed(1) + "Cr";
        if (n >= 100000) return "₹" + (n / 100000).toFixed(1) + "L";
        if (n >= 1000) return "₹" + (n / 1000).toFixed(1) + "K";
        return "₹" + n.toLocaleString("en-IN");
    }

    // ── Navigation ────────────────────────────────────────────────────────
    openLeads(domain_extra) {
        const domain = [];
        if (this.state.companyFilter && this.state.companyFilter !== "all") {
            domain.push(["company_id", "=", parseInt(this.state.companyFilter)]);
        }
        if (this.state.dateFrom) domain.push(["create_date", ">=", this.state.dateFrom + " 00:00:00"]);
        if (this.state.dateTo) domain.push(["create_date", "<=", this.state.dateTo + " 23:59:59"]);
        if (domain_extra) domain.push(...domain_extra);

        this.action.doAction({
            name: "Leads",
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            context: { active_test: false },
            domain,
        });
    }

    onKpiClick(type) {
        if (type === "active") this.openLeads([["active", "=", true], ["probability", "<", 100]]);
        else if (type === "lost") this.openLeads([["active", "=", false]]);
        else if (type === "won") this.openLeads([["active", "=", true], ["probability", "=", 100]]);
        else if (type === "repeat") {
            const rids = this.state.kpi.repeat_lead_ids || [];
            if (rids.length > 0) {
                this.openLeads([["id", "in", rids]]);
            } else {
                this.notification.add("No repeat enquiry leads found for this filter.", { type: "info" });
            }
        }
        else this.openLeads([]);
    }

    onStageClick(stage) {
        if (stage.lead_ids && stage.lead_ids.length > 0) {
            this.openLeads([["id", "in", stage.lead_ids]]);
        } else if (stage.is_lost_sv) {
            this.openLeads([["active", "=", false], ["stage_id.name", "ilike", "Visit Done"]]);
        } else {
            this.openLeads([["stage_id.name", "=", stage.stage]]);
        }
    }
}

registry.category("actions").add("crm_lead_analytics_dashboard", CrmLeadAnalyticsDashboard);
