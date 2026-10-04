//FORM SUBMISSION - catch the submit event
//stop normal browser submission
//extract form data
//build api request payload
//send post request to FastApi
//wait for HTTP response
//parse JSON response and branch on either success or error
//on success, update UI,,,on error extract error then show error
import { showAlert, hideAlert } from "./ui";

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
const successAlertEl = document.getElementById("pageAlert");

form.addEventListener("submit", record_trade_handler);
tradeModal.addEventListener("show.bs.modal", loadRecordTradeOptions);
tradeModal.addEventListener("hidden.bs.modal", resetTradeRecordModal);

function extract_error_message(payload, status){
    //optional string payload.details if payload is not null or undefined
    //function receives payload which is the error details body from readJsonBody()
    //readJsonBody() parses the JSON response body ensuring we don't throw when response error details is a string.
    const detail = payload?.details;

    //if the error detail is a plain string, return detail
    //HTTPEXCEPTION class returns a plain exception.detail as a string.
    if (typeof detail === "string") {
        return detail;
    };

    //RequestValidationError class returns a compoud list of dictionaries as error details.
    //err.loc?.at(-1) gets at the last item in the loc key of the dict for that error, so "loc": ["body", "direction"],
    //gives as direction which is the field in the request body that failed validation.
    //err.loc?.at(-1), we are optionally chaining err.loc with at(-1) because if for any reason err.loc is undefined,
    //we get back undefined instead of throwing an error incase something is missing.
    //we use String(...) incase loc ends in a number due to some esoteric reason, like it shows a list item.
    //this prevents throwing an error when we call .replaceAll which is a string method.
    //.replaceAll(...) takes a field like entry_execution_id and gives us entry execution id, more readable.
    //&&field !== ... is a ternary. if field isn't the string "body", gives us field: error_message else gives us error_message.
    //this exists because err.loc could just be ["body"], so we skip the prefix and just show the error_message.
    if (Array.isArray(detail)) {
        return detail.map(err => {
            const field = String(err.loc?.at(-1) ?? "").replaceAll("_", " ");
            return field && field !== "body" ? `${field} : ${err.msg}` : err.msg;
        }).join("; ");
    }

    //finally, we have no error details payload to work with, fallback to the status.
    if (status >= 500) {
        return "An error occurred. Couldn't access the server. Please try again.";
    }
    return `Request rejected. (HTTP ${status})`;
}

async function readJsonBody(response){
    //central idea: response.json() with throw an error if response isn't JSON
    //uncaught server errors like TypeError or my own JS code error, will come back as a plain string.
    //so we need to parse the JSON defensively such that we don't throw an error, we return something we can use.
    //response.json() can only be read once but I want to log the error to console for debugging.
    //so we call .text() on the response Promise wrapper to read the error contents, then we parse the text.
    //you can't call .text() after response.json() since the body can only be read once.
    const text = await response.text();

    try {
        return JSON.parse(text);
    } catch {
        console.error("Non JSON error body:", text);
        return null;
    }

}

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
async function record_trade_handler(event){
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

    const data = Object.fromEntries(formData);

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
            showAlert(tradeAlert, "danger", extract_error_message(payload, response.status));
            return;
        } else {
            sessionStorage.setItem("flash", JSON.stringify({
                type: "Success",
                message: "Trade Recorded Successfully!!",
            }));
            showFlashMessage();
            resetTradeRecordModal();
            window.location.reload();
            bootstrap.Modal.getOrCreateInstance(tradeModal).hide();
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
function showFlashMessage() {
    const raw = sessionStorage.getItem("flash");
    if (!raw) return;
    sessionStorage.removeItem("flash");

    const {type, message} = JSON.parse(raw);
    successAlertEl.className = `alert alert-${type}`;
    successAlertEl.textContent = message;
}

