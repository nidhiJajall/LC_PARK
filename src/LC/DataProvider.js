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

    getSODetails: (url) => {
        return fetch(`${BASE_URL}${url}`, {
            method: "GET",
            headers: HEADER_JSON,
            ...STANDARD_METHOD_OPTIONS,
        });
    },

    callOCRApi: (url, body) => {
            return fetch(`${BASE_URL}${url}`, {
            method: "POST",
            Authorization: HEADER_JSON.Authorization,
            body: body,
            ...STANDARD_METHOD_OPTIONS,
        });
    },

    // ── POST new LC request (Save or Submit) ──
    // Body is FormData because it includes a PDF file attachment
    createLCRequest: (url, body) => {
        return fetch(`${BASE_URL}${url}`, {
            method: "POST",
            Authorization: HEADER_JSON.Authorization,
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

    syncLCToSAP(url) {
        return fetch(`${BASE_URL}${url}`, {
            method : "POST",
            headers: {
                // Include your Django session / CSRF cookie headers here
                // if your project uses DRF SessionAuthentication.
                // Example for Django CSRF:
                //   "X-CSRFToken": getCookie("csrftoken"),
                "Content-Type": "application/json",
            },
        });
    },

    getSapPayloadPreview: (url) => {
      return fetch(`${BASE_URL}${url}`, {
        method: "GET",
        credentials: "include",
      });
    },

};

export default dataProvider;