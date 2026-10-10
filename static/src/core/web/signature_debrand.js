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

        // Ensure Favicon & PWA Home Screen icons and titles are set to Signature Properties
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

            let appleIcon = head.querySelector("link[rel='apple-touch-icon']");
            if (!appleIcon) {
                appleIcon = document.createElement("link");
                appleIcon.rel = "apple-touch-icon";
                head.appendChild(appleIcon);
            }
            appleIcon.href = "/diyacrm/static/src/img/signature_pwa_ios.png";

            let appNameMeta = head.querySelector("meta[name='apple-mobile-web-app-title']");
            if (!appNameMeta) {
                appNameMeta = document.createElement("meta");
                appNameMeta.name = "apple-mobile-web-app-title";
                head.appendChild(appNameMeta);
            }
            appNameMeta.content = "Signature Properties";

            let appName = head.querySelector("meta[name='application-name']");
            if (!appName) {
                appName = document.createElement("meta");
                appName.name = "application-name";
                head.appendChild(appName);
            }
            appName.content = "Signature Properties";
        } catch (e) {
            // ignore
        }

        return titleObj;
    },
});
