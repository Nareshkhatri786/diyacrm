import { Chatter } from "@mail/chatter/web_portal/chatter";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.actionService = useService("action");
    },

    onClickChatterWhatsApp() {
        if (!this.props.threadId) {
            return;
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "WhatsApp History & Follow-up",
            res_model: "crm.lead.whatsapp.wizard",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_lead_id: this.props.threadId,
            },
        });
    },
});
