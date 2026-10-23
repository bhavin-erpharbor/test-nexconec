/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { renderToElement } from "@web/core/utils/render";
import { jsonrpc } from "@web/core/network/rpc_service";

publicWidget.registry.WebsiteSale.include({
        /**
         * Change Price checking to the regular _onChangeCombination method
         * @override
         */
        _getCombinationInfo: function (ev) {
            var self = this;
            if ($(ev.target).hasClass('variant_custom_value')) {
                return Promise.resolve();
            }
            const $parent = $(ev.target).closest('.js_product');
            if(!$parent.length){
                return Promise.resolve();
            }
            const combination = this.getSelectedVariantValues($parent);
            let parentCombination;
            if ($parent.hasClass('main_product')) {
                parentCombination = $parent.find('ul[data-attribute_exclusions]').data('attribute_exclusions').parent_combination;
                const $optProducts = $parent.parent().find(`[data-parent-unique-id='${$parent.data('uniqueId')}']`);
                for (const optionalProduct of $optProducts) {
                    const $currentOptionalProduct = $(optionalProduct);
                    const childCombination = this.getSelectedVariantValues($currentOptionalProduct);
                    const productTemplateId = parseInt($currentOptionalProduct.find('.product_template_id').val());
                    jsonrpc('/website_sale/get_combination_info', {
                        'product_template_id': productTemplateId,
                        'product_id': this._getProductId($currentOptionalProduct),
                        'combination': childCombination,
                        'add_qty': parseInt($currentOptionalProduct.find('input[name="add_qty"]').val()),
                        'parent_combination': combination,
                        'context': this.context,
                        ...this._getOptionalCombinationInfoParam($currentOptionalProduct),
                    }).then((combinationData) => {
                        this._onChangeCombination(ev, $currentOptionalProduct, combinationData);
                        this._checkExclusions($currentOptionalProduct, childCombination, combinationData.parent_exclusions);
                        var $message = $(renderToElement('scs_website_product.product_location_availability', combinationData));
                        $('div.location_availability_messages').html($message);
                        $('.internal_ref_code').html(combinationData['internal_code'])
                    });
                }
            } else {
                parentCombination = this.getSelectedVariantValues(
                    $parent.parent().find('.js_product.in_cart.main_product')
                );
            }
            return jsonrpc('/website_sale/get_combination_info', {
                'product_template_id': parseInt($parent.find('.product_template_id').val()),
                'product_id': this._getProductId($parent),
                'combination': combination,
                'add_qty': parseInt($parent.find('input[name="add_qty"]').val()),
                'parent_combination': parentCombination,
                'context': this.context,
                ...this._getOptionalCombinationInfoParam($parent),
            }).then((combinationData) => {
                console.log("combinationData",combinationData)
                this._onChangeCombination(ev, $parent, combinationData);
                this._checkExclusions($parent, combination, combinationData.parent_exclusions);
                var $message = $(renderToElement('scs_website_product.product_location_availability',combinationData));
                $('div.location_availability_messages').html($message);
                $('.internal_ref_code').html(combinationData['internal_code'])
            });
        },
    });
