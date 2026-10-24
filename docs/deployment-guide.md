# Deployment & Operations Guide
## Arshith Connect HRMS & Automated Payroll Management Platform

---

## 1. System Requirements
- **Operating System:** Windows, Linux (Ubuntu 22.04+ LTS), or macOS
- **Python:** 3.11, 3.12, or 3.13
- **Node.js:** v18.0.0 or higher
- **Databases Supported:**
  - Cloud Firestore / Local JSON store (zero-config, high availability)
  - PostgreSQL 15+ / MySQL 8.0+ via SQLAlchemy ORM
- **Web Server:** Uvicorn (ASGI) / Gunicorn for production, Vite for frontend

---

## 2. Environment Variables Setup

### Backend `.env` (`backend/.env`)
```bash
PROJECT_NAME="Arshith Connect HRMS & Payroll API"
API_V1_STR="/api"
SECRET_KEY="your_production_secret_key_change_me_in_production"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database Backend: "firebase" (Firestore) or "postgres" or "mysql"
DATABASE_BACKEND=firebase
FIREBASE_DATABASE_NAME="(default)"
FIREBASE_PROJECT_ID="arshith-connect-attendance"
FIREBASE_STORAGE_BUCKET="arshith-connect-attendance.firebasestorage.app"
FIREBASE_CREDENTIALS_PATH="serviceAccountKey.json"

# Local/Production Relational DB (Optional)
DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/arshith_connect_db

# CORS Allowed Origins
FRONTEND_CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
ATTENDANCE_TIMEZONE=Asia/Kolkata
```

### Frontend `.env` (`frontend/.env`)
```bash
VITE_API_URL=http://127.0.0.1:8000/api
```

---

## 3. Step-by-Step Installation

### Step A: Backend Setup
```powershell
# 1. Navigate to backend directory
cd backend

# 2. Activate virtual environment
.\venv\Scripts\Activate.ps1
# (On Linux: source venv/bin/activate)

# 3. Install required packages
pip install -r requirements.txt

# 4. Start the backend ASGI server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Swagger API Documentation will be live at: `http://127.0.0.1:8000/docs`

### Step B: Frontend Setup
```powershell
# 1. Navigate to frontend directory
cd frontend

# 2. Install npm dependencies
npm install

# 3. Start Vite development server
npm run dev
```
Web application will be live at: `http://localhost:5173`

---

## 4. Default Seed Credentials

| Role | Email | Password | Access Portal |
| :--- | :--- | :--- | :--- |
| **Super Admin** | `admin@arshith.com` | `AdminPassword@123` | `http://localhost:5173/admin/login` |
| **HR Administrator** | `hr@arshith.com` | `AdminPassword@123` | `http://localhost:5173/admin/login` |
| **Payroll Admin** | `payroll@arshith.com` | `AdminPassword@123` | `http://localhost:5173/admin/login` |
| **Team Manager** | `manager@arshith.com` | `AdminPassword@123` | `http://localhost:5173/admin/login` |
| **Employee** | `employee@arshith.com` | `Employee@123` | `http://localhost:5173/login` |

---

## 5. Automated Tests Execution
To run all test suites including the exact PDF payroll formula verification:
```powershell
cd backend
.\venv\Scripts\pytest -v tests/
```
