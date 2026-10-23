$(document).ready(function() {
     // Get the MOQ value from the data-moq attribute

    var moq_text = $('#product_moq').text().trim();

    if (document.documentElement.lang === 'en-GB') {
        // For English, remove the thousands separator (comma) and keep the period for decimals
        moq_text = moq_text.replace(/,/g, ''); // Remove thousands separator
    } else if (document.documentElement.lang === 'fr-FR') {
        // For French, replace the comma with a period to correctly parse decimal numbers
        moq_text = moq_text.replace(/\s/g, '').replace(',', '.');
    } else if (document.documentElement.lang === 'it-IT') {
        // For Italian: Remove dot (thousands separator) and replace comma with dot (decimal separator)
        moq_text = moq_text.replace(/\./g, '').replace(',', '.');
    }

function disableAddToCart() {
    $('#add_to_cart')
        .addClass('disabled-moq')
        .attr('aria-disabled', 'true');
}

function enableAddToCart() {
    $('#add_to_cart')
        .removeClass('disabled-moq')
        .removeAttr('aria-disabled');
}

function disableMinus() {
    $('#minus_button')
        .addClass('disabled-moq')
        .attr('aria-disabled', 'true');
}

function enableMinus() {
    $('#minus_button')
        .removeClass('disabled-moq')
        .removeAttr('aria-disabled');
}

    var moq = parseInt(moq_text);

     // Function to check the quantity and enable/disable the minus button
     function checkQuantity() {
         var quantity = parseInt($('#quantity_input').val()) || 1;

         // Disable the minus button if quantity is less than or equal to MOQ
         if (quantity <= moq) {
//             $('#minus_button').prop('disabled', true); // Disable the minus button
        disableMinus();

         } else {
//             $('#minus_button').prop('disabled', false); // Enable the minus button
enableMinus();
         }

         // Disable the Add to Cart button if quantity is less than MOQ
         if (quantity + 1 < moq) {
         disableAddToCart();
//             $('#add_to_cart').prop('disabled', true); // Disable Add to Cart button
         } else {
//             $('#add_to_cart').prop('disabled', false); // Enable Add to Cart button
        enableAddToCart();
                $('.min-qty-warning').fadeOut();


         }
     }

     // Check the initial quantity when the page loads
     checkQuantity();

    $('#add_to_cart').on('click', function(e) {
        var quantity = parseInt($('#quantity_input').val()) || 1;
        if (quantity < moq) {
             var $warning = $('.min-qty-warning');
             $warning.removeClass('animated bounce');
             $warning.width();
             $warning.addClass('animated bounce');
             $warning.fadeIn();
        }
        else{
            var $warning = $('.min-qty-warning');
             $warning.fadeOut();
        }
    });

     // When the plus button is clicked
     $('#plus_button').on('click', function(e) {
         e.preventDefault(); // Prevent the default link behavior
         var currentQuantity = parseInt($('#quantity_input').val()) || 1;
         checkQuantity(); // Recheck the quantity after change
     });

     // When the minus button is clicked
     $('#minus_button').on('click', function(e) {
         e.preventDefault(); // Prevent the default link behavior
         var currentQuantity = parseInt($('#quantity_input').val()) || 1;
         if (currentQuantity > moq) {
             $('#quantity_input').val(currentQuantity);
         }
         checkQuantity();
     });

     $('#quantity_input').on('input', function() {
         checkQuantity();
     });
 });

 $(document).on('click', '#minus_button.disabled-moq', function (e) {
    e.preventDefault();
    e.stopImmediatePropagation();
    return false;
});