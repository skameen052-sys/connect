"""
Full and Final (FnF) Settlement Engine
Calculates complete separation settlement accounts, leave encashment, gratuity,
notice period adjustments, loan recovery, and renders official FnF statement PDFs.
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone, date
import io
from typing import Dict, Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.services.payroll_engine import round_curr
from app.services.payslip_pdf import number_to_words


class FnFEngine:
    """
    Dedicated Full & Final settlement calculator.
    """

    @staticmethod
    def calculate_fnf(
        gross_salary: float,
        basic_salary: float,
        days_worked_in_final_month: float,
        total_days_in_final_month: int = 30,
        accrued_unused_leaves: float = 0.0,
        years_of_service: float = 0.0,
        notice_period_shortfall_days: float = 0.0,
        outstanding_loan_balance: float = 0.0,
        other_additions: float = 0.0,
        other_deductions: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Calculates all line items of the Full & Final settlement statement.
        """
        denominator = total_days_in_final_month or 30
        daily_rate = round_curr(gross_salary / denominator)

        # 1. Earned final month salary
        earned_salary = round_curr(daily_rate * days_worked_in_final_month)

        # 2. Leave Encashment (Earned Leave)
        leave_encashment = round_curr(daily_rate * accrued_unused_leaves) if accrued_unused_leaves > 0 else 0.0

        # 3. Gratuity (Payment of Gratuity Act 1972: 15 * Basic / 26 * Completed Years, eligible if >= 5 years)
        if years_of_service >= 5.0:
            gratuity = round_curr((15.0 * basic_salary / 26.0) * years_of_service)
        else:
            gratuity = 0.0

        total_payable = round_curr(earned_salary + leave_encashment + gratuity + other_additions)

        # Recoveries
        # 4. Notice Period Shortfall Recovery
        notice_recovery = round_curr(daily_rate * notice_period_shortfall_days) if notice_period_shortfall_days > 0 else 0.0

        # 5. Loan Balance Recovery
        loan_recovery = round_curr(outstanding_loan_balance)

        total_recoveries = round_curr(notice_recovery + loan_recovery + other_deductions)

        # Net Settlement Amount
        net_settlement = round_curr(total_payable - total_recoveries)

        return {
            "gross_salary": gross_salary,
            "basic_salary": basic_salary,
            "daily_rate": daily_rate,
            "days_worked_in_final_month": days_worked_in_final_month,
            "total_days_in_final_month": total_days_in_final_month,
            "earned_salary": earned_salary,
            "accrued_unused_leaves": accrued_unused_leaves,
            "leave_encashment": leave_encashment,
            "years_of_service": round(years_of_service, 2),
            "gratuity": gratuity,
            "other_additions": other_additions,
            "total_payable": total_payable,
            "notice_period_shortfall_days": notice_period_shortfall_days,
            "notice_recovery": notice_recovery,
            "outstanding_loan_balance": outstanding_loan_balance,
            "loan_recovery": loan_recovery,
            "other_deductions": other_deductions,
            "total_recoveries": total_recoveries,
            "net_settlement": net_settlement,
        }

    @staticmethod
    def generate_fnf_statement_pdf(
        employee_info: Dict[str, Any],
        settlement_calc: Dict[str, Any],
        resignation_info: Dict[str, Any],
    ) -> bytes:
        """Renders an official Full & Final Settlement Statement PDF."""
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
        c_primary = colors.HexColor("#134e4a")
        c_border = colors.HexColor("#e5e7eb")

        style_company = ParagraphStyle("CHeader", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=c_primary)
        style_title = ParagraphStyle("FTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=c_primary, alignment=2)
        style_body = ParagraphStyle("TBody", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11, textColor=colors.HexColor("#1f2937"))
        style_body_bold = ParagraphStyle("TBodyBold", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=colors.HexColor("#1f2937"))

        story = []

        # 1. Header
        header_data = [
            [
                Paragraph("<b>ARSHITH CONNECT</b><br/><font size=8 color='#6b7280'>Human Capital Management<br/>Full and Final Separation Statement</font>", style_company),
                Paragraph("<b>FULL & FINAL SETTLEMENT</b><br/><font size=8 color='#6b7280'>Status: Approved & Finalized</font>", style_title),
            ]
        ]
        h_table = Table(header_data, colWidths=[330, 190])
        story.append(h_table)
        story.append(HRFlowable(width="100%", thickness=1.5, color=c_primary, spaceBefore=4, spaceAfter=8))

        # 2. Metadata
        emp_name = str(employee_info.get("name") or employee_info.get("full_name") or "Employee")
        emp_id = str(employee_info.get("employee_id") or "EMP-1001")
        lwd = str(resignation_info.get("last_working_date") or date.today().isoformat())
        joining = str(employee_info.get("joining_date") or "2024-01-01")

        meta_data = [
            [Paragraph("<b>Employee Name:</b>", style_body), Paragraph(emp_name, style_body_bold), Paragraph("<b>Employee ID:</b>", style_body), Paragraph(emp_id, style_body_bold)],
            [Paragraph("<b>Date of Joining:</b>", style_body), Paragraph(joining, style_body), Paragraph("<b>Last Working Day:</b>", style_body), Paragraph(lwd, style_body_bold)],
            [Paragraph("<b>Designation:</b>", style_body), Paragraph(str(employee_info.get("designation", "Staff")), style_body), Paragraph("<b>Tenure (Years):</b>", style_body), Paragraph(str(settlement_calc.get("years_of_service", 1.0)), style_body)],
            [Paragraph("<b>Department:</b>", style_body), Paragraph(str(employee_info.get("department", "Operations")), style_body), Paragraph("<b>Settlement Date:</b>", style_body), Paragraph(datetime.now(timezone.utc).strftime("%Y-%m-%d"), style_body)],
        ]
        meta_table = Table(meta_data, colWidths=[110, 150, 120, 140])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9fafb")),
            ("BOX", (0, 0), (-1, -1), 0.5, c_border),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, c_border),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 12))

        # 3. Settlement Breakdown
        tot_pay = settlement_calc.get("total_payable", 0.0)
        tot_rec = settlement_calc.get("total_recoveries", 0.0)
        net_fnf = settlement_calc.get("net_settlement", 0.0)

        breakdown_data = [
            [Paragraph("<b>PAYABLE COMPONENTS</b>", style_body_bold), Paragraph("<b>AMOUNT (₹)</b>", style_body_bold), Paragraph("<b>RECOVERIES / DEDUCTIONS</b>", style_body_bold), Paragraph("<b>AMOUNT (₹)</b>", style_body_bold)],
            [Paragraph(f"Final Month Salary ({settlement_calc.get('days_worked_in_final_month')} days)", style_body), Paragraph(f"₹{settlement_calc.get('earned_salary', 0.0):,.2f}", style_body), Paragraph("Notice Shortfall Recovery", style_body), Paragraph(f"₹{settlement_calc.get('notice_recovery', 0.0):,.2f}", style_body)],
            [Paragraph(f"Leave Encashment ({settlement_calc.get('accrued_unused_leaves')} days)", style_body), Paragraph(f"₹{settlement_calc.get('leave_encashment', 0.0):,.2f}", style_body), Paragraph("Outstanding Loan Balance Recovery", style_body), Paragraph(f"₹{settlement_calc.get('loan_recovery', 0.0):,.2f}", style_body)],
            [Paragraph("Gratuity (Tenure >= 5 Yrs)", style_body), Paragraph(f"₹{settlement_calc.get('gratuity', 0.0):,.2f}", style_body), Paragraph("Other Deductions", style_body), Paragraph(f"₹{settlement_calc.get('other_deductions', 0.0):,.2f}", style_body)],
            [Paragraph("Other Additions / Bonus", style_body), Paragraph(f"₹{settlement_calc.get('other_additions', 0.0):,.2f}", style_body), Paragraph("", style_body), Paragraph("", style_body)],
            [Paragraph("<b>Total Payable Earnings:</b>", style_body_bold), Paragraph(f"<b>₹{tot_pay:,.2f}</b>", style_body_bold), Paragraph("<b>Total Recoveries:</b>", style_body_bold), Paragraph(f"<font color='#dc2626'><b>₹{tot_rec:,.2f}</b></font>", style_body_bold)],
        ]
        b_table = Table(breakdown_data, colWidths=[170, 90, 170, 90])
        b_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("BACKGROUND", (0, 5), (1, 5), colors.HexColor("#f1f5f9")),
            ("BACKGROUND", (2, 5), (3, 5), colors.HexColor("#fee2e2")),
            ("BOX", (0, 0), (-1, -1), 0.5, c_border),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, c_border),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ]))
        story.append(b_table)
        story.append(Spacer(1, 10))

        # 4. Net Settlement Box
        in_words = number_to_words(net_fnf)
        net_box_data = [
            [Paragraph("<b>NET FULL & FINAL SETTLEMENT AMOUNT</b>", ParagraphStyle("NL", parent=styles["Normal"], fontSize=9, leading=11, textColor=colors.HexColor("#ccfbf1"))), Paragraph(f"₹{net_fnf:,.2f}", ParagraphStyle("NV", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=14, leading=16, textColor=colors.white))],
            [Paragraph(f"<b>In Words:</b> {in_words}", ParagraphStyle("NW", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#f0fdf4"))), Paragraph("", style_body)]
        ]
        net_box = Table(net_box_data, colWidths=[360, 160])
        net_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), c_primary),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ]))
        story.append(net_box)
        story.append(Spacer(1, 16))

        # Signatures
        sig_data = [
            [Paragraph("____________________________<br/>Employee Acceptance Signature", style_body), Paragraph("____________________________<br/>Finance Officer Sign-off", style_body), Paragraph("____________________________<br/>HR Authorized Signatory", style_body)]
        ]
        sig_table = Table(sig_data, colWidths=[170, 170, 180])
        sig_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(sig_table)

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
