/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { registry } from "@web/core/registry";

export function getFormattedValue(record, fieldName, attrs) {
    const field = record.fields[fieldName];
    const formatter = registry.category("formatters").get(field.type, (val) => val);
    const formatOptions = {
        escape: false,
        data: record.data,
        isPassword: "password" in attrs,
        digits: attrs.digits ? JSON.parse(attrs.digits) : field.digits,
        field: record.fields[fieldName],
    };
    return record.data[fieldName] !== undefined
        ? formatter(record.data[fieldName], formatOptions)
        : "";
}

patch(ListRenderer.prototype, {
    getFormattedValue(column, record) {
        const fieldName = column.name;
        if (column.options.enable_formatting === false) {
            return record.data[fieldName];
        }
        if (record.model.config.resModel == 'sale.order' && column.name == 'partner_id'){
            return getFormattedValue(record, fieldName, column.attrs).toString().split(",")[0];
        }else{
            return super.getFormattedValue(...arguments);
        }
    }
});

