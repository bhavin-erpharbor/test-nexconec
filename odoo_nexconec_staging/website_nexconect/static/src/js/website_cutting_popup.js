/** @odoo-module **/
import { rpc } from '@web/core/network/rpc';

/* =========================
   HELPERS
========================= */

function el(id) {
    return document.getElementById(id);
}

function getProductId() {
    const input =
        document.querySelector('input[name="product_id"]') ||
        document.querySelector('input.product_id') ||
        document.querySelector('[data-product-product-id]');

    if (!input) return false;

    if (input.value) return parseInt(input.value, 10);
    if (input.dataset && input.dataset.productProductId) {
        return parseInt(input.dataset.productProductId, 10);
    }
    return false;
}

/* ✅ FORCE ODOO QTY FROM POPUP */
function setOdooQuantity(qty) {
    const qtyInput =
        document.querySelector('input[name="add_qty"]') ||
        document.querySelector('.js_quantity');

    if (qtyInput) {
        qtyInput.value = qty;
    }
}

/* ✅ TRIGGER BASE ODOO ADD TO CART */
function triggerOdooBaseAddToCart() {
    const addBtn =
        document.querySelector('#add_to_cart') ||
        document.querySelector('.o_add_cart') ||
        document.querySelector('.a-submit');

    if (!addBtn) {
        console.error("Odoo Add to Cart button not found");
        return;
    }

    addBtn.dispatchEvent(
        new MouseEvent('click', {
            bubbles: true,
            cancelable: true,
            view: window,
        })
    );
}

/* ✅ CLOSE POPUP (NO BOOTSTRAP DEPENDENCY) */
function closeCuttingPopup() {
    const modal = el("cableCuttingModal");
    if (!modal) return;

    modal.classList.remove("show");
    modal.style.display = "none";
    modal.setAttribute("aria-hidden", "true");
    modal.removeAttribute("aria-modal");

    document.body.classList.remove("modal-open");
    document.body.style.removeProperty("overflow");
    document.querySelectorAll(".modal-backdrop").forEach(b => b.remove());
}

/* =========================
   CUTTING LINES LOGIC
========================= */

function linesBody() {
    return el("cutting_lines_body");
}

function rowHtml() {
    return `
        <tr class="cutting-line-row">
            <td>
                <input type="number" class="form-control cut-pieces" min="1" step="1" value="1"/>
            </td>
            <td>
                <input type="number" class="form-control cut-length" min="0.01" step="0.01" value="0"/>
            </td>
            <td>
                <span class="line-total">0.00</span>
            </td>
            <td>
                <button type="button" class="btn btn-danger btn-sm remove-line">Remove</button>
            </td>
        </tr>
    `;
}

function getRows() {
    return Array.from(document.querySelectorAll(".cutting-line-row"));
}

function updateTotals() {
    let total = 0;

    getRows().forEach(row => {
        const pieces = parseFloat(row.querySelector(".cut-pieces")?.value || 0);
        const length = parseFloat(row.querySelector(".cut-length")?.value || 0);
        const qty = pieces * length;

        row.querySelector(".line-total").textContent = qty.toFixed(2);
        total += qty;
    });

    el("grand_total").textContent = total.toFixed(2);
}

/* =========================
   SAVE + ADD TO CART
========================= */

async function saveLinesAndAddToCart() {
    const errorEl = el("cutting_error");
    const successEl = el("cutting_success");

    errorEl.textContent = "";
    successEl.textContent = "";

    const rows = getRows();
    const productId = getProductId();

    if (!rows.length) {
        errorEl.textContent = "Please add at least one cutting line.";
        return;
    }

    let totalQty = 0;
    let lines = [];

    rows.forEach(row => {
        const pieces = parseFloat(row.querySelector(".cut-pieces")?.value || 0);
        const length = parseFloat(row.querySelector(".cut-length")?.value || 0);

        if (pieces > 0 && length > 0) {
            const qty = pieces * length;
            totalQty += qty;

            lines.push({
                pieces: pieces,
                length: length,
            });
        }
    });

    if (totalQty <= 0) {
        errorEl.textContent = "Total quantity must be greater than 0.";
        return;
    }

    try {
        const result = await rpc("/cable/cutting/save", {
            product_id: productId,
            quantity: totalQty,      // ✅ FINAL QTY
            cutting_lines: lines,
        });

        if (!result || !result.success) {
            errorEl.textContent = result?.error || "Save failed.";
            return;
        }

        // ✅ FORCE QTY INTO ODOO
        setOdooQuantity(totalQty);

        successEl.textContent = "Saved successfully.";

        // ✅ CLOSE POPUP
        closeCuttingPopup();

        // ✅ ADD TO CART (BASE ODOO)
        setTimeout(() => {
            triggerOdooBaseAddToCart();
        }, 200);

    } catch (err) {
        errorEl.textContent = "Server error.";
        console.error(err);
    }
}

/* =========================
   EVENTS
========================= */

document.addEventListener("click", function (ev) {

    if (ev.target.closest("#open_cutting_popup")) {
        linesBody().innerHTML = "";
        linesBody().insertAdjacentHTML("beforeend", rowHtml());
        updateTotals();
    }

    if (ev.target.closest("#add_cutting_line")) {
        ev.preventDefault();
        linesBody().insertAdjacentHTML("beforeend", rowHtml());
        updateTotals();
    }

    if (ev.target.closest(".remove-line")) {
        ev.preventDefault();
        ev.target.closest("tr").remove();
        updateTotals();
    }

    if (ev.target.closest("#save_and_add_to_cart")) {
        ev.preventDefault();
        saveLinesAndAddToCart();
    }
});

document.addEventListener("input", function (ev) {
    if (
        ev.target.classList.contains("cut-pieces") ||
        ev.target.classList.contains("cut-length")
    ) {
        updateTotals();
    }
});
