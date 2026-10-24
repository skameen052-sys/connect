"""
Bank Batch Payment Export Service
Generates standard bank disbursement files (NEFT / RTGS batch CSV) for corporate salary transfers.
"""

import csv
import io
from typing import List, Dict, Any


def generate_bank_payment_csv(payroll_run: Dict[str, Any], details: List[Dict[str, Any]]) -> str:
    """
    Produces a CSV string compliant with standard Indian corporate banking batch upload format:
    Columns: Transaction Type, Beneficiary Account No, Amount, Beneficiary Name, IFSC, Narration, Customer Reference
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Header Row
    writer.writerow([
        "Transaction Type",
        "Beneficiary Account Number",
        "Amount (INR)",
        "Beneficiary Name",
        "IFSC Code",
        "Payment Mode",
        "Narration",
        "Customer Reference Number",
        "Employee ID",
        "Department"
    ])

    month_name = payroll_run.get("month_name") or str(payroll_run.get("month", "Month"))
    year = payroll_run.get("year", 2026)
    narration = f"Salary {month_name} {year}"

    for idx, d in enumerate(details, start=1):
        emp_id = d.get("employee_id", f"EMP-{idx}")
        emp_name = d.get("employee_name", "Employee")
        net_amt = float(d.get("net_salary", 0.0))
        acct = d.get("account_number", "987654321012")
        bank_name = d.get("bank_name", "HDFC")
        ifsc = d.get("ifsc_code", "HDFC0001234")
        dept = d.get("department", "Operations")
        ref_num = f"PAY-{year}{payroll_run.get('month', 1):02d}-{emp_id}"

        # Choose payment mode based on amount: RTGS for >= 200,000, else NEFT
        mode = "RTGS" if net_amt >= 200000.0 else "NEFT"

        writer.writerow([
            "CORPORATE_SALARY",
            acct,
            f"{net_amt:.2f}",
            emp_name,
            ifsc,
            mode,
            narration,
            ref_num,
            emp_id,
            dept
        ])

    return output.getvalue()
