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
        this.sourceCanvasRef = useRef("sourceCanvas");
        this.tempCanvasRef = useRef("tempCanvas");

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
            this.renderAllCharts();
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
            
            // Clean canonical 7 stages with exact preview colors
            const stageColors = {
                1: "#3b82f6", // New Lead
                2: "#06b6d4", // Contacted
                3: "#6366f1", // Qualified
                4: "#f59e0b", // Visit Scheduled
                5: "#8b5cf6", // Visit Done
                6: "#ec4899", // Negotiation
                7: "#10b981", // Won
            };
            
            this.state.stages = (data.stages || [])
                .filter(s => !s.name.toLowerCase().includes('lost') && !s.name.toLowerCase().includes('not interested'))
                .slice(0, 7)
                .map((s, idx) => ({
                    ...s,
                    color: stageColors[s.sequence] || stageColors[idx + 1] || "#4f46e5"
                }));

            this.state.temperature = data.temperature;
            this.state.sources = data.sources || [];
            this.state.leaderboard = data.leaderboard || [];
            this.state.loading = false;

            setTimeout(() => this.renderAllCharts(), 60);
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

    renderAllCharts() {
        this.renderCallOutcomeChart();
        this.renderSourceDoughnutChart();
        this.renderTemperatureBarChart();
    }

    // 1. Call Outcome Bar Chart with Y-Axis Grid Lines
    renderCallOutcomeChart() {
        const canvas = this.callCanvasRef.el;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width = canvas.parentElement.clientWidth || 360;
        const h = canvas.height = 160;
        ctx.clearRect(0, 0, w, h);

        const outcomes = [
            { label: 'Answered', val: this.state.calling_outcomes.answered, color: '#10b981' },
            { label: 'No Answer', val: this.state.calling_outcomes.no_answer, color: '#ef4444' },
            { label: 'Busy', val: this.state.calling_outcomes.busy, color: '#f59e0b' },
            { label: 'Switched Off', val: this.state.calling_outcomes.switched_off, color: '#64748b' },
        ];

        const maxVal = Math.max(...outcomes.map(o => o.val), 50);
        const paddingLeft = 35;
        const paddingBottom = 25;
        const paddingTop = 15;
        const chartW = w - paddingLeft - 20;
        const chartH = h - paddingBottom - paddingTop;

        // Draw Y-Axis Grid Lines & Labels
        const gridSteps = 4;
        ctx.strokeStyle = '#f1f5f9';
        ctx.fillStyle = '#94a3b8';
        ctx.font = '10px Plus Jakarta Sans, sans-serif';
        ctx.textAlign = 'right';

        for (let i = 0; i <= gridSteps; i++) {
            const yVal = Math.round((maxVal / gridSteps) * i);
            const yPos = paddingTop + chartH - (i * (chartH / gridSteps));

            ctx.beginPath();
            ctx.moveTo(paddingLeft, yPos);
            ctx.lineTo(w - 10, yPos);
            ctx.stroke();

            ctx.fillText(yVal.toString(), paddingLeft - 6, yPos + 3);
        }

        // Draw Bars
        const barWidth = Math.min(52, (chartW / outcomes.length) * 0.65);
        const gap = (chartW - (barWidth * outcomes.length)) / (outcomes.length + 1);

        outcomes.forEach((item, idx) => {
            const barHeight = Math.max(4, (item.val / maxVal) * chartH);
            const x = paddingLeft + gap + idx * (barWidth + gap);
            const y = paddingTop + chartH - barHeight;

            // Bar
            ctx.fillStyle = item.color;
            ctx.beginPath();
            if (ctx.roundRect) {
                ctx.roundRect(x, y, barWidth, barHeight, [4, 4, 0, 0]);
            } else {
                ctx.rect(x, y, barWidth, barHeight);
            }
            ctx.fill();

            // Label Below Bar
            ctx.fillStyle = '#64748b';
            ctx.font = '10px Plus Jakarta Sans, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(item.label, x + barWidth / 2, h - 8);
        });
    }

    // 2. Source Doughnut Chart with Legend on Right
    renderSourceDoughnutChart() {
        const canvas = this.sourceCanvasRef.el;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width = canvas.parentElement.clientWidth || 320;
        const h = canvas.height = 180;
        ctx.clearRect(0, 0, w, h);

        const colors = ['#4f46e5', '#06b6d4', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'];
        const sources = (this.state.sources.length > 0 ? this.state.sources : [
            { name: 'AI WhatsApp Agent', count: 58 },
            { name: 'WhatsApp Direct', count: 24 },
            { name: 'Walk In', count: 18 },
            { name: 'Reference', count: 14 },
            { name: 'Social Media Ads', count: 21 },
            { name: 'Direct Call', count: 6 },
        ]).slice(0, 6);

        const total = sources.reduce((acc, s) => acc + s.count, 0) || 1;
        const centerX = Math.min(100, w * 0.32);
        const centerY = h / 2;
        const outerRadius = Math.min(65, h * 0.42);
        const innerRadius = outerRadius * 0.65;

        let startAngle = -Math.PI / 2;

        // Draw Doughnut Segments
        sources.forEach((src, idx) => {
            const sliceAngle = (src.count / total) * 2 * Math.PI;
            ctx.beginPath();
            ctx.arc(centerX, centerY, outerRadius, startAngle, startAngle + sliceAngle);
            ctx.arc(centerX, centerY, innerRadius, startAngle + sliceAngle, startAngle, true);
            ctx.closePath();
            ctx.fillStyle = colors[idx % colors.length];
            ctx.fill();
            startAngle += sliceAngle;
        });

        // Center Hole
        ctx.beginPath();
        ctx.arc(centerX, centerY, innerRadius, 0, 2 * Math.PI);
        ctx.fillStyle = '#ffffff';
        ctx.fill();

        // Draw Legend on Right
        const legendX = centerX + outerRadius + 24;
        const startLegendY = 25;
        const itemSpacing = 24;

        ctx.textAlign = 'left';
        sources.forEach((src, idx) => {
            const y = startLegendY + idx * itemSpacing;
            if (y > h - 10) return;

            // Color Square
            ctx.fillStyle = colors[idx % colors.length];
            ctx.fillRect(legendX, y - 9, 10, 10);

            // Label & Count
            ctx.fillStyle = '#334155';
            ctx.font = '10.5px Plus Jakarta Sans, sans-serif';
            const cleanName = src.name.length > 18 ? src.name.substring(0, 16) + '..' : src.name;
            ctx.fillText(`${cleanName} (${src.count})`, legendX + 16, y);
        });
    }

    // 3. Temperature Horizontal Bar Chart
    renderTemperatureBarChart() {
        const canvas = this.tempCanvasRef.el;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width = canvas.parentElement.clientWidth || 320;
        const h = canvas.height = 110;
        ctx.clearRect(0, 0, w, h);

        const items = [
            { label: 'Hot', val: this.state.temperature.hot, color: '#be123c' },
            { label: 'Warm', val: this.state.temperature.warm, color: '#b45309' },
            { label: 'Cold', val: this.state.temperature.cold, color: '#0e7490' },
        ];

        const maxVal = Math.max(...items.map(i => i.val), 50);
        const paddingLeft = 42;
        const paddingBottom = 20;
        const paddingTop = 10;
        const chartW = w - paddingLeft - 20;
        const chartH = h - paddingBottom - paddingTop;

        const rowHeight = chartH / items.length;
        const barHeight = Math.min(18, rowHeight * 0.65);

        // Draw X-Axis Scale Grid
        ctx.strokeStyle = '#f1f5f9';
        ctx.fillStyle = '#94a3b8';
        ctx.font = '9px Plus Jakarta Sans, sans-serif';
        ctx.textAlign = 'center';

        const xSteps = 5;
        for (let i = 0; i <= xSteps; i++) {
            const xVal = Math.round((maxVal / xSteps) * i);
            const xPos = paddingLeft + (i * (chartW / xSteps));

            ctx.beginPath();
            ctx.moveTo(xPos, paddingTop);
            ctx.lineTo(xPos, h - paddingBottom);
            ctx.stroke();

            ctx.fillText(xVal.toString(), xPos, h - 6);
        }

        // Draw Horizontal Bars
        items.forEach((item, idx) => {
            const y = paddingTop + idx * rowHeight + (rowHeight - barHeight) / 2;
            const barW = Math.max(6, (item.val / maxVal) * chartW);

            // Y Label
            ctx.fillStyle = '#64748b';
            ctx.font = '10.5px Plus Jakarta Sans, sans-serif';
            ctx.textAlign = 'right';
            ctx.fillText(item.label, paddingLeft - 8, y + barHeight / 2 + 3);

            // Bar
            ctx.fillStyle = item.color;
            ctx.beginPath();
            if (ctx.roundRect) {
                ctx.roundRect(paddingLeft, y, barW, barHeight, [0, 4, 4, 0]);
            } else {
                ctx.rect(paddingLeft, y, barW, barHeight);
            }
            ctx.fill();
        });
    }
}

registry.category("actions").add("crm_executive_dashboard", CrmExecutiveDashboard);
