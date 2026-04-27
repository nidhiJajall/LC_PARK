// ─────────────────────────────────────────────────────────────────────────────
// LC/Screens/LCRequest/LCRequest.js
//

import React, { useState, useEffect, useRef } from "react";

import {
    Button, Form, Input, Upload, Modal,
    Switch, DatePicker, Row, Col,
    Tag, Spin, Divider,
} from "antd";

import {
    SaveOutlined, FilePdfOutlined, LockOutlined,
    FileSearchOutlined, PaperClipOutlined, RobotOutlined,
    CheckCircleOutlined, SyncOutlined,
} from "@ant-design/icons";

import { useHistory, useParams } from "react-router-dom";
import dayjs from "dayjs";
import customParseFormat from "dayjs/plugin/customParseFormat";

import { openNotification } from "swfrontend/COMS/NotificationMessageMapping";
import { route_url }         from "swfrontend/AppConfigs";
import { BASE_URL }          from "../../../App/Configs/AppConfigs";   // ← for attachment URL fix
import dataProvider          from "../../DataProvider";
import { LC_API_PATH, LC_SO_LOOKUP_API_PATH } from "../../Constants";
import SODetails             from "./Components/SODetails";

// Enable strict custom date parsing
dayjs.extend(customParseFormat);

const sectionStyle = {
    background   : "#ffffff",
    border       : "1px solid #e8e8e8",
    borderRadius : "10px",
    padding      : "20px 24px 12px",
    marginBottom : "16px",
    boxShadow    : "0 1px 4px rgba(0,0,0,0.05)",
};

const sectionHeaderStyle = {
    display        : "flex",
    alignItems     : "center",
    justifyContent : "space-between",
    fontSize       : "14px",
    fontWeight     : 700,
    color          : "#b5000a",
    marginBottom   : "16px",
    paddingBottom  : "10px",
    borderBottom   : "2px solid #f5f5f5",
    textTransform  : "uppercase",
    letterSpacing  : "0.5px",
};

const SectionHeader = ({ icon, title, extra }) => (
    <div style={sectionHeaderStyle}>
        <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "16px" }}>{icon}</span>
            {title}
        </span>
        {extra && <span>{extra}</span>}
    </div>
);

const Lbl = ({ text }) => (
    <span style={{ fontWeight: 600, fontSize: "13px" }}>{text}</span>
);

const SubHeading = ({ text }) => (
    <div style={{
        fontSize     : "11px",
        fontWeight   : 700,
        color        : "#888",
        textTransform: "uppercase",
        letterSpacing: "0.6px",
        marginBottom : "10px",
        marginTop    : "4px",
    }}>
        {text}
    </div>
);

const OCR_API_URL = "/lcpark/lc_request/ocr/";
const OCR_PROJECT    = "LC PARK & ENTRY";
const DATE_FIELDS    = ["opening_date", "dispatch_upto_date", "expiry_date"];

// ─────────────────────────────────────────────────────────────────────────────
// Helper: safely parse a date string to a dayjs object (strict mode)
// ─────────────────────────────────────────────────────────────────────────────
const safeParseDateOCR = (val) => {
    // OCR format: DD.MM.YYYY
    if (!val || val === "Invalid Date" || val === "null" || val === "undefined" || val === "") {
        return null;
    }
    const d = dayjs(val, "DD.MM.YYYY", true); // strict=true
    return d.isValid() ? d : null;
};

const safeParseDateISO = (val) => {
    // Backend format: YYYY-MM-DD
    if (!val || val === "Invalid Date" || val === "null" || val === "undefined" || val === "") {
        return null;
    }
    const d = dayjs(val, "YYYY-MM-DD", true); // strict=true
    return d.isValid() ? d : null;
};


// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────
const LCRequest = () => {

    const [form] = Form.useForm();
    const history = useHistory();
    const { id } = useParams();
    const isEdit = !!id && id !== "new";
    const editId = isEdit ? id : null;

    const [uploadFileList, setUploadFileList]     = useState([]);
    const [existingAttachment, setExistingAttachment] = useState(null);
    const [showProgress, setShowProgress]         = useState(false);
    const [isFetching, setIsFetching]             = useState(false);
    const [fetchedData, setFetchedData]           = useState([]);
    const [ocrLoading, setOcrLoading]             = useState(false);
    const [ocrLoaded, setOcrLoaded]               = useState(false);
    const [lcDetailsVisible, setLcDetailsVisible] = useState(false);

    // ── PDF preview state ─────────────────────────────────────────────────────
    // Stores a blob: URL created from the uploaded file for the in-page preview
    const [pdfPreviewUrl, setPdfPreviewUrl]       = useState(null);
    const pdfPreviewUrlRef = useRef(null);   // keep ref so we can revoke properly

    // ── Load existing LC data in edit mode ────────────────────────────────────
    useEffect(() => {
        if (!isEdit) return;
        dataProvider.getLCDetail(`${LC_API_PATH}${editId}/`)
            .then((res) => res.json())
            .then((data) => {
                if (data.so_details && data.so_details.length > 0) {
                    setFetchedData(data.so_details);
                }

                const fields = { ...data };

                // Model typo: unance_period → usance_period
                if ("unance_period" in fields) {
                    fields.usance_period = fields.unance_period;
                    delete fields.unance_period;
                }

                // FIX 1: Parse dates with strict ISO format
                DATE_FIELDS.forEach((f) => {
                    fields[f] = safeParseDateISO(fields[f]);
                });

                // Convert "yes"/"no" strings to booleans for Switch
                ["es", "et", "er"].forEach((f) => {
                    fields[f] = fields[f] === "yes";
                });

                form.setFieldsValue(fields);
                setLcDetailsVisible(true);

                // FIX 3: store only the path; prepend BASE_URL when rendering href
                if (data.attachment) {
                    setExistingAttachment(data.attachment);
                }
            })
            .catch(() => {
                openNotification("error", "Error", "Failed to load LC data");
            });
    }, [isEdit, editId]); // eslint-disable-line react-hooks/exhaustive-deps

    // ── OCR call + PDF preview ────────────────────────────────────────────────
    useEffect(() => {
        // ── File added ──
        if (uploadFileList.length > 0 && !ocrLoaded) {
            const file = uploadFileList[0].originFileObj;
            if (!file) return;

            // Create blob URL for inline PDF preview
            const blobUrl = URL.createObjectURL(file);
            pdfPreviewUrlRef.current = blobUrl;
            setPdfPreviewUrl(blobUrl);

            setOcrLoading(true);

            const fd = new FormData();
            fd.append("file",         file);
            fd.append("project_name", OCR_PROJECT);

            fetch(OCR_API_URL, { method: "POST", body: fd })
                .then((res) => {
                    if (!res.ok) throw new Error(`OCR API responded with ${res.status}`);
                    return res.json();
                })
                .then((data) => {
                    const prediction = data.prediction || {};

                    const mapped = {
                        instrument_number   : prediction.Instrument_Number,
                        form_of_doc         : prediction.Form_of_DOC,
                        opening_bank        : prediction.Opening_Bank,
                        advising_bank       : prediction.Advising_Bank,
                        customer_name       : prediction.Customer_Name,
                        cust_name_inv_print : prediction.Cust_Name_Inv_Print,
                        usance_period       : prediction.Unance_Period,
                        negotiation_days    : prediction.Negotiation_Days,
                        place_take_in_charge          : prediction.Place_TakeIn_charge,
                        place_of_final_destination    : prediction.Place_of_Final_Destination,
                        incoterm            : prediction.Incoterm,
                        grace_value         : prediction.Grace_Value,
                        // FIX 2: This is a text field (e.g. "10/10"), not a number
                        percentage_credit_amount_tolerance: prediction.Credit_Tolerance,
                        imps_remark         : prediction["IMPS Remark"],
                        es                  : prediction.ES === "yes",
                        et                  : prediction.ET === "yes",
                        er                  : prediction.ER === "yes",
                        clause_45a          : prediction.Clause_45A,
                        additional_condition_46a : prediction.Additional_Condition_47A,
                        clause_78           : prediction.Clause78,

                        // Dates — raw strings from OCR, parsed below
                        opening_date        : prediction.Opening_Date,
                        expiry_date         : prediction.Expiry_Date,
                        dispatch_upto_date  : prediction.Dispatch_Upto_Date,
                    };

                    // FIX 1: Parse OCR date strings strictly (DD.MM.YYYY)
                    DATE_FIELDS.forEach((field) => {
                        mapped[field] = safeParseDateOCR(mapped[field]);
                    });

                    form.setFieldsValue(mapped);
                    setOcrLoading(false);
                    setOcrLoaded(true);
                    setLcDetailsVisible(true);
                    openNotification("success", "OCR Complete", "LC document parsed successfully.");
                })
                .catch((err) => {
                    setOcrLoading(false);
                    openNotification(
                        "error",
                        "OCR Failed",
                        err.message || "Could not extract data from the PDF. Please fill the fields manually."
                    );
                    // Still show the form so the user can fill manually
                    setLcDetailsVisible(true);
                });
        }

        // FIX 4: File removed — hide form, revoke blob URL, reset all fields
        if (uploadFileList.length === 0) {
            setOcrLoaded(false);
            setLcDetailsVisible(false);   // ← hide the form section
            form.resetFields();           // ← clear ALL previously filled fields

            // Revoke the old blob URL to avoid memory leak
            if (pdfPreviewUrlRef.current) {
                URL.revokeObjectURL(pdfPreviewUrlRef.current);
                pdfPreviewUrlRef.current = null;
            }
            setPdfPreviewUrl(null);
        }
    }, [uploadFileList]); // eslint-disable-line react-hooks/exhaustive-deps

    // ── SO fetch ─────────────────────────────────────────────────────────────
    const handleFetchData = () => {
        const soNumber = form.getFieldValue("so_number_input");

        if (!soNumber || soNumber.trim() === "") {
            openNotification("error", "Error", "Please enter a SO Number first");
            return;
        }

        if (fetchedData.length >= 24) {
            openNotification("warning", "Limit Reached", "A maximum of 24 SOs can be added to one LC Request");
            return;
        }

        const alreadyExists = fetchedData.some((row) => row.so_number === soNumber.trim());
        if (alreadyExists) {
            openNotification("warning", "Duplicate", `SO ${soNumber} is already added`);
            return;
        }

        setIsFetching(true);
        dataProvider
            .getSODetails(
                `${LC_SO_LOOKUP_API_PATH}list?page=1&pageSize=20&so_number=${soNumber.trim()}&filter=1`
            )
            .then((res) => {
                setIsFetching(false);
                if (res.ok) {
                    res.json().then((soData) => {
                        const rows = soData.results || [];
                        if (rows.length === 0) {
                            openNotification("error", "Not Found", `SO Number ${soNumber} not found`);
                            return;
                        }

                        const newRow = rows[0];

                        // Validation: payment term must be EX01
                        const pyt = (newRow.pyt_terms || "").trim().toUpperCase();
                        if (pyt !== "EX01") {
                            openNotification(
                                "error",
                                "Invalid Payment Term",
                                `SO ${soNumber} has payment term "${newRow.pyt_terms || "—"}". Only EX01 is allowed.`
                            );
                            return;
                        }

                        if (fetchedData.length > 0) {
                            const first = fetchedData[0];

                            // Validation: all SOs must share the same customer code
                            if (newRow.customer_code !== first.customer_code) {
                                openNotification(
                                    "error",
                                    "Customer Code Mismatch",
                                    `SO ${soNumber} has customer code "${newRow.customer_code}" but existing SOs have "${first.customer_code}". All SOs must belong to the same customer.`
                                );
                                return;
                            }

                            // ADD-ON 1: PO Number (cust_reference) must match
                            if (newRow.cust_reference !== first.cust_reference) {
                                openNotification(
                                    "error",
                                    "PO Number Mismatch",
                                    `SO ${soNumber} has PO Number "${newRow.cust_reference || "—"}" but existing SOs have "${first.cust_reference || "—"}". All SOs must have the same PO Number.`
                                );
                                return;
                            }

                            // ADD-ON 1: PO Date (cust_reference_date) must match
                            if (newRow.cust_reference_date !== first.cust_reference_date) {
                                openNotification(
                                    "error",
                                    "PO Date Mismatch",
                                    `SO ${soNumber} has PO Date "${newRow.cust_reference_date || "—"}" but existing SOs have "${first.cust_reference_date || "—"}". All SOs must have the same PO Date.`
                                );
                                return;
                            }
                        }

                        setFetchedData((prev) => [...prev, newRow]);
                        form.setFieldsValue({ so_number_input: "" });
                        openNotification("success", "Fetched", `SO ${soNumber} data loaded`);
                    });
                } else {
                    openNotification("error", "Not Found", `SO Number ${soNumber} not found`);
                }
            })
            .catch(() => {
                setIsFetching(false);
                openNotification("error", "Error", "Error connecting to server");
            });
    };

    const handleDeleteRow = (soNumber) => {
        setFetchedData((prev) => prev.filter((row) => row.so_number !== soNumber));
    };

    const handleSyncToSAP = () => {
        Modal.confirm({
            title  : "Sync to SAP",
            content: "Are you sure you want to sync this LC Request to SAP?",
            okText        : "Yes, Sync",
            cancelText    : "Cancel",
            okButtonProps : { style: { background: "#1890ff", borderColor: "#1890ff" } },
            onOk: () => {
                setShowProgress(true);
                dataProvider.syncLCToSAP(`${LC_API_PATH}${editId}/sync_to_sap/`)
                    .then((res) => {
                        setShowProgress(false);
                        if (res.ok) {
                            openNotification("success", "Synced", "LC Request synced to SAP successfully.");
                        } else {
                            res.json().then((err) =>
                                openNotification("error", "Sync Failed", err.message || "Something went wrong")
                            );
                        }
                    })
                    .catch(() => {
                        setShowProgress(false);
                        openNotification("error", "Error", "Error connecting to server");
                    });
            },
        });
    };

    const handleSave = () => {
        form.validateFields()
            .then((values) => submitForm(values, "draft"))
            .catch(() => openNotification("error", "Validation", "Please fill all required fields"));
    };

    const submitForm = (values, status) => {
        setShowProgress(true);
        const fmt = (d) => (d && dayjs.isDayjs(d) ? d.format("YYYY-MM-DD") : "");

        const fd = new FormData();
        fd.append("interest_free_credit_days", values.interest_free_credit_days || "");
        fd.append("interest_charges",          values.interest_charges          || "");
        fd.append("status",   status);
        fd.append("password", values.password || "");
        if (fetchedData.length > 0) {
            fd.append("so_details", JSON.stringify(fetchedData));
        }
        if (uploadFileList.length > 0) {
            fd.append("file", uploadFileList[0].originFileObj);
        }

        fd.append("instrument_number",                  values.instrument_number                   || "");
        fd.append("form_of_doc",                        values.form_of_doc                         || "");
        fd.append("opening_bank",                       values.opening_bank                        || "");
        fd.append("opening_date",                       fmt(values.opening_date));
        fd.append("usance_period",                      values.usance_period                       || "");
        fd.append("dispatch_upto_date",                 fmt(values.dispatch_upto_date));
        fd.append("negotiation_days",                   values.negotiation_days                    || "");
        fd.append("expiry_date",                        fmt(values.expiry_date));
        fd.append("place_take_in_charge",               values.place_take_in_charge                || "");
        fd.append("place_of_final_destination",         values.place_of_final_destination          || "");
        fd.append("advising_bank",                      values.advising_bank                       || "");
        fd.append("es",                                 values.es  ? "yes" : "no");
        fd.append("et",                                 values.et  ? "yes" : "no");
        fd.append("er",                                 values.er  ? "yes" : "no");
        fd.append("grace_value",                        values.grace_value                         || "");
        fd.append("percentage_credit_amount_tolerance", values.percentage_credit_amount_tolerance  || "");
        fd.append("cust_name_inv_print",                values.cust_name_inv_print                 || "");
        fd.append("customer_name",                      values.customer_name                       || "");
        fd.append("clause_45a",                         values.clause_45a                          || "");
        fd.append("incoterm",                           values.incoterm                            || "");
        fd.append("imps_remark",                        values.imps_remark                         || "");
        fd.append("additional_condition_46a",           values.additional_condition_46a            || "");
        fd.append("clause_78",                          values.clause_78                           || "");

        const apiCall = isEdit
            ? dataProvider.updateLCRequest(`${LC_API_PATH}${editId}/`, fd)
            : dataProvider.createLCRequest(LC_API_PATH, fd);

        apiCall
            .then((res) => {
                setShowProgress(false);
                if (res.ok) {
                    openNotification("success", "Success", "LC Request Saved as Draft!");
                    history.push(route_url.url + "/lc_request");
                } else {
                    res.json().then((err) =>
                        openNotification("error", "Error", err.message || "Something went wrong")
                    );
                }
            })
            .catch(() => {
                setShowProgress(false);
                openNotification("error", "Error", "Error connecting to server");
            });
    };

    // ADD-ON 3: Show split layout when PDF is uploaded and OCR completed
    const showSplitLayout = !!pdfPreviewUrl && lcDetailsVisible;

    // ─── LC Details Form Fields (shared between split and normal layout) ──────
    const LCDetailsFormContent = () => (
        <>
            <SubHeading text="Instrument Information" />
            <Row gutter={[16, 0]}>
                <Col xs={24} sm={12} md={8}>
                    <Form.Item name="instrument_number" label={<Lbl text="Instrument Number" />}>
                        <Input placeholder="e.g. LC2024-MUM-00892" style={{ borderRadius: "6px" }} />
                    </Form.Item>
                </Col>
                <Col xs={24} sm={12} md={8}>
                    <Form.Item name="form_of_doc" label={<Lbl text="Form of Document" />}>
                        <Input placeholder="e.g. IRREVOCABLE" style={{ borderRadius: "6px" }} />
                    </Form.Item>
                </Col>
                <Col xs={24} sm={12} md={8}>
                    <Form.Item name="opening_bank" label={<Lbl text="Opening Bank" />}>
                        <Input placeholder="Bank name & branch" style={{ borderRadius: "6px" }} />
                    </Form.Item>
                </Col>
            </Row>

            <Row gutter={[16, 0]}>
                <Col xs={24} sm={12} md={8}>
                    <Form.Item name="advising_bank" label={<Lbl text="Advising Bank" />}>
                        <Input placeholder="Bank name & branch" style={{ borderRadius: "6px" }} />
                    </Form.Item>
                </Col>
                <Col xs={24} sm={12} md={8}>
                    <Form.Item name="customer_name" label={<Lbl text="Customer Name" />}>
                        <Input placeholder="Customer legal name" style={{ borderRadius: "6px" }} />
                    </Form.Item>
                </Col>
                <Col xs={24} sm={12} md={8}>
                    <Form.Item name="cust_name_inv_print" label={<Lbl text="Customer Name (Invoice Print)" />}>
                        <Input placeholder="As printed on invoice" style={{ borderRadius: "6px" }} />
                    </Form.Item>
                </Col>
            </Row>

            <Divider style={{ margin: "4px 0 16px" }} />

            <SubHeading text="Dates & Periods" />
            <Row gutter={[16, 0]}>
                <Col xs={24} sm={12} md={8}>
                    <Form.Item name="opening_date" label={<Lbl text="Opening Date" />}>
                        <DatePicker style={{ width: "100%", borderRadius: "6px" }} format="DD-MM-YYYY" />
                    </Form.Item>
                </Col>
                <Col xs={24} sm={12} md={8}>
                    <Form.Item name="expiry_date" label={<Lbl text="Expiry Date" />}>
                        <DatePicker style={{ width: "100%", borderRadius: "6px" }} format="DD-MM-YYYY" />
                    </Form.Item>
                </Col>
                <Col xs={24} sm={12} md={8}>
                    <Form.Item name="dispatch_upto_date" label={<Lbl text="Dispatch Upto Date" />}>
                        <DatePicker style={{ width: "100%", borderRadius: "6px" }} format="DD-MM-YYYY" />
                    </Form.Item>
                </Col>
            </Row>

            <Row gutter={[16, 0]}>
                <Col xs={24} sm={12} md={8}>
                    <Form.Item name="usance_period" label={<Lbl text="Usance Period" />}>
                        <Input
                            type="number"
                            placeholder="e.g. 90"
                            style={{ borderRadius: "6px" }}
                            suffix={<span style={{ color: "#bbb", fontSize: "11px" }}>days</span>}
                        />
                    </Form.Item>
                </Col>
                <Col xs={24} sm={12} md={8}>
                    <Form.Item name="negotiation_days" label={<Lbl text="Negotiation Days" />}>
                        <Input
                            type="number"
                            placeholder="e.g. 21"
                            style={{ borderRadius: "6px" }}
                            suffix={<span style={{ color: "#bbb", fontSize: "11px" }}>days</span>}
                        />
                    </Form.Item>
                </Col>
                <Col xs={24} sm={12} md={8} />
            </Row>

            <Divider style={{ margin: "4px 0 16px" }} />

            <SubHeading text="Places" />
            <Row gutter={[16, 0]}>
                <Col xs={24} sm={12} md={8}>
                    <Form.Item name="place_take_in_charge" label={<Lbl text="Place of Taking in Charge" />}>
                        <Input placeholder="e.g. NHAVA SHEVA, INDIA" style={{ borderRadius: "6px" }} />
                    </Form.Item>
                </Col>
                <Col xs={24} sm={12} md={8}>
                    <Form.Item name="place_of_final_destination" label={<Lbl text="Place of Final Destination" />}>
                        <Input placeholder="e.g. HAMBURG, GERMANY" style={{ borderRadius: "6px" }} />
                    </Form.Item>
                </Col>
                <Col xs={24} sm={12} md={8}>
                    <Form.Item name="incoterm" label={<Lbl text="Incoterm" />}>
                        <Input placeholder="e.g. CIF HAMBURG" style={{ borderRadius: "6px" }} />
                    </Form.Item>
                </Col>
            </Row>

            <Divider style={{ margin: "4px 0 16px" }} />

            <SubHeading text="Financial" />
            <Row gutter={[16, 0]}>
                <Col xs={24} sm={12} md={8}>
                    <Form.Item name="grace_value" label={<Lbl text="Grace Value (₹)" />}>
                        <Input type="number" placeholder="e.g. 500000" style={{ borderRadius: "6px" }} />
                    </Form.Item>
                </Col>
                <Col xs={24} sm={12} md={8}>
                    {/* FIX 2: Text input — OCR returns values like "10/10", not a plain number */}
                    <Form.Item name="percentage_credit_amount_tolerance" label={<Lbl text="Credit Amount Tolerance" />}>
                        <Input
                            placeholder="e.g. 10/10 or 5"
                            style={{ borderRadius: "6px" }}
                        />
                    </Form.Item>
                </Col>
                <Col xs={24} sm={12} md={8}>
                    <Form.Item name="imps_remark" label={<Lbl text="IMPS Remark" />}>
                        <Input placeholder="IMPS instruction" style={{ borderRadius: "6px" }} />
                    </Form.Item>
                </Col>
            </Row>

            <Divider style={{ margin: "4px 0 16px" }} />

            <SubHeading text="Flags" />
            <Row gutter={[16, 0]}>
                {["es", "et", "er"].map((field) => (
                    <Col xs={8} sm={8} md={8} key={field}>
                        <Form.Item
                            name={field}
                            valuePropName="checked"
                            label={<span style={{ fontWeight: 600, fontSize: "13px" }}>{field.toUpperCase()}</span>}
                        >
                            <Switch checkedChildren="Yes" unCheckedChildren="No" />
                        </Form.Item>
                    </Col>
                ))}
            </Row>

            <Divider style={{ margin: "4px 0 16px" }} />

            <SubHeading text="Clauses" />
            <Form.Item name="clause_45a" label={<Lbl text="Clause 45A — Description of Goods / Services" />}>
                <Input.TextArea rows={3} placeholder="Description of goods / services as per LC clause 45A" style={{ borderRadius: "6px", resize: "vertical" }} />
            </Form.Item>

            <Form.Item name="additional_condition_46a" label={<Lbl text="Additional Conditions (46A)" />}>
                <Input.TextArea rows={4} placeholder="Additional conditions as per LC clause 46A" style={{ borderRadius: "6px", resize: "vertical" }} />
            </Form.Item>

            <Form.Item name="clause_78" label={<Lbl text="Clause 78 — Instructions to Paying / Accepting / Negotiating Bank" />}>
                <Input.TextArea rows={3} placeholder="Reimbursement / payment instructions as per LC clause 78" style={{ borderRadius: "6px", resize: "vertical" }} />
            </Form.Item>
        </>
    );

    return (
        <div style={{ padding: "4px 0" }}>
            <Form
                className="ant-form ant-form-vertical"
                form={form}
                encType="multipart/form-data"
            >

                {/* ── SO Details ───────────────────────────────────────────── */}
                <div style={sectionStyle}>
                    <SectionHeader icon={<FileSearchOutlined />} title="SO Details" />
                    <SODetails
                        onFetchData={handleFetchData}
                        fetchedData={fetchedData}
                        isFetching={isFetching}
                        onDeleteRow={handleDeleteRow}
                    />
                </div>

                {/* ── Attachment ───────────────────────────────────────────── */}
                <div style={sectionStyle}>
                    <SectionHeader icon={<PaperClipOutlined />} title="Attachment" />

                    <Row gutter={[24, 0]}>
                        <Col xs={24} sm={24} md={12}>
                            {isEdit ? (
                                <Form.Item label={<Lbl text="LC Document" />}>
                                    {existingAttachment ? (
                                        // FIX 3: Prepend BASE_URL so the link goes to Django, not React dev server
                                        <a
                                            href={`${BASE_URL}${existingAttachment}`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            style={{
                                                display    : "inline-flex",
                                                alignItems : "center",
                                                gap        : "6px",
                                                color      : "#b5000a",
                                                fontWeight : 500,
                                                fontSize   : "13px",
                                            }}
                                        >
                                            <FilePdfOutlined />
                                            View Attached LC Document
                                        </a>
                                    ) : (
                                        <span style={{ color: "#aaa", fontSize: "13px" }}>No attachment on file</span>
                                    )}
                                </Form.Item>
                            ) : (
                                /* Create mode: full upload. FIX 4: onChange also manages pdfPreviewUrl */
                                <Form.Item
                                    name="file"
                                    label={<Lbl text="Upload LC Document" />}
                                    rules={[{ required: true, message: "Please upload the LC PDF" }]}
                                >
                                    <Upload
                                        accept=".pdf"
                                        maxCount={1}
                                        beforeUpload={() => false}
                                        onChange={({ fileList }) => setUploadFileList(fileList)}
                                        fileList={uploadFileList}
                                    >
                                        <Button
                                            icon={<FilePdfOutlined style={{ color: uploadFileList.length > 0 ? "#bbb" : "#b5000a" }} />}
                                            disabled={uploadFileList.length > 0}
                                            style={{
                                                borderRadius : "6px",
                                                borderStyle  : "dashed",
                                                borderColor  : uploadFileList.length > 0 ? "#d9d9d9" : "#b5000a",
                                                color        : uploadFileList.length > 0 ? "#bbb"    : "#b5000a",
                                                fontWeight   : 500,
                                            }}
                                        >
                                            Upload LC Attachment (.PDF)
                                        </Button>
                                    </Upload>
                                </Form.Item>
                            )}
                        </Col>

                        <Col xs={24} sm={24} md={12}>
                            <Form.Item
                                name="password"
                                label={<Lbl text="PDF Password (if encrypted)" />}
                                tooltip="If your LC document is password-protected, enter the password here so the OCR engine can open it."
                            >
                                <Input.Password
                                    prefix={<LockOutlined style={{ color: uploadFileList.length > 0 ? "#b5000a" : "#bbb" }} />}
                                    placeholder="Enter PDF password"
                                    style={{ borderRadius: "6px" }}
                                    autoComplete="new-password"
                                    disabled={isEdit}
                                />
                            </Form.Item>
                        </Col>
                    </Row>
                </div>

                {/* ── LC Details ───────────────────────────────────────────── */}
                {(uploadFileList.length > 0 || lcDetailsVisible) && (
                    <div style={sectionStyle}>
                        <SectionHeader
                            icon={<RobotOutlined />}
                            title="LC Details"
                            extra={
                                ocrLoading ? (
                                    <span style={{ fontSize: "12px", color: "#888" }}>
                                        <Spin size="small" style={{ marginRight: 6 }} />
                                        Extracting from PDF…
                                    </span>
                                ) : (
                                    <Tag icon={<CheckCircleOutlined />} color="green" style={{ fontSize: "12px" }}>
                                        OCR Extracted — verify &amp; edit if needed
                                    </Tag>
                                )
                            }
                        />

                        {ocrLoading ? (
                            <div style={{
                                textAlign   : "center",
                                padding     : "48px",
                                background  : "#fafafa",
                                borderRadius: "8px",
                                border      : "1px dashed #d9d9d9",
                                color       : "#888",
                            }}>
                                <Spin size="large" />
                                <p style={{ marginTop: 14, fontSize: "13px" }}>
                                    Parsing LC document via OCR…
                                </p>
                            </div>
                        ) : (
                            /* ADD-ON 3: Split layout — PDF on left, form on right */
                            showSplitLayout ? (
                                <Row gutter={[16, 0]}>
                                    {/* Left: PDF Preview */}
                                    <Col xs={24} md={10}>
                                        <div style={{
                                            position   : "sticky",
                                            top        : "12px",
                                            height     : "calc(100vh - 180px)",
                                            minHeight  : "500px",
                                            border     : "1px solid #e8e8e8",
                                            borderRadius: "8px",
                                            overflow   : "hidden",
                                            background : "#f5f5f5",
                                        }}>
                                            <div style={{
                                                background  : "#b5000a",
                                                color       : "#fff",
                                                padding     : "8px 14px",
                                                fontSize    : "12px",
                                                fontWeight  : 600,
                                                display     : "flex",
                                                alignItems  : "center",
                                                gap         : "6px",
                                            }}>
                                                <FilePdfOutlined />
                                                PDF Preview
                                            </div>
                                            <iframe
                                                src={pdfPreviewUrl}
                                                title="LC Document Preview"
                                                style={{
                                                    width : "100%",
                                                    height: "calc(100% - 36px)",
                                                    border: "none",
                                                }}
                                            />
                                        </div>
                                    </Col>

                                    {/* Right: Form fields */}
                                    <Col xs={24} md={14}>
                                        <div style={{ overflowY: "auto", maxHeight: "calc(100vh - 180px)" }}>
                                            <LCDetailsFormContent />
                                        </div>
                                    </Col>
                                </Row>
                            ) : (
                                <LCDetailsFormContent />
                            )
                        )}
                    </div>
                )}

                {/* ── Action Buttons — ADD-ON 4: Submit button removed ──── */}
                <div style={{
                    display       : "flex",
                    justifyContent: "flex-end",
                    alignItems    : "center",
                    gap           : "10px",
                    padding       : "12px 4px",
                }}>
                    <span style={{ color: "#aaa", fontSize: "12px", marginRight: "6px" }}>
                        ⚠ Verify SO data and LC details before saving
                    </span>

                    {isEdit && (
                        <Button
                            icon={<SyncOutlined />}
                            onClick={handleSyncToSAP}
                            loading={showProgress}
                            style={{
                                background  : "#1890ff",
                                borderColor : "#1890ff",
                                color       : "#fff",
                                fontWeight  : 600,
                                borderRadius: "6px",
                                height      : "36px",
                                paddingLeft : "18px",
                                paddingRight: "18px",
                            }}
                        >
                            Sync to SAP
                        </Button>
                    )}

                    <Button
                        icon={<SaveOutlined />}
                        onClick={handleSave}
                        loading={showProgress}
                        style={{
                            background  : "#e67e00",
                            borderColor : "#e67e00",
                            color       : "#fff",
                            fontWeight  : 600,
                            borderRadius: "6px",
                            height      : "36px",
                            paddingLeft : "18px",
                            paddingRight: "18px",
                        }}
                    >
                        Save Draft
                    </Button>
                    {/* Submit button removed per ADD-ON 4 */}
                </div>

            </Form>
        </div>
    );
};

export default LCRequest;