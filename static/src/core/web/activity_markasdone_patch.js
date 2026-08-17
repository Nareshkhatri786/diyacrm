import { ActivityMarkAsDone } from "@mail/core/web/activity_markasdone_popover";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";

patch(ActivityMarkAsDone.prototype, {
    setup() {
        super.setup();
        const initialTab = this.isSiteVisitActivity ? "site_visit" : "call";
        this.state = useState({
            activeTab: initialTab,
            selectedOutcome: null,
            // Site Visit Outcomes
            purchaseTimeline: "Not discussed",
            financeMode: "Not discussed",
            budgetComfort: "Not discussed",
            decisionMaker: "Not discussed",
            accompaniedBy: [],
            userNote: "",
        });
    },

    get isSiteVisitActivity() {
        const act = this.props.activity || {};
        const typeName = (
            act.activity_type_id?.name ||
            act.type?.name ||
            act.activity_type_name ||
            (Array.isArray(act.activity_type_id) ? act.activity_type_id[1] : "") ||
            ""
        ).toLowerCase();
        const summary = (act.summary || "").toLowerCase();
        const category = (act.activity_category || "").toLowerCase();

        return (
            category === "meeting" ||
            typeName.includes("visit") ||
            typeName.includes("site") ||
            typeName.includes("meeting") ||
            summary.includes("visit") ||
            summary.includes("site") ||
            summary.includes("meeting")
        );
    },

    get isCallActivity() {
        return !this.isSiteVisitActivity;
    },

    get selectedOutcome() {
        return this.state.selectedOutcome;
    },

    setActiveTab(tab) {
        this.state.activeTab = tab;
    },

    selectOutcome(outcome) {
        this.state.selectedOutcome = outcome;
        const currentFeedback = this.props.activity.feedback || "";
        const cleanedFeedback = currentFeedback.replace(/^Call Outcome: [^\n]+\n?/, "");
        this.props.activity.feedback = `Call Outcome: ${outcome}${cleanedFeedback ? "\n" + cleanedFeedback : ""}`;
    },

    toggleAccompaniedPerson(person) {
        if (person === "Alone") {
            if (this.state.accompaniedBy.includes("Alone")) {
                this.state.accompaniedBy = [];
            } else {
                this.state.accompaniedBy = ["Alone"];
            }
        } else {
            let list = this.state.accompaniedBy.filter((p) => p !== "Alone");
            if (list.includes(person)) {
                list = list.filter((p) => p !== person);
            } else {
                list.push(person);
            }
            this.state.accompaniedBy = list;
        }
        this.onSiteVisitChange();
    },

    onSiteVisitChange() {
        const lines = [
            "--- Site Visit Outcome ---",
            `Purchase Timeline: ${this.state.purchaseTimeline}`,
            `Finance Mode: ${this.state.financeMode}`,
            `Budget Comfort: ${this.state.budgetComfort}`,
            `Decision Maker: ${this.state.decisionMaker}`,
            `Client Ke Saath Kaun Aaya: ${this.state.accompaniedBy.length ? this.state.accompaniedBy.join(", ") : "Not specified"}`,
        ];
        const formattedBlock = lines.join("\n");

        const currentFeedback = this.props.activity.feedback || "";
        const cleanedFeedback = currentFeedback.replace(/--- Site Visit Outcome ---[\s\S]*?(?=\n\n|$)/, "").trim();

        this.props.activity.feedback = `${formattedBlock}${cleanedFeedback ? "\n\n" + cleanedFeedback : ""}`;
    },
});
