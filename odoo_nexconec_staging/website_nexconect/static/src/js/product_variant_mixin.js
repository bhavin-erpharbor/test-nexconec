odoo.define('website_nexconect.product_variant_mixin', function (require) {
    "use strict";

    var ajax = require('web.ajax');
    var core = require('web.core');
    var VariantMixin = require('sale.VariantMixin');
    var ProductConfiguratorFormRenderer = require('sale_product_configurator.ProductConfiguratorFormRenderer');

    var _t = core._t;

    ProductConfiguratorFormRenderer.include({
        events: _.extend({
            'keypress input.variant_custom_value.custom_attribute': '_onChangeCustomValue',
        }, ProductConfiguratorFormRenderer.prototype.events),
        _onChangeCustomValue: function (ev) {
            //Only Integer/Float values allowed
            if ((ev.which != 46) && (ev.which < 48 || ev.which > 57)) {
                ev.preventDefault();
            }
        },
        _getCombinationInfo : function (ev) {
            var self = this;
            var $parent = $(ev.target).closest('.js_product');
            var qty = $parent.find('input[name="add_qty"]').val();
            var combination = VariantMixin.getSelectedVariantValues($parent);
            var parentCombination = $parent.find('ul[data-attribute_exclusions]').data('attribute_exclusions').parent_combination;
            var productTemplateId = parseInt($parent.find('.product_template_id').val());
            var custom_val = $('input.variant_custom_value').val();
            if ($(ev.target).hasClass('variant_custom_value')) {
                custom_val = $(ev.target).val()
            }
            if (custom_val === undefined) {
                var customValueIds = this.state.data.product_custom_attribute_value_ids;
                if (customValueIds) {
                    _.each(customValueIds.data, function (customValue) {
                        var attributeValueId = customValue.data.custom_product_template_attribute_value_id.data.id;
                        var $input = self._findRelatedAttributeValueInput(attributeValueId);
                        if (($input.length == 1) && (customValue.data.custom_value)) {
                            custom_val = customValue.data.custom_value
                        }
                    });
                }
            }
            VariantMixin._checkExclusions($parent, combination);
            return ajax.jsonRpc(VariantMixin._getUri('/sale/get_combination_info'), 'call', {
                'product_template_id': productTemplateId,
                'product_id': VariantMixin._getProductId($parent),
                'combination': combination,
                'add_qty': parseInt(qty),
                'custom_val': custom_val,
                'pricelist_id': self.pricelistId || false,
                'parent_combination': parentCombination,
            }).then(function (combinationData) {
                VariantMixin._onChangeCombination(ev, $parent, combinationData);
            });
        },
        handleCustomValues: function ($target) {
            var $variantContainer;
            var $customInput = false;
            if ($target.is('input[type=radio]') && $target.is(':checked')) {
                $variantContainer = $target.closest('ul').closest('li');
                $customInput = $target;
            } else if ($target.is('select')) {
                $variantContainer = $target.closest('li');
                $customInput = $target
                    .find('option[value="' + $target.val() + '"]');
            }

            if ($variantContainer) {
                if ($customInput && $customInput.data('is_custom') === 'True') {
                    var attributeValueId = $customInput.data('value_id');
                    var attributeValueName = $customInput.data('value_name');

                    if ($variantContainer.find('.variant_custom_value').length === 0
                            || $variantContainer
                                  .find('.variant_custom_value')
                                  .data('custom_product_template_attribute_value_id') !== parseInt(attributeValueId)) {
                        $variantContainer.find('.variant_custom_value').remove();

                        var $input = $('<input>', {
                            type: 'text',
                            'data-custom_product_template_attribute_value_id': attributeValueId,
                            'data-attribute_value_name': attributeValueName,
                            class: 'variant_custom_value form-control'
                        });
                        //Add custom value for default input for calcultor custom values
                        var custom_attribute = $customInput.data('custom_attribute') || false;
                        if (custom_attribute){
                            var custom_value = $customInput.data('custom_value') || 1;
                            $input.addClass('custom_attribute');
                            $input.attr('data-custom_value', custom_value);
                            $input.attr('data-custom_attribute', custom_attribute);
                            $input.val(custom_value)
                        }

                        var isRadioInput = $target.is('input[type=radio]') &&
                            $target.closest('label.css_attribute_color').length === 0;

                        if (isRadioInput && $customInput.data('is_single_and_custom') !== 'True') {
                            $input.addClass('custom_value_radio');
                            $target.closest('div').after($input);
                        } else {
                            $input.attr('placeholder', attributeValueName);
                            $input.addClass('custom_value_own_line');
                            $variantContainer.append($input);
                        }
                    }
                } else {
                    $variantContainer.find('.variant_custom_value').remove();
                }
            }
        },
    })
})