/** @odoo-module */
import { onWillStart, useState, useSubEnv } from "@odoo/owl";
import { ProductConfiguratorDialog } from "@sale/js/product_configurator_dialog/product_configurator_dialog";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";


patch(ProductConfiguratorDialog.prototype, {
    setup() {
        super.setup();

        this.state = useState({
// Customization Start
            multiProducts: [],
// Customization End
        });

// Customization Start
        useSubEnv({
            addMultiProduct: this._addMultiProduct.bind(this),
        })
// Customization End

        onWillStart(async () => {
            const {
                products,
                optional_products,
                currency_id,
                multiProducts
            } = await this._loadData(this.props.edit);
// Customization Start
            this.state.multiProducts = [];
// Customization End
        });
    },

// Customization Start
    async _getMultiProducts(product,  product_qty, customValue) {
        return rpc('/sale_product_configurator/get_multi_products', {
            product_template_id: product.product_tmpl_id,
            combination: this._getCombination(product),
            parent_combination: this._getParentsCombination(product),
            currency_id: this.props.currencyId,
            pricelist_id: this.props.pricelistId,
            so_date: this.props.soDate,
            quantity: product_qty,
            product_uom_id: this.props.productUOMId,
            company_id: this.props.companyId,
            customValue: customValue
        });
    },

    // Handler to remove a product when the delete button is clicked
    async _removeMultiProduct(event) {
        // Find the row of the clicked button
        const row = event.target.closest('tr');
        if (row) {
            const productId = parseInt(row.querySelector('[name="product_id"]').innerText);
            const customVal = row.querySelector('[name="custom_val"]').innerText;
            if ( customVal && customVal !== "undefined" ) {
                this.state.multiProducts = this.state.multiProducts.filter(
                    p => !(p.id === productId && p.customValue == customVal)
                );
            }
            else {
                this.state.multiProducts = this.state.multiProducts.filter(
                    p => (p.id !== productId)
                );
            }

            // Removes the table row
            row.remove();
        }
    },

    async _renderVariants(variants) {
    const table = document.getElementById('sol_product_tbody');
    variants.forEach((variant) => {
        // Check if a row already exists for the given productTmplId
        let existingRow = table.querySelector(`tr[data-product-id="${variant.product}"][data-custom-vals="${variant.custom_val}"]`);
        if (existingRow) {
            // Remove the product from multiProducts if the row is being updated
            var multiProducts = this.state.multiProducts = this.state.multiProducts.filter(
                product => !(product.id === variant.product && product.customValue === variant.custom_val)
            );
            this.state.multiProducts = this.state.multiProducts.filter(
                    product => !(product.id === variant.product && product.custom_val === variant.custom_val)
                );
            // Update the existing row with new data
            existingRow.querySelector('[name="prod_ref"]').textContent = variant.prodref;
            existingRow.querySelector('[name="product_id"]').textContent = variant.product;
            existingRow.querySelector('[name="prod_qty"]').textContent = variant.quantity;
        } else {
            // Append a new row if it doesn't exist using native JavaScript
            const newRow = document.createElement('tr');
            newRow.className = 'config-tr-data';
            newRow.setAttribute('data-product-id', variant.product);
            newRow.setAttribute('data-custom-vals', variant.custom_val);
            newRow.innerHTML = `
                <td><span id="prod_ref" name="prod_ref">${variant.prodref}</span></td>
                <td style="display: none;"><span id="product_id" name="product_id">${variant.product}</span></td>
                <td><span id="prod_qty" name="prod_qty">${variant.quantity}</span></td>
                <td style="display: none;"><span id="custom_val" name="custom_val">${variant.custom_val}</span></td>
                <td style="display: none;"><span id="product_tmpl_id" name="product_tmpl_id">${variant.productTmplId}</span></td>
                <td>
                    <div id="js_remove_multi" class="js_remove_multi text-center" data-product-id="${variant.productTmplId}">
                        <small><i class="fa fa-trash-o js_remove" title="You can remove the product line using this button"></i></small>
                    </div>
                </td>
            `;
            table.appendChild(newRow);
        }

        // Attach the click event with the remove multi line table button
        const removeButtons = document.querySelectorAll('#js_remove_multi');
        removeButtons.forEach((div) => {
            div.addEventListener('click', (event) => this._removeMultiProduct(event));
        });
    });
},

//    async _renderVariants(variants) {
//        const table = document.getElementById('sol_product_tbody');
//        console.log('\n\ntable:::;', table)
//        variants.forEach((variant) => {
//            // Check if a row already exists for the given productTmplId
//            let existingRow = table.querySelector(`tr[data-product-id="${variant.product}"][data-custom-vals="${variant.custom_val}"]`);
//            console.log("\nnexistingRow::::::::",existingRow)
//            if (existingRow) {
//                // Remove the product from multiProducts if the row is being updated
//                var multiProducts = this.state.multiProducts = this.state.multiProducts.filter(
//                    product => !(product.id === variant.product && product.customValue === variant.custom_val)
//                );
//                this.state.multiProducts = this.state.multiProducts.filter(
//                        product => !(product.id === variant.product && product.custom_val === variant.custom_val)
//                    );
//                // Update the existing row with new data
//                existingRow.querySelector('[name="prod_ref"]').textContent = variant.prodref;
//                existingRow.querySelector('[name="product_id"]').textContent = variant.product;
//                existingRow.querySelector('[name="prod_qty"]').textContent = variant.quantity;
//            } else {
//                // Append a new row if it doesn't exist
//                $(table).append(`
//                    <tr class="config-tr-data" data-product-id="${variant.product}" data-custom-vals="${variant.custom_val}">
//                        <td><span id="prod_ref" name="prod_ref">${variant.prodref}</span></td>
//                        <td style="display: none;"><span id="product_id" name="product_id">${variant.product}</span></td>
//                        <td><span id="prod_qty" name="prod_qty">${variant.quantity}</span></td>
//                        <td style="display: none;"><span id="custom_val" name="custom_val">${variant.custom_val}</span></td>
//                        <td style="display: none;"><span id="product_tmpl_id" name="product_tmpl_id">${variant.productTmplId}</span></td>
//                        <td>
//                            <div id="js_remove_multi" class="js_remove_multi text-center" data-product-id="${variant.productTmplId}">
//                                <small><i class="fa fa-trash-o js_remove" title="You can remove the product line using this button"></i></small>
//                            </div>
//                        </td>
//                    </tr>
//                `);
//            }
//
//            // Attach the click event with the remove multi line table button
//            const removeButtons = document.querySelectorAll('#js_remove_multi');
//            removeButtons.forEach((div) => {
//                div.addEventListener('click', (event) => this._removeMultiProduct(event));
//            });
//        });
//    },
// Customization End

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

// Customization Start
    /**
     * Add the product to the list of products and fetch his multipla products.
     *
     * @param {Number} productTmplId - The product template id, as a `product.template` id.
     */
    async _addMultiProduct(productTmplId) {
        const index = this.state.products.findIndex(
            p => p.product_tmpl_id === productTmplId
        );
        if (index >= 0) {
            // Render the variants in the table
            const product = this._findProduct(productTmplId);

            // Create new product
            if(!product){
                const product = this.onMultiConfirm()
            }

            const templateData = await rpc('/web/dataset/call_kw/product.template/read', {
                model: 'product.template',
                method: 'read',
                args: [[product.product_tmpl_id], ['name', 'default_code']],
                kwargs: {}
            });
            // Extract the reference number (default_code) from the fetched rpc data
            // const reference = templateData && templateData[0] && templateData[0].default_code || '';
            var reference = await rpc('/configurator/internal_ref', {
                product_id: product.id,
                custom_val: this.props.customValue,
                combination: this._getParentsCombination(product)
            });

            const variants = [{
                productTmplId: product.product_tmpl_id,
                prodref: reference,
                product: product.id,
                custom_val: this.props.customValue,
                // custom_vals: this._updatePTAVCustomValue.bind(this),
                quantity: product.quantity
            }];
            // Create the new multi product dynamic table
            this._renderVariants(variants);

            // Create the new multi product combination
            let newMultiProducts = await this._getMultiProducts(product, product.quantity, this.props.customValue);

            for(const newmultiProductDict of newMultiProducts) {
                // Ensure the multiProduct exists and the first product is being checked
                if (newmultiProductDict && newMultiProducts[0]?.[0].id === product.id) {

                    // Added custom attribute lines
                    newmultiProductDict[0].attribute_lines = this.state.products && this.state.products[0].attribute_lines
                }
                if (newmultiProductDict) this.state.multiProducts.push(...newmultiProductDict);

            }
        }
    },
// Customization End

    /**
     * Confirm the current combination(s).
     *
     * @return {undefined}
     */
    async onMultiConfirm(options) {
        if (!this.isPossibleConfiguration()) return;
        // Create the products with dynamic attributes
        for (const product of this.state.products) {
            if (
                !product.id &&
                product.attribute_lines.some(ptal => ptal.create_variant === "dynamic")
            ) {
                const productId = await this._createProduct(product);
                product.id = parseInt(productId);
            }
            return product
        }
    },

    /**
     * Confirm the current combination(s).
     *
     * @return {undefined}
     */
    async onConfirm(options) {
        if (!this.isPossibleConfiguration()) return;
        // Create the products with dynamic attributes
        for (const product of this.state.products) {
            if (
                !product.id &&
                product.attribute_lines.some(ptal => ptal.create_variant === "dynamic")
            ) {
                const productId = await this._createProduct(product);
                product.id = parseInt(productId);
            }
        }
        await this.props.save(
            this.state.products.find(
                p => p.product_tmpl_id === this.env.mainProductTmplId
            ),
            this.state.products.filter(
                p => p.product_tmpl_id !== this.env.mainProductTmplId
            ),

// Customization Start
            this.state.multiProducts,
            options,

// Customization End
        );
        this.props.close();
    },

});
