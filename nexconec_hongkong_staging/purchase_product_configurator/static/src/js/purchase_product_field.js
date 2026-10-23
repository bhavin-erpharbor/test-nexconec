/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductConfiguratorDialog } from "@sale/js/product_configurator_dialog/product_configurator_dialog";
import { PurchaseOrderLineProductField } from '@purchase_product_matrix/js/purchase_product_field';
import { Record } from "@web/model/relational_model/record";
import { serializeDateTime } from "@web/core/l10n/dates";
import { x2ManyCommands } from "@web/core/orm_service";
import { useMatrixConfigurator } from "@product_matrix/js/matrix_configurator_hook";
import { useProductConfigurator } from "@purchase_product_configurator/js/product_configurator_hook";
import { rpc } from "@web/core/network/rpc";

import { ProductList } from "@sale/js/product_list/product_list";
import { Product } from "@sale/js/product/product";
import { ProductTemplateAttributeLine } from "@sale/js/product_template_attribute_line/product_template_attribute_line";

patch(ProductTemplateAttributeLine.prototype, {

    getPTAVSelectName(ptav) {
        super.getPTAVSelectName(ptav);
        return ptav?.name;
    }
})

patch(ProductConfiguratorDialog.prototype, {

    async _updatePTAVCustomValue(productTmplId, ptavId, customValue) {
        let rec = await super._updatePTAVCustomValue(productTmplId, ptavId, customValue);
        try {
            const product = this._findProduct(productTmplId);
            this.props.customValue = customValue
            this.props.updatedValues = await this._updateCombination(product, product?.quantity);
            Object.assign(product, this.props.updatedValues);
        }
        catch {
            return rec;
        }
        return rec
    },

    async _updateCombination(product, quantity, uomId) {
        var customValue = this.props.customValue
        return rpc('/sale_product_configurator/update_combination', {
            product_template_id: product.product_tmpl_id,
            ptav_ids: this._getCombination(product),
            currency_id: this.currency.id,
            so_date: this.props.soDate,
            quantity: quantity,
            product_uom_id: uomId,
            company_id: this.props.companyId,
            pricelist_id: this.props.pricelistId,
            customValue: customValue || null,
            ...this._getAdditionalRpcParams(),
        });
    },
});

ProductConfiguratorDialog.props = {
    ...ProductConfiguratorDialog.props,
    hidePrice: { optional: true },
};

ProductList.props = {
    ...ProductList.props,
    hidePrice: { optional: true },
};

Product.props = {
    ...Product.props,
    hidePrice: { optional: true },
};

patch(PurchaseOrderLineProductField.prototype, {
      setup() {
        super.setup();
        this.productConfigurator = useProductConfigurator();
      },

       async _onProductTemplateUpdate() {
        const result = await this.orm.call(
            'product.template',
            'get_single_product_variant',
            [this.props.record.data.product_template_id.id],
        );
        if(result && result.product_id) {
            if (this.props.record.data.product_id != result.product_id.id) {
                this.props.record.update({
                    // TODO right name get (same problem as configurator)
                    product_id: { id: result.product_id, display_name: result.product_name },
                });
            }
        } else {
             if (this.props.record.data.product_add_mode == 'matrix') {
                this.matrixConfigurator.open(this.props.record, false);
            } else {
                this.productConfigurator.open(this.props.record, false);
            }

        }
    },

});
