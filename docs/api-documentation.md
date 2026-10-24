# REST API Documentation
## Arshith Connect HRMS & Automated Payroll Management Platform

Base URL: `http://127.0.0.1:8000/api`  
Interactive OpenAPI Swagger Docs: `http://127.0.0.1:8000/docs`

---

## 1. Authentication & Users (`/api/auth`)
- `POST /api/auth/login`: Authenticate email and password; returns JWT token, user claims, and role.
- `POST /api/auth/register`: Public employee registration application.
- `GET /api/auth/me`: Fetch authenticated user profile.
- `POST /api/auth/logout`: Revoke/clear session.
- `POST /api/auth/change-password`: Update account password.

---

## 2. Employees & Hierarchy (`/api/employees`)
- `GET /api/employees`: Paginated employee roster with filtering by department, status, and search query.
- `GET /api/employees/{id}`: Detailed employee profile (restricted financial fields based on caller role).
- `POST /api/employees`: Create new employee profile.
- `PUT /api/employees/{id}`: Update employee demographic and job parameters.
- `PATCH /api/employees/{id}/status`: Activate, deactivate, or terminate employee.
- `GET /api/departments`: List of all organizational departments.
- `POST /api/departments`: Create department.
- `GET /api/designations`: List of job designations.
- `POST /api/designations`: Create designation.

---

## 3. Attendance & Corrections (`/api/attendance`)
- `POST /api/attendance/check-in`: Daily punch in with timestamp, GPS lat/long, and selfie image.
- `POST /api/attendance/check-out`: Daily punch out with duration computation.
- `GET /api/attendance/today`: Authenticated employee's current day punch status.
- `GET /api/attendance/history`: Monthly attendance records for employee.
- `GET /api/attendance/all`: Organization-wide daily attendance dashboard.
- `POST /api/attendance/corrections`: Submit attendance correction request for missing punch.
- `GET /api/attendance/corrections`: List pending correction requests.
- `PATCH /api/attendance/corrections/{id}`: Approve or reject correction.

---

## 4. Leaves & Holidays (`/api/leaves`, `/api/holidays`)
- `GET /api/leaves/balances`: Employee's available and consumed leave quotas (CL, SL, EL).
- `POST /api/leaves/apply`: Submit leave application.
- `GET /api/leaves/my`: History of personal leave applications.
- `GET /api/leaves/admin`: All submitted leave requests for manager/HR review.
- `PATCH /api/leaves/{id}/status`: Approve or reject leave request.
- `GET /api/holidays`: Calendar of corporate observed holidays.

---

## 5. Salary Structures (`/api/salary-structures`)
- `GET /api/salary-structures`: Retrieve all employee salary structures.
- `GET /api/salary-structures/{employee_id}`: Retrieve active structure for an employee.
- `POST /api/salary-structures`: Define or update salary structure (Basic, HRA, Allowances, PF, ESI, PT, TDS).
- `GET /api/salary-structures/{employee_id}/history`: Revision audit history.

---

## 6. Automated Payroll Engine (`/api/payroll`)
- `GET /api/payroll/runs`: List all monthly payroll runs with status and totals.
- `GET /api/payroll/runs/{id}`: Full breakdown of a payroll run including all employee line items.
- `POST /api/payroll/calculate`: Trigger automated attendance-driven calculation for `(month, year)`.
- `POST /api/payroll/runs/{id}/review`: Transition status to `UNDER_REVIEW`.
- `POST /api/payroll/runs/{id}/approve`: Authorized approval transition to `APPROVED`.
- `POST /api/payroll/runs/{id}/finalize`: Lock payroll batch to `FINALIZED` and generate immutable payslips.
- `GET /api/payroll/runs/{id}/exceptions`: Inspect missing punches, unreviewed leaves, and LOP anomalies.

---

## 7. Payslips (`/api/payslips`)
- `GET /api/payslips`: List payslips (Employees see only their own; Admins see all).
- `GET /api/payslips/{id}`: Retrieve payslip metadata and itemized breakdown.
- `GET /api/payslips/{id}/download`: Download high-resolution branded PDF payslip generated via ReportLab.

---

## 8. Salary Payments & Banking (`/api/payments`)
- `GET /api/payments/runs/{run_id}`: List payment disbursement records.
- `POST /api/payments/export-bank-file`: Generate and download CSV bank batch payment file (NEFT/RTGS).
- `POST /api/payments/record-confirmation`: Update payment record with UTR reference, payment date, and status.

---

## 9. Recruitment & Onboarding (`/api/recruitment`)
- `GET /api/recruitment/jobs`: Job openings board.
- `POST /api/recruitment/jobs`: Create job opening.
- `GET /api/recruitment/candidates`: Candidate pipeline list with stage filter.
- `POST /api/recruitment/candidates`: Register candidate application.
- `PATCH /api/recruitment/candidates/{id}/stage`: Transition stage (`Screening`, `Interview`, `Offered`, `Hired`).
- `POST /api/recruitment/candidates/{id}/convert-to-employee`: Seamlessly create employee profile from hired candidate.

---

## 10. Performance Management (`/api/performance`)
- `GET /api/performance/goals`: List performance goals.
- `POST /api/performance/goals`: Create goal with target metrics.
- `GET /api/performance/reviews`: Appraisal review cycles.
- `POST /api/performance/reviews`: Submit performance evaluation with 1-5 rating and increment recommendation.

---

## 11. Loans & Salary Advances (`/api/loans`)
- `GET /api/loans`: List employee loans and advances.
- `POST /api/loans/apply`: Apply for loan or advance.
- `PATCH /api/loans/{id}/status`: Approve or reject loan and generate EMI schedule.
- `GET /api/loans/{id}/schedule`: Repayment installment schedule.

---

## 12. Resignation & Final Settlement (`/api/separation`)
- `GET /api/separation/requests`: Resignation submissions.
- `POST /api/separation/submit`: Submit employee resignation.
- `PATCH /api/separation/{id}/approve`: Approve resignation and set last working date.
- `POST /api/separation/{id}/calculate-fnf`: Run automated Full-and-Final settlement calculation.
- `GET /api/separation/{id}/statement`: Generate and download official FnF statement.

---

## 13. Reports & Audits (`/api/reports`, `/api/audit`)
- `GET /api/reports/payroll-register`: Monthly salary register.
- `GET /api/reports/attendance-summary`: Monthly employee attendance rate.
- `GET /api/reports/statutory-summary`: PF, ESI, and Tax withholding compliance report.
- `GET /api/audit/logs`: Immutable security and operation audit trail.
