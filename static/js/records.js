//RECORDS PAGE: page-specific JS, loaded from records.html only (NOT through main.js).
//ON PAGE LOAD
//  fetch the summary and the table rows in parallel, each one independently,
//  so one failing endpoint never blanks the other half of the page.
//  render the summary cards and the table rows.
//ON LOOKUP FORM SUBMIT
//  stop normal submission, validate, check the trade exists via the API,
//  then navigate to /trades/{id} or show the error inline.
import { showAlert, hideAlert, extractErrorMessage, readJsonBody } from "./utils.js";

const MAX_POINTS = 5; //entry execution and management points both run 1..5

const alertEl = document.getElementById("recordsAlert");
const totalEl = document.getElementById("rec-total");
const latestEl = document.getElementById("rec-latest");
const latestEmptyEl = document.getElementById("rec-latest-empty");
const latestLinkEl = document.getElementById("rec-latest-link");
const latestResultEl = document.getElementById("rec-latest-result");
const latestAmountEl = document.getElementById("rec-latest-amount");
const latestMetaEl = document.getElementById("rec-latest-meta");
const tableBody = document.getElementById("rec-table-body");
const lookupForm = document.getElementById("recordsLookupForm");
const lookupInput = document.getElementById("rec-lookup-id");
const lookupSubmit = document.getElementById("rec-lookup-submit");

lookupForm.addEventListener("submit", lookupHandler);
loadRecords();

// --------------------------------------------------------------------------
//  FORMATTING HELPERS
// --------------------------------------------------------------------------

//Bootstrap 5.3 classes. Keys match the grade strings stored in the database.
const GRADE_CLASSES = {
    "A+": "text-bg-success",
    "A": "text-bg-success",
    "B": "text-bg-info",
    "C": "text-bg-warning",
    "D": "bg-danger-subtle text-danger-emphasis",
    "F": "text-bg-danger",
};

const moneyFormat = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    signDisplay: "exceptZero",   // +$15.13, -$7.35, $0.00
});

function formatMoney(amount) {
    return moneyFormat.format(Number(amount));
}

function formatDate(isoDate) {
    //"2026-10-19" -> "Mon 19 Oct 2026".
    //new Date("2026-10-19") parses as UTC midnight, which can display as the previous
    //day in timezones behind UTC. Building it from parts keeps it a local calendar date.
    const [year, month, day] = isoDate.split("-").map(Number);
    return new Date(year, month - 1, day).toLocaleDateString("en-GB", {
        weekday: "short", day: "numeric", month: "short", year: "numeric",
    });
}

function resultInfo(result, dollarAmount) {
    //TradeResult has no BREAKEVEN yet (issue B4), so a 0 dollar amount arrives as LOSS.
    //Checking the amount first means this works now and keeps working once the backend adds it.
    if (Number(dollarAmount) === 0 || result === "BREAKEVEN") {
        return { label: "BE", cls: "text-secondary" };
    }
    if (result === "PROFIT") return { label: "PROFIT", cls: "text-success" };
    if (result === "LOSS") return { label: "LOSS", cls: "text-danger" };
    return { label: result ?? "—", cls: "" };
}

function gradeBadge(grade) {
    const badge = document.createElement("span");
    if (grade == null) {
        badge.className = "badge text-bg-secondary";
        badge.textContent = "UNGRADED";
        return badge;
    }
    badge.className = `badge ${GRADE_CLASSES[grade] ?? "text-bg-secondary"}`;
    badge.textContent = grade;
    return badge;
}

function makeCell(...children) {
    const td = document.createElement("td");
    td.append(...children);
    return td;
}

function scoreCell(score) {
    //score = { archetype, grade, points }: grade badge + points, archetype name underneath.
    const top = document.createElement("div");
    const points = document.createElement("span");
    points.className = "ms-2";
    points.textContent = `${score.points}/${MAX_POINTS}`;
    top.append(gradeBadge(score.grade), points);

    const name = document.createElement("div");
    name.className = "text-secondary small";
    name.textContent = score.archetype;

    return makeCell(top, name);
}

// --------------------------------------------------------------------------
//  RENDERING
// --------------------------------------------------------------------------
function setTableMessage(message, cls = "text-secondary") {
    const td = document.createElement("td");
    td.colSpan = 6;
    td.className = `text-center py-4 ${cls}`;
    td.textContent = message;

    const tr = document.createElement("tr");
    tr.append(td);
    tableBody.replaceChildren(tr);
}

function renderRows(rows) {
    if (rows.length === 0) {
        setTableMessage("No trades recorded yet.");
        return;
    }

    const trs = rows.map(row => {
        const idLink = document.createElement("a");
        idLink.href = `/journal/${row.trade_id}`;
        idLink.className = "text-decoration-none fw-semibold";
        idLink.textContent = `#${row.trade_id}`;

        const result = resultInfo(row.result, row.dollar_amount);
        const resultSpan = document.createElement("span");
        resultSpan.className = `fw-semibold ${result.cls}`;
        resultSpan.textContent = result.label;

        const amountTd = makeCell(formatMoney(row.dollar_amount));
        amountTd.className = `text-end ${result.cls}`;

        const tr = document.createElement("tr");
        tr.append(
            makeCell(idLink),
            makeCell(gradeBadge(row.overall_trade_grade)),
            scoreCell(row.entry_execution),
            scoreCell(row.management_execution),
            makeCell(resultSpan),
            amountTd,
        );
        return tr;
    });

    tableBody.replaceChildren(...trs);
}

function renderSummary(summary) {
    totalEl.textContent = summary.total_trades;

    const latest = summary.latest_trade;
    if (!latest) {
        latestEl.classList.add("d-none");
        latestEmptyEl.classList.remove("d-none");
        return;
    }

    const result = resultInfo(latest.result, latest.dollar_amount);

    latestLinkEl.href = `/journal/${latest.trade_id}`;
    latestLinkEl.textContent = `#${latest.trade_id}`;
    latestResultEl.className = `fw-semibold font-monospace ${result.cls}`;
    latestResultEl.textContent = result.label;
    latestAmountEl.className = `font-monospace ${result.cls}`;
    latestAmountEl.textContent = formatMoney(latest.dollar_amount);
    latestMetaEl.textContent = `${formatDate(latest.date)} · ${latest.asset} ${latest.direction}`;

    latestEmptyEl.classList.add("d-none");
    latestEl.classList.remove("d-none");
}

// --------------------------------------------------------------------------
//  LOADING
// --------------------------------------------------------------------------
async function fetchJson(url) {
    //never throws on HTTP errors, only on network failure (caught by the caller).
    const response = await fetch(url);
    const payload = await readJsonBody(response);
    return { ok: response.ok, status: response.status, payload };
}

async function loadRecords() {
    hideAlert(alertEl);

    let summary, rows;
    try {
        [summary, rows] = await Promise.all([
            fetchJson("/api/records/summary"),
            fetchJson("/api/records/trades"),
        ]);
    } catch (error) {
        console.error(error);
        showAlert(alertEl, "danger", "Error detected. Couldn't access the server!");
        setTableMessage("Failed to load trades.", "text-danger");
        return;
    }

    const problems = [];

    if (summary.ok) {
        renderSummary(summary.payload);
    } else {
        problems.push(extractErrorMessage(summary.payload, summary.status));
    }

    if (rows.ok) {
        renderRows(rows.payload);
    } else {
        problems.push(extractErrorMessage(rows.payload, rows.status));
        setTableMessage("Failed to load trades.", "text-danger");
    }

    if (problems.length > 0) {
        showAlert(alertEl, "danger", problems.join("; "));
    }
}

// --------------------------------------------------------------------------
//  LOOKUP: VIEW A SINGLE TRADE
// --------------------------------------------------------------------------
async function lookupHandler(event) {
    event.preventDefault();
    hideAlert(alertEl);

    if (!lookupForm.checkValidity()) {
        lookupForm.classList.add("was-validated");
        return;
    }

    const tradeId = Number(lookupInput.value);

    //GET is idempotent, but disabling still stops double clicks racing two navigations.
    lookupSubmit.disabled = true;
    try {
        //ask the API first so a bad ID shows an inline message instead of a full error page.
        const result = await fetchJson(`/api/trades/${tradeId}`);

        if (!result.ok) {
            showAlert(alertEl, "danger", extractErrorMessage(result.payload, result.status));
            return;
        }

        window.location.href = `/trades/${tradeId}`;
    } catch (error) {
        console.error(error);
        showAlert(alertEl, "danger", "Error detected. Couldn't access the server!");
    } finally {
        lookupSubmit.disabled = false;
    }
}
