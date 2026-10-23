import publicWidget from "@web/legacy/js/public/public_widget";
//import '@website_sale/interactions/website_sale';
import { renderToFragment } from "@web/core/utils/render";
import { _t } from "@web/core/l10n/translation";
import { patch } from '@web/core/utils/patch';
import { patchDynamicContent } from '@web/public/utils';
import { rpc } from '@web/core/network/rpc';
import wSaleUtils from '@website_sale/js/website_sale_utils';
import { WebsiteSale } from '@website_sale/interactions/website_sale';

patch(WebsiteSale.prototype, {
     setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            'keypress input.variant_custom_value': {
                't-on-keypress': this._onChangeCustomValue.bind(this),
            },
            'click a.custom_add_cart': {
                't-on-click': this._AddToCartWithoutRedirect.bind(this),
            },
            '#quantity_input': { 't-on-change': this.onChangeQtyInput.bind(this), },
        });
    },

     // Utility function to format the MOQ text
    _formatMOQText(moqText) {
        const lang = document.documentElement.lang;
        if (lang === 'en-GB') {
            return moqText.replace(/,/g, '');
        } else if (lang === 'fr-FR') {
            return moqText.replace(/\s/g, '').replace(',', '.');
        } else if (lang === 'it-IT') {
            return moqText.replace(/\./g, '').replace(',', '.');
        }
        return moqText;
    },

    _updateButtonsByMOQ(quantity, moq) {
        const addBtn = document.querySelector('#add_to_cart');
        const minusBtn = document.querySelector('[name="remove_one"]');

        if (!addBtn || !minusBtn) return;

        // Add to Cart Button
        if (quantity < moq) {
            addBtn.classList.add('disabled-moq');
            this._toggleWarning(true);
            addBtn.setAttribute('aria-disabled', 'true');
        } else {
            addBtn.classList.remove('disabled-moq');
            this._toggleWarning(false);
            addBtn.removeAttribute('aria-disabled');
        }

        // Minus Button
        if (quantity <= moq) {
            minusBtn.classList.add('disabled-moq');
            minusBtn.setAttribute('aria-disabled', 'true');
        } else {
            minusBtn.classList.remove('disabled-moq');
            minusBtn.removeAttribute('aria-disabled');
        }
    },

    // Utility function to toggle the warning message
    _toggleWarning(show) {
        const warning = $('.min-qty-warning');
        if (show) {
            warning.removeClass('animated bounce').width();
            warning.addClass('animated bounce').fadeIn();
        } else {
            warning.fadeOut();
        }
    },

    start() {
        super.start();
        const input = this.el.querySelector('.input-group input');
        if (!input) return;

        let moqText = document.querySelector('#product_moq')?.textContent?.trim() || '0';
        this.moq = parseInt(this._formatMOQText(moqText)) || 0;

        const quantity = parseFloat(input.value || 0);

        // Disable buttons on page load
        if (this.moq > 0) {
            this._updateButtonsByMOQ(quantity, this.moq);
        }
    },

    onChangeQtyInput(ev) {
        const input = this.el.querySelector('.input-group input');
        if (!input) return;

        let moqText = document.querySelector('#product_moq')?.textContent?.trim() || '0';
        this.moq = parseInt(this._formatMOQText(moqText)) || 0;

        const quantity = parseFloat(input.value || 0);

        if (this.moq > 0) {
            this._updateButtonsByMOQ(quantity, this.moq);
        }
    },

    onChangeQuantity(ev) {
        let moqText = $('#product_moq').text().trim();
        const moq = parseInt(this._formatMOQText(moqText));

        const input = ev.currentTarget.closest('.input-group').querySelector('input');
        const min = parseFloat(input.dataset.min || 0);
        const max = parseFloat(input.dataset.max || Infinity);
        const previousQty = parseFloat(input.value || 0);

        const quantity = (
            ev.currentTarget.name === 'remove_one' ? -1 : 1
        ) + previousQty;

        const newQty = Math.min(Math.max(quantity, min), max);

        if (newQty !== previousQty) {
            input.value = newQty;
            // Trigger `onChangeAddQuantity`.
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }

        this._updateButtonsByMOQ(newQty, moq);
    },

    _onChangeCustomValue: function (ev) {
        //Only Integer/Float values allowed
        if ((ev.which != 46) && (ev.which < 48 || ev.which > 57)) {
            ev.preventDefault();
        }
    },

     async _AddToCartWithoutRedirect(ev) {
        const $card = $(ev.currentTarget).closest('form');
        const root = WebsiteSale.prototype;

        try {
            const data = await this.waitFor(rpc({
                route: "/shop/cart/update_json",
                params: {
                    product_id: parseInt($card.find('input[name="product_id"]').val()),
                    add_qty: parseInt($card.find('input[name="add_qty"]').val() || 1),
                    product_custom_attribute_values: JSON.stringify(root.getCustomVariantValues($card.find('.js_product'))),
                    variant_values: JSON.stringify(root.getSelectedVariantValues($card.find('.js_product'))),
                    no_variant_attribute_values: JSON.stringify(root.getNoVariantAttributeValues($card.find('.js_product')))
                },
            }));

            const $navButton = $('header .o_wsale_my_cart').first();
            wSaleUtils.animateClone($navButton, $card, 25, 40);
            $card.find('.added_txt').remove();
            $card.find('input.quantity').val('1');
            $card.append('<p class="added_txt text-success">Added to Cart.</p>').fadeIn();

            setTimeout(() => {
                $card.find('.added_txt').fadeOut('slow');
            }, 10000);

            $('.my_cart_quantity').html(data.cart_quantity || '<i class="fa fa-warning" /> ');
        } catch (error) {
            console.error('Failed to add to cart:', error);
        }
    },

        handleCustomValues(el) {
            let variantContainer;
            let customInput = false;
            if (el.matches('input[type=radio]:checked')) {
                variantContainer = el.closest('ul').closest('li');
                customInput = el;
            } else if (el.matches('select')) {
                variantContainer = el.closest('li');
                customInput = el.querySelector(`option[value="${el.value}"]`);
            }

            if (variantContainer) {
                const customValue = variantContainer.querySelector('.variant_custom_value');
                if (customInput && customInput.dataset.isCustom === 'True') {
                    const attributeValueId = customInput.dataset.valueId;
                    if (
                        !customValue
                        || customValue.dataset.customProductTemplateAttributeValueId !== attributeValueId
                    ) {
                        customValue?.remove();

                        const previousCustomValue = customInput.getAttribute('previous_custom_value');
                        const input = document.createElement('input');
                        input.type = 'text';
                        input.dataset.customProductTemplateAttributeValueId = attributeValueId;
                        input.classList.add(
                            'variant_custom_value', 'custom_value_radio', 'form-control', 'mt-2'
                        );
                        input.setAttribute('placeholder', customInput.dataset.valueName);

                        const custom_attribute = customInput.dataset.custom_attribute || false;
                         if (custom_attribute){
                            const custom_value = customInput.dataset.custom_value || 1;
                            input.classList.add('custom_attribute');
                            input.setAttribute('data-custom_value', custom_value);
                            input.setAttribute('data-custom_attribute', custom_attribute);
                            input.value = custom_value;
                        }
                        variantContainer.appendChild(input);
                        if (previousCustomValue) {
                            input.value = previousCustomValue;
                        }
                    }
                } else {
                    customValue?.remove();
                }
            }
        },

});

//publicWidget.registry.WebsiteSale.include({
//    events: Object.assign({}, publicWidget.registry.WebsiteSale.prototype.events, {
//        'keypress input.variant_custom_value': '_onChangeCustomValue',
//        'click a.custom_add_cart' : '_AddToCartWithoutRedirect'
//    }),
//
//    _onChangeCustomValue: function (ev) {
//        //Only Integer/Float values allowed
//        if ((ev.which != 46) && (ev.which < 48 || ev.which > 57)) {
//            ev.preventDefault();
//        }
//    },
//        _AddToCartWithoutRedirect:function (ev) {
//            var $card = $(ev.currentTarget).closest('form');
//            var root = publicWidget.registry.WebsiteSale.prototype
//            this.rpc({
//                route: "/shop/cart/update_json",
//                params: {
//                    product_id: parseInt($card.find('input[name="product_id"]').val()),
//                    add_qty: parseInt($card.find('input[name="add_qty"]').val() || 1),
//                    product_custom_attribute_values: JSON.stringify(root.getCustomVariantValues($card.find('.js_product'))),
//                    variant_values: JSON.stringify(root.getSelectedVariantValues($card.find('.js_product'))),
//                    no_variant_attribute_values: JSON.stringify(root.getNoVariantAttributeValues($card.find('.js_product')))
//            },
//            }).then(function (data) {
//                var $navButton = $('header .o_wsale_my_cart').first();
//                wSaleUtils.animateClone($navButton, $card, 25, 40);
//                $card.find('.added_txt').remove();
//                $card.find('input.quantity').val('1')
//                $card.append('<p class="added_txt text-success">Added to Cart.</p>').fadeIn();
//                setTimeout(function() {
//                    $card.find('.added_txt').fadeOut('slow');
//                }, 10000);
//                $('.my_cart_quantity').html(data.cart_quantity || '<i class="fa fa-warning" /> ');
//            });
//
//        },
//        /**
//         * Change Price checking to the regular _onChangeCombination method
//         * @override
//         */
//
//        async _getCombinationInfo(ev) {
//            var custom_val = $('input.variant_custom_value').val();
////            if (ev.target.classList.contains('variant_custom_value')) return Promise.resolve();
//            const parent = ev.target.closest('.js_product');
//            if (!parent) return Promise.resolve();
//            const combination = wSaleUtils.getSelectedAttributeValues(parent);
//
//            const combinationInfo = await this.waitFor(rpc('/website_sale/get_combination_info', {
//                'product_template_id': parseInt(parent.querySelector('.product_template_id')?.value),
//                'product_id': this._getProductId(parent),
//                'combination': combination,
//                'add_qty': parseInt(parent.querySelector('input[name="add_qty"]')?.value),
//                'uom_id': this._getUoMId(parent),
//                'context': this.context,
//                'custom_val': custom_val,
//                ...this._getOptionalCombinationInfoParam(parent),
//            }));
//            this._onChangeCombination(ev, parent, combinationInfo);
//            this._checkExclusions(parent, combination);
//            $('.oe_website_sale')
//            .find('.location_availability_messages')
//            .empty(); // Remove older messages
//            $('div.location_availability_messages').append(renderToFragment(
//                'website_nexconect.product_location_availability',
//                combinationData
//            ));
//            $('.internal_ref_code').html(combinationData['internal_code'])
//        },
//
//
////        _getCombinationInfo: function (ev) {
////            var custom_val = $('input.variant_custom_value').val();
////            const $parent = $(ev.target).closest('.js_product');
////            if(!$parent.length){
////                return Promise.resolve();
////            }
////
////            const combination = this.getSelectedVariantValues($parent);
////            let parentCombination;
////
////            if ($parent.hasClass('main_product')) {
////                parentCombination = $parent.find('ul[data-attribute_exclusions]').data('attribute_exclusions').parent_combination;
////                const $optProducts = $parent.parent().find(`[data-parent-unique-id='${$parent.data('uniqueId')}']`);
////
////                for (const optionalProduct of $optProducts) {
////                    const $currentOptionalProduct = $(optionalProduct);
////                    const childCombination = this.getSelectedVariantValues($currentOptionalProduct);
////                    const productTemplateId = parseInt($currentOptionalProduct.find('.product_template_id').val());
////                    jsonrpc('/website_sale/get_combination_info', {
////                        'product_template_id': productTemplateId,
////                        'product_id': this._getProductId($currentOptionalProduct),
////                        'combination': childCombination,
////                        'add_qty': parseInt($currentOptionalProduct.find('input[name="add_qty"]').val()),
////                        'parent_combination': combination,
////                        'context': this.context,
////                        'custom_val': custom_val,
////                        ...this._getOptionalCombinationInfoParam($currentOptionalProduct),
////                    }).then((combinationData) => {
////                        this._onChangeCombination(ev, $currentOptionalProduct, combinationData);
////                        this._checkExclusions($currentOptionalProduct, childCombination, combinationData.parent_exclusions);
////                    });
////                }
////            } else {
////                parentCombination = this.getSelectedVariantValues(
////                    $parent.parent().find('.js_product.in_cart.main_product')
////                );
////            }
////
////            return jsonrpc('/website_sale/get_combination_info', {
////                'product_template_id': parseInt($parent.find('.product_template_id').val()),
////                'product_id': this._getProductId($parent),
////                'combination': combination,
////                'add_qty': parseInt($parent.find('input[name="add_qty"]').val()),
////                'parent_combination': parentCombination,
////                'context': this.context,
////                'custom_val': custom_val,
////                ...this._getOptionalCombinationInfoParam($parent),
////            }).then((combinationData) => {
////                this._onChangeCombination(ev, $parent, combinationData);
////                this._checkExclusions($parent, combination, combinationData.parent_exclusions);
////                $('.oe_website_sale')
////                .find('.location_availability_messages')
////                .empty(); // Remove older messages
////                $('div.location_availability_messages').append(renderToFragment(
////                    'website_nexconect.product_location_availability',
////                    combinationData
////                ));
////                $('.internal_ref_code').html(combinationData['internal_code'])
////            });
////        },
//
//        handleCustomValues(el) {
//        let variantContainer;
//        let customInput = false;
//        if (el.matches('input[type=radio]:checked')) {
//            variantContainer = el.closest('ul').closest('li');
//            customInput = el;
//        } else if (el.matches('select')) {
//            variantContainer = el.closest('li');
//            customInput = el.querySelector(`option[value="${el.value}"]`);
//        }
//
//        if (variantContainer) {
//            const customValue = variantContainer.querySelector('.variant_custom_value');
//            if (customInput && customInput.dataset.isCustom === 'True') {
//                const attributeValueId = customInput.dataset.valueId;
//                if (
//                    !customValue
//                    || customValue.dataset.customProductTemplateAttributeValueId !== attributeValueId
//                ) {
//                    customValue?.remove();
//
//                    const previousCustomValue = customInput.getAttribute('previous_custom_value');
//                    const input = document.createElement('input');
//                    input.type = 'text';
//                    input.dataset.customProductTemplateAttributeValueId = attributeValueId;
//                    input.classList.add(
//                        'variant_custom_value', 'custom_value_radio', 'form-control', 'mt-2'
//                    );
//                    input.setAttribute('placeholder', customInput.dataset.valueName);
//
//                    const custom_attribute = customInput.data('custom_attribute') || false;
//                     if (custom_attribute){
//                        const custom_value = customInput.data('custom_value') || 1;
//                        input.addClass('custom_attribute');
//                        input.attr('data-custom_value', custom_value);
//                        input.attr('data-custom_attribute', custom_attribute);
//                        input.val(custom_value)
//                    }
//                    variantContainer.appendChild(input);
//                    if (previousCustomValue) {
//                        input.value = previousCustomValue;
//                    }
//                }
//            } else {
//                customValue?.remove();
//            }
//        }
//    },
//    });
