// LC/Screens/LCRequest/Components/SOAutoCapture.js
// ─────────────────────────────────────────────────────────────────────────────
// Read-only fields that get auto-filled when SO Number is entered.
// User CANNOT type here — data comes from SO lookup API via parent (LCRequest.js)
// Parent calls form.setFieldsValue() to populate these fields automatically.
// ─────────────────────────────────────────────────────────────────────────────

import React from "react";
import { Form, Input } from "antd";

const SOAutoCapture = () => {
    return (
        <div className="col-lg-12 col-md-12">
            <div className="row">

                <div className="col-lg-3 col-md-12">
                    <Form.Item name="company_code" label="Company Code">
                        <Input placeholder="Auto Capture from SO" disabled />
                    </Form.Item>
                </div>

                <div className="col-lg-3 col-md-12">
                    <Form.Item name="plant_code" label="Plant Code">
                        <Input placeholder="Auto Capture from SO" disabled />
                    </Form.Item>
                </div>

                <div className="col-lg-3 col-md-12">
                    <Form.Item name="customer_code" label="Customer Code">
                        <Input placeholder="Auto Capture from SO" disabled />
                    </Form.Item>
                </div>

                <div className="col-lg-3 col-md-12">
                    <Form.Item name="ship_to_party" label="Ship To Party">
                        <Input placeholder="Auto Capture from SO" disabled />
                    </Form.Item>
                </div>

                <div className="col-lg-3 col-md-12">
                    <Form.Item name="so_value" label="SO Value">
                        <Input placeholder="Auto Capture from SO" disabled />
                    </Form.Item>
                </div>

                <div className="col-lg-3 col-md-12">
                    <Form.Item name="payment_terms" label="Payment Terms">
                        <Input placeholder="Auto Capture from SO" disabled />
                    </Form.Item>
                </div>

                <div className="col-lg-3 col-md-12">
                    <Form.Item name="special_remark" label="Special Remark - Sales Contract">
                        <Input placeholder="Auto Capture from SO" disabled />
                    </Form.Item>
                </div>

                <div className="col-lg-3 col-md-12">
                    <Form.Item name="cust_ref_po_number" label="Cust. Reference / PO Number">
                        <Input placeholder="Auto Capture from SO" disabled />
                    </Form.Item>
                </div>

                <div className="col-lg-3 col-md-12">
                    <Form.Item name="cust_ref_po_date" label="Cust. Ref. Date / PO Date">
                        <Input placeholder="Auto Capture from SO" disabled />
                    </Form.Item>
                </div>

            </div>
        </div>
    );
};

export default SOAutoCapture;
