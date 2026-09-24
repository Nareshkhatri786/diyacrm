/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class CrmUnitMatrix extends Component {
    static template = "diyacrm.CrmUnitMatrix";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            activeBlock: "B",
            filterSize: "all",
            filterFacing: "all",
            filterPlc: "all",
            filterStatus: "all",
            searchQuery: "",
            data: {
                company_name: "The 1st Residency",
                company_id: false,
                total_count: 0,
                available_count: 0,
                booked_count: 0,
                hold_count: 0,
                blocks: ["B", "C"],
                block_data: {},
                size_stats: { "265": 0, "270": 0, "275": 0 },
            },
        });

        onWillStart(async () => {
            await this.loadMatrixData();
        });
    }

    async loadMatrixData() {
        this.state.loading = true;
        try {
            const res = await this.orm.call("crm.property.unit", "get_unit_matrix_data", []);
            if (res) {
                this.state.data = res;
                if (res.blocks && res.blocks.length > 0 && !res.blocks.includes(this.state.activeBlock)) {
                    this.state.activeBlock = res.blocks[0];
                }
            }
        } catch (err) {
            console.error("Error loading unit matrix data:", err);
            this.notification.add("Could not load unit matrix data: " + (err.message || err), {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    switchBlock(block) {
        this.state.activeBlock = block;
    }

    setSizeFilter(size) {
        this.state.filterSize = size;
    }

    setFacingFilter(facing) {
        this.state.filterFacing = facing;
    }

    setPlcFilter(plc) {
        this.state.filterPlc = plc;
    }

    setStatusFilter(status) {
        this.state.filterStatus = status;
    }

    onSearchInput(ev) {
        this.state.searchQuery = (ev.target.value || "").trim().toLowerCase();
    }

    isUnitVisible(unit) {
        if (this.state.filterSize !== "all" && unit.size !== this.state.filterSize) {
            return false;
        }
        if (this.state.filterFacing !== "all" && unit.facing !== this.state.filterFacing) {
            return false;
        }
        if (this.state.filterPlc !== "all") {
            const hasPlc = this.state.filterPlc === "yes";
            if (unit.plc !== hasPlc) return false;
        }
        if (this.state.filterStatus !== "all" && unit.status !== this.state.filterStatus) {
            return false;
        }
        if (this.state.searchQuery) {
            const q = this.state.searchQuery;
            const matchName = (unit.name || "").toLowerCase().includes(q);
            const matchBuyer = (unit.buyer || "").toLowerCase().includes(q);
            const matchSize = (unit.size || "").toLowerCase().includes(q);
            if (!matchName && !matchBuyer && !matchSize) {
                return false;
            }
        }
        return true;
    }

    async onUnitClick(unit) {
        if (unit.status === "available" || unit.status === "hold") {
            // Open booking wizard
            this.action.doAction({
                name: `Book Unit: ${unit.name}`,
                type: "ir.actions.act_window",
                res_model: "crm.unit.booking.wizard",
                view_mode: "form",
                views: [[false, "form"]],
                target: "new",
                context: {
                    default_unit_id: unit.id,
                },
            }, {
                onClose: async () => {
                    await this.loadMatrixData();
                },
            });
        } else {
            // Open unit form view to view booking info or release
            this.action.doAction({
                name: `Unit ${unit.name} (Booked)`,
                type: "ir.actions.act_window",
                res_model: "crm.property.unit",
                res_id: unit.id,
                views: [[false, "form"]],
                target: "current",
            });
        }
    }

    openListView() {
        this.action.doAction({
            name: "Property Units List",
            type: "ir.actions.act_window",
            res_model: "crm.property.unit",
            view_mode: "list,kanban,form",
            views: [[false, "list"], [false, "kanban"], [false, "form"]],
            target: "current",
            context: {
                search_default_filter_available: 1,
            },
        });
    }
}

registry.category("actions").add("crm_unit_matrix", CrmUnitMatrix);
