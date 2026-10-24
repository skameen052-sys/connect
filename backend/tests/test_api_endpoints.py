"""
Integration tests for Arshith Connect HRMS & Payroll REST API endpoints.
Validates login, employee listing, payroll calculation, payslips, and payment workflows.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.anyio
async def test_auth_login_admin():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/auth/admin-login", json={
            "email": "admin@arshith.com",
            "password": "AdminPassword@123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "admin"


@pytest.mark.anyio
async def test_auth_and_payroll_calculate():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Login as Admin
        login_res = await ac.post("/api/auth/admin-login", json={
            "email": "admin@arshith.com",
            "password": "AdminPassword@123",
        })
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Check departments
        dept_res = await ac.get("/api/departments", headers=headers)
        assert dept_res.status_code == 200
        assert len(dept_res.json()) > 0

        # 3. Check designations
        desig_res = await ac.get("/api/designations", headers=headers)
        assert desig_res.status_code == 200

        # 4. Calculate monthly payroll
        calc_res = await ac.post("/api/payroll/calculate", json={
            "month": 10,
            "year": 2026,
            "custom_payroll_days": 30,
            "notes": "Automated verification test run",
        }, headers=headers)
        assert calc_res.status_code in [200, 201]
        calc_data = calc_res.json()
        assert "run" in calc_data
        run_id = calc_data["run"]["id"]

        # 5. Review run
        rev_res = await ac.post(f"/api/payroll/runs/{run_id}/review", json={"notes": "Reviewed OK"}, headers=headers)
        assert rev_res.status_code == 200
        assert rev_res.json()["run"]["status"] == "UNDER_REVIEW"

        # 6. Approve run
        app_res = await ac.post(f"/api/payroll/runs/{run_id}/approve", json={"notes": "Approved OK"}, headers=headers)
        assert app_res.status_code == 200
        assert app_res.json()["run"]["status"] == "APPROVED"

        # 7. Finalize run (generates payslips and payment records)
        fin_res = await ac.post(f"/api/payroll/runs/{run_id}/finalize", json={"notes": "Finalized OK"}, headers=headers)
        assert fin_res.status_code == 200
        assert fin_res.json()["run"]["status"] == "FINALIZED"

        # 8. Check generated payslips
        payslips_res = await ac.get("/api/payslips", headers=headers)
        assert payslips_res.status_code == 200
        payslips = payslips_res.json()
        assert len(payslips) > 0

        # 9. Download PDF for first payslip
        ps_id = payslips[0]["id"]
        dl_res = await ac.get(f"/api/payslips/{ps_id}/download", headers=headers)
        assert dl_res.status_code == 200
        assert dl_res.headers["content-type"] == "application/pdf"
        assert dl_res.content.startswith(b"%PDF")

        # 10. Export bank payment file
        bank_res = await ac.post("/api/payments/export-bank-file", json={"payroll_run_id": run_id}, headers=headers)
        assert bank_res.status_code == 200
        assert "text/csv" in bank_res.headers["content-type"]
        assert "Beneficiary Account Number" in bank_res.text
