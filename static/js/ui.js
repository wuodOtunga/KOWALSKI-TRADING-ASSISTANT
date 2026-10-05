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
    tradeAlert.scrollIntoView({behavior: "smooth", block: "nearest"});
}