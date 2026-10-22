// Journal entry page: the server renders everything; this file only handles changes.
//   notes   -> save (PUT upsert) / delete
//   charts  -> delete
//   trade   -> delete
//   parameters -> deliberately NOT here. They are read-only.
import { showAlert, hideAlert, extractErrorMessage, readJsonBody } from "./utils.js";

const root = document.getElementById("journal-view");
const tradeId = Number(root.dataset.tradeId);
const NOTE_FIELDS = ["emotions", "mistakes", "lessons", "general_notes"];
const JSON_HEADERS = { "Content-Type": "application/json" };

const $ = (selector) => root.querySelector(selector);
const byId = (id) => document.getElementById(id);
const show = (element, visible) => element.classList.toggle("d-none", !visible);

// ---------------------------------------------------------------- API helper
// Returns the parsed body (null for 204) and THROWS an Error with a readable
// message on any failure. Callers only need try/catch and error.message.
async function api(url, options = {}) {
    let response;
    try {
        response = await fetch(url, options);
    } catch (error) {
        console.error(error);
        throw new Error("Couldnt reach the server. Check your connection and try again.");
    }

    if (response.status === 204) return null;

    const payload = await readJsonBody(response);
    if (!response.ok) throw new Error(extractErrorMessage(payload, response.status));
    return payload;
}

// ------------------------------------------------------------ confirm dialog
// One modal serves every destructive action. `action` is an async function: if it
// throws, the error shows inside the dialog and the dialog stays open for a retry.
const confirmModalEl = byId("confirmModal");
const confirmTitle = byId("confirm-title");
const confirmMessage = byId("confirm-message");
const confirmAlert = byId("confirm-alert");
const confirmAccept = byId("confirm-accept");
let pendingAction = null;

function confirmAction({ title, message, acceptLabel, action }) {
    confirmTitle.textContent = title;
    confirmMessage.textContent = message;
    confirmAccept.textContent = acceptLabel;
    pendingAction = action;
    hideAlert(confirmAlert);
    bootstrap.Modal.getOrCreateInstance(confirmModalEl).show();
}

confirmAccept.addEventListener("click", async () => {
    confirmAccept.disabled = true;   // deletes aren't safe to fire twice
    try {
        await pendingAction();
        bootstrap.Modal.getOrCreateInstance(confirmModalEl).hide();
    } catch (error) {
        showAlert(confirmAlert, "danger", error.message);
    } finally {
        confirmAccept.disabled = false;
    }
});

// --------------------------------------------------------------------- notes
const notesView = $("#notes-view");
const notesEmpty = $("#notes-empty");
const notesForm = $("#notes-form");
const notesToolbar = $("#notes-toolbar");
const notesAlert = $("#notes-alert");
const notesSave = $("#notes-save");
let hasNotes = root.dataset.hasNotes === "true";

// Exactly one panel is visible at a time. Every notes change goes through this
// function, so the UI can't end up half view and half edit.
function setNotesMode(mode) {   // "view" | "empty" | "edit"
    show(notesView, mode === "view");
    show(notesEmpty, mode === "empty");
    show(notesForm, mode === "edit");
    show(notesToolbar, mode === "view");
}

// notes === null means "this trade has no notes"
function renderNotes(notes) {
    hasNotes = notes !== null;
    if (hasNotes) {
        for (const field of NOTE_FIELDS) {
            $(`[data-note-field="${field}"]`).textContent = notes[field];
        }
    }
    setNotesMode(hasNotes ? "view" : "empty");
}

function startEditingNotes() {
    hideAlert(notesAlert);
    notesForm.classList.remove("was-validated");
    for (const field of NOTE_FIELDS) {
        // the displayed text is the source of truth; blank when there are no notes yet
        notesForm.elements[field].value = hasNotes ? $(`[data-note-field="${field}"]`).textContent : "";
    }
    setNotesMode("edit");
    notesForm.elements[NOTE_FIELDS[0]].focus();
}

notesForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideAlert(notesAlert);

    if (!notesForm.checkValidity()) {
        notesForm.classList.add("was-validated");
        return;
    }

    // PUT /api/trades/${tradeId}/notes is an upsert: it creates the notes if none exist, so one
    // form covers both "add" and "edit".
    const body = Object.fromEntries(new FormData(notesForm));

    notesSave.disabled = true;
    try {
        const saved = await api(`/api/trades/${tradeId}/notes`, {
            method: "PUT",
            headers: JSON_HEADERS,
            body: JSON.stringify(body),
        });
        renderNotes(saved);   // render what the server stored, not what we sent
        showAlert(notesAlert, "success", "Notes saved.");
    } catch (error) {
        showAlert(notesAlert, "danger", error.message);   // stay in edit mode so nothing typed is lost
    } finally {
        notesSave.disabled = false;
    }
});

function confirmDeleteNotes() {
    confirmAction({
        title: "Delete notes?",
        message: "The emotions, mistakes, lessons and general notes for this trade will be removed permanently.",
        acceptLabel: "Delete notes",
        action: async () => {
            await api(`/api/trades/${tradeId}/notes`, { method: "DELETE" });
            renderNotes(null);
            hideAlert(notesAlert);
        },
    });
}

// -------------------------------------------------------------------- charts
const chartsGrid = $("#charts-grid");
const chartsEmpty = $("#charts-empty");
const chartsCount = $("#charts-count");

function confirmDeleteChart(chartId, chartName) {
    confirmAction({
        title: "Delete chart?",
        message: `“${chartName}” will be removed permanently, including the image file.`,
        acceptLabel: "Delete chart",
        action: async () => {
            await api(`/api/trades/${tradeId}/charts/${chartId}`, { method: "DELETE" });
            chartsGrid.querySelector(`[data-chart-id="${chartId}"]`)?.remove();
            const remaining = chartsGrid.children.length;
            chartsCount.textContent = remaining;
            show(chartsEmpty, remaining === 0);
        },
    });
}

// --------------------------------------------------------------------- trade
function confirmDeleteTrade() {
    confirmAction({
        title: `Delete trade #${tradeId}?`,
        message: "This removes the trade together with its notes, charts and parameters, and its result leaves the account balance. The amendment history is kept. This can’t be undone.",
        acceptLabel: "Delete trade",
        action: async () => {
            await api(`/api/trades/${tradeId}`, { method: "DELETE" });
            window.location.assign("/trades");   // this page no longer has anything to show
        },
    });
}

// ----------------------------------------------- one delegated click listener
// Buttons declare what they do with data-action; nothing is wired per element,
// so cards added or removed later need no extra listeners.
const ACTIONS = {
    "edit-notes": startEditingNotes,
    "cancel-notes": () => { hideAlert(notesAlert); setNotesMode(hasNotes ? "view" : "empty"); },
    "delete-notes": confirmDeleteNotes,
    "delete-chart": (button) => confirmDeleteChart(button.dataset.chartId, button.dataset.chartName),
    "delete-trade": confirmDeleteTrade,
};

root.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (button) ACTIONS[button.dataset.action]?.(button);
});

// ------------------------------------------------------------------- modals
// Any trigger with data-prefill-trade-input="<input id>" fills that input with this
// trade's ID when its modal opens, so the shared navbar modals work from this page
// without retyping the ID. Bootstrap's modal events bubble, so one listener covers all.
document.addEventListener("show.bs.modal", (event) => {
    const inputId = event.relatedTarget?.dataset.prefillTradeInput;
    if (inputId) byId(inputId).value = tradeId;
});

const lightbox = byId("chartLightbox");
const lightboxImg = byId("chart-lightbox-img");
const lightboxCaption = byId("chart-lightbox-caption");

lightbox.addEventListener("show.bs.modal", (event) => {
    const { chartSrc, chartName } = event.relatedTarget.dataset;
    lightboxImg.src = chartSrc;
    lightboxImg.alt = `Chart screenshot: ${chartName}`;
    lightboxCaption.textContent = chartName;
});

// clear src on close so the next chart never flashes the previous image
lightbox.addEventListener("hidden.bs.modal", () => lightboxImg.removeAttribute("src"));
