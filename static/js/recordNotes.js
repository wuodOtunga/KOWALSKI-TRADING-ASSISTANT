//FORM SUBMISSION - catch the submit event
//stop normal browser submission
//extract form data
//build api request payload
//send post request to FastApi
//wait for HTTP response
//parse JSON response and branch on either success or error
//on success, update UI,,,on error extract error then show error
import { showAlert, hideAlert, extractErrorMessage, readJsonBody, showSuccessModal } from "./utils.js";

const form = document.getElementById("recordNotesForm");
const notesModal = document.getElementById("recordNotesModal");
const notesAlert = document.getElementById("recordNotesAlert");
const submitButton = document.querySelector(`button[form="recordNotesForm"]`);
const successMessageEl = document.getElementById("successMessage");
const successModal = document.getElementById("successModal");

form.addEventListener("submit", recordNotesHandler);
successModal.addEventListener("hidden.bs.modal", resetNotesModal);

function resetNotesModal() {
    //reset form inputs to defaults
    form.reset()
    //stop fields from showing red on reopen
    form.classList.remove("was-validated");
    //hide any previous alerts in the modal.
    hideAlert(notesAlert);
    //reload the window to refresh data to avoid stale writes.
    window.location.reload();

}

export async function recordNotesHandler(event) {

    //stop normal browser form submission
    event.preventDefault();

    //clear any previous alert displayed on the modal
    hideAlert(notesAlert);

    //check validity of the form inputs
    if (!form.checkValidity()) {
        form.classList.add("was-validated")
        return;
    };

    //extract and assemble form data into a JS object
    const formData = new FormData(form);
    const tradeId = Number(formData.get("trade_id"));
    formData.delete("trade_id");
    const notesData = Object.fromEntries(formData.entries());

    //disable form submit button to prevent accidental re-submissions due to double clicks
    //this is because POST isn't IDEMPOTENT
    submitButton.disabled = true;

    //build api request payload
    let response = null;
    try {
        response = await fetch(`/api/trades/${tradeId}/notes`, {
            method: "POST",
            headers: {
                "Content-type": "application/json"
            },
            body: JSON.stringify(notesData)
        });

        //parse JSON response body and branch on success/error
        if (!response.ok) {
            const payload = await readJsonBody(response);
            showAlert(notesAlert, "danger", extractErrorMessage(payload, response.status));
            return;
        } else {
            const responseData = await readJsonBody(response);
            successMessageEl.textContent = `NOTES FOR TRADE WITH TRADE_ID OF ${responseData?.trade_id} RECORDED SUCCESSFULLY!`;
            bootstrap.Modal.getOrCreateInstance(notesModal).hide();
            showSuccessModal("successModal");
        }
        //catch any network errors that may arise that causes server to be unreachable
    } catch (error) {
        console.log(error);
        showAlert(notesAlert, "danger", "Error detected. Couldn't access the server!");
        return;
        //reenable the form submit button for the next submissions.
    } finally {
        submitButton.disabled = false;
    }
}