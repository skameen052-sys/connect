# Software Requirements Specification (SRS)
## Employee Management & Automated Payroll Management System (HRMS)

**Version:** 1.0.0  
**Project Name:** Arshith Connect HRMS & Payroll Engine  
**Standard Compliance:** 14-Page System Architecture & Automated Payroll Specification

---

## 1. Project Overview and Objectives
The **Employee Management & Automated Payroll Management System** is a centralized, enterprise-grade web application engineered to unify workforce management, biometric/GPS attendance tracking, leave governance, salary structure configuration, attendance-driven payroll processing, statutory deductions, PDF payslip generation, banking disbursements, and human capital administration.

### Core Objectives:
1. **Unified Enterprise Directory:** Centralized personnel master data with role-governed data protection.
2. **Attendance-Driven Payroll Engine:** Accurate salary calculations powered by daily attendance punches, approved leaves, and loss of pay (LOP) proration rather than static flat monthly estimates.
3. **Multi-Tier Role Governance:** Distinct dashboards and permission controls for Super Admin, HR Administrator, Team Manager, Payroll/Finance Administrator, and Employees.
4. **Statutory Compliance:** Dynamic, configurable statutory calculation rules for Provident Fund (EPF), Employee State Insurance (ESIC), Professional Tax (PT), and Tax Deducted at Source (TDS).
5. **End-to-End Compensation Lifecycle:** Salary structure revisions, monthly payroll runs, PDF payslips, banking export files, salary loans/advances, and Full & Final (FnF) separation settlement.

---

## 2. Employee Registration & Profile Management
- **Unique Employee Identification:** Generation of standardized identifiers (e.g., `EMP-1001`, `EMP-1002`).
- **Comprehensive Demographic Records:** Legal full name, personal contact numbers, corporate email, emergency contacts, profile photo, date of birth, blood group, marital status, and permanent/current address.
- **Employment Hierarchy:** Department association, designation/job position, employment type (`Full-time`, `Contract`, `Probation`, `Intern`), employment status (`Active`, `On Leave`, `Suspended`, `Terminated`), reporting manager, work location, and shift schedule.
- **Confidential Financial Records:** Bank account number, IFSC code, bank name, PAN number, and UAN (PF) number with access restricted to HR, Finance, and the employee themselves.
- **Document Management:** Offer letters, government IDs, educational certificates, appointment letters, and signed NDA contracts stored with private, authenticated access.

---

## 3. Authentication & Role-Based Access Control (RBAC)
The application enforces strict authorization through 5 defined roles:
1. **Super Admin:** Master platform administration, role definitions, company policies, audit trail inspection, system configuration.
2. **HR Administrator:** Workforce onboarding, department/designation administration, leave/attendance approvals, recruitment, performance cycles, separation processing.
3. **Manager / Team Leader:** Team attendance monitoring, leave approvals, performance evaluations, task delegation.
4. **Payroll / Finance Administrator:** Salary structure setup, attendance-driven payroll batch generation, exception review, payroll finalization, payslip generation, bank payment exports, loan management.
5. **Employee:** Self-service portal for clock-in/out, personal attendance calendar, leave requests, reimbursement/loan requests, payslip download, and personal document access.

---

## 4. Attendance Management
- **Clock-In / Clock-Out:** High-precision server timestamps with optional GPS geolocation coordinates and webcam selfie verification.
- **Work Hours & Breaks:** Automatic computation of total work duration, active working hours, breaks, and overtime hours.
- **Daily Attendance Classifications:** `Present`, `Late`, `Half-day`, `Absent`, `Weekly Off`, and `Holiday`.
- **Shift & Policy Enforcement:** Configurable grace periods (e.g., 15 minutes), half-day thresholds, and overtime multiplier rules.
- **Attendance Regularization:** Request-driven correction workflow allowing employees to submit missing-punch explanations for supervisor/HR approval.
- **Monthly Attendance Cutoff:** Freeze attendance periods for monthly payroll calculation.

---

## 5. Leave Management
- **Leave Categorization:** Casual Leave (CL), Sick Leave (SL), Earned/Privilege Leave (EL/PL), and Loss of Pay / Unpaid Leave (LOP).
- **Entitlement & Accrual:** Configurable annual quotas, monthly accrual rules, and carry-forward limits.
- **Application Workflow:** Multi-day or half-day requests, documentation attachment, reason submission, overlapping leave validation, and manager approval/rejection.
- **Payroll Synchronization:** Approved paid leaves are credited as payable days; unapproved absences or unpaid leaves trigger automatic Loss of Pay deductions in the payroll engine.

---

## 6. Salary Structure Management
- **Earnings Components:** Basic Salary, House Rent Allowance (HRA), Special Allowance, Conveyance, Medical, Performance Bonus, Overtime Pay, and Arrears.
- **Deduction Components:** Employee Provident Fund (EPF), Employee State Insurance (ESIC), Professional Tax (PT), Tax Deducted at Source (TDS), Loan EMI repayments, and Other Deductions.
- **Employer Contributions:** Employer PF (12% matching / EPS split) and Employer ESI (3.25%) computed as Cost to Company (CTC) without reducing employee take-home pay.
- **Revision History:** Effective-dated salary revisions preventing retroactive corruption of finalized payroll periods.

---

## 7. Automated Payroll Engine
The dedicated business service layer executes automated attendance-driven payroll calculations:
1. **Gross Salary:** $\text{Basic} + \text{HRA} + \text{Allowances}$
2. **Daily Rate:** $\text{Daily Rate} = \frac{\text{Gross Salary}}{\text{Configured Days Denominator (e.g., 30)}}$
3. **Loss of Pay (LOP):** $\text{LOP Amount} = \text{Daily Rate} \times \text{Unpaid Absence Days}$
4. **Adjusted Gross Earnings:** $\text{Gross Salary} - \text{LOP Amount} + \text{Approved Overtime/Incentives}$
5. **Employee Deductions:** $\text{EPF} + \text{ESIC} + \text{PT} + \text{TDS} + \text{Loan EMI}$
6. **Net Disbursed Salary:** $\text{Adjusted Gross Earnings} - \text{Total Employee Deductions}$
7. **Employer Cost:** $\text{Adjusted Gross Earnings} + \text{Employer Contributions}$

### Canonical PDF Verification Benchmark:
- Basic: ₹20,000 | HRA: ₹8,000 | Other Allowances: ₹4,000 $\rightarrow$ Gross: ₹32,000
- Days in Month: 30 | Payable Days: 28 | Unpaid Absence: 2 days
- $\text{LOP} = \frac{32,000}{30} \times 2 = ₹2,133.33$
- $\text{Adjusted Gross} = 32,000 - 2,133.33 = ₹29,866.67$
- Employee PF (12% of ₹18,000 PF wage base) = ₹2,160.00
- $\text{Net Salary Before Additional Deductions} = ₹27,706.67$

---

## 8. Payslips & Salary Payments
- **Digital Payslips:** Automated generation of branded PDF payslips containing company insignia, employee details, earnings breakdown, deduction breakdown, net pay words, and verification barcode/reference.
- **Disbursement Lifecycle:**
  $$\text{DRAFT} \rightarrow \text{CALCULATED} \rightarrow \text{UNDER REVIEW} \rightarrow \text{APPROVED} \rightarrow \text{FINALIZED} \rightarrow \text{PAYMENT PROCESSING} \rightarrow \text{PAID}$$
- **Bank Batch Files:** Generation of NEFT/RTGS batch transfer CSV files containing Beneficiary Name, Account Number, IFSC, and Net Amount.
- **Reconciliation:** Recording payment date, UTR/transaction reference, and payment mode with non-destructive audit retention.

---

## 9. HR, Finance & Company Administration
- Department and Designation master registries with hierarchical reporting lines.
- Official company holiday calendars with gazetted, restricted, and optional classifications.
- Comprehensive audit trail recording user identity, IP address, timestamp, affected entity, and before/after state diffs.

---

## 10. Recruitment & Onboarding
- Job Openings board with position requirements, vacancy counts, and department tagging.
- Candidate pipeline tracking through stages: `Applied` $\rightarrow$ `Screening` $\rightarrow$ `Interview` $\rightarrow$ `Offered` $\rightarrow$ `Hired` $\rightarrow$ `Rejected`.
- Seamless Candidate-to-Employee conversion preserving recruitment records while populating the employee directory.

---

## 11. Performance Management
- Objective & Key Results (OKRs) and employee goal setting.
- Structured appraisal cycles with self-reviews, manager evaluations, and 1–5 performance ratings.
- Increment and merit promotion recommendations routed directly to salary revision governance.

---

## 12. Loans & Salary Advances
- Online loan and advance applications with tenure and interest configurations.
- Multi-level manager/finance approval workflow.
- Automated monthly EMI schedule integration with the payroll calculation engine, automatically decrementing outstanding loan balances upon finalized payroll runs.

---

## 13. Resignation & Full-and-Final (FnF) Settlement
- Employee resignation submission with notice period tracking and designated last working date.
- Departmental clearance checklist (IT assets, documentation, finance, manager sign-off).
- Automated FnF calculation engine:
  - Prorated salary for working days in final month.
  - Leave encashment for accrued unused paid leave.
  - Gratuity calculation where eligible by tenure.
  - Recovery of unserved notice period or outstanding loan balances.
- Generation of the official Full & Final Settlement Statement.

---

## 14. Document Management & Private Storage
- Secure repository for identity documents, tax declaration proofs, signed appointment letters, and payslips.
- Encrypted file storage with signed download URLs and role-based permissions preventing unauthorized employee document inspection.

---

## 15. In-App Notifications
- Automated triggers for attendance anomalies, leave application statuses, payroll approvals, payslip releases, and policy circulars.
- Real-time notification badge and mark-as-read inbox.

---

## 16. Dashboard Analytics & Reporting
- **Super Admin & HR Dashboard:** Headcount velocity, active/inactive staff, daily attendance doughnut, late punches, leave volume, and departmental distributions.
- **Payroll Dashboard:** Total monthly payroll liability, gross vs net delta chart, statutory PF/ESI liability, pending approvals, and historical payroll trends.
- **Employee Portal:** Personal check-in widget, monthly punch calendar, leave balance badges, recent payslip list, and upcoming holidays.
- **Exportable Reports:** Attendance Master Register, Monthly Payroll Summary, Statutory PF/ESI Report, TDS Withholding Schedule, and Bank Transfer Summary.

---

## 17. Security, Integrity & Compliance
- Passwords hashed using industry-standard Bcrypt with individual cryptographic salts.
- JSON Web Tokens (JWT) with algorithm validation and configurable session expiration.
- Database transactions preventing race conditions and duplicate payroll processing.
- Strict immutability: Finalized payroll batches cannot be modified or deleted through ordinary CRUD interfaces.
