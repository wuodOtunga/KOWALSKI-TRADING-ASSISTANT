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

form.addEventListener("submit", recordParametersHandler);

async function populateParametersCheckboxes(containerElement, url) {

    try {
        response = await fetch(url);

        if (!response.ok) {
            throw new Error(`${response.status}`)
        }

        const items = readJsonBody(response);
        if (!Array.isArray(items)) {
            return;
        }

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
    const loaded = await populateParametersCheckboxes(parametersContainer, "/api/static_models/parameters");
    parametersSubmit.disabled = !loaded;
});

async function recordParametersHandler(event) {

    event.preventDefault();
    hideAlert(parametersAlert);

    if (!form.checkValidity()) {
        form.classList.add("was-validated");
        return;
    }

    const formData = new FormData(form);
    const parametersData = Object.fromEntries(formData.entries());

    parametersData = {
        "trade_id": Number(parametersData.get("trade_id")),
        "parameters_list": parametersData.getAll("parameters"),
    }

    let response = null;
    try {
        response = await fetch("/api/parameters", {
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
            successMessageEl.textContent = "PARAMETERS RECORDED SUCCESSFULLY!";
            bootstrap.Modal.getOrCreateInstance(parametersModal).hide();
            showSuccessModal("successModal");
            form.reset();
            window.location.reload();
            return;
        }
    } catch (error) {
        console.log(error);
        showAlert(parametersAlert, "danger", "Error detected. Couldn't access the server!");
        hideAlert();
        return;
    };
}