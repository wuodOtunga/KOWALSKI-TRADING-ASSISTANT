import { showAlert, hideAlert, extractErrorMessage, readJsonBody, populateSelectDropdowns } from "./utils.js";

const byId = (id) => document.getElementById(id);

const form = byId("amendTradeForm");
const modalEl = byId("amendTradeModal");
const alertEl = byId("amendTradeAlert");
const submitButton = byId("at-submit");
const columnSelect = byId("at-column");
const resultPanel = byId("at-result");
const placeholderGroup = byId("at-group-placeholder");
const fkLabel = byId("at-value-fk-label");
const fkSelect = byId("at-value-fk");

form.addEventListener("submit", amendTradeHandler);

//amend_trade_modal.html is already built around one idea:
//the HTML describes what each field needs, and the JS just reads that description.
// Each <option> carries a data-input attribute (number, asset, direction, fk), and the JS shows the matching input.
//The whole file is five small pieces

//1. Grab elements, and build a lookup table
//byId is a one-line shortcut so you aren’t typing document.getElementById 20 times.
//VALUE_CONTROLS is the core design. Instead of an if/else if chain per column, the JS looks up VALUE_CONTROLS[kind].
//Adding a fifth input type later means one HTML block and one line here.
// keys match the data-input values in the HTML exactly
const VALUE_CONTROLS = {
    number:    { group: byId("at-group-number"),    input: byId("at-value-number") },
    asset:     { group: byId("at-group-asset"),     input: byId("at-value-asset") },
    direction: { group: byId("at-group-direction"), input: byId("at-value-direction") },
    fk:        { group: byId("at-group-fk"),        input: fkSelect },
};

let amended = false;   // did anything actually change while the modal was open?

//2. Show one value control, disable the rest
//classList.toggle(name, force): with the second argument, true adds the class and false removes it.
//So toggle("d-none", !active) means “hidden unless active”, with no if/else.
//Object.entries plus destructuring:
//Object.entries(obj) gives [key, value] pairs, and [name, { group, input }] unpacks each pair in the loop header.
//Why disabled matters more than d-none:
//all four inputs share name="new_value" and are required.
//A disabled control is skipped by form.checkValidity() and left out of FormData.
//So the three hidden inputs can’t block validation or send an empty value.
//If you only hid them, validation would always fail on the empty hidden ones.
//kind = null is “no column chosen yet”, which shows the grey “Choose a field first” box.
// kind = "number" | "asset" | ... | null
function showValueControl(kind) {
    placeholderGroup.classList.toggle("d-none", kind !== null);

    for (const [name, { group, input }] of Object.entries(VALUE_CONTROLS)) {
        const active = name === kind;
        group.classList.toggle("d-none", !active);
        input.disabled = !active;
    }
}

//3. React when the column changes
//selectedOptions[0] is the <option> element itself, not just its value string. That’s how you reach its attributes.
//option.dataset exposes every data-* attribute, with dashes converted to camelCase:
//data-value-key becomes dataset.valueKey, data-label-key becomes dataset.labelKey, and data-source becomes dataset.source.
//This lets the HTML tell the JS which endpoint feeds a dropdown.
//new Option("Loading...", "") creates an <option> with text and value.
//It clears the previous column’s choices (stale “Model” options under an “Account” label would be bad).
//Its empty value also keeps the required check failing until real options load.
//If you flip quickly between two linked columns, a slow response could overwrite a newer one.
//For a single user this is harmless, so I’d leave it and have a fix for the multi user app version.
columnSelect.addEventListener("change", async () => {
    const option = columnSelect.selectedOptions[0];
    const kind = option.dataset.input;
    showValueControl(kind);

    if (kind !== "fk") return;

    const { source, valueKey, labelKey } = option.dataset;
    fkLabel.textContent = `New ${option.textContent.toLowerCase()}`;
    fkSelect.replaceChildren(new Option("Loading...", ""));
    await populateSelectDropdowns(fkSelect, source, valueKey, labelKey);
});

//4. The submit handler
//The trade ID goes in the URL, not the body.
//That matches the PATCH /api/trades/{trade_id} contract and your charts handler.
//Types are decided by kind, not by the column name. Form values are always strings.
//Numbers and IDs get Number(), and asset/direction stay as strings.
//Your service layer re-casts anyway (_COLUMN_CASTERS), but sending the right type keeps the request honest.
//The try/catch/finally shape is identical to the other handlers.
//catch is for the network failing, the !response.ok branch is for the server answering with an error,
//and finally always re-enables the button.
async function amendTradeHandler(event) {
    event.preventDefault();
    hideAlert(alertEl);
    resultPanel.classList.add("d-none");        // don't show the previous amendment next to a new attempt

    if (!form.checkValidity()) {
        form.classList.add("was-validated");
        return;
    }

    const formData = new FormData(form);
    const tradeId = formData.get("trade_id");
    const kind = columnSelect.selectedOptions[0].dataset.input;
    const rawValue = formData.get("new_value");   // only ONE enabled control, so only one value

    const requestBody = {
        column_name: formData.get("column_name"),
        new_value: (kind === "number" || kind === "fk") ? Number(rawValue) : rawValue,
    };

    submitButton.disabled = true;   // each PATCH writes an audit row, so block double-clicks

    try {
        const response = await fetch(`/api/trades/${tradeId}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(requestBody),
        });

        if (!response.ok) {
            const errorPayload = await readJsonBody(response);
            showAlert(alertEl, "danger", extractErrorMessage(errorPayload, response.status));
            return;
        }

        renderAmendment(await readJsonBody(response));
        amended = true;
    } catch (error) {
        console.error(error);
        showAlert(alertEl, "danger", "Error detected. Couldn't access the server!");
    } finally {
        submitButton.disabled = false;
    }
}

//5. Show the result, and reset on close
//Use textContent, not innerHTML, for values that came from a server.
//It treats everything as plain text, so nothing can be interpreted as HTML.
//This modal deliberately doesn’t use successModal.
//The HTML already has an inline result panel, so the user can see old and new values and amend again without reopening.
//It also sidesteps the E1 issue, where every module’s listener on the shared #successModal fires on any success.
//The reload is conditional. The amended flag reloads only if something changed, so cancelling doesn’t refresh the page.
//form.reset() restores input values, but not the d-none classes or disabled flags.
//That’s why showValueControl(null) is needed.
//For linked columns, old and new values are IDs (2 → 4), not names.
//Showing names would need another lookup, which I will skip for now.
//The transferable idea from this handler:
//let the markup carry configuration (data-*),
//keep one lookup table in JS, and use disabled to control what gets validated and submitted.
function renderAmendment(change) {
    byId("at-result-change-id").textContent = change.change_id;
    byId("at-result-trade-id").textContent = change.trade_id;
    byId("at-result-column").textContent = change.column_name;
    byId("at-result-old").textContent = change.old_value;
    byId("at-result-new").textContent = change.new_value;
    byId("at-result-time").textContent = new Date(change.amended_at).toLocaleString();
    resultPanel.classList.remove("d-none");
}

modalEl.addEventListener("hidden.bs.modal", () => {
    form.reset();
    form.classList.remove("was-validated");
    hideAlert(alertEl);
    resultPanel.classList.add("d-none");
    showValueControl(null);          // form.reset() does NOT fire "change", so reset the controls by hand
    if (amended) window.location.reload();
});