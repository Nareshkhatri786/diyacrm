import { ActivityMarkAsDone } from "@mail/core/web/activity_markasdone_popover";
import { patch } from "@web/core/utils/patch";
import * as owl from "@odoo/owl";

const makeReactiveState = (initialState) => {
    if (typeof owl.useState === "function") {
        try {
            return owl.useState(initialState);
        } catch (e) {
            // fallback if not in component setup hook context
        }
    }
    if (typeof owl.reactive === "function") {
        return owl.reactive(initialState);
    }
    return initialState;
};

patch(ActivityMarkAsDone.prototype, {
    setup() {
        super.setup();
        this.state = makeReactiveState({
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

    get isCallActivity() {
        const act = this.props.activity;
        return (
            act.activity_category === "phonecall" ||
            act.summary === "Call" ||
            act.activity_type_id?.name === "Call" ||
            (Array.isArray(act.activity_type_id) && act.activity_type_id[1] === "Call")
        );
    },

    get isSiteVisitActivity() {
        const act = this.props.activity;
        return (
            act.summary === "Site Visit" ||
            act.activity_type_id?.name === "Site Visit" ||
            (Array.isArray(act.activity_type_id) && act.activity_type_id[1] === "Site Visit")
        );
    },

    get selectedOutcome() {
        return this.state.selectedOutcome;
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
            // Remove 'Alone' if another person is checked
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
        // Remove previous Site Visit block if already present
        const cleanedFeedback = currentFeedback.replace(/--- Site Visit Outcome ---[\s\S]*?(?=\n\n|$)/, "").trim();

        this.props.activity.feedback = `${formattedBlock}${cleanedFeedback ? "\n\n" + cleanedFeedback : ""}`;
    },
});
