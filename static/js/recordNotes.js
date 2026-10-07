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

form.addEventListener("submit", recordNotesHandler);

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
    const notesData = Object.fromEntries(formData.entries());


    //convert trade_id from string to number, the other inputs are strings.
    notesData["trade_id"] = Number(notesData["trade_id"]);

    //disable form submit button to prevent accidental re-submissions due to double clicks
    //this is because POST isn't IDEMPOTENT
    submitButton.disabled = true;

    //build api request payload
    let response = null;
    try {
        response = await fetch("/api/notes", {
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
            successMessageEl.textContent = `NOTES FOR TRADE WITH TRADE_ID OF ${payload.trade_id} RECORDED SUCCESSFULLY!`;
            bootstrap.Modal.getOrCreateInstance(notesModal).hide();
            showSuccessModal("successModal");
            form.reset();
            window.location.reload();
            return;
        }
        //catch any network errors that may arise that causes server to be unreachable
    } catch (error) {
        console.log(error);
        showAlert(notesAlert, "danger", "Error detected. Couldn't access the server!");
        hideAlert(notesAlert);
        return;
        //reenable the form submit button for the next submissions.
    } finally {
        submitButton.disabled = false;
    }
}