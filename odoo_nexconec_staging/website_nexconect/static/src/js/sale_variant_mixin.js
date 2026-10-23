import VariantMixin from "@website_sale/js/variant_mixin";
import { rpc } from '@web/core/network/rpc';
import wSaleUtils from '@website_sale/js/website_sale_utils';
import { renderToFragment } from "@web/core/utils/render";


VariantMixin._getCombinationInfo = async function (ev) {
    const custom_val = $('input.variant_custom_value').val();
    const parent = ev.target.closest('.js_product');
    if (!parent) return Promise.resolve();
    const combination = wSaleUtils.getSelectedAttributeValues(parent);

    const combinationInfo = await this.waitFor(rpc('/website_sale/get_combination_info', {
        'product_template_id': parseInt(parent.querySelector('.product_template_id')?.value),
        'product_id': this._getProductId(parent),
        'combination': combination,
        'add_qty': parseInt(parent.querySelector('input[name="add_qty"]')?.value),
        'uom_id': this._getUoMId(parent),
        'context': this.context,
        'custom_val': custom_val,
        ...this._getOptionalCombinationInfoParam(parent),
    }));
    this._onChangeCombination(ev, parent, combinationInfo);
    this._checkExclusions(parent, combination);
    $('.oe_website_sale')
    .find('.location_availability_messages')
    .empty(); // Remove older messages
     this.el.querySelector('div.location_availability_messages').append(renderToFragment(
        'website_nexconect.product_location_availability', combinationInfo
    ));
    $('.internal_ref_code').html(combinationInfo['internal_code'])
};




//import { OptionalProductsModal } from "@website_sale_product_configurator/js/sale_product_configurator_modal";
//import { jsonrpc } from '@web/core/network/rpc_service';
//import { renderToFragment } from "@web/core/utils/render";
//import VariantMixin from "@website_sale/js/sale_variant_mixin";
//const VariantMixinInherit = VariantMixin.handleCustomValues;
//
//
//VariantMixin.handleCustomValues = function ($target) {
//    var $variantContainer;
//    var $customInput = false;
//    if ($target.is('input[type=radio]') && $target.is(':checked')) {
//        $variantContainer = $target.closest('ul').closest('li');
//        $customInput = $target;
//    } else if ($target.is('select')) {
//        $variantContainer = $target.closest('li');
//        $customInput = $target
//            .find('option[value="' + $target.val() + '"]');
//    }
//
//    if ($variantContainer) {
//        if ($customInput && $customInput.data('is_custom') === 'True') {
//            var attributeValueId = $customInput.data('value_id');
//            var attributeValueName = $customInput.data('value_name');
//
//            if ($variantContainer.find('.variant_custom_value').length === 0
//                || $variantContainer
//                    .find('.variant_custom_value')
//                    .data('custom_product_template_attribute_value_id') !== parseInt(attributeValueId)) {
//                $variantContainer.find('.variant_custom_value').remove();
//
//                const previousCustomValue = $customInput.attr("previous_custom_value");
//                var $input = $('<input>', {
//                    type: 'text',
//                    'data-custom_product_template_attribute_value_id': attributeValueId,
//                    'data-attribute_value_name': attributeValueName,
//                    class: 'variant_custom_value form-control mt-2'
//                });
//                var custom_attribute = $customInput.data('custom_attribute') || false;
//                if (custom_attribute) {
//                    var custom_value = $customInput.data('custom_value') || 1;
//                    $input.addClass('custom_attribute');
//                    $input.attr('data-custom_value', custom_value);
//                    $input.attr('data-custom_attribute', custom_attribute);
//                    $input.val(custom_value)
//                }
//                $input.attr('placeholder', attributeValueName);
//                $input.addClass('custom_value_radio');
//                $variantContainer.append($input);
//                if (previousCustomValue) {
//                    $input.val(previousCustomValue);
//                }
//            }
//        } else {
//            $variantContainer.find('.variant_custom_value').remove();
//        }
//    }
//    VariantMixinInherit.apply(this, arguments);
//}

//OptionalProductsModal.include({
//    events: Object.assign({}, OptionalProductsModal.prototype.events || {}, {
//        'keypress input.variant_custom_value': '_onChangeCustomValue',
//    }),
//
//    _onChangeCustomValue: function (ev) {
//        //Only Integer/Float values allowed
//        if ((ev.which != 46) && (ev.which < 48 || ev.which > 57)) {
//            ev.preventDefault();
//        }
//    },
//    _getCombinationInfo: function (ev) {
//        var custom_val = $('input.variant_custom_value').val();
//        const $parent = $(ev.target).closest('.js_product');
//        if (!$parent.length) {
//            return Promise.resolve();
//        }
//
//        const combination = this.getSelectedVariantValues($parent);
//        let parentCombination;
//
//        if ($parent.hasClass('main_product')) {
//            parentCombination = $parent.find('ul[data-attribute_exclusions]').data('attribute_exclusions').parent_combination;
//            const $optProducts = $parent.parent().find(`[data-parent-unique-id='${$parent.data('uniqueId')}']`);
//
//            for (const optionalProduct of $optProducts) {
//                const $currentOptionalProduct = $(optionalProduct);
//                const childCombination = this.getSelectedVariantValues($currentOptionalProduct);
//                const productTemplateId = parseInt($currentOptionalProduct.find('.product_template_id').val());
//                jsonrpc('/website_sale/get_combination_info', {
//                    'product_template_id': productTemplateId,
//                    'product_id': this._getProductId($currentOptionalProduct),
//                    'combination': childCombination,
//                    'add_qty': parseInt($currentOptionalProduct.find('input[name="add_qty"]').val()),
//                    'parent_combination': combination,
//                    'context': this.context,
//                    'custom_val': custom_val,
//                    ...this._getOptionalCombinationInfoParam($currentOptionalProduct),
//                }).then((combinationData) => {
//                    this._onChangeCombination(ev, $currentOptionalProduct, combinationData);
//                    this._checkExclusions($currentOptionalProduct, childCombination, combinationData.parent_exclusions);
//                });
//            }
//        } else {
//            parentCombination = this.getSelectedVariantValues(
//                $parent.parent().find('.js_product.in_cart.main_product')
//            );
//        }
//
//        return jsonrpc('/website_sale/get_combination_info', {
//            'product_template_id': parseInt($parent.find('.product_template_id').val()),
//            'product_id': this._getProductId($parent),
//            'combination': combination,
//            'add_qty': parseInt($parent.find('input[name="add_qty"]').val()),
//            'parent_combination': parentCombination,
//            'context': this.context,
//            'custom_val': custom_val,
//            ...this._getOptionalCombinationInfoParam($parent),
//        }).then((combinationData) => {
//            this._onChangeCombination(ev, $parent, combinationData);
//            this._checkExclusions($parent, combination, combinationData.parent_exclusions);
//            $('.oe_website_sale')
//                .find('.location_availability_messages')
//                .empty(); // Remove older messages
//            $('div.location_availability_messages').append(renderToFragment(
//                'website_nexconect.product_location_availability',
//                combinationData
//            ));
//            $('.internal_ref_code').html(combinationData['internal_code'])
//        });
//    },
//})
