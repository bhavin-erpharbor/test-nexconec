/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { ProductConfiguratorDialog } from "@sale/js/product_configurator_dialog/product_configurator_dialog";
import { CableCuttingDialog } from "./cable_cutting_dialog";

console.log("Cable cutting configurator patch file loaded");

patch(ProductConfiguratorDialog.prototype, {
    setup() {
        if (super.setup) {
            super.setup(...arguments);
        }
        this.dialog = useService("dialog");
        this.orm = useService("orm");
    },

    async onConfirm(options) {
        console.log("Cable cutting patched onConfirm called");

        if (!this.isPossibleConfiguration()) {
            return;
        }

        // 1) Create dynamic variants first, same as base logic
        for (const product of this.state.products) {
            if (
                !product.id &&
                product.attribute_lines.some(ptal => ptal.create_variant === "dynamic")
            ) {
                const productId = await this._createProduct(product);
                product.id = parseInt(productId);
            }
        }

        const mainProduct = this.state.products.find(
            p => p.product_tmpl_id === this.env.mainProductTmplId
        );

        const optionalProducts = this.state.products.filter(
            p => p.product_tmpl_id !== this.env.mainProductTmplId
        );

        console.log("mainProduct:", mainProduct);

        if (!mainProduct || !mainProduct.id) {
            console.warn("Main product not found, normal save.");
            await this.props.save(
                mainProduct,
                optionalProducts,
                this.state.multiProducts,
                options
            );
            this.props.close();
            return;
        }

        // 2) Read allow_cable_cutting from product.product
        // Make sure product.product has related field allow_cable_cutting.
        let allowCableCutting = false;

        try {
            const productData = await this.orm.read(
                "product.product",
                [mainProduct.id],
                ["allow_cable_cutting"]
            );

            allowCableCutting = productData?.[0]?.allow_cable_cutting || false;
        } catch (error) {
            console.error("Could not read allow_cable_cutting:", error);
        }

        console.log("allowCableCutting:", allowCableCutting);

        // 3) If not cable cutting product, continue normal flow
        if (!allowCableCutting) {
            await this.props.save(
                mainProduct,
                optionalProducts,
                this.state.multiProducts,
                options
            );
            this.props.close();
            return;
        }

        // 4) Open cutting popup before saving
        this.dialog.add(CableCuttingDialog, {
            productName: mainProduct.display_name || mainProduct.name || "",
            confirm: async (cuttingData) => {
                console.log("cuttingData:", cuttingData, this.props, this.props.record);

                // Product qty becomes total length from popup
                mainProduct.quantity = cuttingData.total_length;

                const updatedOptions = {
                    ...(options || {}),
                    cable_cutting_data: {
                        product_id: mainProduct.id,
                        product_tmpl_id: mainProduct.product_tmpl_id,
                        total_length: cuttingData.total_length,
                        total_pieces: cuttingData.total_pieces,
                        lines: cuttingData.lines,
                    },
                };

                await this.props.save(
                    mainProduct,
                    optionalProducts,
                    this.state.multiProducts,
                    updatedOptions
                );

                this.props.close();
            },
        });
    },
});