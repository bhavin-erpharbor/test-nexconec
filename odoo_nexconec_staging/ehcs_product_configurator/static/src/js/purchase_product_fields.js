/** @odoo-module **/

import { PurchaseOrderLineProductField } from '@purchase_product_matrix/js/purchase_product_field';
import { serializeDateTime } from "@web/core/l10n/dates";
import { x2ManyCommands } from "@web/core/orm_service";
import { patch } from "@web/core/utils/patch";
import { ProductConfiguratorDialog } from "@sale/js/product_configurator_dialog/product_configurator_dialog";


async function applyPurchaseProduct(record, product, customValue=false) {

    // handle custom values & no variants
    const customAttributesCommands = [
        x2ManyCommands.set([]),  // Command.clear isn't supported in static_list/_applyCommands
    ];
    for (const ptal of product.attribute_lines) {
        const selectedCustomPTAV = getSelectedCustomPtav(ptal);
        if (selectedCustomPTAV) {
            customAttributesCommands.push(
                x2ManyCommands.create(undefined, {
                    custom_product_template_attribute_value_id: [
                        selectedCustomPTAV.id,
                        "we don't care",
                    ],
                    custom_value: ptal.customValue,
                })
            );
        }
        // Customization Start
        if(selectedCustomPTAV && customValue){
            ptal.customValue = customValue
        }
        // Customization End
    }

    const noVariantPTAVIds = product.attribute_lines
        .filter((ptal) => ptal.create_variant === "no_variant")
        .flatMap((ptal) => ptal.selected_attribute_value_ids);

    // We use `_update` (not locked) instead of `update` (locked) so that multiple records can be
    // updated in parallel (for performance).
    const update_values = {
        product_id: { id: product.id, display_name: product.display_name },
        product_uom_qty: product.quantity,
        product_no_variant_attribute_value_ids: [x2ManyCommands.set(noVariantPTAVIds)],
        product_custom_attribute_value_ids: customAttributesCommands,
    }
    if (product.uom) {
        // only update uom field if uom are enabled (uom_data provided), otherwise we don't have the display_name
        // and the value isn't expected to change anyway.
        update_values.product_uom_id = product.uom;
    }
    await record._update(update_values);
  };

// Purchase Order Configurator
patch(PurchaseOrderLineProductField.prototype, {

    _prepareMultiNewLineData(_line, product) {
        return product;
    },

    async _openProductConfigurator(edit=false, selectedComboItems = []) {
        const purchaseOrderRecord = this.props.record.model.root;

        let ptavIds = this.props.record.data.product_template_attribute_value_ids.records.map(
            record => record.resId
        );
        let customAttributeValues = [];

        if (edit) {
            /**
             * no_variant and custom attribute don't need to be given to the configurator for new
             * products.
             */
            ptavIds = ptavIds.concat(this.props.record.data.product_no_variant_attribute_value_ids.records.map(
                record => record.resId
            ));
            /**
             *  `product_custom_attribute_value_ids` records are not loaded in the view bc sub templates
             *  are not loaded in list views. Therefore, we fetch them from the server if the record is
             *  saved. Else we use the value stored on the line.
             */
            customAttributeValues =
                this.props.record.data.product_custom_attribute_value_ids.records[0]?.isNew ?
                this.props.record.data.product_custom_attribute_value_ids.records.map(
                    record => record.data
                ) :
                await this.orm.read(
                    'product.attribute.custom.value',
                    this.props.record.data.product_custom_attribute_value_ids.currentIds,
                    ["custom_product_template_attribute_value_id", "custom_value"]
                )
        }
        this.dialog.add(ProductConfiguratorDialog, {
            productTemplateId: this.props.record.data.product_template_id[0],
            ptavIds: ptavIds,
            customAttributeValues: customAttributeValues.map(
                data => {
                    return {
                        ptavId: data.custom_product_template_attribute_value_id[0],
                        value: data.custom_value,
                    }
                }
            ),
            quantity: this.props.record.data.product_qty ? this.props.record.data.product_qty : 1,
            productUOMId: this.props.record.data.product_uom[0],
            companyId: purchaseOrderRecord.data.company_id[0],
            currencyId: this.props.record.data.currency_id[0],
            soDate: serializeDateTime(purchaseOrderRecord.data.date_order),
            edit: edit,
            hidePrice: true,
            save: async (mainProduct, optionalProducts, multiProducts) => {

                // Main Product
                await applyPurchaseProduct(this.props.record, mainProduct);
                // this._onProductUpdate();
                purchaseOrderRecord.data.order_line.leaveEditMode();

                // Optional Products
                for (const optionalProduct of optionalProducts) {
                    const line = await purchaseOrderRecord.data.order_line.addNewRecord({
                        position: 'bottom',
                        mode: "readonly",
                    });
                    await applyPurchaseProduct(line, optionalProduct);
                }

// Customization Start
                // Multi Products
                if (multiProducts.length > 0) {
                    // Remove main product line if multi products added
                    purchaseOrderRecord.data.order_line.delete(this.props.record);
                }
                for (const multiProduct of multiProducts) {
                    // if (multiProduct.id !== mainProduct.id) {
                        const line = await purchaseOrderRecord.data.order_line.addNewRecord({
                            position: 'bottom',
                            mode: "readonly",
                        });

                        await applyPurchaseProduct(line, multiProduct, multiProduct.customValue);
                        // this._onProductUpdate();
                    // }
                }
// Customization End
            },
            discard: () => {
                purchaseOrderRecord.data.order_line.delete(this.props.record);
            },
        });
    }

});
