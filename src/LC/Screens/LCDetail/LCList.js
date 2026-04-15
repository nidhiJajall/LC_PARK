// LC/Screens/LCList/LCList.js
//
// React Router v5  →  useHistory hook (NOT useNavigate)
// Pattern          →  Function-based component with useState / useEffect
// Detail view      →  Ant Design Drawer opens on row click — no separate route needed
//                     Shows SO child rows + LC Details (all 23 OCR fields)

import React, { useEffect, useState } from "react";
import { AgGridReact } from "ag-grid-react/lib/agGridReact";
import {
    Drawer, Tag, Table, Divider, Row, Col, Spin, Button,
} from "antd";
import {
    FileSearchOutlined, PaperClipOutlined, RobotOutlined,
    FilePdfOutlined, CheckCircleOutlined, ClockCircleOutlined,
    EyeOutlined,
} from "@ant-design/icons";
import { useHistory } from "react-router-dom";           // ← v5 hook
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

/* ─── Module-level grid API reference (standard SWF pattern) ─────────
   Stored outside component so overlay helpers don't cause re-renders. */
let gridApi   = null;
const gridHeight = window.innerHeight - 400 + "px";

const onFirstDataRendered = (params) => params.api.sizeColumnsToFit();
const onGridReady         = (params) => { gridApi = params.api; };

/* ─── Small read-only label+value block used inside the Drawer ───────── */
const FieldCell = ({ label, value, mono = false }) => (
    <div style={{ marginBottom: "14px" }}>
        <div style={{
            fontSize: "11px", fontWeight: 700, color: "#999",
            textTransform: "uppercase", letterSpacing: "0.4px", marginBottom: "3px",
        }}>
            {label}
        </div>
        <div style={{
            fontSize: "13px",
            color: value !== null && value !== undefined && value !== "" ? "#222" : "#ccc",
            fontFamily: mono ? "monospace" : "inherit",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
        }}>
            {value !== null && value !== undefined && value !== "" ? value : "—"}
        </div>
    </div>
);

/* ─── Boolean flag displayed as a coloured Tag ───────────────────────── */
const BoolFlag = ({ label, value }) => (
    <div style={{ marginBottom: "14px" }}>
        <div style={{
            fontSize: "11px", fontWeight: 700, color: "#999",
            textTransform: "uppercase", letterSpacing: "0.4px", marginBottom: "3px",
        }}>
            {label}
        </div>
        <Tag color={value ? "green" : "default"}>{value ? "Yes" : "No"}</Tag>
    </div>
);

/* ─── Drawer section header ───────────────────────────────────────────── */
const DrawerSection = ({ icon, title }) => (
    <div style={{
        display: "flex", alignItems: "center", gap: "8px",
        fontSize: "13px", fontWeight: 700, color: "#b5000a",
        marginBottom: "14px", paddingBottom: "8px",
        borderBottom: "2px solid #f5f5f5",
        textTransform: "uppercase", letterSpacing: "0.5px",
    }}>
        <span style={{ fontSize: "15px" }}>{icon}</span>
        {title}
    </div>
);

/* ─── Columns for the SO child row table inside the drawer ───────────── */
const SO_DETAIL_COLUMNS = [
    {
        title: "SO Number",
        dataIndex: "so_number",
        key: "so_number",
        render: (v) => <span style={{ fontWeight: 600, color: "#b5000a" }}>{v}</span>,
    },
    { title: "Int. Free Credit Days", dataIndex: "interest_free_credit_days", key: "ifc" },
    {
        title: "Interest Charges",
        dataIndex: "interest_charges",
        key: "ic",
        render: (v) => (v != null ? `${v}%` : "—"),
    },
    {
        title: "Usance Period",
        dataIndex: "usance_period",
        key: "up",
        render: (v) => (v != null ? `${v} days` : "—"),
    },
];

/* ═══════════════════════════════════════════════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════════════════════════════════════════════ */
const LCList = () => {
    const history = useHistory();                        // ← React Router v5

    /* ── Grid / pagination state ────────────────────────────────────── */
    const [rowData,      setRowData]      = useState(null);
    const [total,        setTotal]        = useState(0);
    const [currentPage,  setCurrentPage]  = useState(1);
    const [pageSize,     setPageSize]     = useState(20);
    const [searchQuery,  setSearchQuery]  = useState(null);
    const [filterQuery,  setFilterQuery]  = useState(null);

    /* ── Detail drawer state ────────────────────────────────────────── */
    const [drawerOpen,   setDrawerOpen]   = useState(false);
    const [drawerData,   setDrawerData]   = useState(null);  // full LC record
    const [drawerLoading, setDrawerLoading] = useState(false);

    /* ── Re-fetch whenever page / search / filter changes ───────────── */
    useEffect(() => {
        fetchGridData(currentPage);
    }, [currentPage, searchQuery, filterQuery]);

    /* ── API call ───────────────────────────────────────────────────── */
    const fetchGridData = (pageNo) => {
        let qs = `?page=${pageNo}&pageSize=${pageSize}`;
        if (searchQuery) qs += `&${searchQuery}`;
        if (filterQuery) qs += `&${filterQuery}&filter=1`;

        dataProvider
            .getLCList(LC_API_PATH + qs)
            .then((res) => {
                if (res.ok) {
                    res.json().then((data) => {
                        try { gridApi.hideOverlay(); } catch (_) {}
                        setTotal(data.total);
                        setRowData(data.results);
                    });
                } else {
//                    openNotification("error", "Error", "Failed to load LC requests");
                }
            })
            .catch(() => openNotification("error", "Error", "Error connecting to server"));
    };

    /* ── Open drawer: fetch full detail for clicked row ─────────────── */
    const handleRowClick = (event) => {
        const id = event.data && event.data.id;
        if (!id) return;
        setDrawerOpen(true);
        setDrawerLoading(true);
        setDrawerData(null);

        // GET /lc_request/<id>/ — returns full record including so_details
        dataProvider
            .getLCList(`${LC_API_PATH}${id}/`)
            .then((res) => {
                setDrawerLoading(false);
                if (res.ok) {
                    res.json().then(setDrawerData);
                } else {
                    openNotification("error", "Error", "Could not load LC details");
                    setDrawerOpen(false);
                }
            })
            .catch(() => {
                setDrawerLoading(false);
                openNotification("error", "Error", "Error connecting to server");
                setDrawerOpen(false);
            });
    };

    /* ── Navigate to new form ───────────────────────────────────────── */
    const handleNewButtonClick = () => {
        history.push(route_url.url + "/lc_request/new");  // ← v5 push
    };

    /* ── Pagination / search / filter handlers ──────────────────────── */
    const onPaginationChange = (page, size) => {
        try { gridApi.showLoadingOverlay(); } catch (_) {}
        setPageSize(size);
        setCurrentPage(page || 1);
    };

    const handleSearchApply = (value) => {
        try { gridApi.showLoadingOverlay(); } catch (_) {}
        setSearchQuery(value ? `search=${value}` : null);
        setCurrentPage(1);
    };

    const handleFilterApply = (querystring) => {
        try { gridApi.showLoadingOverlay(); } catch (_) {}
        setFilterQuery(querystring);
        setCurrentPage(1);
    };

    const handleResetFilter = () => {
        try { gridApi.showLoadingOverlay(); } catch (_) {}
        setFilterQuery(null);
        setCurrentPage(1);
    };

    const handleResetSearch = () => {
        try { gridApi.showLoadingOverlay(); } catch (_) {}
        setSearchQuery(null);
    };

    /* ── Helpers for drawer ─────────────────────────────────────────── */
    const fmt = (d) => (d ? new Date(d).toLocaleDateString("en-IN") : "—");

    /* ── RENDER ───────────────────────────────────────────────────────── */
    return (
        <div className="col-md-12">

            {/* ── List header: search / filter / Add button ── */}
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

            {/* ── AG Grid ── */}
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
                                rowData={rowData}
                                pagination={false}
                                onGridReady={onGridReady}
                                onFirstDataRendered={onFirstDataRendered}
                                onRowClicked={handleRowClick}     // ← opens detail drawer
                                rowStyle={{ cursor: "pointer" }}
                            />
                        </div>
                    </div>
                </div>
            </div>

            {/* ── Pagination ── */}
            <ListFooter
                total={total}
                currentPage={currentPage}
                onShowSizeChange={onPaginationChange}
                onPaginationChange={onPaginationChange}
            />

            {/* ════════════════════════════════════════════════════════════
                DETAIL DRAWER
                Opens when the user clicks any row in the grid.
                Loads the full LC record (including so_details child rows)
                from GET /lc_request/<id>/ and renders all sections.
            ════════════════════════════════════════════════════════════ */}
            <Drawer
                title={
                    drawerData ? (
                        <span>
                            LC Request&nbsp;
                            <strong style={{ color: "#b5000a" }}>#{drawerData.id}</strong>
                            &nbsp;&nbsp;
                            <Tag
                                icon={
                                    drawerData.status === "submitted"
                                        ? <CheckCircleOutlined />
                                        : <ClockCircleOutlined />
                                }
                                color={drawerData.status === "submitted" ? "green" : "orange"}
                                style={{ textTransform: "capitalize" }}
                            >
                                {drawerData.status}
                            </Tag>
                        </span>
                    ) : "LC Details"
                }
                width={820}
                open={drawerOpen}
                onClose={() => setDrawerOpen(false)}
                bodyStyle={{ padding: "20px 24px" }}
            >
                {drawerLoading ? (
                    <div style={{ textAlign: "center", paddingTop: "60px" }}>
                        <Spin size="large" />
                        <p style={{ color: "#888", marginTop: 16 }}>Loading LC details…</p>
                    </div>
                ) : drawerData ? (
                    <>
                        {/* ── Audit row ───────────────────────────────── */}
                        <div style={{ fontSize: "12px", color: "#aaa", marginBottom: "20px" }}>
                            Created: {new Date(drawerData.created_date).toLocaleString("en-IN")}
                            &nbsp;|&nbsp;
                            Updated: {new Date(drawerData.updated_date).toLocaleString("en-IN")}
                            &nbsp;|&nbsp;
                            By: {drawerData.created_by || "—"}
                        </div>

                        {/* ══ SECTION A: SO Details ─────────────────── */}
                        <DrawerSection icon={<FileSearchOutlined />} title="SO Details" />
                        {drawerData.so_details && drawerData.so_details.length > 0 ? (
                            <Table
                                size="small"
                                rowKey="id"
                                dataSource={drawerData.so_details}
                                columns={SO_DETAIL_COLUMNS}
                                pagination={false}
                                style={{ borderRadius: "6px", overflow: "hidden", marginBottom: "20px" }}
                            />
                        ) : (
                            <p style={{ color: "#aaa", fontSize: "13px", marginBottom: "20px" }}>
                                No SO rows attached.
                            </p>
                        )}

                        <Divider style={{ margin: "4px 0 20px" }} />

                        {/* ══ SECTION B: Attachment ─────────────────── */}
                        <DrawerSection icon={<PaperClipOutlined />} title="Attachment" />
                        <Row gutter={[24, 0]} style={{ marginBottom: "8px" }}>
                            <Col xs={24} sm={12}>
                                <FieldCell
                                    label="LC Document"
                                    value={
                                        drawerData.attachment ? (
                                            <a
                                                href={drawerData.attachment}
                                                target="_blank"
                                                rel="noreferrer"
                                                style={{ color: "#b5000a", fontWeight: 500 }}
                                            >
                                                <FilePdfOutlined style={{ marginRight: 6 }} />
                                                View / Download PDF
                                            </a>
                                        ) : null
                                    }
                                />
                            </Col>
                            <Col xs={24} sm={12}>
                                <FieldCell
                                    label="PDF Password"
                                    value={drawerData.password ? "••••••••" : "Not set"}
                                />
                            </Col>
                        </Row>

                        <Divider style={{ margin: "4px 0 20px" }} />

                        {/* ══ SECTION C: LC Details (all 23 OCR fields) ═ */}
                        <DrawerSection icon={<RobotOutlined />} title="LC Details" />

                        {/* Instrument info */}
                        <Row gutter={[24, 0]}>
                            <Col xs={24} sm={8}>
                                <FieldCell label="Instrument Number" value={drawerData.instrument_number} />
                            </Col>
                            <Col xs={24} sm={8}>
                                <FieldCell label="Form of Document"  value={drawerData.form_of_doc} />
                            </Col>
                            <Col xs={24} sm={8}>
                                <FieldCell label="Opening Bank"      value={drawerData.opening_bank} />
                            </Col>
                        </Row>

                        {/* Dates & periods */}
                        <Row gutter={[24, 0]}>
                            <Col xs={12} sm={6}>
                                <FieldCell label="Opening Date"       value={fmt(drawerData.opening_date)} />
                            </Col>
                            <Col xs={12} sm={6}>
                                <FieldCell label="Usance Period"      value={drawerData.usance_period != null ? `${drawerData.usance_period} days` : null} />
                            </Col>
                            <Col xs={12} sm={6}>
                                <FieldCell label="Dispatch Upto Date" value={fmt(drawerData.dispatch_upto_date)} />
                            </Col>
                            <Col xs={12} sm={6}>
                                <FieldCell label="Negotiation Days"   value={drawerData.negotiation_days != null ? `${drawerData.negotiation_days} days` : null} />
                            </Col>
                        </Row>

                        {/* Expiry & places */}
                        <Row gutter={[24, 0]}>
                            <Col xs={24} sm={6}>
                                <FieldCell label="Expiry Date"                value={fmt(drawerData.expiry_date)} />
                            </Col>
                            <Col xs={24} sm={9}>
                                <FieldCell label="Place of Taking in Charge"  value={drawerData.place_take_in_charge} />
                            </Col>
                            <Col xs={24} sm={9}>
                                <FieldCell label="Place of Final Destination" value={drawerData.place_of_final_destination} />
                            </Col>
                        </Row>

                        {/* Banks & customer */}
                        <Row gutter={[24, 0]}>
                            <Col xs={24} sm={8}>
                                <FieldCell label="Advising Bank"              value={drawerData.advising_bank} />
                            </Col>
                            <Col xs={24} sm={8}>
                                <FieldCell label="Customer Name"              value={drawerData.customer_name} />
                            </Col>
                            <Col xs={24} sm={8}>
                                <FieldCell label="Customer Name (Inv. Print)" value={drawerData.cust_name_inv_print} />
                            </Col>
                        </Row>

                        {/* Financial */}
                        <Row gutter={[24, 0]}>
                            <Col xs={12} sm={6}>
                                <FieldCell
                                    label="Grace Value"
                                    value={
                                        drawerData.grace_value != null
                                            ? `₹ ${Number(drawerData.grace_value).toLocaleString("en-IN")}`
                                            : null
                                    }
                                />
                            </Col>
                            <Col xs={12} sm={6}>
                                <FieldCell
                                    label="Credit Amount Tolerance"
                                    value={
                                        drawerData.percentage_credit_amount_tolerance != null
                                            ? `${drawerData.percentage_credit_amount_tolerance}%`
                                            : null
                                    }
                                />
                            </Col>
                            <Col xs={12} sm={6}>
                                <FieldCell label="Incoterm"    value={drawerData.incoterm} />
                            </Col>
                            <Col xs={12} sm={6}>
                                <FieldCell label="IMPS Remark" value={drawerData.imps_remark} />
                            </Col>
                        </Row>

                        {/* ES / ET / ER flags */}
                        <div
                            style={{
                                background: "#fafafa",
                                border: "1px solid #f0f0f0",
                                borderRadius: "8px",
                                padding: "12px 20px",
                                marginBottom: "16px",
                                display: "flex",
                                gap: "36px",
                                flexWrap: "wrap",
                                alignItems: "center",
                            }}
                        >
                            <span style={{ fontSize: "11px", fontWeight: 700, color: "#999", textTransform: "uppercase", letterSpacing: "0.4px" }}>
                                Flags:
                            </span>
                            <BoolFlag label="ES" value={drawerData.es} />
                            <BoolFlag label="ET" value={drawerData.et} />
                            <BoolFlag label="ER" value={drawerData.er} />
                        </div>

                        {/* Text clauses */}
                        <FieldCell label="Clause 45A — Description of Goods / Services" value={drawerData.clause_45a} />
                        <FieldCell label="Additional Conditions (46A)"                   value={drawerData.additional_condition_46a} />
                        <FieldCell label="Clause 78 — Reimbursement Instructions"        value={drawerData.clause_78} />
                    </>
                ) : null}
            </Drawer>

        </div>
    );
};

export default LCList;
