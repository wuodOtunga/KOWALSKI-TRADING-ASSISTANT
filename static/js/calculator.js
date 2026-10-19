//FORM SUBMISSION - catch the submit event
//stop normal browser submission
//extract form data
//build api request payload
//send post request to FastApi
//wait for HTTP response
//parse JSON response and branch on either success or error
//on success, update UI,,,on error extract error then show error

//IMPORT showAlert, hideAlert, extractErrorMessage, readJsonBody FROM utils.js
import { showAlert, hideAlert, extractErrorMessage, readJsonBody } from "./utils.js";

//numeric constants from the form
const TRADE_NUMERICS = ["entry_price", "exit_price", "take_profit", "stop_loss", "position_size", "account_balance"];
const SIZING_NUMERICS = ["account_balance", "entry_price", "stop_loss", "risk_percent"];

//GRAB ELEMENTS (forms, alerts, submit buttons, result panels, empty states)
//naming convention: tc-* === trade-calculator, ps-** === position-size
//----------CALCULATOR ELEMENTS
const calculatorForm = document.getElementById("tradeCalcForm");
const calculatorAlert = document.getElementById("tcAlert");
const calcSubmitButton = document.querySelector('button[form="tradeCalcForm"]');
const calculatorEmptyState = document.getElementById("tc-result-empty");
const calculatorResultPanel = document.getElementById("tc-result");
const resultBadge = document.getElementById("tc-result-badge");
const dollarAmountElement = document.getElementById("tc-result-dollar");
const percentElement = document.getElementById("tc-result-percent");
const rrElement = document.getElementById("tc-result-rr");
const riskPercentElement = document.getElementById("tc-result-risk-percent");
const riskAmountElement = document.getElementById("tc-result-risk-amount");
const rewardAmountElement = document.getElementById("tc-result-reward-amount");

//--------POSITION SIZE ELEMENTS
const positionSizeForm = document.getElementById("positionSizeForm");
const positionSizeAlert = document.getElementById("psAlert");
const positionSizeSubmitButton = document.querySelector('button[form="positionSizeForm"]');
const positionSizeEmptyState = document.getElementById("ps-result-empty");
const positionSizeResultPanel = document.getElementById("ps-result");
const positionSizeElement = document.getElementById("ps-result-size");


//register listeners
calculatorForm.addEventListener("submit", calculatorHandler);
positionSizeForm.addEventListener("submit", positionSizeHandler);
calculatorForm.addEventListener("reset", () => clearResults("trade"));
positionSizeForm.addEventListener("reset", () => clearResults("sizing"));

//-------small helper functions----------
//show empty-state + result-panel pair
//Bootstrap’s d-none is just display: none.
//“Show” means removing d-none and “hide” means adding it.
//So “hide result panel, show empty state” is two classList calls.
//Because it appears in several places (error, reset, success), it’s worth putting in one small helper.
function showResultPanel(emptyElement, resultElement) {
    //hide empty state, show result panel
    emptyElement.classList.add("d-none");
    resultElement.classList.remove("d-none");
}

function showEmptyState(emptyElement, resultElement) {
    //show empty state, hide result panel
    resultElement.classList.add("d-none");
    emptyElement.classList.remove("d-none");
}

//this does: 1245 => "&+1245", -80 => "&-80"
function formatSignedMoney(value) {
    const sign = value > 0 ? "+" : value < 0 ? "-" : "";
    return `${sign}$${Math.abs(value).toFixed(2)}`;
}

function formatMoney(value) {
    return `$${Math.abs(value).toFixed(2)}`;
}

//For colours, the trap is that classList.add("text-success") on every calculation piles classes up,
//so a loss after a profit ends up with both. Remove both, then add the right one.
//I need to toggle text-success / text-danger on the headline by PROFIT vs LOSS.
function setProfitLossColor(element, isProfit) {
    element.classList.remove("text-success", "text-danger");
    element.classList.add(isProfit ? "text-success" : "text-danger");
}

//--------trade-calculator handler-----------------
export async function calculatorHandler(event) {

    //stop normal browser form submission
    event.preventDefault();

    //hide any previous alerts
    hideAlert(calculatorAlert);

    //check validity of the form inputs
    if (!calculatorForm.checkValidity()) {
        calculatorForm.classList.add("was-validated")
        return;
    };

    //extract and assemble form data into a JS object
    const calculatorData = Object.fromEntries(new FormData(calculatorForm).entries());

    // convert TRADE_NUMERIC keys with Number()
    //form values are strings by default, server uses floats/Number.
    for (const key of TRADE_NUMERICS) calculatorData[key] = Number(calculatorData[key]);

    //disable submit button. not for idempotency, just stops double-click spam
    calcSubmitButton.disabled = true;

    //build api request payload
    let response = null;
    try {
        response = await fetch("api/calculator/trade-metrics", {
            method: "POST",
            headers: {"Content-type": "application/json"},
            body: JSON.stringify(calculatorData)
        });

        //parse JSON response body and branch on success/error
        if (!response.ok) {
            const payload = await readJsonBody(response);
            showAlert(calculatorAlert, "danger", extractErrorMessage(payload, response.status));
            //we didn't get a response with the calculated trade metrics so you show
            //the empty state telling user to fill in values and hide result panel
            //because we still don't have results to show.
            showEmptyState(calculatorEmptyState, calculatorResultPanel);
            return;
        }
        //no need for else clause because if the if block didn't run this means
        //we successfully got back calculator results from the server.
        //notice how I am avoiding creating redundant variables and else blocks.
        renderTradeResults(await readJsonBody(response));
    } catch (error) {
        console.error(error);
        showAlert(calculatorAlert, "danger", "Error detected. Couldn't access the server");
        return;
    } finally {
        calcSubmitButton.disabled = false;
    }
}

function renderTradeResults(results) {
    //shape of calculator results looks something like this:
    //{ result, rr_multiple, risk_percent, risk_amount, reward_amount, dollar_amount, dollar_percent }
    //hide empty state, show results panel since we now have results to render
    showResultPanel(calculatorEmptyState, calculatorResultPanel);

    const isProfit = results.result === "PROFIT";

    //format dollar amount to 2 decimal places
    dollarAmountElement.textContent = formatSignedMoney(results.dollar_amount);

    // toggle text-success / text-danger on the headline by PROFIT vs LOSS
    setProfitLossColor(dollarAmountElement, isProfit);

    // set dollar_percent, rr multiple, risk amount, reward amount, risk percent.
    //dollar_percent is the dollar_amount's percentage share for the account_balance.
    percentElement.textContent = `${results.dollar_percent.toFixed(2)}% of account`;
    rrElement.textContent = `${results.rr_multiple.toFixed(2)}R`;
    riskPercentElement.textContent = `${results.risk_percent.toFixed(2)}%`;
    riskAmountElement.textContent = formatMoney(results.risk_amount);
    rewardAmountElement.textContent = formatMoney(results.reward_amount);

    //set badge text + colour from result verdict
    //The badge: the HTML starts it as badge text-bg-secondary d-none.
    //Setting className to a fresh string in renderTradeResults replaces all of that at once,
    //d-none included, which is why it appears. clearResults puts d-none back.
    resultBadge.textContent = results.result;
    resultBadge.className = `badge ${isProfit ? "text-bg-success" : "text-bg-danger"}`;
}

function renderPositionSizingResults(results) {
    //results shape from the server: { lot_size }
    showResultPanel(positionSizeEmptyState, positionSizeResultPanel);
    positionSizeElement.textContent = results.lot_size;

}

//-----POSITION SIZE CALCULATOR FORM HANDLER------------------
export async function positionSizeHandler(event) {
    event.preventDefault();
    hideAlert(positionSizeAlert);

    //check validity of the form inputs
    if (!positionSizeForm.checkValidity()) {
        positionSizeForm.classList.add("was-validated")
        return;
    };

    //extract and assemble form data into a JS object
    const positionSizeData = Object.fromEntries(new FormData(positionSizeForm).entries());

    // convert SIZING_NUMERIC keys with Number()
    for (const key of SIZING_NUMERICS) positionSizeData[key] = Number(positionSizeData[key]);

    //disable submit button. not for idempotency, just stops double-click spam
    positionSizeSubmitButton.disabled = true;

    //build api request payload
    let response = null;
    try {
        response = await fetch("api/calculator/position-size", {
            method: "POST",
            headers: {"Content-type": "application/json"},
            body: JSON.stringify(positionSizeData),
        });
        //parse JSON response body and branch on success/error
        if (!response.ok) {
            const payload = await readJsonBody(response);
            showAlert(positionSizeAlert, "danger", extractErrorMessage(payload, response.status));
            showEmptyState(positionSizeEmptyState, positionSizeResultPanel);
            return;
        }

        renderPositionSizingResults(await readJsonBody(response));
    } catch (error) {
        console.error(error);
        showAlert(positionSizeAlert, "danger", "Error detected. Couldn't access the server");
        return;
    } finally {
        positionSizeSubmitButton.disabled = false;
    }
}

//----------RESET-----------------------
//The reset event: the Reset button is type="reset" with form="tradeCalcForm",
//so the browser fires a reset event on the form and clears the inputs itself.
//The listener only needs to clean up the display.
function clearResults(which) {
    if (which === "trade") {
        showEmptyState(calculatorEmptyState, calculatorResultPanel);
        hideAlert(calculatorAlert);
        calculatorForm.classList.remove("was-validated");
        resultBadge.classList.add("d-none");
        dollarAmountElement.classList.remove("text-success", "text-danger");
    } else {
        showEmptyState(positionSizeEmptyState, positionSizeResultPanel);
        hideAlert(positionSizeAlert);
        positionSizeForm.classList.remove("was-validated");
    }
}
