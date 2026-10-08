import { showAlert, hideAlert, extractErrorMessage, readJsonBody, showSuccessModal } from "./utils.js";

const form = document.getElementById("recordChartsForm");
const chartsModal = document.getElementById("recordChartsModal");
const chartsAlert = document.getElementById("recordChartsAlert");
const submitBtn = document.querySelector('button[form="recordChartsForm"]');
const successMessageElement = document.getElementById("successMessage");

form.addEventListener("submit", recordChartsHandler);

async function recordChartsHandler(event) {
    event.preventDefault();
    hideAlert(alertEl);

    if (!form.checkValidity()) {
        form.classList.add("was-validated");
        return;
    }

    const formData = new FormData(form);            // NOT Object.fromEntries: multiple files
    const tradeId = formData.get("trade_id");
    formData.delete("trade_id");                    // trade_id lives in the URL now.

    submitBtn.disabled = true;                      // POST isn't idempotent
    try {
        const response = await fetch(`/api/trades/${tradeId}/charts`, {
            method: "POST",
            body: formData,                         // NO Content-Type header: browser adds the boundary
        });

        const payload = await readJsonBody(response);

        // Batch responses (201 / 207 / 500) carry per-file outcomes
        if (payload?.outcomes) {
            const failed = payload.outcomes.filter(o => !o.success);

            if (failed.length === 0) {
                bootstrap.Modal.getOrCreateInstance(chartsModal).hide();
                successMessageElement.textContent = "ALL CHARTS RECORDED SUCCESSFULLY!";
                showSuccessModal("successModal");
                window.location.reload();
                return;
            }

            const lines = failed.map(o => `${o.filename}: ${o.error}`).join("; ");
            const prefix = payload.succeeded > 0
                ? `${payload.succeeded} saved, ${failed.length} failed. `
                : "No charts were saved. ";
            // Don't reload: the user must see which files failed
            showAlert(chartsAlert, payload.succeeded > 0 ? "warning" : "danger", prefix + lines);
            return;
        }

        // Request-level failures (404 / 413 / 415 / 422)
        showAlert(chartsAlert, "danger", extractErrorMessage(payload, response.status));
    } catch (error) {
        console.error(error);
        showAlert(chartsAlert, "danger", "Error detected. Couldn't access the server!");
    } finally {
        submitBtn.disabled = false;
    }
}