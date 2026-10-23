import { useService } from "@web/core/utils/hooks";
import { serializeDateTime } from "@web/core/l10n/dates";
import { getSelectedCustomPtav } from "@sale/js/sale_utils";
import { x2ManyCommands } from "@web/core/orm_service";
import { ProductConfiguratorDialog } from "@sale/js/product_configurator_dialog/product_configurator_dialog";

async function applyPurchaseProduct(record, product, customValue = false) {

    // handle custom values & no variants
    const customAttributesCommands = [
        x2ManyCommands.set([]), // Command.clear isn't supported in static_list/_applyCommands
    ];
    for (const ptal of product.attribute_lines) {
        const selectedCustomPTAV = getSelectedCustomPtav(ptal);
         // Customization Start
        if (selectedCustomPTAV && customValue) {
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
        product_id: {
            id: product.id,
            display_name: product.display_name
        },
        product_qty: product.quantity,
        product_no_variant_attribute_value_ids: [x2ManyCommands.set(noVariantPTAVIds)],
        product_custom_attribute_value_ids: customAttributesCommands,
        price_unit: product.price,
        price_subtotal: product.price * product.quantity
    }
    if (product.uom) {
        // only update uom field if uom are enabled (uom_data provided), otherwise we don't have the display_name
        // and the value isn't expected to change anyway.
        update_values.product_uom_id = product.uom;
    }

    await record._update(update_values);
    record.data.product_qty = product.quantity
    record.data.price_unit = product.price
    record.data.price_subtotal = product.price * product.quantity
};


export function useProductConfigurator() {
    const dialog = useService("dialog");

    const prepareMultiNewLineData = (_line, product) => {
        return product;
    };

    async function _onProductUpdate() {}

    const openPurchaseDialog = (rootRecord, ptavIds, customPtavs, edit, selectedComboItems, purchaseOrderLine, record) => {

        dialog.add(ProductConfiguratorDialog, {
            productTemplateId: purchaseOrderLine.product_template_id.id,
            ptavIds: ptavIds,
            customPtavs: customPtavs,
            quantity: purchaseOrderLine.product_qty ? purchaseOrderLine.product_qty : 1,
            productUOMId: purchaseOrderLine.product_uom_id.id,
            companyId: purchaseOrderLine.company_id.id,
            currencyId: purchaseOrderLine.currency_id.id,
            soDate: serializeDateTime(rootRecord.data.date_order),
            edit: edit,
            hidePrice: true,
            selectedComboItems: selectedComboItems,
            save: async (mainProduct, optionalProducts, multiProducts, options) => {

                if (multiProducts.length > 0) {
                    // Remove main product line if multi products added
                    rootRecord.data.order_line.delete(record);
                }

                await Promise.all([
                    // Don't add main product if it's a combo product as it has already been added
                    // from combo configurator
                    ...(
                        !selectedComboItems.length ? [applyPurchaseProduct(record, mainProduct)] : []
                    ),
                    ...optionalProducts.map(async product => {
                        const line = await rootRecord.data.order_line.addNewRecord({
                            position: 'bottom',
                            mode: 'readonly'
                        });
                        const productData = this._prepareNewLineData(line, product);
                        await applyPurchaseProduct(line, productData);
                    }),

                    // Multi products
                    ...(multiProducts.length > 0 ? multiProducts.map(async (multiProduct) => {
                        const line = await rootRecord.data.order_line.addNewRecord({
                            position: 'bottom',
                            mode: 'readonly',
                        });
                        const multiProductData = prepareMultiNewLineData(line, multiProduct);
                        await applyPurchaseProduct(line, multiProductData, multiProductData.customValue);
                    }) : [])

                ]);
                await _onProductUpdate();
                rootRecord.data.order_line.leaveEditMode();
            },

            discard: () => {
                if (!selectedComboItems.length) {
                    // Don't delete the main product if it's a combo product as it has been added
                    // from combo configurator
                    rootRecord.data.order_line.delete(record);
                }
            },
        });
    };

    const getVariantPtavIds = (purchaseOrderLine) => {
        return purchaseOrderLine.product_template_attribute_value_ids.currentIds;
    };

    const getNoVariantPtavIds = (purchaseOrderLine) => {
        return purchaseOrderLine.product_no_variant_attribute_value_ids.currentIds;
    };

    const getCustomPtavs = async (purchaseOrderLine) => {
        const customPtavIds = purchaseOrderLine.product_custom_attribute_value_ids;
        let customPtavs = [];

        if (customPtavIds.records[0]?.isNew) {
            customPtavs = customPtavIds.records.map(record => record.data);
        } else if (customPtavIds.currentIds.length) {
            const specification = {
                custom_product_template_attribute_value_id: {
                    fields: {
                        id: {}
                    },
                },
                custom_value: {},
            };

            try {
                customPtavs = await this.orm.webRead(
                    'product.attribute.custom.value',
                    customPtavIds.currentIds, {
                        specification
                    }
                );
            } catch (error) {
                console.error("Error fetching custom PTAVs:", error);
            }
        }

        return customPtavs.map(customPtav => ({
            id: customPtav.custom_product_template_attribute_value_id?.id,
            value: customPtav.custom_value,
        }));
    };

    const open = async (record, edit) => {
        const PurchaseOrderRecord = record.model.root;

        const purchaseOrderLine = record.data;
        const ptavIds = getVariantPtavIds(purchaseOrderLine);
        let customPtavs = [];
        let selectedComboItems = [];
        if (edit) {
            /**
             * no_variant and custom attribute don't need to be given to the configurator for new
             * products.
             */
            ptavIds.push(...getNoVariantPtavIds(purchaseOrderLine));
            customPtavs = await getCustomPtavs(purchaseOrderLine);
        }

        openPurchaseDialog(
            PurchaseOrderRecord,
            ptavIds,
            customPtavs,
            edit,
            selectedComboItems,
            record.data,
            record,
        );
    };

    return { open };
}
