/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

export class CrmExecutiveDashboard extends Component {
    static template = "diyacrm.CrmExecutiveDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.callOutcomeCanvasRef = useRef("callOutcomeChart");
        this.sourceCanvasRef = useRef("sourceChart");
        this.tempCanvasRef = useRef("tempChart");

        this.callChart = null;
        this.sourceChart = null;
        this.tempChart = null;

        this.state = useState({
            loading: true,
            period: "48h",
            selectedCompanyId: "all",
            selectedUserId: "all",
            isMultiCompany: false,
            activeCompanies: [],
            availableCompanies: [],
            kpis: {
                total_calls: 0,
                connected_pct: 0,
                new_opps: 0,
                updated_opps: 0,
                visits_scheduled: 0,
                visits_done: 0,
                won: 0,
            },
            calling_outcomes: {
                answered: 0,
                no_answer: 0,
                busy: 0,
                switched_off: 0,
                answered_pct: 0,
                no_answer_pct: 0,
                busy_pct: 0,
                switched_off_pct: 0,
            },
            stages: [],
            temperature: {
                hot: 0,
                warm: 0,
                cold: 0,
            },
            sources: [],
            leaderboard: [],
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });

        onMounted(async () => {
            try {
                await loadJS("https://cdn.jsdelivr.net/npm/chart.js");
            } catch (e) {
                console.warn("Chart.js CDN load failed, falling back to local:", e);
            }
            this.initOrUpdateCharts();
        });
    }

    async loadDashboardData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call("crm.lead", "get_dashboard_data", [], {
                period: this.state.period,
                company_id: this.state.selectedCompanyId,
                user_id: this.state.selectedUserId,
            });

            this.state.isMultiCompany = data.is_multi_company;
            this.state.activeCompanies = data.active_companies || [];
            this.state.availableCompanies = data.available_companies || [];
            this.state.kpis = data.kpis;
            this.state.calling_outcomes = data.calling_outcomes;
            
            const stageColors = {
                1: "#3b82f6",
                2: "#06b6d4",
                3: "#6366f1",
                4: "#f59e0b",
                5: "#8b5cf6",
                6: "#ec4899",
                7: "#10b981",
            };
            
            const rawStages = data.stages || [];
            const maxStageCount = Math.max(...rawStages.map(s => s.count), 1);
            this.state.stages = rawStages.map((s, idx) => ({
                ...s,
                color: s.color || stageColors[s.sequence] || "#4f46e5",
                pct: Math.round((s.count / maxStageCount) * 100),
            }));

            this.state.temperature = data.temperature;
            this.state.sources = data.sources || [];
            this.state.leaderboard = data.leaderboard || [];
            this.state.loading = false;

            setTimeout(() => this.initOrUpdateCharts(), 50);
        } catch (error) {
            console.error("Failed to load dashboard data:", error);
            this.state.loading = false;
        }
    }

    async onPeriodChange(ev) {
        this.state.period = ev.target.value;
        await this.loadDashboardData();
    }

    async onCompanyChange(ev) {
        this.state.selectedCompanyId = ev.target.value;
        await this.loadDashboardData();
    }

    async onUserChange(ev) {
        this.state.selectedUserId = ev.target.value;
        await this.loadDashboardData();
    }

    openOpportunities(filterType) {
        let domain = [];
        if (filterType === 'won') {
            domain = [['probability', '=', 100]];
        } else if (filterType === 'new') {
            domain = [['stage_id.sequence', '=', 1]];
        } else if (filterType === 'visit') {
            domain = [['stage_id.name', 'ilike', 'Visit']];
        }

        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Opportunities',
            res_model: 'crm.lead',
            view_mode: 'kanban,list,form',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
            domain: domain,
        });
    }

    initOrUpdateCharts() {
        if (typeof window.Chart === "undefined") {
            return;
        }

        // 1. Call Outcome Bar Chart
        const callCanvas = this.callOutcomeCanvasRef.el;
        if (callCanvas) {
            if (this.callChart) {
                this.callChart.destroy();
            }
            const ctxCall = callCanvas.getContext('2d');
            this.callChart = new window.Chart(ctxCall, {
                type: 'bar',
                data: {
                    labels: ['Answered', 'No Answer', 'Busy', 'Switched Off'],
                    datasets: [{
                        label: 'Calls',
                        data: [
                            this.state.calling_outcomes.answered,
                            this.state.calling_outcomes.no_answer,
                            this.state.calling_outcomes.busy,
                            this.state.calling_outcomes.switched_off,
                        ],
                        backgroundColor: ['#10b981', '#ef4444', '#f59e0b', '#64748b'],
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { stepSize: 1 } },
                        x: { grid: { display: false } }
                    }
                }
            });
        }

        // 2. Source Doughnut Chart
        const sourceCanvas = this.sourceCanvasRef.el;
        if (sourceCanvas) {
            if (this.sourceChart) {
                this.sourceChart.destroy();
            }
            const sources = this.state.sources.length > 0 ? this.state.sources : [
                { name: 'Walk In', count: 1 }
            ];
            const ctxSource = sourceCanvas.getContext('2d');
            this.sourceChart = new window.Chart(ctxSource, {
                type: 'doughnut',
                data: {
                    labels: sources.map(s => s.name),
                    datasets: [{
                        data: sources.map(s => s.count),
                        backgroundColor: ['#4f46e5', '#06b6d4', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'right',
                            labels: {
                                boxWidth: 12,
                                font: { size: 11, family: 'Plus Jakarta Sans, sans-serif' }
                            }
                        }
                    },
                    cutout: '70%'
                }
            });
        }

        // 3. Temperature Horizontal Bar Chart
        const tempCanvas = this.tempCanvasRef.el;
        if (tempCanvas) {
            if (this.tempChart) {
                this.tempChart.destroy();
            }
            const ctxTemp = tempCanvas.getContext('2d');
            this.tempChart = new window.Chart(ctxTemp, {
                type: 'bar',
                data: {
                    labels: ['Hot', 'Warm', 'Cold'],
                    datasets: [{
                        data: [
                            this.state.temperature.hot,
                            this.state.temperature.warm,
                            this.state.temperature.cold,
                        ],
                        backgroundColor: ['#be123c', '#b45309', '#0e7490'],
                        borderRadius: 4
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { stepSize: 1 } },
                        y: { grid: { display: false } }
                    }
                }
            });
        }
    }
}

registry.category("actions").add("crm_executive_dashboard", CrmExecutiveDashboard);
