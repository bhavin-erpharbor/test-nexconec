/** @odoo-module **/

function el(id) {
    return document.getElementById(id);
}

function openCartCuttingRecapModal(titleText, htmlContent) {
    const modalEl = el("cartCuttingRecapModal");
    const titleEl = el("cartCuttingRecapTitle");
    const bodyEl = el("cartCuttingRecapBody");

    if (!modalEl || !titleEl || !bodyEl) {
        console.error("Recap modal elements not found");
        return;
    }

    titleEl.textContent = titleText || "Cutting Recap";
    bodyEl.innerHTML = htmlContent || "";

    modalEl.classList.add("show");
    modalEl.style.display = "block";
    modalEl.removeAttribute("aria-hidden");
    modalEl.setAttribute("aria-modal", "true");

    document.body.classList.add("modal-open");
    document.body.style.overflow = "hidden";

    // create backdrop if missing
    if (!document.querySelector(".modal-backdrop")) {
        const backdrop = document.createElement("div");
        backdrop.className = "modal-backdrop fade show";
        document.body.appendChild(backdrop);
    }
}

function closeCartCuttingRecapModal() {
    const modalEl = el("cartCuttingRecapModal");
    if (!modalEl) return;

    modalEl.classList.remove("show");
    modalEl.style.display = "none";
    modalEl.setAttribute("aria-hidden", "true");
    modalEl.removeAttribute("aria-modal");

    document.body.classList.remove("modal-open");
    document.body.style.removeProperty("overflow");
    document.body.style.removeProperty("padding-right");

    document.querySelectorAll(".modal-backdrop").forEach((backdrop) => backdrop.remove());
}

document.addEventListener("click", function (ev) {
    // open recap
    const recapBtn = ev.target.closest(".open_cutting_recap");
    if (recapBtn) {
        ev.preventDefault();

        const row = recapBtn.closest(".o_cart_product");
        const source = row ? row.querySelector(".cutting_recap_source") : null;
        const productName = recapBtn.dataset.productName || "Cutting Recap";

        if (!source) {
            console.error("Recap source not found");
            return;
        }

        openCartCuttingRecapModal(`Cutting Recap - ${productName}`, source.innerHTML);
        return;
    }

    // close buttons
    if (
        ev.target.closest("#close_cart_cutting_recap_header") ||
        ev.target.closest("#close_cart_cutting_recap_footer")
    ) {
        ev.preventDefault();
        closeCartCuttingRecapModal();
        return;
    }

    // close when clicking outside modal content
    const modalEl = el("cartCuttingRecapModal");
    if (modalEl && ev.target === modalEl) {
        closeCartCuttingRecapModal();
    }
});
