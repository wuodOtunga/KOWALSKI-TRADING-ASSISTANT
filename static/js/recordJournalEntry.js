//JS handler for recording a journal entry.
//Journal entry = trade + notes + parameters + charts in one form as a unit of entry work.
//The page is four mini-forms that share one fact (the trade_id) and one rule (each step can only run in certain states).
// So the file isn’t four copies of handler code. It has three parts:
//1) A step table and one function, setStep, that is the only place the UI changes state.
//2) One helper, runStep, that owns the shared lifecycle:
//validate, disable button, fetch, handle network failure, re-enable.
//3) Four small handlers that supply only what differs: the request, and what success means.

//1) Describe the steps as data.
import { showAlert, hideAlert, extractErrorMessage, readJsonBody, populateSelectDropdowns } from "./utils";

const byId = (id) => document.getElementById(id);

//notes, charts, parameters are all linked to a specific trade via the trade_id.
//the trade_id is the foreign key in their respective tables and the 3 resources,
//can't be recorded without a valid trade_id. This is why the trade is recorded first,
//while the rest of the forms have been disabled via the HTML disabled attribute.
//the returned trade_id from a successful trade submission is passed onto the three other,
//forms which is then used for submission of the respective resources.
const NUMERIC_VALUES = ["entry_price", "exit_price", "stop_loss", "take_profit", "position_size"];
const INTEGER_VALUES = ["model_id", "account_id", "management_id", "entry_execution_id"];
const TRADE_ID_INPUTS = ["je-notes-trade-id", "je-charts-trade-id", "je-parameters-trade-id"];

//makeStep follows the naming convention. The IDs are je-<step>-fieldset, -submit and -alert,
//so one function builds all four objects. Each step then carries everything the JS touches.
//The badge is found through the data-step attribute on the progress list.
//STATUS is a lookup table, the same idea as VALUE_CONTROLS in the amend modal.
//Each status says how the badge looks and whether the step accepts input.
//partial exists for charts, where some files saved and some failed, so the step must stay usable.
function makeStep(name, formId, prefix) {
    return {
        form: byId(formId),
        fieldset: byId(`${prefix}-fieldset`),
        submit: byId(`${prefix}-submit`),
        alert: byId(`${prefix}-alert`),
        badge: document.querySelector(`#je-progress [data-step="${name}"] .badge`),
    };
};

const STEPS = {
    trade: makeStep("trade", "journalTradeForm", "je-trade"),
    notes: makeStep("notes", "journalNotesForm", "je-notes"),
    charts: makeStep("charts", "journalChartsForm", "je-charts"),
    parameters: makeStep("parameters", "journalParametersForm", "je-parameters"),
};

const STATUS = {
    pending: { label: "Pending", color: "warning", enabled: true },
    locked: { label: "Locked", color: "secondary", enabled: false },
    ready: { label: "Ready", color: "info", enabled: true },
    partial: { label: "Partial", color: "warning", enabled: true},
    done: { label: "Done", color: "success", enabled: false },
};

//current status per step
const stepStatus = {};

//2. One function changes step
//Why both fieldset.disabled and submit.disabled:
//the submit buttons live in each card-footer, outside the <form> and its <fieldset>.
//They’re tied to the form only through the form="..." attribute.
//Disabling the fieldset greys out the inputs but not the button, so you must do both.
//disabled also affects data. Controls inside a disabled fieldset are skipped by checkValidity() and left out of FormData.
//That’s harmless here, because a locked step can’t be submitted anyway.
//stepStatus[name] is the single source of truth. runStep reads it to decide whether to re-enable a button.
function setStep(name, status) {
    const step = STEPS[name];
    const { label, color, enabled } = STATUS[status];

    stepStatus[name] = status;
    step.fieldset.disabled = !enabled;
    step.submit.disabled = !enabled;
    step.badge.textContent = label;
    step.badge.className = `badge text-bg-${color}`;
};

//3. The shared lifecycle
const jsonRequest = (url, body) => ({
    url,
    options: {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    },
});

function reportFailure(name, response, payload) {
    if (response.ok) return false;
    showAlert(STEPS[name].alert, "danger", extractErrorMessage(payload, response.status));
    return true;
};

//This is the same try/catch/finally shape as the other handlers, written once.
//The two callbacks are the key idea.
//buildRequest and onResponse are functions passed in as arguments,
//so each step says what to send and what to do with the answer,
//and runStep handles everything around that.
//The finally can’t just set disabled = false.
//If notes succeed, onResponse calls setStep("notes", "done"), which disables the button.
//An unconditional re-enable would undo it.
//Asking “should this status be enabled?” keeps the lifecycle and the lock rules from fighting.
//reportFailure returns true if it displayed an error.
//That lets handlers write if (reportFailure(...)) return;
async function runStep(name, buildRequest, onResponse) {
    const step = STEPS[name];
    hideAlert(step.alert);

    if (!step.form.checkValidity()) {
        step.form.classList.add("was-validated");
        return;
    }

    const { url, options } = buildRequest();
    step.submit.disabled = true;

    try {
        const response = await fetch(url, options);
        const payload = await readJsonBody(response);
        onResponse(response, payload);
    } catch (error) {
        console.error(error);
        showAlert(step.alert, "danger", "Error detected. Couldn't access the server");
    } finally {
        step.submit.disabled = !STATUS[stepStatus[name]].enabled;
    }
};

//4. Four resources, four small handlers
//STEP:Trade, REQUEST: POST /api/trades, BODY: JSON, numbers cast, onSuccess: Unlock the other three steps.
//STEP:Notes, REQUEST: POST /api/notes, BODY: JSON, trade_id cast, onSuccess: Lock notes.
//STEP:Charts, REQUEST: POST /api/trades/{id}/charts, BODY:	FormData (multipart), onSuccess: Per-file results, lock only if all saved
//STEP:Parameters, REQUEST:	POST /api/parameters, BODY: JSON, list of names, onSuccess: Lock (trade is now graded).

//Trade is the step the others depend on:
//The hidden inputs carry the trade ID between steps.
//The HTML has a <input type="hidden" name="trade_id"> in the notes, charts and parameters forms.
//onTradeRecorded fills all three with the returned ID.
//Every later handler reads its trade_id from its own form, so no module-level variable has to stay in sync.
STEPS.trade.form.addEventListener("submit", (event) => {
    event.preventDefault();
    runStep("trade",
        () => {
            const data = Object.fromEntries(new FormData(STEPS.trade.form));
            for (const key of NUMERIC_VALUES) data[key] = Number(data[key]);
            for (const key of INTEGER_VALUES) data[key] = parseInt(data[key], 10);
            return jsonRequest("/api/trades", data);
        },
        (response, payload) => {
            if (reportFailure("trade", response, payload)) return;
            onTradeRecorded(payload.trade_id);
        });
});

function onTradeRecorded(tradeId) {
    for (const id of TRADE_ID_INPUTS) byId(id).value = tradeId;

    setStep("trade", "done");
    setStep("notes", "ready");
    setStep("charts", "ready");
    setStep("parameters", "ready");

    setBanner("success", `Trade #${tradeId} recorded. Add notes, charts and parameters below.`);
    byId("je-new-entry").classList.remove("d-none");
};

const banner = byId("je-trade-banner");
function setBanner(kind, text) {
    banner.classList.remove("alert-secondary", "alert-success");
    banner.classList.add(`alert-${kind}`);
    byId("je-trade-banner-text").textContent = text;
};

//Notes is the plainest one:
////The success alert stays visible after locking because the alert sits outside the form.
STEPS.notes.form.addEventListener("submit", (event) => {
    event.preventDefault();
    runStep("notes",
        () => {
            const data = Object.fromEntries(new FormData(STEPS.notes.form));
            data.trade_id = Number(data.trade_id);
            return jsonRequest("/api/notes", data);
        },
        (response, payload) => {
            if (reportFailure("notes", response, payload)) return;
            setStep("notes", "done");
            showAlert(STEPS.notes.alert, "success", "Notes recorded.");
        });
});

//Charts differs in two ways.
//The body is multipart, so you pass the FormData object itself and set no Content-Type header,
//letting the browser add the boundary. And the response contains per-file outcomes even on 207 or 500:
//Branch on the payload’s shape, not the status code. Only batch responses have outcomes,
//so its presence tells you which kind of response you got.
//The results list is a running log. It is appended to rather than cleared,
//so earlier successes stay visible after a retry.
//Only “Start a new entry” clears it.
//Partial failure keeps the step open. That’s what the partial status is for.
//Re-uploading the whole selection would duplicate the files that saved,
//so the message tells the user to reselect only the failed ones.
STEPS.charts.form.addEventListener("submit", (event) => {
    event.preventDefault();
    runStep("charts",
        () => {
            const formData = new FormData(STEPS.charts.form);
            const tradeId = formData.get("trade_id");
            formData.delete("trade_id");             // it's in the URL now
            return { url: `/api/trades/${tradeId}/charts`, options: { method: "POST", body: formData } };
        },
        (response, payload) => {
            // request-level failures (404 / 413 / 415 / 422) have no outcomes list
            if (!payload?.outcomes) {
                showAlert(STEPS.charts.alert, "danger", extractErrorMessage(payload, response.status));
                return;
            }

            renderChartOutcomes(payload.outcomes);
            const failed = payload.outcomes.filter((o) => !o.success);

            if (failed.length === 0) {
                setStep("charts", "done");
                showAlert(STEPS.charts.alert, "success", "All charts recorded.");
            } else {
                setStep("charts", payload.succeeded > 0 ? "partial" : "ready");
                showAlert(
                    STEPS.charts.alert,
                    payload.succeeded > 0 ? "warning" : "danger",
                    `${payload.succeeded} saved, ${failed.length} failed. Re-select only the failed files to retry.`,
                );
            }
        });
});

function renderChartOutcomes(outcomes) {
    const list = byId("je-charts-results");
    for (const outcome of outcomes) {
        const item = document.createElement("li");
        item.className = `list-group-item ${outcome.success ? "text-success" : "text-danger"}`;
        item.textContent = outcome.success ? `${outcome.filename}: saved` : `${outcome.filename}: ${outcome.error}`;
        list.append(item);
    }
};

//Parameters sends a list of names:
//getAll, not get. Every ticked checkbox shares name="parameters_list".
//formData.get returns the first, and getAll returns an array.
//Unticking everything gives [], which is what the HTML’s “leave unticked if none” text promises.
//It locks on success because grading happens once.
//This is why it’s the last step in the HTML and carries the warning banner.
STEPS.parameters.form.addEventListener("submit", (event) => {
    event.preventDefault();
    runStep("parameters",
        () => {
            const formData = new FormData(STEPS.parameters.form);
            return jsonRequest("/api/parameters", {
                trade_id: Number(formData.get("trade_id")),
                parameters_list: formData.getAll("parameters_list"),
            });
        },
        (response, payload) => {
            if (reportFailure("parameters", response, payload)) return;
            setStep("parameters", "done");
            showAlert(STEPS.parameters.alert, "success", "Parameters recorded and trade graded.");
        });
});

//5. Page load and “Start a new entry”
//resetEntry runs at load and on “Start a new entry”. It loops over STEPS,
//so the initial state and the reset state are the same code and can’t drift apart.
//form.reset() also clears the hidden trade_id inputs.
//JS-assigned values don’t become the “default value”, so reset blanks them.
//Promise.all loads all five lists in parallel, as in recordTrade.js.
//The checkboxes are rebuilt here because recordParameters.js hardcodes name="parameters" and pt-param- IDs.
//If the duplication bothers you, move the builder to utils.js with the name and ID prefix as arguments.

//This page deliberately avoids successModal.
//Every module that listens on #successModal reloads the page on any success (the E1 issue),
//which would wipe the multi-step state. Inline alerts and the progress badges avoid that.

//The takeaway is to put per-step differences in data and callbacks,
//and keep one function responsible for each shared behaviour.
//STATUS and STEPS hold the data, setStep owns the UI state, and runStep owns the request lifecycle.
//A fifth step would need one makeStep line, one STATUS use, and one handler.
async function loadParameterCheckboxes() {
    const container = byId("je-parameters-options");
    try {
        const response = await fetch("/api/static_models/parameters");
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        container.replaceChildren();
        for (const item of await response.json()) {
            const col = document.createElement("div");
            col.className = "col";
            const wrapper = document.createElement("div");
            wrapper.className = "form-check";

            const input = document.createElement("input");
            input.className = "form-check-input";
            input.type = "checkbox";
            input.name = "parameters_list";
            input.value = item.parameter_name;
            input.id = `je-param-${item.parameter_id}`;

            const label = document.createElement("label");
            label.className = "form-check-label";
            label.htmlFor = input.id;
            label.textContent = item.parameter_name;

            wrapper.append(input, label);
            col.append(wrapper);
            container.append(col);
        }
    } catch (error) {
        console.error(error);
        container.textContent = "Failed to load parameters";
    }
};

function resetEntry() {
    for (const [name, step] of Object.entries(STEPS)) {
        step.form.reset();
        step.form.classList.remove("was-validated");
        hideAlert(step.alert);
        setStep(name, name === "trade" ? "pending" : "locked");
    }
    byId("je-charts-results").replaceChildren();
    setBanner("secondary", "No trade recorded yet.");
    byId("je-new-entry").classList.add("d-none");
};

byId("je-new-entry").addEventListener("click", resetEntry);

resetEntry();   // sets the initial state

Promise.all([
    populateSelectDropdowns(byId("je-account"), "/api/accounts", "account_id", "account_name"),
    populateSelectDropdowns(byId("je-model-id"), "/api/static_models/models", "model_id", "model_name"),
    populateSelectDropdowns(byId("je-management-id"), "/api/static_models/trade_management", "management_id", "archetype"),
    populateSelectDropdowns(byId("je-entry-execution-id"), "/api/static_models/entry_execution", "entry_execution_id", "archetype"),
    loadParameterCheckboxes(),
]);