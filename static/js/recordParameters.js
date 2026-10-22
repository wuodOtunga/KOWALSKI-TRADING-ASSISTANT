//JS FORM HANDLER FOR THE PARAMETERS LIST CHECKBOX.
//FORM SUBMISSION - catch the submit event
//stop normal browser submission
//extract form data
//build api request payload
//send post request to FastApi
//wait for HTTP response
//parse JSON response and branch on either success or error
//on success, update UI,,,on error extract error then show error

import { showAlert, hideAlert, extractErrorMessage, readJsonBody, showSuccessModal } from "./utils.js";

const form = document.getElementById("recordParametersForm");
const parametersAlert = document.getElementById("recordParametersAlert");
const successMessageEl = document.getElementById("successMessage");
const parametersModal = document.getElementById("recordParametersModal");
const parametersContainer = document.getElementById("pt-parameters-list");
const parametersSubmit = document.querySelector('button[form="recordParametersForm"]');
const successModal = document.getElementById("successModal");

form.addEventListener("submit", recordParametersHandler);
successModal.addEventListener("hidden.bs.modal", resetParametersModal);

async function populateParametersCheckboxes(containerElement, url) {

    let response = null;
    try {
        response = await fetch(url);

        if (!response.ok) {
            throw new Error(`${response.status}`)
        }

        const items = await response.json();

        containerElement.replaceChildren()

        for (const item of items) {
            const colDiv = document.createElement("div");
            colDiv.className = "col";
            const wrapper = document.createElement("div");
            wrapper.className = "form-check";

            const input = document.createElement("input");
            input.className = "form-check-input";
            input.type = "checkbox";
            input.name = "parameters";
            input.value = item.parameter_name;
            input.id = `pt-param-${item.parameter_id}`;

            const label = document.createElement("label");
            label.className = "form-check-label";
            label.htmlFor = input.id;
            label.textContent = item.parameter_name;

            wrapper.append(input, label);
            colDiv.append(wrapper);
            containerElement.append(colDiv);
        };
        return true;
    } catch (error) {
        console.error(error);
        containerElement.replaceChildren();
        const msg = document.createElement("p");
        msg.className = "text-danger mb-0";
        msg.textContent = "Failed to load parameters";
        containerElement.append(msg);
        return false;
    }
}

parametersModal.addEventListener("show.bs.modal", async () => {
    parametersSubmit.disabled = true;
    const loaded = await populateParametersCheckboxes(parametersContainer, "/api/static-models/parameters");
    parametersSubmit.disabled = !loaded;
});

function resetParametersModal() {
    //reset form inputs to defaults
    form.reset();
    //stop fields from showing red on reopen
    form.classList.remove("was-validated");
    //hide any previous alerts in the modal.
    hideAlert(parametersAlert);
    //reload the window to refresh data to avoid stale writes.
    window.location.reload();
}

async function recordParametersHandler(event) {

    event.preventDefault();
    hideAlert(parametersAlert);

    if (!form.checkValidity()) {
        form.classList.add("was-validated");
        return;
    }

    const formData = new FormData(form);
    const tradeId = Number(formData.get("trade_id"));
    formData.delete("trade_id");
    let parametersData = Object.fromEntries(formData.entries());

    parametersData = {
        "parameters_list": formData.getAll("parameters"),
    }

    let response = null;
    try {
        response = await fetch(`/api/trades/${tradeId}/parameters`, {
            method: "POST",
            headers: {
                "Content-type": "application/json"
            },
            body: JSON.stringify(parametersData),
        });

        if (!response.ok) {
            const payload = await readJsonBody(response);
            showAlert(parametersAlert, "danger", extractErrorMessage(payload, response.status));
            return;
        } else {
            const responseData = await readJsonBody(response);
            successMessageEl.textContent = `PARAMETERS FOR TRADE WITH TRADE_ID ${responseData?.trade_id} RECORDED SUCCESSFULLY!`;
            bootstrap.Modal.getOrCreateInstance(parametersModal).hide();
            showSuccessModal("successModal");
        }
    } catch (error) {
        console.log(error);
        showAlert(parametersAlert, "danger", "Error detected. Couldn't access the server!");
        return;
    };
}