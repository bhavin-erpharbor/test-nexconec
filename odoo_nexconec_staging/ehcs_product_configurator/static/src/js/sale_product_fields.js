/** @odoo-module **/

import { SaleOrderLineProductField } from '@sale/js/sale_product_field';
import { serializeDateTime } from "@web/core/l10n/dates";
import { x2ManyCommands } from "@web/core/orm_service";
import { patch } from "@web/core/utils/patch";
import { ProductConfiguratorDialog } from "@sale/js/product_configurator_dialog/product_configurator_dialog";
import { getLinkedSaleOrderLines, serializeComboItem, getSelectedCustomPtav } from "@sale/js/sale_utils";


async function applyProduct(record, product, customValue=false) {

    // handle custom values & no variants
    const customAttributesCommands = [
        x2ManyCommands.set([]),  // Command.clear isn't supported in static_list/_applyCommands
    ];
    for (const ptal of product.attribute_lines) {
        const selectedCustomPTAV = getSelectedCustomPtav(ptal);
// Customization Start
        if(selectedCustomPTAV && customValue){
            ptal.customValue = customValue
        }
// Customization End
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


// Sale Order Configurator
patch(SaleOrderLineProductField.prototype, {

    _prepareMultiNewLineData(_line, product) {
        return product;
    },

    async _openProductConfigurator(edit=false, selectedComboItems = []) {
        const saleOrderRecord = this.props.record.model.root;
        const saleOrderLine = this.props.record.data;
        const ptavIds = this._getVariantPtavIds(saleOrderLine);
        let customPtavs = [];

         if (edit) {
            /**
             * no_variant and custom attribute don't need to be given to the configurator for new
             * products.
             */
            ptavIds.push(...this._getNoVariantPtavIds(saleOrderLine));
            customPtavs = await this._getCustomPtavs(saleOrderLine);
        }

        this.dialog.add(ProductConfiguratorDialog, {
            productTemplateId: saleOrderLine.product_template_id.id,
            ptavIds: ptavIds,
            customPtavs: customPtavs,
            quantity: saleOrderLine.product_uom_qty,
            productUOMId: saleOrderLine.product_uom_id.id,
            companyId: saleOrderRecord.data.company_id.id,
            pricelistId: saleOrderRecord.data.pricelist_id.id,
            currencyId: saleOrderLine.currency_id.id,
            soDate: serializeDateTime(saleOrderRecord.data.date_order),
            selectedComboItems: selectedComboItems,
            edit: edit,
            save: async (mainProduct, optionalProducts, multiProducts, options) => {

                if (multiProducts.length > 0) {
                    // Remove main product line if multi products added
                    saleOrderRecord.data.order_line.delete(this.props.record);
                }

                const proms = !selectedComboItems.length
                        ? [applyProduct(this.props.record, mainProduct)]
                        : [];

                for (const [i, product] of optionalProducts.entries()) {
                    const index =
                        saleOrderRecord.data.order_line.records.indexOf(this.props.record)
                        + selectedComboItems.length
                        + i;
                    const line = await saleOrderRecord.data.order_line.addNewRecordAtIndex(index, {
                        mode: 'readonly',
                    });
                    const productData = this._prepareNewLineData(line, product);
                    proms.push(applyProduct(line, productData));
                }

                // Multi products
                let baseIndex = saleOrderRecord.data.order_line.records.indexOf(this.props.record);
                let offset = selectedComboItems.length + optionalProducts.length;

                for (const [i, multiProduct] of multiProducts.entries()) {
                    // Calculate sequence index
                    const currentIndex = baseIndex + offset + i;

                    const line = await saleOrderRecord.data.order_line.addNewRecordAtIndex(currentIndex, {
                        mode: 'readonly',
                    });

                    const multiProductData = this._prepareMultiNewLineData(line, multiProduct);

                    proms.push(
                        applyProduct(line, multiProductData, multiProductData.customValue)
                    );
                }

                await Promise.all(proms);
                this._onProductUpdate();
                saleOrderRecord.data.order_line.leaveEditMode();

            },
             discard: () => {
                if (!selectedComboItems.length) {
                    // Don't delete the main product if it's a combo product as it has been added
                    // from combo configurator
                    saleOrderRecord.data.order_line.delete(this.props.record);
                }
            },
            ...this._getAdditionalDialogProps(),
        });
    }


});
