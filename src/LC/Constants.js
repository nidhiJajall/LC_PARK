// LC/Constants.js

// API Paths — these are the endpoints your backend exposes
export const LC_API_PATH         = "/lc_request/";
export const LC_OCR_API_PATH     = "/lc_request/ocr/";          // POST PDF here → Django proxies to OCR API
export const LC_SO_LOOKUP_API_PATH = "/master/Master.Sodata/";  // called when SO number is entered

// AG Grid Column Definitions for the List Screen
export const LC_LIST_COLUMNDEFS = [
    { headerName: "Instrument Number", field: "instrument_number", sortable: true, filter: true},
    { headerName: "SO Number",     field: "so_number",     sortable: true, filter: true },
    { headerName: "Customer Code", field: "customer_code", sortable: true, filter: true },
    { headerName: "SO Value",      field: "so_value",      sortable: true, filter: true },
    { headerName: "Status",        field: "status",        sortable: true, filter: true },
    { headerName: "Created By",    field: "created_by",    sortable: true, filter: true },
    { headerName: "Created Date",  field: "created_date",  sortable: true, filter: true },
];

// Header column defs (checkbox column)
export const LC_LIST_HEADER_COLUMNDEFS = [
    { headerName: "", checkboxSelection: true, width: 50 },
];