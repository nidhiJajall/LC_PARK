// LC/DataProvider.js
// ─────────────────────────────────────────────────────────────────────────────
// ALL API calls for the LC module live here.
// Screens never call fetch() directly — they always go through dataProvider.
// ─────────────────────────────────────────────────────────────────────────────

import {
    BASE_URL,
    STANDARD_METHOD_OPTIONS,
    HEADER_JSON,
} from "../App/Configs/AppConfigs";

const dataProvider = {

    // ── GET paginated list of LC requests (used by LCList.js) ──
    getLCList: (url) => {
        return fetch(`${BASE_URL}${url}`, {
            method: "GET",
            headers: HEADER_JSON,
            ...STANDARD_METHOD_OPTIONS,
        });
    },

    // ── GET single LC request by ID (used for view/edit) ──
    getLCDetail: (url) => {
        return fetch(`${BASE_URL}${url}`, {
            method: "GET",
            headers: HEADER_JSON,
            ...STANDARD_METHOD_OPTIONS,
        });
    },

    // ── GET SO data by SO Number ──
    // Called when user enters SO number and tabs out (onBlur)
    // Returns: company_code, plant_code, customer_code, ship_to_party, so_value, etc.
    getSODetails: (url) => {
        return fetch(`${BASE_URL}${url}`, {
            method: "GET",
            headers: HEADER_JSON,
            ...STANDARD_METHOD_OPTIONS,
        });
    },

    // ── POST new LC request (Save or Submit) ──
    // Body is FormData because it includes a PDF file attachment
    createLCRequest: (url, body) => {
        return fetch(`${BASE_URL}${url}`, {
            method: "POST",
            body: body,
            ...STANDARD_METHOD_OPTIONS,
        });
    },

    // ── PATCH existing LC request (edit mode) ──
    updateLCRequest: (url, body) => {
        return fetch(`${BASE_URL}${url}`, {
            method: "PATCH",
            body: body,
            ...STANDARD_METHOD_OPTIONS,
        });
    },
};

export default dataProvider;
