/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
// Adjust this import to your actual sale product field class.
import { SaleOrderLineProductField } from "@sale/js/sale_product_field";

console.log("Sale product field cutting patch loaded");

patch(SaleOrderLineProductField.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
    },

    async _onProductConfiguratorSave(mainProduct, optionalProducts, multiProducts, options) {
        /*
         * This is only an example.
         * You must merge this logic into your existing save method if your method name is different.
         */

        const result = await super._onProductConfiguratorSave(
            mainProduct,
            optionalProducts,
            multiProducts,
            options
        );

        /*
         * You need the sale.order.line id here.
         * Depending on your implementation, it may be:
         * - this.props.record.resId
         * - result.line_id
         * - mainProduct.sale_order_line_id
         * - your own returned line id
         */

        const lineId =
            result?.line_id ||
            mainProduct?.sale_order_line_id ||
            this.props.record?.resId;

        console.log("Configurator saved lineId:", lineId);
        console.log("Cable data:", options?.cable_cutting_data);

        if (options?.cable_cutting_data && lineId) {
            await this.orm.call(
                "sale.order.line",
                "action_apply_cable_cutting_from_configurator",
                [[lineId]],
                {
                    cutting_data: options.cable_cutting_data,
                }
            );
        }

        return result;
    },
});