// A file for utility functions used by our frontend HTML/CSS pages
// We have error message extraction from API responses.
// Show a Boostrap modal by ID.
// Hide a Boostrap modal by ID.
// We need JS to interact with our API.
// We can add JS to our home.html page that provides functionality
// The JS handlers needs to be on the home page because we want the handlers to be on every page
//since our modals are on every page. We do this in HTML using <script></script> tags.
//so this gives us functionality to record our trades.
//record trade form handler
//shared helper functions for displaying and hiding alerts to the UI
//functions to be exported where required

export function hideAlert(element) {
    element.className = "alert d-none";
    element.textContent = "";
}

export function showAlert(element, type, message) {
    //type here can be "success", "warning", "danger"
    //the below assignment replaces the entire class list which also drops d-none
    element.className = `alert alert-${type}`;
    element.textContent = message;

    //I want to see my alert even when I scroll down since my recordTradeModal has many fields.
    element.scrollIntoView({behavior: "smooth", block: "nearest"});
}

export function extractErrorMessage(payload, status){
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

export async function readJsonBody(response){
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

//show the success modal
export function showSuccessModal(modalId) {
    const modal = bootstrap.Modal.getOrCreateInstance(
        document.getElementById(modalId)
    );
    modal.show();
    return modal;
}