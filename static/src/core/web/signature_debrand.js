/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { titleService } from "@web/core/browser/title_service";

// 1. Remove Odoo account and Odoo help links from User Profile dropdown
const userMenuRegistry = registry.category("user_menuitems");
if (userMenuRegistry.contains("odoo_account")) {
    userMenuRegistry.remove("odoo_account");
}
if (userMenuRegistry.contains("support")) {
    userMenuRegistry.remove("support");
}

// 2. Patch Title Service to replace any "Odoo" branding with "Signature Properties"
patch(titleService, {
    start() {
        const titleObj = super.start(...arguments);
        const origSetParts = titleObj.setParts;

        titleObj.setParts = function (parts) {
            for (const key in parts) {
                if (typeof parts[key] === "string") {
                    parts[key] = parts[key].replace(/\bOdoo\b/g, "Signature Properties");
                }
            }
            if (!parts.brand) {
                parts.brand = "Signature Properties";
            }
            return origSetParts.call(this, parts);
        };

        // Initialize with Signature Properties branding
        titleObj.setParts({ brand: "Signature Properties" });

        // Ensure Favicon is set to Signature Properties icon
        try {
            const head = document.head;
            let iconLink = head.querySelector("link[rel*='icon']");
            if (!iconLink) {
                iconLink = document.createElement("link");
                iconLink.type = "image/x-icon";
                iconLink.rel = "shortcut icon";
                head.appendChild(iconLink);
            }
            iconLink.href = "/diyacrm/static/src/img/favicon.ico";
        } catch (e) {
            // ignore
        }

        return titleObj;
    },
});
