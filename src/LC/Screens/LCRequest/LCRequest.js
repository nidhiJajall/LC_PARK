// ─────────────────────────────────────────────────────────────────────────────
// LC/Screens/LCRequest/LCRequest.js
//

import React, { useState, useEffect } from "react";

import {
    Button, Form, Input, Upload, Modal,
    Switch, DatePicker, Row, Col,
    Tag, Spin, Divider,
} from "antd";

import {
    SaveOutlined, SendOutlined, FilePdfOutlined, LockOutlined,
    FileSearchOutlined, PaperClipOutlined, RobotOutlined,
    CheckCircleOutlined, InboxOutlined,
} from "@ant-design/icons";

import { useHistory } from "react-router-dom";
import dayjs from "dayjs";

import { openNotification } from "swfrontend/COMS/NotificationMessageMapping";
import { route_url }         from "swfrontend/AppConfigs";
import dataProvider          from "../../DataProvider";
import { LC_API_PATH, LC_SO_LOOKUP_API_PATH } from "../../Constants";
import SODetails             from "./Components/SODetails";

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


// Section card header — icon on the left, optional badge/tag on the right
const SectionHeader = ({ icon, title, extra }) => (
    <div style={sectionHeaderStyle}>
        <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "16px" }}>{icon}</span>
            {title}
        </span>
        {/* extra is optional — only rendered when passed in */}
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

const OCR_API_URL = "/testproject/lc_request/ocr/";
const OCR_PROJECT    = "LC PARK & ENTRY";
const DATE_FIELDS    = ["opening_date", "dispatch_upto_date", "expiry_date"];


// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────
const LCRequest = () => {

    const [form] = Form.useForm();
    const history = useHistory();

    const [uploadFileList, setUploadFileList] = useState([]);
    const [showProgress, setShowProgress] = useState(false);
    const [isFetching, setIsFetching] = useState(false);
    const [fetchedData, setFetchedData] = useState([]);
    const [ocrLoading, setOcrLoading] = useState(false);
    const [ocrLoaded, setOcrLoaded] = useState(false);

    // ── Real OCR API call ────────────────────────────────────────────────────
    //   Fires as soon as a PDF is added; resets state when the file is removed.
    useEffect(() => {
        if (uploadFileList.length > 0 && !ocrLoaded) {
            const file = uploadFileList[0].originFileObj;
            if (!file) return;

            setOcrLoading(true);

            const fd = new FormData();
            fd.append("file",   file);         // Django reads request.FILES["file"]
            fd.append("project_name", OCR_PROJECT);  // forwarded to OCR API by Django

            // Django's IsAuthenticated requires the token — grab it from wherever
            // your app stores it (localStorage key may differ in your project).
//            const token = localStorage.getItem("token") || "";

            fetch(OCR_API_URL, {
                method : "POST",
//                headers: { "Authorization": `Token ${token}` },  // no Content-Type — browser sets multipart boundary automatically
                body   : fd,
            })
                .then((res) => {
                    if (!res.ok) throw new Error(`OCR API responded with ${res.status}`);
                    return res.json();
                })
                .then((data) => {
                    // Access the 'prediction' object from your API response
                    const prediction = data.prediction || {};

                    // Map API keys to your Ant Design Form field names
                    const mapped = {
                        Instrument_Number: prediction.Instrument_Number,
                        form_of_doc:       prediction.Form_of_DOC, // API has Form_of_DOC
                        opening_bank:      prediction.Opening_Bank,
                        advising_bank:     prediction.Advising_Bank,
                        customer_name:     prediction.Customer_Name,
                        cust_name_inv_print: prediction.Cust_Name_Inv_Print,
                        usance_period:     prediction.Unance_Period, // API has Unance_Period (typo in API?)
                        negotiation_days:  prediction.Negotiation_Days,
                        place_take_in_charge: prediction.Place_TakeIn_charge,
                        place_of_final_destination: prediction.Place_of_Final_Destination,
                        incoterm:          prediction.Incoterm,
                        grace_value:       prediction.Grace_Value,
                        percentage_credit_amount_tolerance: prediction.Credit_Tolerance,
                        imps_remark:       prediction["IMPS Remark"], // API has a space
                        es:                prediction.ES === "yes", // Convert "yes"/"no" to boolean for Switch
                        et:                prediction.ET === "yes",
                        er:                prediction.ER === "yes",
                        clause_45a:        prediction.Clause_45A, // Check if your API provides this
                        additional_condition_46a: prediction.Additional_Condition_47A, // Mapping 47A to your 46A field
                        clause_78:         prediction.Clause78,

                        // Dates (handled specifically below)
                        opening_date:      prediction.Opening_Date,
                        expiry_date:       prediction.Expiry_Date,
                        dispatch_upto_date: prediction.Dispatch_Upto_Date,
                    };

                    // Convert Date strings (DD.MM.YYYY) to dayjs objects
                    DATE_FIELDS.forEach((field) => {
                        if (mapped[field]) {
                            // Note: Your API uses dots (31.03.2026), dayjs parses this well
                            mapped[field] = dayjs(mapped[field], "DD.MM.YYYY");
                        }
                    });

                    form.setFieldsValue(mapped);
                    setOcrLoading(false);
                    setOcrLoaded(true);
                    openNotification("success", "OCR Complete", "LC document parsed successfully.");
                })
                .catch((err) => {
                    setOcrLoading(false);
                    openNotification(
                        "error",
                        "OCR Failed",
                        err.message || "Could not extract data from the PDF. Please fill the fields manually."
                    );
                });
        }
        // If user removes the uploaded file, reset so they can re-upload
        if (uploadFileList.length === 0) {
            setOcrLoaded(false);
            form.resetFields(DATE_FIELDS); // clear any previously filled LC fields
        }
    }, [uploadFileList]);

    const handleFetchData = () => {
        const soNumber = form.getFieldValue("so_number_input");

        if (!soNumber || soNumber.trim() === "") {
            openNotification("error", "Error", "Please enter a SO Number first");
            return;
        }

        // Guard: same SO number should not appear twice in the table
        const alreadyExists = fetchedData.some(
            (row) => row.so_number === soNumber.trim()
        );
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

                        setFetchedData((prev) => [...prev, rows[0]]);
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

    const handleSave = () => {
        form.validateFields()
            .then((values) => submitForm(values, "draft"))
            .catch(() => openNotification("error", "Validation", "Please fill all required fields"));
    };

    const handleSubmit = () => {
        form.validateFields()
            .then((values) => {
                Modal.confirm({
                    title  : "Confirm Submission",
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
                    okText        : "Yes, Submit",
                    cancelText    : "Cancel",
                    okButtonProps : { style: { background: "#1a6b3c", borderColor: "#1a6b3c" } },
                    onOk          : () => submitForm(values, "submitted"),
                });
            })
            .catch(() => openNotification("error", "Validation", "Please fill all required fields"));
    };

    const submitForm = (values, status) => {
        setShowProgress(true);
        const fmt = (d) => (d && dayjs.isDayjs(d) ? d.format("YYYY-MM-DD") : "");

        const fd = new FormData();
        fd.append("status",   status);
        fd.append("password", values.password || "");
        if (fetchedData.length > 0) {
            fd.append("so_details", JSON.stringify(fetchedData));
        }

        if (uploadFileList.length > 0) {
            fd.append("file", uploadFileList[0].originFileObj);
        }

        // ── All 23 LC Detail fields ───────────────────────────────────────
        fd.append("Instrument_Number",                  values.Instrument_Number                   || "");
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

        dataProvider
            .createLCRequest(LC_API_PATH, fd)
            .then((res) => {
                setShowProgress(false);
                if (res.ok) {
                    openNotification(
                        "success", "Success",
                        status === "submitted"
                            ? "LC Request Submitted Successfully!"
                            : "LC Request Saved as Draft!"
                    );
                    history.push(route_url.url + "/lc_request"); // v5 push
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

    return (
        <div style={{ padding: "4px 0" }}>
            <Form
                className="ant-form ant-form-vertical"
                form={form}
                encType="multipart/form-data"
            >

                <div style={sectionStyle}>
                    <SectionHeader icon={<FileSearchOutlined />} title="SO Details" />
                    <SODetails
                        onFetchData={handleFetchData}
                        fetchedData={fetchedData}
                        isFetching={isFetching}
                        onDeleteRow={handleDeleteRow}
                    />
                </div>

                <div style={sectionStyle}>
                    <SectionHeader icon={<PaperClipOutlined />} title="Attachment" />

                    <Row gutter={[24, 0]}>

                        {/* Upload field — col span 12 = half width */}
                        <Col xs={24} sm={24} md={12}>
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
                        </Col>

                        {/* Password field — col span 12 = half width */}
                        <Col xs={24} sm={24} md={12}>
                            <Form.Item
                                name="password"
                                label={<Lbl text="PDF Password (if encrypted)" />}
                                tooltip="If your LC document is password-protected, enter the password here so the OCR engine can open it."
                            >
                                <Input.Password
                                    prefix={
                                        <LockOutlined
                                            style={{
                                                color: uploadFileList.length > 0 ? "#b5000a" : "#bbb",
                                            }}
                                        />
                                    }
                                    placeholder="Enter PDF password"
                                    style={{ borderRadius: "6px" }}
                                    autoComplete="new-password"
                                />
                            </Form.Item>
                        </Col>
                    </Row>
                </div>

                {uploadFileList.length > 0 && (
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
                                    <Tag
                                        icon={<CheckCircleOutlined />}
                                        color="green"
                                        style={{ fontSize: "12px" }}
                                    >
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
                            <>


                                {/* ── GROUP 1: Basic Instrument Info ─────── */}
                                <SubHeading text="Instrument Information" />
                                <Row gutter={[16, 0]}>
                                    <Col xs={24} sm={12} md={8}>
                                        <Form.Item name="Instrument_Number" label={<Lbl text="Instrument Number" />}>
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

                                {/* ── GROUP 2: Dates & Periods ────────────── */}
                                <SubHeading text="Dates & Periods" />
                                <Row gutter={[16, 0]}>
                                    <Col xs={24} sm={12} md={8}>

                                        <Form.Item name="opening_date" label={<Lbl text="Opening Date" />}>
                                            <DatePicker
                                                style={{ width: "100%", borderRadius: "6px" }}
                                                format="DD-MM-YYYY"
                                            />
                                        </Form.Item>
                                    </Col>
                                    <Col xs={24} sm={12} md={8}>
                                        <Form.Item name="expiry_date" label={<Lbl text="Expiry Date" />}>
                                            <DatePicker
                                                style={{ width: "100%", borderRadius: "6px" }}
                                                format="DD-MM-YYYY"
                                            />
                                        </Form.Item>
                                    </Col>
                                    <Col xs={24} sm={12} md={8}>
                                        <Form.Item name="dispatch_upto_date" label={<Lbl text="Dispatch Upto Date" />}>
                                            <DatePicker
                                                style={{ width: "100%", borderRadius: "6px" }}
                                                format="DD-MM-YYYY"
                                            />
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
                                    {/* Third column intentionally empty to keep 3-col rhythm */}
                                    <Col xs={24} sm={12} md={8} />
                                </Row>

                                <Divider style={{ margin: "4px 0 16px" }} />

                                {/* ── GROUP 3: Places ─────────────────────── */}
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

                                {/* ── GROUP 4: Financial ───────────────────── */}
                                <SubHeading text="Financial" />
                                <Row gutter={[16, 0]}>
                                    <Col xs={24} sm={12} md={8}>
                                        <Form.Item name="grace_value" label={<Lbl text="Grace Value (₹)" />}>
                                            <Input
                                                type="number"
                                                placeholder="e.g. 500000"
                                                style={{ borderRadius: "6px" }}
                                            />
                                        </Form.Item>
                                    </Col>
                                    <Col xs={24} sm={12} md={8}>
                                        <Form.Item
                                            name="percentage_credit_amount_tolerance"
                                            label={<Lbl text="Credit Amount Tolerance (%)" />}
                                        >
                                            <Input
                                                type="number"
                                                placeholder="e.g. 10"
                                                style={{ borderRadius: "6px" }}
                                                suffix={<span style={{ color: "#bbb", fontSize: "11px" }}>%</span>}
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
                                                label={
                                                    <span style={{ fontWeight: 600, fontSize: "13px" }}>
                                                        {field.toUpperCase()}
                                                    </span>
                                                }
                                            >
                                                <Switch checkedChildren="Yes" unCheckedChildren="No" />
                                            </Form.Item>
                                        </Col>
                                    ))}
                                </Row>

                                <Divider style={{ margin: "4px 0 16px" }} />

                                <SubHeading text="Clauses" />
                                <Form.Item
                                    name="clause_45a"
                                    label={<Lbl text="Clause 45A — Description of Goods / Services" />}
                                >
                                    <Input.TextArea
                                        rows={3}
                                        placeholder="Description of goods / services as per LC clause 45A"
                                        style={{ borderRadius: "6px", resize: "vertical" }}
                                    />
                                </Form.Item>

                                <Form.Item
                                    name="additional_condition_46a"
                                    label={<Lbl text="Additional Conditions (46A)" />}
                                >
                                    <Input.TextArea
                                        rows={4}
                                        placeholder="Additional conditions as per LC clause 46A"
                                        style={{ borderRadius: "6px", resize: "vertical" }}
                                    />
                                </Form.Item>

                                <Form.Item
                                    name="clause_78"
                                    label={<Lbl text="Clause 78 — Instructions to Paying / Accepting / Negotiating Bank" />}
                                >
                                    <Input.TextArea
                                        rows={3}
                                        placeholder="Reimbursement / payment instructions as per LC clause 78"
                                        style={{ borderRadius: "6px", resize: "vertical" }}
                                    />
                                </Form.Item>
                            </>
                        )}
                    </div>
                )}

                {/* ── Action Buttons ─────────────────────────────────────── */}
                <div style={{
                    display       : "flex",
                    justifyContent: "flex-end",
                    alignItems    : "center",
                    gap           : "10px",
                    padding       : "12px 4px",
                }}>
                    <span style={{ color: "#aaa", fontSize: "12px", marginRight: "6px" }}>
                        ⚠ Verify SO data and LC details before submitting
                    </span>

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

                    <Button
                        icon={<SendOutlined />}
                        onClick={handleSubmit}
                        loading={showProgress}
                        style={{
                            background  : "#1a6b3c",
                            borderColor : "#1a6b3c",
                            color       : "#fff",
                            fontWeight  : 600,
                            borderRadius: "6px",
                            height      : "36px",
                            paddingLeft : "18px",
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