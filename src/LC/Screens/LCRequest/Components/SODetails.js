// LC/Screens/LCRequest/Components/SODetails.js

import React from "react";
import { Form, Input, Button, Table, Tag, Tooltip } from "antd";
import {
    SearchOutlined,
    DeleteOutlined,
    FileTextOutlined,
    InfoCircleOutlined,
} from "@ant-design/icons";

const SODetails = ({ onFetchData, fetchedData, isFetching, onDeleteRow }) => {

    const columns = [
        {
            title: "SO Number",
            dataIndex: "so_number",
            key: "so_number",
            width: 140,
            fixed: "left",
            render: (val) => (
                <span style={{ fontWeight: 600, color: "#b5000a" }}>{val}</span>
            ),
        },
        {
            title: "Company Code",
            dataIndex: "company_code",
            key: "company_code",
            width: 130,
        },
        {
            title: "Plant Code",
            dataIndex: "plant_code",
            key: "plant_code",
            width: 120,
        },
        {
            title: "Customer Code",
            dataIndex: "customer_code",
            key: "customer_code",
            width: 150,
        },
        {
            title: "Ship To Party",
            dataIndex: "ship_to_party",
            key: "ship_to_party",
            width: 140,
        },
        {
            title: "SO Value",
            dataIndex: "so_value",
            key: "so_value",
            width: 130,
            align: "right",
            render: (val) =>
                val != null ? (
                    <span style={{ fontWeight: 600, color: "#1a6b3c" }}>
                        ₹ {Number(val).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </span>
                ) : "—",
        },
        {
            title: "Payment Terms",
            dataIndex: "pyt_terms",
            key: "pyt_terms",
            width: 140,
            render: (val) => val ? <Tag color="blue">{val}</Tag> : "—",
        },
        {
            title: "Special Remark",
            dataIndex: "remarks",
            key: "remarks",
            width: 180,
            render: (val) => val || <span style={{ color: "#bbb" }}>—</span>,
        },
        {
            title: "Cust Ref / PO No",
            dataIndex: "cust_reference",
            key: "cust_reference",
            width: 170,
        },
        {
            title: "Cust Ref Date",
            dataIndex: "cust_reference_date",
            key: "cust_reference_date",
            width: 140,
        },
        {
            title: "Status",
            dataIndex: "status",
            key: "status",
            width: 110,
            render: (val) => {
                const color = val === "ACTIVE" ? "green" : "default";
                return <Tag color={color}>{val || "—"}</Tag>;
            },
        },
        {
            title: "Action",
            key: "action",
            width: 60,
            fixed: "right",
            render: (_, record) => (
                <Tooltip title="Remove this SO">
                    <Button
                        type="text"
                        onClick={() => onDeleteRow(record.so_number)}
                        style={{
                            color: "#ff4d4f",
                            fontWeight: 500,
                            padding: "3 2px",
                        }}
                        size="small"
                    >
                        {<DeleteOutlined />}
                    </Button>
                </Tooltip>
            ),
        },
    ];

    return (
        <div style={{ width: "100%" }}>

            {/* ── Input Row ─────────────────────────────────────────────── */}
            <div
                style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: "12px",
                    alignItems: "flex-end",
                    marginBottom: "16px",
                    background: "#fafafa",
                    border: "1px solid #f0f0f0",
                    borderRadius: "8px",
                    padding: "16px",
                }}
            >
                {/* SO Number Input */}
                <div style={{ flex: "1 1 200px", minWidth: "180px", maxWidth: "260px" }}>
                    <Form.Item
                        name="so_number_input"
                        label={
                            <span style={{ fontWeight: 600, fontSize: "13px" }}>
                                SO Number
                            </span>
                        }
                        // rules={[{ required: true, message: "Please enter SO Number" }]}
                        style={{ marginBottom: 0 }}
                    >
                        <Input
                            placeholder="Enter exact SO Number"
                            style={{ borderRadius: "6px" }}
                            onPressEnter={onFetchData}
                        />
                    </Form.Item>
                </div>

                {/* Fetch Button */}
                <div style={{ display: "flex", alignItems: "flex-end", paddingBottom: "1px" }}>
                    <Button
                        type="primary"
                        icon={<SearchOutlined />}
                        onClick={onFetchData}
                        loading={isFetching}
                        style={{
                            background: "#b5000a",
                            borderColor: "#b5000a",
                            borderRadius: "6px",
                            fontWeight: 600,
                            height: "32px",
                            paddingLeft: "16px",
                            paddingRight: "16px",
                        }}
                    >
                        Fetch
                    </Button>
                </div>

                {/* Divider */}
                <div style={{ width: "1px", height: "32px", background: "#e0e0e0", alignSelf: "flex-end" }} />

                {/* Interest Free Credit Days */}
                <div style={{ flex: "1 1 160px", minWidth: "140px" }}>
                    <Form.Item
                        name="interest_free_credit_days"
                        label={
                            <span style={{ fontWeight: 600, fontSize: "13px" }}>
                                Interest Free Credit Days
                                <Tooltip title="Number of days credit is interest-free">
                                    <InfoCircleOutlined style={{ marginLeft: 4, color: "#999" }} />
                                </Tooltip>
                            </span>
                        }
                        rules={[{ required: true, message: "Required" }]}
                        style={{ marginBottom: 0 }}
                    >
                        <Input
                            placeholder="e.g. 30"
                            type="number"
                            style={{ borderRadius: "6px" }}
                            suffix={<span style={{ color: "#bbb", fontSize: "11px" }}>days</span>}
                        />
                    </Form.Item>
                </div>

                {/* Interest Charges */}
                <div style={{ flex: "1 1 160px", minWidth: "140px" }}>
                    <Form.Item
                        name="interest_charges"
                        label={
                            <span style={{ fontWeight: 600, fontSize: "13px" }}>
                                Interest Charges (%)
                            </span>
                        }
                        rules={[{ required: true, message: "Required" }]}
                        style={{ marginBottom: 0 }}
                    >
                        <Input
                            placeholder="e.g. 8.5"
                            type="number"
                            style={{ borderRadius: "6px" }}
                            suffix={<span style={{ color: "#bbb", fontSize: "11px" }}>%</span>}
                        />
                    </Form.Item>
                </div>

                {/* Usance Period */}
                <div style={{ flex: "1 1 160px", minWidth: "140px" }}>
                    <Form.Item
                        name="usance_period"
                        label={
                            <span style={{ fontWeight: 600, fontSize: "13px" }}>
                                Usance Period (days)
                            </span>
                        }
                        rules={[{ required: true, message: "Required" }]}
                        style={{ marginBottom: 0 }}
                    >
                        <Input
                            placeholder="e.g. 90"
                            type="number"
                            style={{ borderRadius: "6px" }}
                            suffix={<span style={{ color: "#bbb", fontSize: "11px" }}>days</span>}
                        />
                    </Form.Item>
                </div>
            </div>

            {/* ── Results Table ──────────────────────────────────────────── */}
            {fetchedData && fetchedData.length > 0 ? (
                <div>
                    {/* Summary bar */}
                    <div
                        style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            marginBottom: "8px",
                        }}
                    >
                        <span style={{ fontSize: "13px", color: "#555" }}>
                            <FileTextOutlined style={{ marginRight: 6, color: "#b5000a" }} />
                            <strong>{fetchedData.length}</strong> SO{fetchedData.length > 1 ? "s" : ""} added
                        </span>
                        <span style={{ fontSize: "12px", color: "#888" }}>
                            Total SO Value:{" "}
                            <strong style={{ color: "#1a6b3c" }}>
                                ₹{" "}
                                {fetchedData
                                    .reduce((sum, r) => sum + (Number(r.so_value) || 0), 0)
                                    .toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                            </strong>
                        </span>
                    </div>

                    <Table
                        size="small"
                        rowKey="so_number"
                        dataSource={fetchedData}
                        columns={columns}
                        pagination={{ pageSize: 10, size: "small" }}
                        scroll={{ x: 1400 }}
                        style={{ borderRadius: "8px", overflow: "hidden" }}
                        rowClassName={(_, index) =>
                            index % 2 === 0 ? "lc-table-row-even" : "lc-table-row-odd"
                        }
                    />
                </div>
            ) : (
                <div
                    style={{
                        textAlign: "center",
                        padding: "32px 16px",
                        border: "1px dashed #d9d9d9",
                        borderRadius: "8px",
                        color: "#aaa",
                        background: "#fafafa",
                    }}
                >
                    <FileTextOutlined style={{ fontSize: "28px", marginBottom: "8px", display: "block" }} />
                    <span style={{ fontSize: "13px" }}>
                        Enter an SO Number and click <strong>Fetch</strong> to load SO data
                    </span>
                </div>
            )}
        </div>
    );
};

export default SODetails;