// LC/Screens/LCRequest/LCRequest.js

import React, { useState } from "react";
import { Button, Form, Input, Upload, Modal, Divider } from "antd";
import {
    UploadOutlined,
    SaveOutlined,
    SendOutlined,
    FilePdfOutlined,
    LockOutlined,
    FileSearchOutlined,
    PaperClipOutlined,
    MailOutlined,
} from "@ant-design/icons";
import { openNotification } from "swfrontend/COMS/NotificationMessageMapping";
import { route_url } from "swfrontend/AppConfigs";
import dataProvider from "../../DataProvider";
import { LC_API_PATH, LC_SO_LOOKUP_API_PATH } from "../../Constants";
import SODetails from "./Components/SODetails";

/* ─── Inline styles reused across sections ─────────────────────────── */
const sectionStyle = {
    background: "#ffffff",
    border: "1px solid #e8e8e8",
    borderRadius: "10px",
    padding: "20px 24px 8px",
    marginBottom: "16px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.05)",
};

const sectionHeaderStyle = {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    fontSize: "14px",
    fontWeight: 700,
    color: "#b5000a",
    marginBottom: "16px",
    paddingBottom: "10px",
    borderBottom: "2px solid #f5f5f5",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
};

const SectionHeader = ({ icon, title }) => (
    <div style={sectionHeaderStyle}>
        <span style={{ fontSize: "16px" }}>{icon}</span>
        {title}
    </div>
);

/* ─────────────────────────────────────────────────────────────────────── */

const LCRequest = ({ history }) => {
    const [form] = Form.useForm();

    const [state, setState] = useState({
        uploadFileList: [],
        showProgress: false,
        isFetching: false,
        fetchedData: [],
    });

    // ── FETCH SO DATA ──────────────────────────────────────────────────────
    const handleFetchData = () => {
        const soNumber = form.getFieldValue("so_number_input");

        if (!soNumber || soNumber.trim() === "") {
            openNotification("error", "Error", "Please enter a SO Number first");
            return;
        }

        const alreadyExists = state.fetchedData.some(
            (row) => row.so_number === soNumber.trim()
        );
        if (alreadyExists) {
            openNotification("warning", "Duplicate", `SO ${soNumber} is already added`);
            return;
        }

        setState((prev) => ({ ...prev, isFetching: true }));

        dataProvider
            .getSODetails(
                `${LC_SO_LOOKUP_API_PATH}list?page=1&pageSize=20&so_number=${soNumber.trim()}&filter=1`
            )
            .then((res) => {
                setState((prev) => ({ ...prev, isFetching: false }));
                if (res.ok) {
                    res.json().then((soData) => {
                        const rows = soData.results || [];
                        if (rows.length === 0) {
                            openNotification("error", "Not Found", `SO Number ${soNumber} not found`);
                            return;
                        }
                        setState((prev) => ({
                            ...prev,
                            fetchedData: [...prev.fetchedData, rows[0]],
                        }));
                        form.setFieldsValue({ so_number_input: "" });
                        openNotification("success", "Fetched", `SO ${soNumber} data loaded`);
                    });
                } else {
                    openNotification("error", "Not Found", `SO Number ${soNumber} not found`);
                }
            })
            .catch(() => {
                setState((prev) => ({ ...prev, isFetching: false }));
                openNotification("error", "Error", "Error connecting to server");
            });
    };

    // ── SAVE (DRAFT) ───────────────────────────────────────────────────────
    const handleSave = () => {
        form.validateFields()
            .then((values) => submitForm(values, "draft"))
            .catch(() => {
                openNotification("error", "Validation", "Please fill all required fields");
            });
    };

    // ── SUBMIT ─────────────────────────────────────────────────────────────
    const handleSubmit = () => {
        form.validateFields()
            .then((values) => {
                Modal.confirm({
                    title: "Confirm Submission",
                    content: (
                        <div>
                            <p style={{ marginBottom: 4 }}>
                                Please verify SO Data as per LC before submitting.
                            </p>
                            <p style={{ color: "#888", fontSize: "13px" }}>
                                This action cannot be undone once submitted.
                            </p>
                        </div>
                    ),
                    okText: "Yes, Submit",
                    cancelText: "Cancel",
                    okButtonProps: {
                        style: { background: "#1a6b3c", borderColor: "#1a6b3c" },
                    },
                    onOk: () => submitForm(values, "submitted"),
                });
            })
            .catch(() => {
                openNotification("error", "Validation", "Please fill all required fields");
            });
    };

    const handleDeleteRow = (soNumber) => {
        setState((prev) => ({
            ...prev,
            fetchedData: prev.fetchedData.filter((row) => row.so_number !== soNumber),
        }));
    };

    // ── BUILD FORM DATA AND POST ───────────────────────────────────────────
    const submitForm = (values, status) => {
        setState((prev) => ({ ...prev, showProgress: true }));

        const formData = new FormData();
        formData.append("status", status);
        formData.append("interest_free_credit_days", values.interest_free_credit_days || "");
        formData.append("interest_charges",          values.interest_charges          || "");
        formData.append("usance_period",             values.usance_period             || "");
        formData.append("password",                  values.password                  || "");
        formData.append("email_recipients",          values.email_recipients          || "");

        if (state.fetchedData.length > 0) {
            formData.append("so_details", JSON.stringify(state.fetchedData));
        }

        if (state.uploadFileList.length > 0) {
            formData.append("attachment", state.uploadFileList[0].originFileObj);
        }

        dataProvider
            .createLCRequest(LC_API_PATH, formData)
            .then((res) => {
                setState((prev) => ({ ...prev, showProgress: false }));
                if (res.ok) {
                    openNotification(
                        "success",
                        "Success",
                        status === "submitted"
                            ? "LC Request Submitted Successfully!"
                            : "LC Request Saved as Draft!"
                    );
                    history.push(route_url.url + "/lc_request");
                } else {
                    res.json().then((err) => {
                        openNotification("error", "Error", err.message || "Something went wrong");
                    });
                }
            })
            .catch(() => {
                setState((prev) => ({ ...prev, showProgress: false }));
                openNotification("error", "Error", "Error connecting to server");
            });
    };

    /* ── RENDER ─────────────────────────────────────────────────────────── */
    return (
        <div style={{ padding: "4px 0" }}>
            <Form
                className="ant-form ant-form-vertical"
                form={form}
                encType="multipart/form-data"
            >

                {/* ── SECTION 1: SO Details ──────────────────────────────── */}
                <div style={sectionStyle}>
                    <SectionHeader
                        icon={<FileSearchOutlined />}
                        title="SO Details"
                    />
                    <SODetails
                        onFetchData={handleFetchData}
                        fetchedData={state.fetchedData}
                        isFetching={state.isFetching}
                        onDeleteRow={handleDeleteRow}
                    />
                </div>

                {/* ── SECTION 2: Attachment + Password ──────────────────── */}
                <div style={sectionStyle}>
                    <SectionHeader
                        icon={<PaperClipOutlined />}
                        title="Attachment"
                    />

                    <div style={{ display: "flex", flexWrap: "wrap", gap: "24px" }}>
                        {/* Upload */}
                        <div style={{ flex: "1 1 280px", minWidth: "240px", maxWidth: "400px" }}>
                            <Form.Item
                                name="attachment"
                                label={
                                    <span style={{ fontWeight: 600, fontSize: "13px" }}>
                                        Upload LC Document
                                    </span>
                                }
                                rules={[{ required: true, message: "Please upload LC PDF" }]}
                            >
                                <Upload
                                    accept=".pdf"
                                    maxCount={1}
                                    beforeUpload={() => false}
                                    onChange={({ fileList }) =>
                                        setState((prev) => ({ ...prev, uploadFileList: fileList }))
                                    }
                                    fileList={state.uploadFileList}
                                >
                                    <Button
                                        icon={<FilePdfOutlined style={{ color: "#b5000a" }} />}
                                        style={{
                                            borderRadius: "6px",
                                            borderStyle: "dashed",
                                            borderColor: "#b5000a",
                                            color: "#b5000a",
                                            fontWeight: 500,
                                        }}
                                    >
                                        Upload Attachment.PDF
                                    </Button>
                                </Upload>
                            </Form.Item>
                        </div>

                        {/* Password */}
                        {/* Password Field */}
                        <div style={{ flex: "1 1 280px", minWidth: "240px", maxWidth: "400px" }}>
                            <Form.Item
                                name="password"
                                label={
                                    <span style={{ fontWeight: 600, fontSize: "13px" }}>
                                        PDF Password
                                    </span>
                                }
                                // Optional: Add a tooltip to explain why this is here
                                tooltip="If your LC document is encrypted, please provide the password here."
                            >
                                <Input.Password
                                    prefix={<LockOutlined style={{ color: state.uploadFileList.length > 0 ? "#b5000a" : "#bbb" }} />}
                                    placeholder="Enter PDF password"
                                    style={{ borderRadius: "6px" }}
                                    autoComplete="new-password" // Prevents browser autofill interference
                                />
                            </Form.Item>
                        </div>

                    </div>
                </div>

                {/* ── ACTION BUTTONS ────────────────────────────────────── */}
                <div
                    style={{
                        display: "flex",
                        justifyContent: "flex-end",
                        alignItems: "center",
                        gap: "10px",
                        padding: "12px 4px",
                    }}
                >
                    <span style={{ color: "#aaa", fontSize: "12px", marginRight: "6px" }}>
                        ⚠ Verify SO data against LC before submitting
                    </span>

                    <Button
                        icon={<SaveOutlined />}
                        onClick={handleSave}
                        loading={state.showProgress}
                        style={{
                            background: "#e67e00",
                            borderColor: "#e67e00",
                            color: "#fff",
                            fontWeight: 600,
                            borderRadius: "6px",
                            height: "36px",
                            paddingLeft: "18px",
                            paddingRight: "18px",
                        }}
                    >
                        Save Draft
                    </Button>

                    <Button
                        icon={<SendOutlined />}
                        onClick={handleSubmit}
                        loading={state.showProgress}
                        style={{
                            background: "#1a6b3c",
                            borderColor: "#1a6b3c",
                            color: "#fff",
                            fontWeight: 600,
                            borderRadius: "6px",
                            height: "36px",
                            paddingLeft: "18px",
                            paddingRight: "18px",
                        }}
                    >
                        Submit
                    </Button>
                </div>

            </Form>
        </div>
    );
};

export default LCRequest;