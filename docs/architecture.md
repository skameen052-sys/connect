# System Architecture & Technical Design
## Arshith Connect HRMS & Automated Payroll System

---

## 1. High-Level Architecture
The system follows a decoupled, three-tier enterprise client-server architecture:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND CLIENT TIER                            │
│   React 19 + Vite + React Router v7 + Lucide Icons + Modular Styling   │
│   Responsive Role Portals: Super Admin | HR | Payroll | Manager | Emp  │
└─────────────────────────────────┬──────────────────────────────────────┘
                                  │ HTTPS / REST JSON API
                                  ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        APPLICATION API TIER                            │
│   FastAPI (Python 3.13) + Uvicorn ASGI Server                          │
│   ├─ Authentication & RBAC Guard Services                              │
│   ├─ Employee & Demographic Service Layer                              │
│   ├─ Biometric & GPS Attendance Verification Engine                    │
│   ├─ Leave Entitlement & Accrual Calculator                            │
│   ├─ Dedicated Attendance-Driven Payroll Engine (Decimal-Safe)         │
│   ├─ Payslip Generation Service (ReportLab PDF)                        │
│   ├─ Separation & Full-and-Final (FnF) Engine                          │
│   ├─ Loans & Advance Amortization Tracker                              │
│   └─ Audit Trail & Compliance Logger                                   │
└─────────────────────────────────┬──────────────────────────────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
┌──────────────────────────────┐        ┌──────────────────────────────┐
│       PRIMARY DATABASE       │        │     OBJECT & FILE STORAGE    │
│  PostgreSQL / MySQL ORM      │        │  Local Storage / Cloud Store │
│  + Dual Cloud Firestore Sync │        │  Protected Payslips, Resumes │
│  Relational Tables & Schema  │        │  & Identity Documents        │
└──────────────────────────────┘        └──────────────────────────────┘
```

---

## 2. Directory Layout & Organization

### Backend (`/backend`)
```text
backend/
├── app/
│   ├── core/           # Security, configuration, JWT, exceptions, hashing
│   ├── db/             # SQLAlchemy engine, session maker, connection pool
│   ├── dependencies/   # RBAC injection, authentication tokens, DB dependencies
│   ├── models/         # SQLAlchemy ORM model definitions
│   ├── routers/        # FastAPI endpoints categorized by domain
│   ├── schemas/        # Pydantic v2 schemas for request validation & response
│   ├── services/       # Dedicated business logic (Payroll, Attendance, Payslips, FnF)
│   └── utils/          # Date arithmetic, PDF helpers, number-to-words converters
├── tests/              # Pytest automated test suites
├── requirements.txt    # Frozen pip dependencies
└── run.py / main.py    # ASGI entrypoint
```

### Frontend (`/frontend`)
```text
frontend/
├── src/
│   ├── assets/         # Corporate logos, SVG badges, brand assets
│   ├── components/     # Reusable UI widgets: Data tables, modals, badges, charts
│   ├── context/        # AuthContext, NotificationContext, ThemeContext
│   ├── layouts/        # AdminLayout, EmployeeLayout, PublicLayout
│   ├── pages/
│   │   ├── admin/      # Management, Employees, Attendance, Leaves, Payroll, FnF
│   │   ├── auth/       # Login, Registration, Forgot Password
│   │   └── employee/   # Self-Service Dashboard, Punch Clock, Payslips, Leaves
│   ├── routes/         # Protected routes with role guards
│   ├── services/       # Axios API client services
│   └── styles/         # CSS design system (tokens, forest green theme, cards)
```

---

## 3. Dedicated Service Layer Architecture
To ensure separation of concerns and maintainability, all calculations reside in the service layer:

1. **`PayrollEngineService`**:
   - Accepts employee master profile, salary structure, approved attendance punches, and leave approvals.
   - Computes payable days, loss of pay (LOP), adjusted gross, statutory EPF/ESIC, professional tax, loan EMIs, and net pay.
   - Enforces immutability: Rejects modification of finalized payroll batches.

2. **`PayslipService`**:
   - Synthesizes payroll execution records into PDF payslips using ReportLab.
   - Includes tabular earnings, itemized deductions, net pay in currency words, and unique reference codes.

3. **`LoanAmortizationService`**:
   - Manages loan approvals, schedules monthly deductions, and reduces balances automatically when monthly payroll is finalized.

4. **`SeparationService`**:
   - Executes Full-and-Final (FnF) statements including notice pay adjustment, leave encashment, and loan balance netting.

---

## 4. Security Architecture
- **Bearer JWT Authentication:** Expiry-guarded tokens carrying identity and role claims.
- **Granular Permissions:** Every endpoint validates user roles (`super_admin`, `admin`, `hr`, `payroll`, `manager`, `employee`).
- **Restricted Data Exposure:** Employee salary details and bank accounts are scrubbed from public listings.
- **Audit Logging:** Security-sensitive operations write immutable audit log records.
