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

    // ── POST PDF to OCR endpoint ──
    // Body is FormData; do NOT set Content-Type — browser sets it with boundary.
    callOCRApi: (url, body) => {
        return fetch(`${BASE_URL}${url}`, {
            method: "POST",
            headers: {
                Authorization: HEADER_JSON.Authorization,
            },
            body: body,
            ...STANDARD_METHOD_OPTIONS,
        });
    },

    // ── POST new LC request (Save or Submit) ──
    // Body is FormData because it includes a PDF file attachment.
    // Do NOT set Content-Type — let browser set it with the multipart boundary.
    createLCRequest: (url, body) => {
        return fetch(`${BASE_URL}${url}`, {
            method: "POST",
            headers: {
                Authorization: HEADER_JSON.Authorization,
            },
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

    // ── POST: execute the CSRF-fetch + SAP POST flow ──
    syncLCToSAP: (url) => {
        return fetch(`${BASE_URL}${url}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: HEADER_JSON.Authorization,
            },
            ...STANDARD_METHOD_OPTIONS,
        });
    },

    // ── GET: preview SAP payload without sending (dry-run) ──
    getSapPayloadPreview: (url) => {
        return fetch(`${BASE_URL}${url}`, {
            method: "GET",
            headers: HEADER_JSON,
            ...STANDARD_METHOD_OPTIONS,
        });
    },

};

export default dataProvider;