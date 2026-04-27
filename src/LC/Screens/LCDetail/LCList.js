// LC/Screens/LCList/LCList.js
import React, { useEffect, useState } from "react";
import { AgGridReact } from "ag-grid-react/lib/agGridReact";
import { Button } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { useHistory } from "react-router-dom";

import ListFooter from "swfrontend/MDM/MDMScreens/ListView/ListFooter.js";
import ListHeader from "swfrontend/MDM/MDMScreens/ListView/ListHeader";
import { route_url } from "swfrontend/AppConfigs";
import dataProvider from "../../DataProvider";
import { LC_API_PATH, LC_LIST_COLUMNDEFS, LC_LIST_HEADER_COLUMNDEFS } from "../../Constants";

let gridApi = null;

const LCList = () => {
    const history = useHistory();

    const [rowData, setRowData] = useState([]);
    const [total, setTotal] = useState(0);
    const [currentPage, setCurrentPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const [searchQuery, setSearchQuery] = useState(null);
    const [filterQuery, setFilterQuery] = useState(null);

    useEffect(() => {
        fetchGridData(currentPage);
    }, [currentPage, searchQuery, filterQuery]);

    const fetchGridData = (pageNo) => {
        let qs = `?page=${pageNo}&pageSize=${pageSize}`;
        if (searchQuery) qs += `&${searchQuery}`;
        if (filterQuery) qs += `&${filterQuery}&filter=1`;

        dataProvider.getLCList(LC_API_PATH + qs)
            .then((res) => {
                if (res.ok) {
                    res.json().then((data) => {
                        setTotal(data.total);
                        setRowData(data.results);
                    });
                }
            })
            .catch(() => console.error("Failed to load LC list"));
    };

    // ==================== DOUBLE CLICK → EDIT IN SAME FORM ====================
    const onRowDoubleClicked = (event) => {
        const id = event.data?.id;
        if (!id) return;
        history.push(`${route_url.url}/lc_request/${id}`);   // Edit mode
    };

    // ==================== NEW BUTTON ====================
    const handleNewButtonClick = () => {
        history.push(`${route_url.url}/lc_request/new`);
    };

    // Pagination & Search Handlers
    const onPaginationChange = (page, size) => {
        setPageSize(size);
        setCurrentPage(page || 1);
    };

    const handleSearchApply = (value) => {
        setSearchQuery(value ? `search=${value}` : null);
        setCurrentPage(1);
    };

    const handleFilterApply = (querystring) => {
        setFilterQuery(querystring);
        setCurrentPage(1);
    };

    const handleResetFilter = () => {
        setFilterQuery(null);
        setCurrentPage(1);
    };

    const handleResetSearch = () => {
        setSearchQuery(null);
    };

    return (
        <div className="col-md-12">
            <ListHeader
                excelExport={() => {}}
                showListHeader={true}
                addButton={true}
                columnFilterButton={false}
                columnDefs={LC_LIST_HEADER_COLUMNDEFS}
                onSearch={handleSearchApply}
                onFilter={handleFilterApply}
                onResetSearch={handleResetSearch}
                onResetFilter={handleResetFilter}
                addField={handleNewButtonClick}
            />

            <div className="grid-background">
                <div className="row">
                    <div className="col-md-12">
                        <div
                            id="grid"
                            className="table-responsive table-bordered table table-hover ag-theme-balham gridViewDisplay"
                            style={{ height: window.innerHeight - 280 + "px" }}
                        >
                            <AgGridReact
                                columnDefs={LC_LIST_COLUMNDEFS}
                                rowData={rowData}
                                pagination={false}
                                onGridReady={(params) => { gridApi = params.api; }}
                                onRowDoubleClicked={onRowDoubleClicked}     // ← Double Click to Edit
                                rowSelection="multiple"
                                suppressRowClickSelection={true}
                            />
                        </div>
                    </div>
                </div>
            </div>

            <ListFooter
                total={total}
                currentPage={currentPage}
                onShowSizeChange={onPaginationChange}
                onPaginationChange={onPaginationChange}
            />
        </div>
    );
};

export default LCList;