# Automated Payroll Calculations Specification
## Arshith Connect HRMS Attendance-Driven Payroll Engine

---

## 1. Mathematical Formulation

### 1.1 Gross Salary
$$\text{Gross Salary} = \text{Basic Salary} + \text{HRA} + \text{Other Fixed Allowances}$$

### 1.2 Daily Rate & Loss of Pay (LOP)
Let $D$ be the configured payroll days denominator (typically 30, or the actual calendar days in month, or working days):
$$\text{Daily Rate} = \frac{\text{Gross Salary}}{D}$$
$$\text{Unpaid Absence Days} = \text{Total Period Days} - \text{Payable Days}$$
$$\text{Loss of Pay (LOP)} = \text{Daily Rate} \times \text{Unpaid Absence Days} = \frac{\text{Gross Salary}}{D} \times \text{Unpaid Absence Days}$$

### 1.3 Adjusted Gross Earnings
$$\text{Adjusted Gross Earnings} = \text{Gross Salary} - \text{LOP} + \text{Approved Overtime} + \text{Bonus} + \text{Incentives}$$

### 1.4 Employee Deductions
1. **Employee Provident Fund (EPF):**
   $$\text{EPF Deduction} = \text{PF Wage Base} \times \text{PF Rate (12\%)}$$
   *(PF wage base is configurable; default uses Basic or illustrative ceiling ₹18,000 / statutory ₹15,000)*
2. **Employee State Insurance (ESIC):**
   $$\text{ESIC Deduction} = \text{Gross Earnings} \times 0.75\% \quad (\text{if gross } \le ₹21,000)$$
3. **Professional Tax (PT):** Configurable state tax slabs (e.g. ₹200/month).
4. **Income Tax Withholding (TDS):** Configurable monthly TDS projection.
5. **Loan / Advance EMI:** Scheduled monthly installment from active loans.
$$\text{Total Employee Deductions} = \text{EPF} + \text{ESIC} + \text{PT} + \text{TDS} + \text{Loan Installment} + \text{Other Deductions}$$

### 1.5 Net Disbursed Salary
$$\text{Net Salary} = \text{Adjusted Gross Earnings} - \text{Total Employee Deductions}$$

### 1.6 Employer Cost to Company (CTC Contribution)
$$\text{Employer PF} = \text{PF Wage Base} \times 12\%$$
$$\text{Employer ESIC} = \text{Gross Earnings} \times 3.25\%$$
$$\text{Total Employer Cost} = \text{Adjusted Gross Earnings} + \text{Employer PF} + \text{Employer ESIC}$$
*(Note: Employer PF & ESIC are company liabilities and are never deducted from employee take-home pay).*

---

## 2. Canonical PDF Verification Benchmark

| Parameter | Configuration / Input | Calculation Step | Result |
| :--- | :--- | :--- | :--- |
| **Basic Salary** | Defined Structure | Fixed | ₹20,000.00 |
| **HRA** | Defined Structure | Fixed | ₹8,000.00 |
| **Other Allowances** | Defined Structure | Fixed | ₹4,000.00 |
| **Gross Salary** | Component Sum | $20,000 + 8,000 + 4,000$ | **₹32,000.00** |
| **Payroll Days ($D$)** | Period Configuration | Denominator | 30 |
| **Payable Days** | Attendance + Approved Leave | Recorded | 28 |
| **Unpaid Absence** | Missing / Unapproved | $30 - 28$ | 2 days |
| **Daily Rate** | Rate Formula | $\frac{32,000}{30}$ | ₹1,066.6667 |
| **Loss of Pay (LOP)** | LOP Formula | $1,066.6667 \times 2$ | **₹2,133.33** |
| **Adjusted Gross** | Gross minus LOP | $32,000 - 2,133.33$ | **₹29,866.67** |
| **Illustrative PF Wage** | Configured Wage Base | Provided in PDF | ₹18,000.00 |
| **Employee PF (12%)** | $18,000 \times 12\%$ | Employee Deduction | **₹2,160.00** |
| **Other Deductions** | None in sample | - | ₹0.00 |
| **Net Salary** | Take-home Pay | $29,866.67 - 2,160.00$ | **₹27,706.67** |

---

## 3. Payroll Lifecycle & State Transitions

```
[ DRAFT ]
   │
   ▼ (Calculate Attendance, LOP & Statutory Deductions)
[ CALCULATED ]
   │
   ▼ (Flag Exceptions, Missing Punches, Unreviewed Leaves)
[ UNDER REVIEW ]
   │
   ▼ (HR / Authorized Administrator Approval)
[ APPROVED ]
   │
   ▼ (Lock Payroll Run, Generate Immutable Payslips)
[ FINALIZED ] ─── Immutable Snapshot
   │
   ▼ (Export Bank Batch File / Disburse)
[ PAYMENT PROCESSING ]
   │
   ├── (Payment Success) ──► [ PAID ]
   ├── (Partial Batches) ──► [ PARTIALLY PAID ]
   └── (Reversal / Error) ──► [ PAYMENT FAILED ]
```

---

## 4. Immutability & Duplicate Prevention Safeguards
1. **Uniqueness Constraint:** Unique index on `(year, month)`. Duplicate draft generation for the same period is rejected.
2. **Locking Mechanism:** When transitioning to `FINALIZED`, the state is locked. No salary component, attendance record, or leave can retroactively alter a finalized payroll run.
3. **Audit Trail:** Every status transition records `user_id`, `timestamp`, and `notes`.
