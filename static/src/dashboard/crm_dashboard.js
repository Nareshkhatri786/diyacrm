/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class CrmExecutiveDashboard extends Component {
    static template = "diyacrm.CrmExecutiveDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.callCanvasRef = useRef("callCanvas");

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

        onMounted(() => {
            this.renderCharts();
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
            this.state.stages = data.stages || [];
            this.state.temperature = data.temperature;
            this.state.sources = data.sources || [];
            this.state.leaderboard = data.leaderboard || [];
            this.state.loading = false;

            setTimeout(() => this.renderCharts(), 50);
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

    renderCharts() {
        const callCanvas = this.callCanvasRef.el;
        if (callCanvas) {
            const ctx = callCanvas.getContext('2d');
            const w = callCanvas.width = callCanvas.parentElement.clientWidth || 300;
            const h = callCanvas.height = 140;
            ctx.clearRect(0, 0, w, h);

            const outcomes = [
                { label: 'Answered', val: this.state.calling_outcomes.answered, color: '#10b981' },
                { label: 'No Answer', val: this.state.calling_outcomes.no_answer, color: '#ef4444' },
                { label: 'Busy', val: this.state.calling_outcomes.busy, color: '#f59e0b' },
                { label: 'Switched Off', val: this.state.calling_outcomes.switched_off, color: '#64748b' },
            ];

            const maxVal = Math.max(...outcomes.map(o => o.val), 1);
            const barWidth = Math.min(50, (w - 60) / outcomes.length);
            const gap = (w - (barWidth * outcomes.length)) / (outcomes.length + 1);

            outcomes.forEach((item, idx) => {
                const barHeight = Math.max(8, (item.val / maxVal) * (h - 40));
                const x = gap + idx * (barWidth + gap);
                const y = h - 25 - barHeight;

                ctx.fillStyle = item.color;
                ctx.beginPath();
                if (ctx.roundRect) {
                    ctx.roundRect(x, y, barWidth, barHeight, 6);
                } else {
                    ctx.rect(x, y, barWidth, barHeight);
                }
                ctx.fill();

                ctx.fillStyle = '#0f172a';
                ctx.font = 'bold 11px sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText(item.val.toString(), x + barWidth / 2, y - 5);

                ctx.fillStyle = '#64748b';
                ctx.font = '10px sans-serif';
                ctx.fillText(item.label.substring(0, 7), x + barWidth / 2, h - 8);
            });
        }
    }
}

registry.category("actions").add("crm_executive_dashboard", CrmExecutiveDashboard);
