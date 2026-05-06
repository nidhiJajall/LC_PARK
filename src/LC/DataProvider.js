import {
    BASE_URL,
    STANDARD_METHOD_OPTIONS,
} from "../App/Configs/AppConfigs";

/**
 * Read the auth token from localStorage at call time, not at module load time.
 * HEADER_JSON in AppConfigs is built once on import (before login), so the
 * Authorization value is always null if read statically.
 */
const getAuthToken = () =>
    JSON.parse(
        localStorage.getItem(`${process.env.REACT_APP_TOKEN_PREFIX}-auth-token`)
    );

const getAuthHeaders = () => ({
    Accept: "application/json",
    Authorization: getAuthToken(),
    source: "workflow",
    req: "list",
});

const dataProvider = {

    // ── GET paginated list of LC requests (used by LCList.js) ──
    getLCList: (url) => {
        return fetch(`${BASE_URL}${url}`, {
            method: "GET",
            headers: getAuthHeaders(),
            ...STANDARD_METHOD_OPTIONS,
        });
    },

    // ── GET single LC request by ID (used for view/edit) ──
    getLCDetail: (url) => {
        return fetch(`${BASE_URL}${url}`, {
            method: "GET",
            headers: getAuthHeaders(),
            ...STANDARD_METHOD_OPTIONS,
        });
    },

    getSODetails: (url) => {
        return fetch(`${BASE_URL}${url}`, {
            method: "GET",
            headers: getAuthHeaders(),
            ...STANDARD_METHOD_OPTIONS,
        });
    },

    // ── POST PDF to OCR endpoint ──
    // Body is FormData; do NOT set Content-Type — browser sets it with boundary.
    callOCRApi: (url, body) => {
        return fetch(`${BASE_URL}${url}`, {
            method: "POST",
            headers: {
                Authorization: getAuthToken(),
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
                Authorization: getAuthToken(),
            },
            body: body,
            ...STANDARD_METHOD_OPTIONS,
        });
    },

    // ── PATCH existing LC request (edit mode) ──
    // Authorization header was missing entirely — added here.
    updateLCRequest: (url, body) => {
        return fetch(`${BASE_URL}${url}`, {
            method: "PATCH",
            headers: {
                Authorization: getAuthToken(),
            },
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
                Authorization: getAuthToken(),
            },
            ...STANDARD_METHOD_OPTIONS,
        });
    },

    // ── GET: preview SAP payload without sending (dry-run) ──
    getSapPayloadPreview: (url) => {
        return fetch(`${BASE_URL}${url}`, {
            method: "GET",
            headers: getAuthHeaders(),
            ...STANDARD_METHOD_OPTIONS,
        });
    },

};

export default dataProvider;