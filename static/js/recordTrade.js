//FORM SUBMISSION - catch the submit event
//stop normal browser submission
//extract form data
//build api request payload
//send post request to FastApi
//wait for HTTP response
//parse JSON response and branch on either success or error
//on success, update UI,,,on error extract error then show error
import { showAlert, hideAlert, extractErrorMessage, readJsonBody, showSuccessModal, populateSelectDropdowns } from "./utils.js";

const INTEGER_VALUES = ["model_id", "entry_execution_id", "management_id", "account_id"];
const NUMERIC_VALUES = ["entry_price", "exit_price", "take_profit", "stop_loss", "position_size"];

const form = document.getElementById("recordTradeForm");
const tradeAlert = document.getElementById("recordTradeAlert");
const tradeModal = document.getElementById("recordTradeModal");
const tradeSubmit = document.querySelector('button[form="recordTradeForm"]');
const modelSelectEl = document.getElementById("rt-model-id");
const accountSelectEl = document.getElementById("rt-account");
const managementSelectEl = document.getElementById("rt-management-id");
const executionSelectEl = document.getElementById("rt-entry-execution-id");
const successMessageEl = document.getElementById("successMessage");
const successModal = document.getElementById("successModal");

form.addEventListener("submit", recordTradeHandler);
tradeModal.addEventListener("show.bs.modal", loadRecordTradeOptions);
successModal.addEventListener("hidden.bs.modal", resetTradeRecordModal);




function resetTradeRecordModal() {
    //reset form inputs to defaults
    form.reset();
    //stop fields from showing red on reopen
    form.classList.remove("was-validated");
    //clear old success/error message
    hideAlert(tradeAlert);
    window.location.reload();
}

async function loadRecordTradeOptions() {
    await Promise.all([
        populateSelectDropdowns(accountSelectEl, "/api/accounts", "account_id", "account_name"),
        populateSelectDropdowns(modelSelectEl, "/api/static-models/models", "model_id", "model_name"),
        populateSelectDropdowns(managementSelectEl, "/api/static-models/trade-management", "management_id", "archetype"),
        populateSelectDropdowns(executionSelectEl, "/api/static-models/entry-execution", "entry_execution_id", "archetype"),
    ]);
}

//TO-DO: implement a success modal for showing success feedback
export async function recordTradeHandler(event){
    //stops the normal browser submission & lets our JS handle form submission
    event.preventDefault();

    hideAlert(tradeAlert);
    const formData = new FormData(form);

    //do client-side validity checks before turning formData to an object
    //if !formData.checkValidity(), === formData invalid. show feedback then stop
    //'was-validated' enables our invalid_feedback divs to show in the browser === show feedback
    if (!form.checkValidity()) {
        form.classList.add('was-validated');
        return;
    };

    const data = Object.fromEntries(formData.entries());

    for (const key of NUMERIC_VALUES) data[key] = Number(data[key]);
    for (const key of INTEGER_VALUES) data[key] = parseInt(data[key]);

    //POST isn't idempotent and so we disable the submit button for the recordTradeModal.
    //this prevents accidental submissions via double clicks.
    tradeSubmit.disabled = true;

    let response;
    try {
        response = await fetch("/api/trades", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data),
        });


        if (!response.ok) {
            //if !response.ok, we get back a JSON response that has details as the exception message
            //and the related status code. so on failure we get back an error JSON response
            //on success, we get back the TradeResponse with the response data.
            const payload = await readJsonBody(response);
            showAlert(tradeAlert, "danger", extractErrorMessage(payload, response?.status));
            return;
        } else {
            const responseData = await readJsonBody(response);
            successMessageEl.textContent = `TRADE WITH TRADE_ID OF ${responseData?.trade_id} RECORDED SUCCESSFULLY!`;
            bootstrap.Modal.getOrCreateInstance(tradeModal).hide();
            showSuccessModal("successModal");
        }

        //fetch will throw an error if no response comes back from the server.
        //server might be down, CORS issues etc
    } catch (error) {
        console.error(error);
        showAlert(tradeAlert, "danger", "Error detected. Couldn't access the server");
        return;
    } finally {
        tradeSubmit.disabled = false;
    }
}


