# Role-Based Access Control (RBAC) & Permissions Matrix
## Arshith Connect HRMS & Automated Payroll System

---

## 1. Five Distinct Roles

1. **Super Admin**: Master organizational administration and complete system configuration.
2. **HR Administrator**: Workforce onboarding, attendance/leave verification, recruitment, performance, and separations.
3. **Manager / Team Leader**: Supervision of direct reports, leave approvals, attendance correction sign-offs, and performance feedback.
4. **Payroll / Finance Administrator**: Compensation setup, salary structures, payroll calculation runs, payslip generation, bank disbursements, and loan schedules.
5. **Employee**: Self-service portal for clocking in/out, viewing attendance history, applying for leaves, loan requests, downloading payslips, and personal documents.

---

## 2. Granular Permissions Matrix

| Module / Operation | Super Admin | HR Admin | Manager | Payroll / Finance | Employee |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **User & Role Management** | ✅ Full | ❌ None | ❌ None | ❌ None | ❌ None |
| **Company Settings & Holidays** | ✅ Full | ✅ Edit | 👁️ View | 👁️ View | 👁️ View |
| **Departments & Designations** | ✅ Full | ✅ Full | 👁️ View | 👁️ View | 👁️ View |
| **Employee Directory** | ✅ Full | ✅ Full | 👥 Team Only | 👁️ View (Masked) | 👤 Self Only |
| **Bank & Tax Details** | ✅ View | ✏️ Manage | ❌ None | ✅ View & Pay | 👤 Self Only |
| **Attendance Check-In/Out** | ✅ Any | ✅ Any | 👤 Self | 👤 Self | 👤 Self |
| **Attendance Approvals & Corrections** | ✅ Approve | ✅ Approve | ✅ Approve Team | ❌ None | 📝 Request Only |
| **Leave Applications** | 📝 Self | 📝 Self | 📝 Self | 📝 Self | 📝 Self |
| **Leave Approvals** | ✅ Approve | ✅ Approve | ✅ Approve Team | ❌ None | ❌ None |
| **Salary Structure Setup** | ✅ Full | 👁️ View | ❌ None | ✅ Full | ❌ None |
| **Draft & Calculate Payroll** | ✅ Full | 👁️ Review | ❌ None | ✅ Full | ❌ None |
| **Approve Payroll Batch** | ✅ Full | ✅ Authorized | ❌ None | ❌ None | ❌ None |
| **Finalize & Lock Payroll** | ✅ Full | ❌ None | ❌ None | ✅ Authorized | ❌ None |
| **Generate & Download Payslips** | ✅ Any | ✅ Any | ❌ None | ✅ Any | 👤 Self Only |
| **Export Bank Payment Batch** | ✅ Full | ❌ None | ❌ None | ✅ Full | ❌ None |
| **Confirm Salary Payments** | ✅ Full | ❌ None | ❌ None | ✅ Full | ❌ None |
| **Recruitment & Job Openings** | ✅ Full | ✅ Full | 👥 Interviewer | ❌ None | ❌ None |
| **Performance Goals & Reviews** | ✅ Full | ✅ Full | ✅ Evaluate Team | ❌ None | 👤 Self Assessment |
| **Loans & Advances** | ✅ Full | 👁️ View | 👁️ View Team | ✅ Approve & Schedule | 📝 Request Self |
| **Resignation & FnF Settlement** | ✅ Full | ✅ Execute | 👥 Endorse Team | ✅ Settle & Pay | 📝 Request Self |
| **Audit Logs** | ✅ View All | ❌ None | ❌ None | ❌ None | ❌ None |
| **Reports & Analytics** | ✅ All | ✅ HR Reports | 👥 Team Reports | ✅ Financial Reports | 👤 Self Reports |

---

## 3. Enforcement Layers
- **Backend Enforced:** Every FastAPI route injects dependency guards (`require_roles`, `get_current_admin`, `get_current_employee`).
- **Frontend Responsive:** Navigation bars, dashboard views, action buttons, and route guards dynamically adapt to user role claims.
