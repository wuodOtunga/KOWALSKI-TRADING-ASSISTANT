//FORM SUBMISSION - catch the submit event
//stop normal browser submission
//extract form data
//build api request payload
//send post request to FastApi
//wait for HTTP response
//parse JSON response and branch on either success or error
//on success, update UI,,,on error extract error then show error
import { showAlert, hideAlert, extractErrorMessage, readJsonBody, showSuccessModal } from "./utils.js";

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

form.addEventListener("submit", recordTradeHandler);
tradeModal.addEventListener("show.bs.modal", loadRecordTradeOptions);
tradeModal.addEventListener("hidden.bs.modal", resetTradeRecordModal);



async function populateSelectDropdowns(selectEl, url, valueKey, labelKey){
    //fetch the lists
    //loop over it and create <option> elements
    //value = id and text = name
    //append them to the select

    let response;
    try {
        response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`)
        };

        const items = await response.json();

        selectEl.replaceChildren();

        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = "Choose from...";
        placeholder.disabled = true;
        placeholder.selected = true;
        placeholder.defaultSelected = true;
        selectEl.append(placeholder);

        for (const item of items) {
            const option = document.createElement("option");
            option.value = item[valueKey];
            option.textContent = item[labelKey];
            selectEl.append(option);
        };
    } catch (error) {
        selectEl.replaceChildren();

        const fallback = document.createElement("option");
        fallback.value = "";
        fallback.textContent = "Failed to load";
        selectEl.append(fallback);
    };
}

function resetTradeRecordModal() {
    //reset form inputs to defaults
    form.reset();
    //stop fields from showing red on reopen
    form.classList.remove("was-validated");
    //clear old success/error message
    hideAlert(tradeAlert);
}

async function loadRecordTradeOptions() {
    await Promise.all([
        populateSelectDropdowns(accountSelectEl, "/api/accounts", "account_id", "account_name"),
        populateSelectDropdowns(modelSelectEl, "/api/static_models/models", "model_id", "model_name"),
        populateSelectDropdowns(managementSelectEl, "/api/static_models/trade_management", "management_id", "archetype"),
        populateSelectDropdowns(executionSelectEl, "/api/static_models/entry_execution", "entry_execution_id", "archetype"),
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
            const payload = await readJsonBody(response);
            showAlert(tradeAlert, "danger", extractErrorMessage(payload, response.status));
            return;
        } else {
            successMessageEl.textContent = `TRADE WITH TRADE_ID OF ${payload.trade_id} RECORDED SUCCESSFULLY!`;
            bootstrap.Modal.getOrCreateInstance(tradeModal),hide();
            showSuccessModal("successModal");
            form.reset();
            window.location.reload();
            return;
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


