/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

console.log("[lot_availability] widget JS loaded");

export class LotAvailabilityField extends Component {
    static template = "sale_lot_availability.LotAvailabilityField";
    static props = {
        ...standardFieldProps,
    };

    get count() {
        return this.props.record.data.available_lots_count || 0;
    }

    get tooltipContent() {
        const raw = this.props.record.data.lot_tooltip || "";
        console.log("[lot_availability] lot_tooltip =", raw);
        if (!raw) return "Aucun lot disponible";
        return raw.split("\n").filter(Boolean).join("\n");
    }

    get badgeClass() {
        if (this.count === 0) return "badge text-bg-danger";
        if (this.count <= 2) return "badge text-bg-warning";
        return "badge text-bg-success";
    }
}

registry.category("fields").add("lot_availability", {
    component: LotAvailabilityField,
    supportedTypes: ["integer"],
});
