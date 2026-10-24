"""
Unit Tests for Payroll Calculation Engine
Validates calculations against the canonical PDF benchmark and rules:
1. Basic 20,000 + HRA 8,000 + Other 4,000 = Gross 32,000
2. 30 payroll days, 28 payable days, 2 unpaid absence days
3. LOP = (32,000 / 30) * 2 = 2,133.33
4. Adjusted Gross = 32,000 - 2,133.33 = 29,866.67
5. Illustrative PF Wage = 18,000; Employee PF (12%) = 2,160.00
6. Net Salary Before Other Deductions = 27,706.67
"""

import pytest
from app.services.payroll_engine import PayrollEngine, round_curr
from app.services.payslip_pdf import generate_payslip_pdf, number_to_words


def test_pdf_canonical_payroll_calculation():
    """Verify exact numerical results from PDF Page 8 & 9."""
    salary_structure = {
        "basic_salary": 20000.0,
        "hra": 8000.0,
        "other_allowances": 4000.0,
        "pf_applicable": True,
        "pf_wage_base": 18000.0,
        "esi_applicable": False,
        "professional_tax": 0.0,
        "tds_monthly": 0.0,
    }

    result = PayrollEngine.calculate_employee_payroll(
        salary_structure=salary_structure,
        total_period_days=30,
        payable_days=28,
        custom_pf_wage_base=18000.0,
        custom_daily_rate_denominator=30,
    )

    # 1. Gross Salary
    assert result["gross_salary"] == 32000.00, f"Expected 32000, got {result['gross_salary']}"

    # 2. Unpaid days
    assert result["unpaid_days"] == 2.0

    # 3. Loss of Pay (LOP) = 32000 / 30 * 2 = 2133.33
    assert result["loss_of_pay"] == 2133.33, f"Expected 2133.33, got {result['loss_of_pay']}"

    # 4. Adjusted Gross Earnings = 32000 - 2133.33 = 29866.67
    assert result["adjusted_gross"] == 29866.67, f"Expected 29866.67, got {result['adjusted_gross']}"

    # 5. Employee PF Deduction = 18000 * 12% = 2160.00
    assert result["employee_pf"] == 2160.00, f"Expected 2160.00, got {result['employee_pf']}"

    # 6. Net Take-Home Salary = 29866.67 - 2160.00 = 27706.67
    assert result["net_salary"] == 27706.67, f"Expected 27706.67, got {result['net_salary']}"

    # 7. Employer PF (recorded as employer cost, NOT subtracted again from net salary)
    assert result["employer_pf"] == 2160.00
    assert result["employer_cost"] == round_curr(29866.67 + 2160.00)


def test_payslip_pdf_generation():
    """Verify PDF generates valid bytes and header signature."""
    sample_detail = {
        "employee_id": "EMP-1001",
        "employee_name": "Arshith Developer",
        "department": "Engineering",
        "designation": "Full-Stack Engineer",
        "basic_salary": 20000.0,
        "hra": 8000.0,
        "other_allowances": 4000.0,
        "gross_salary": 32000.0,
        "total_days": 30,
        "payable_days": 28,
        "unpaid_days": 2,
        "loss_of_pay": 2133.33,
        "adjusted_gross": 29866.67,
        "employee_pf": 2160.0,
        "employee_esi": 0.0,
        "professional_tax": 200.0,
        "income_tax_tds": 0.0,
        "loan_deduction": 0.0,
        "total_deductions": 2360.0,
        "net_salary": 27506.67,
        "employer_pf": 2160.0,
        "employer_esi": 0.0,
        "employer_cost": 32026.67,
    }

    sample_run = {
        "month": 10,
        "month_name": "October",
        "year": 2026,
    }

    pdf_bytes = generate_payslip_pdf(sample_detail, sample_run)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    # PDF magic byte header check: %PDF
    assert pdf_bytes.startswith(b"%PDF")


def test_number_to_words_conversion():
    """Verify Indian currency words generation."""
    words = number_to_words(27706.67)
    assert "Twenty Seven Thousand Seven Hundred Six Rupees and Sixty Seven Paise Only" == words or "Twenty Seven Thousand Seven Hundred Six Rupees" in words
