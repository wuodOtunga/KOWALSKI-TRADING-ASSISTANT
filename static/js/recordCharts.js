import { showAlert, hideAlert, extractErrorMessage, readJsonBody, showSuccessModal } from "./utils.js";

const form = document.getElementById("recordChartsForm");
const chartsModal = document.getElementById("recordChartsModal");
const chartsAlert = document.getElementById("recordChartsAlert");
const submitButton = document.querySelector('button[form="recordChartsForm"]');
const successMessageElement = document.getElementById("successMessage");
const successModal = document.getElementById("successModal");

form.addEventListener("submit", recordChartsHandler);
successModal.addEventListener("hidden.bs.modal", resetChartsModal);

function resetChartsModal() {
    //reset form inputs to defaults
    form.reset()
    //stop fields from showing red on reopen
    form.classList.remove("was-validated");
    //hide any previous alerts in the modal.
    hideAlert(chartsAlert);
    //reload the window to refresh data to avoid stale writes.
    window.location.reload();
}

async function recordChartsHandler(event) {
    event.preventDefault();
    hideAlert(chartsAlert);

    if (!form.checkValidity()) {
        form.classList.add("was-validated");
        return;
    }

    const formData = new FormData(form);            // NOT Object.fromEntries: multiple files
    const tradeId = formData.get("trade_id");
    formData.delete("trade_id");                    // trade_id lives in the URL now.

    submitButton.disabled = true; // POST isn't idempotent

    let response = null;
    try {
        response = await fetch(`/api/trades/${tradeId}/charts`, {
            method: "POST",
            body: formData,                         // NO Content-Type header: browser adds the boundary
        });

        const payload = await readJsonBody(response);

        // Batch responses (201 / 207 / 500) carry per-file outcomes
        if (payload?.outcomes) {
            const failed = payload.outcomes.filter(o => !o.success);

            if (failed.length === 0) {
                successMessageElement.textContent = "ALL CHARTS RECORDED SUCCESSFULLY!";
                bootstrap.Modal.getOrCreateInstance(chartsModal).hide();
                showSuccessModal("successModal");
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
        submitButton.disabled = false;
    }
}