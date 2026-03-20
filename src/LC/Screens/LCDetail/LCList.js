// LC/Screens/LCList/LCList.js
// ─────────────────────────────────────────────────────────────────────────────
// LIST SCREEN — Shows all LC Requests in an AG Grid table.
//
// Responsibilities:
//   1. Fetches paginated data from API on mount + on page/filter/search change
//   2. Renders ListHeader (search, filter, add button)
//   3. Renders AgGridReact with column definitions from Constants.js
//   4. Renders ListFooter (pagination)
//   5. "Add" button navigates to LCRequest form
// ─────────────────────────────────────────────────────────────────────────────

import React, { useEffect, useState } from "react";
import { AgGridReact } from "ag-grid-react/lib/agGridReact";
import { openNotification } from "swfrontend/COMS/NotificationMessageMapping";
import ListFooter from "swfrontend/MDM/MDMScreens/ListView/ListFooter.js";
import ListHeader from "swfrontend/MDM/MDMScreens/ListView/ListHeader";
import { route_url } from "swfrontend/AppConfigs";
import dataProvider from "../../DataProvider";
import {
    LC_API_PATH,
    LC_LIST_COLUMNDEFS,
    LC_LIST_HEADER_COLUMNDEFS,
} from "../../Constants";

// ── Module-level gridApi (standard pattern across all list screens) ──
// Allows us to control the grid (show/hide overlay) from outside the component
let gridApi = null;
let gridHeight = window.innerHeight - 400 + "px";

const onFirstDataRendered = (params) => params.api.sizeColumnsToFit();
const onGridReady = (params) => { gridApi = params.api; };

const LCList = ({ history }) => {
    const [state, setState] = useState({
        selectedRow: null,
        rowData: null,
        pageSize: 20,
        searchQuery: null,
        filterQuery: null,
        total: 0,
        currentPage: 1,
    });

    // ── Re-fetch whenever currentPage changes ──
    useEffect(() => {
        fetchGridData(state.currentPage);
    }, [state.currentPage]);

    // ────────────────────────────────────────────────────────────────
    // FETCH: Build query string and call dataProvider.getLCList()
    // Query string combines: page, pageSize, search, filter params
    // ────────────────────────────────────────────────────────────────
    const fetchGridData = (pageNo) => {
        let values = "?page=" + pageNo + "&pageSize=" + state.pageSize;

        if (state.searchQuery) values += "&" + state.searchQuery;
        if (state.filterQuery) values += "&" + state.filterQuery + "&filter=1";

        dataProvider
            .getLCList(LC_API_PATH + values)
            .then((res) => {
                if (res.ok) {
                    res.json().then((rowData) => {
                        try { gridApi.hideOverlay(); } catch (e) {}
                        setState((prev) => ({
                            ...prev,
                            total: rowData.total,
                            rowData: rowData.results,
                        }));
                    });
                } else {
                    openNotification("error", "Error", "Failed to load LC requests");
                }
            })
            .catch(() => {
                openNotification("error", "Error", "Error connecting to server");
            });
    };

    // ── Navigate to new form on Add button click ──
    const handleNewButtonClick = () => {
        console.log("route_url.url →", route_url.url);
        console.log("pushing to →", route_url.url + '/lc_request/new');
        history.push(route_url.url + '/lc_request/new');
    };

    const onPaginationChange = (page, pageSize) => {
        if (!page) page = 1;
        gridApi.showLoadingOverlay();
        setState((prev) => ({ ...prev, pageSize, currentPage: page }));
    };

    const handleSearchApply = (value) => {
        gridApi.showLoadingOverlay();
        setState((prev) => ({
            ...prev,
            searchQuery: value ? "search=" + value : null,
            currentPage: 1,
        }));
    };

    const handleFilterApply = (querystring) => {
        gridApi.showLoadingOverlay();
        setState((prev) => ({ ...prev, filterQuery: querystring, currentPage: 1 }));
    };

    const handleResetFilter = () => {
        gridApi.showLoadingOverlay();
        setState((prev) => ({
            ...prev,
            selectedRow: null,
            filterQuery: null,
            currentPage: 1,
        }));
    };

    const handleResetSearch = () => {
        gridApi.showLoadingOverlay();
        setState((prev) => ({ ...prev, selectedRow: null, searchQuery: null }));
    };

    return (
        <div className="col-md-12">
            {/* ── Header: search bar, filter, add button ── */}
            <ListHeader
                excelExport={() => {}}
                showListHeader={true}
                addButton={true}
                columnFilterButton={false}
                columnDefs={LC_LIST_HEADER_COLUMNDEFS}
                onSearch={(q) => handleSearchApply(q)}
                onFilter={(q) => handleFilterApply(q)}
                onResetSearch={handleResetSearch}
                onResetFilter={handleResetFilter}
                addField={handleNewButtonClick}
            />

            {/* ── AG Grid Table ── */}
            <div className="grid-background">
                <div className="row">
                    <div className="col-md-12">
                        <div
                            id="grid"
                            className="table-responsive table-bordered table table-hover ag-theme-balham gridViewDisplay"
                            style={{ height: gridHeight }}
                        >
                            <AgGridReact
                                columnDefs={LC_LIST_COLUMNDEFS}
                                rowData={state.rowData}
                                pagination={false}
                                onGridReady={onGridReady}
                                onFirstDataRendered={onFirstDataRendered}
                            />
                        </div>
                    </div>
                </div>
            </div>

            {/* ── Footer: pagination ── */}
            <ListFooter
                total={state.total}
                currentPage={state.currentPage}
                onShowSizeChange={onPaginationChange}
                onPaginationChange={onPaginationChange}
            />
        </div>
    );
};

export default LCList;
