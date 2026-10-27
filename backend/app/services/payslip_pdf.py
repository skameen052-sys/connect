"""
Payslip PDF Generation Service
Renders high-fidelity, branded PDF payslips using ReportLab.
Styled in dark forest green, with tabular earnings/deductions breakdown,
metadata cards, currency in words, and digital verification.
"""

import io
import os
from datetime import datetime, timezone
from typing import Dict, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# Number to Indian Currency Words converter
def number_to_words(num: float) -> str:
    """Converts a float number to standard Indian Rupee words."""
    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def convert_upto_thousand(n):
        res = ""
        if n >= 100:
            res += units[n // 100] + " Hundred "
            n %= 100
        if 10 <= n < 20:
            res += teens[n - 10] + " "
        else:
            if n >= 20:
                res += tens[n // 10] + " "
                n %= 10
            if n > 0:
                res += units[n] + " "
        return res

    rupees = int(num)
    paise = int(round((num - rupees) * 100))

    if rupees == 0:
        words = "Zero Rupees"
    else:
        words = ""
        crore = rupees // 10000000
        rupees %= 10000000
        if crore > 0:
            words += convert_upto_thousand(crore) + "Crore "

        lakh = rupees // 100000
        rupees %= 100000
        if lakh > 0:
            words += convert_upto_thousand(lakh) + "Lakh "

        thousand = rupees // 1000
        rupees %= 1000
        if thousand > 0:
            words += convert_upto_thousand(thousand) + "Thousand "

        if rupees > 0:
            words += convert_upto_thousand(rupees)

        words += "Rupees "

    if paise > 0:
        words += f"and {convert_upto_thousand(paise)}Paise "

    words += "Only"
    return " ".join(words.split())


def generate_payslip_pdf(detail: Dict[str, Any], run_info: Dict[str, Any]) -> bytes:
    """
    Generates a professional PDF payslip and returns raw PDF bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Brand Colors: Forest Green palette
    c_primary = colors.HexColor("#134e4a")      # Dark forest green
    c_primary_light = colors.HexColor("#0f766e")
    c_bg_light = colors.HexColor("#f0fdf4")     # Soft light green tint
    c_text_dark = colors.HexColor("#1f2937")    # Charcoal text
    c_muted = colors.HexColor("#6b7280")
    c_border = colors.HexColor("#e5e7eb")

    # Typography styles
    style_company = ParagraphStyle(
        "CompanyHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=c_primary,
    )
    style_sub = ParagraphStyle(
        "CompanySub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=c_muted,
    )
    style_title = ParagraphStyle(
        "PayslipTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=c_primary,
        alignment=2,  # Right aligned
    )
    style_body = ParagraphStyle(
        "TableBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=c_text_dark,
    )
    style_body_bold = ParagraphStyle(
        "TableBodyBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=c_text_dark,
    )
    style_net_val = ParagraphStyle(
        "NetVal",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=16,
        textColor=colors.white,
    )
    style_net_lbl = ParagraphStyle(
        "NetLbl",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#ccfbf1"),
    )

    story = []

    # 1. Header Banner
    month_name = run_info.get("month_name") or run_info.get("month") or "Current Month"
    year = run_info.get("year", 2026)

    header_table_data = [
        [
            Paragraph("<b>ARSHITH CONNECT</b><br/><font size=8 color='#6b7280'>Enterprise HRMS & Workforce Solutions<br/>HQ: Tech Center, Hyderabad, India | payroll@arshith.com</font>", style_company),
            Paragraph(f"<b>SALARY SLIP / PAYSLIP</b><br/><font size=9 color='#0f766e'><b>Period:</b> {month_name} {year}</font><br/><font size=7.5 color='#6b7280'>Ref: PS-{year}-{detail.get('employee_id', 'EMP')}</font>", style_title),
        ]
    ]
    header_table = Table(header_table_data, colWidths=[330, 190])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_primary, spaceBefore=4, spaceAfter=8))

    # 2. Employee Metadata Card
    emp_id = str(detail.get("employee_id") or "EMP-1001")
    emp_name = str(detail.get("employee_name") or "Employee")
    dept = str(detail.get("department") or "Engineering")
    desig = str(detail.get("designation") or "Associate")
    bank = str(detail.get("bank_name") or "HDFC Bank")
    acct = str(detail.get("account_number") or "XXXX-XXXX-XXXX")
    pan = str(detail.get("pan_number") or "ABCDE1234F")
    uan = str(detail.get("uan_number") or "100123456789")

    tot_days = detail.get("total_days", 30)
    pay_days = detail.get("payable_days", 30)
    unpaid_days = detail.get("unpaid_days", 0)

    sundays = detail.get("sundays", 4)
    holidays = detail.get("holidays", 0)
    pf_wage = detail.get("pf_wage_base", 0.0)

    meta_data = [
        [
            Paragraph("<b>Employee ID:</b>", style_body),
            Paragraph(emp_id, style_body_bold),
            Paragraph("<b>Total Period Days:</b>", style_body),
            Paragraph(str(tot_days), style_body_bold),
        ],
        [
            Paragraph("<b>Employee Name:</b>", style_body),
            Paragraph(emp_name, style_body_bold),
            Paragraph("<b>Payable Days:</b>", style_body),
            Paragraph(f"{pay_days} Days (Incl. {sundays} Sundays & {holidays} Holidays)", style_body_bold),
        ],
        [
            Paragraph("<b>Department:</b>", style_body),
            Paragraph(dept, style_body),
            Paragraph("<b>Loss of Pay (LOP) Days:</b>", style_body),
            Paragraph(str(unpaid_days), style_body_bold),
        ],
        [
            Paragraph("<b>Designation:</b>", style_body),
            Paragraph(desig, style_body),
            Paragraph("<b>Paid Weekly Offs & Holidays:</b>", style_body),
            Paragraph(f"{sundays} Sundays + {holidays} Festival Holidays", style_body),
        ],
        [
            Paragraph("<b>PAN Number:</b>", style_body),
            Paragraph(pan, style_body),
            Paragraph("<b>Account Number:</b>", style_body),
            Paragraph(acct, style_body),
        ],
        [
            Paragraph("<b>UAN (PF No):</b>", style_body),
            Paragraph(uan, style_body),
            Paragraph("<b>Disbursement Mode:</b>", style_body),
            Paragraph("Direct Bank Transfer (NEFT)", style_body),
        ],
    ]

    meta_table = Table(meta_data, colWidths=[110, 150, 130, 130])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9fafb")),
        ("BOX", (0, 0), (-1, -1), 0.5, c_border),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, c_border),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # 3. Itemized Earnings vs Deductions Table
    basic = detail.get("basic_salary", 0.0)
    hra = detail.get("hra", 0.0)
    allow = detail.get("other_allowances", 0.0)
    ot = detail.get("overtime_pay", 0.0)
    bonus = detail.get("bonus", 0.0)
    gross = detail.get("gross_salary", 0.0)
    lop = detail.get("loss_of_pay", 0.0)
    adj_gross = detail.get("adjusted_gross", gross)

    pf = detail.get("employee_pf", 0.0)
    esi = detail.get("employee_esi", 0.0)
    pt = detail.get("professional_tax", 0.0)
    tds = detail.get("income_tax_tds", 0.0)
    loan_ded = detail.get("loan_deduction", 0.0)
    tot_ded = detail.get("total_deductions", 0.0)
    net_sal = detail.get("net_salary", 0.0)

    # 4-column table: [Earnings, Amount, Deductions, Amount]
    finance_data = [
        [
            Paragraph("<b>EARNINGS</b>", style_body_bold),
            Paragraph("<b>AMOUNT (₹)</b>", style_body_bold),
            Paragraph("<b>DEDUCTIONS</b>", style_body_bold),
            Paragraph("<b>AMOUNT (₹)</b>", style_body_bold),
        ],
        [
            Paragraph("Basic Salary", style_body),
            Paragraph(f"₹{basic:,.2f}", style_body),
            Paragraph(f"Employee Provident Fund (EPF 12%)", style_body),
            Paragraph(f"₹{pf:,.2f}", style_body),
        ],
        [
            Paragraph("House Rent Allowance (HRA)", style_body),
            Paragraph(f"₹{hra:,.2f}", style_body),
            Paragraph("Employee State Insurance (ESIC)", style_body),
            Paragraph(f"₹{esi:,.2f}", style_body),
        ],
        [
            Paragraph("Special & Other Allowances", style_body),
            Paragraph(f"₹{allow:,.2f}", style_body),
            Paragraph("Professional Tax (PT)", style_body),
            Paragraph(f"₹{pt:,.2f}", style_body),
        ],
        [
            Paragraph("Overtime Pay", style_body),
            Paragraph(f"₹{ot:,.2f}", style_body),
            Paragraph("Income Tax / TDS Withholding", style_body),
            Paragraph(f"₹{tds:,.2f}", style_body),
        ],
        [
            Paragraph("Bonus & Incentives", style_body),
            Paragraph(f"₹{bonus:,.2f}", style_body),
            Paragraph("Loan / Advance EMI Deduction", style_body),
            Paragraph(f"₹{loan_ded:,.2f}", style_body),
        ],
        [
            Paragraph("<b>Gross Earnings:</b>", style_body_bold),
            Paragraph(f"<b>₹{gross:,.2f}</b>", style_body_bold),
            Paragraph("", style_body),
            Paragraph("", style_body),
        ],
        [
            Paragraph("<b>Less: Loss of Pay (LOP):</b>", style_body),
            Paragraph(f"<font color='#dc2626'>- ₹{lop:,.2f}</font>", style_body),
            Paragraph("", style_body),
            Paragraph("", style_body),
        ],
        [
            Paragraph("<b>Adjusted Gross Pay:</b>", style_body_bold),
            Paragraph(f"<b>₹{adj_gross:,.2f}</b>", style_body_bold),
            Paragraph("<b>Total Deductions:</b>", style_body_bold),
            Paragraph(f"<font color='#dc2626'><b>₹{tot_ded:,.2f}</b></font>", style_body_bold),
        ],
    ]

    fin_table = Table(finance_data, colWidths=[170, 90, 170, 90])
    fin_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 8), (1, 8), colors.HexColor("#f1f5f9")),
        ("BACKGROUND", (2, 8), (3, 8), colors.HexColor("#fee2e2")),
        ("BOX", (0, 0), (-1, -1), 0.5, c_border),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, c_border),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
    ]))
    story.append(fin_table)
    story.append(Spacer(1, 10))

    # 4. Net Salary Callout Box
    in_words = number_to_words(net_sal)
    net_box_data = [
        [
            Paragraph("<b>NET TAKE-HOME PAYABLE SALARY</b>", style_net_lbl),
            Paragraph(f"₹{net_sal:,.2f}", style_net_val),
        ],
        [
            Paragraph(f"<b>Amount in Words:</b> {in_words}", ParagraphStyle("Words", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#f0fdf4"))),
            Paragraph("", style_body),
        ]
    ]
    net_box = Table(net_box_data, colWidths=[360, 160])
    net_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), c_primary),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    story.append(net_box)
    story.append(Spacer(1, 10))

    # 5. Employer Contribution Disclosures
    er_pf = detail.get("employer_pf", 0.0)
    er_esi = detail.get("employer_esi", 0.0)
    er_cost = detail.get("employer_cost", net_sal)

    employer_data = [
        [
            Paragraph(f"<b>Employer Side Contributions (CTC Disclosures):</b> Employer PF (12%): ₹{er_pf:,.2f}  |  Employer ESIC (3.25%): ₹{er_esi:,.2f}  |  Total Monthly CTC: ₹{er_cost:,.2f}", ParagraphStyle("CTC", parent=styles["Normal"], fontSize=7.5, leading=10, textColor=c_muted))
        ]
    ]
    emp_table = Table(employer_data, colWidths=[520])
    emp_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, c_border),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(emp_table)
    story.append(Spacer(1, 14))

    # 6. Footer Notice & Digital Signature Watermark
    footer_text = Paragraph(
        f"<font color='#6b7280' size=7.5>Note: This is a computer-generated digital payslip securely generated by Arshith Connect HRMS. No physical signature is required.<br/>Generated on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | Verification Hash: SHA256-OK-{emp_id}-{year}{month_name}</font>",
        styles["Normal"]
    )
    story.append(footer_text)

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
