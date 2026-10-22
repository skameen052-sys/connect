from datetime import datetime, timezone
from typing import Optional, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.core.firebase import verify_firebase_token
from app.db.session import get_db
from app.services.firestore_service import FirestoreService

security_scheme = HTTPBearer(auto_error=False)


class DictEntity:
    """Wrapper that permits attribute-style and dict-style access to Firestore documents."""
    def __init__(self, data: dict):
        self._data = dict(data)
        for k, v in self._data.items():
            setattr(self, k, v)
        # Ensure common alternate naming aliases
        if "id" not in self._data and "_firestore_id" in self._data:
            self.id = self._data["_firestore_id"]
        if "uid" in self._data and "id" not in self._data:
            self.id = self._data["uid"]
        if "id" in self._data and "uid" not in self._data:
            self.uid = self._data["id"]

        if "employee_id" in self._data and "employeeId" not in self._data:
            self.employeeId = self._data["employee_id"]
            self._data["employeeId"] = self._data["employee_id"]
        elif "employeeId" in self._data and "employee_id" not in self._data:
            self.employee_id = self._data["employeeId"]
            self._data["employee_id"] = self._data["employeeId"]
        elif "employee_id" in self._data and "employeeId" in self._data:
            self.employeeId = self._data["employeeId"]
            self.employee_id = self._data["employee_id"]

        if "full_name" in self._data and "fullName" not in self._data:
            self.fullName = self._data["full_name"]
            self.name = self._data["full_name"]
        elif "fullName" in self._data and "full_name" not in self._data:
            self.full_name = self._data["fullName"]
            self.name = self._data["fullName"]
        elif "name" in self._data:
            self.full_name = self._data["name"]
            self.fullName = self._data["name"]

    def __getitem__(self, key: str) -> Any:
        return self._data.get(key)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def to_dict(self) -> dict:
        return dict(self._data)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> Any:
    """Validate Bearer JWT token (FastAPI JWT or Firebase ID Token) and return authenticated User."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    user_id = None
    token_role = None
    email = None
    token_emp_id = None

    # 1. Attempt decoding as local application JWT
    payload = decode_access_token(token)
    if payload:
        user_id = payload.get("sub")
        token_role = payload.get("role")
        email = payload.get("email")
        token_emp_id = payload.get("employeeId") or payload.get("employee_id")
    else:
        # 2. Attempt decoding as Firebase Authentication ID token
        fb_token = verify_firebase_token(token)
        if fb_token:
            user_id = fb_token.get("uid")
            email = fb_token.get("email")
            token_role = fb_token.get("role") or ("admin" if fb_token.get("admin") else "employee")

    if not user_id and not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired or is invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Resolve User via Firestore if DATABASE_BACKEND == "firebase"
    if settings.DATABASE_BACKEND == "firebase":
        user_data = None
        clean_email = email.lower().strip() if email else ""

        # A. Search 'users' collection
        if user_id:
            user_data = FirestoreService.get_by_id("users", str(user_id))
        if not user_data and clean_email:
            matches = FirestoreService.query("users", {"email": clean_email})
            if matches:
                user_data = matches[0]

        if user_data:
            user_data = dict(user_data)
            u_role = str(user_data.get("role", "employee")).strip().lower()
            if u_role != "admin":
                if token_emp_id:
                    user_data["employee_id"] = token_emp_id
                    user_data["employeeId"] = token_emp_id
                if not user_data.get("employee_id") and not user_data.get("employeeId"):
                    emp_lookup = []
                    if clean_email:
                        emp_lookup = FirestoreService.query("employees", {"email": clean_email})
                    if not emp_lookup and user_id:
                        e_doc = FirestoreService.get_by_id("employees", str(user_id))
                        if e_doc:
                            emp_lookup = [e_doc]
                    if not emp_lookup and user_id:
                        emp_lookup = FirestoreService.query("employees", {"uid": str(user_id)})
                    if not emp_lookup and user_id:
                        emp_lookup = FirestoreService.query("employees", {"user_id": user_id})
                    if not emp_lookup and user_id and str(user_id).isdigit():
                        emp_lookup = FirestoreService.query("employees", {"user_id": int(user_id)})
                    if emp_lookup:
                        f_emp = emp_lookup[0]
                        f_eid = f_emp.get("employee_id") or f_emp.get("employeeId") or f_emp.get("id")
                        if f_eid:
                            user_data["employee_id"] = f_eid
                            user_data["employeeId"] = f_eid
                        if "name" not in user_data:
                            user_data["name"] = f_emp.get("name") or f_emp.get("fullName") or f_emp.get("full_name")


        # B. Search 'admins' collection if not in users
        if not user_data:
            if user_id:
                user_data = FirestoreService.get_by_id("admins", str(user_id))
            if not user_data and clean_email:
                matches = FirestoreService.query("admins", {"email": clean_email})
                if matches:
                    user_data = matches[0]
            if user_data:
                user_data = dict(user_data)
                user_data["role"] = "admin"
                user_data["is_active"] = True
                user_data["approval_status"] = "APPROVED"
                if "id" not in user_data and "_firestore_id" in user_data:
                    user_data["id"] = user_data["_firestore_id"]

        # C. Search authoritative 'employees' collection (where mobile and approved employees reside)
        if not user_data:
            if user_id:
                user_data = FirestoreService.get_by_id("employees", str(user_id))
            if not user_data and clean_email:
                matches = FirestoreService.query("employees", {"email": clean_email})
                if matches:
                    user_data = matches[0]
            if not user_data and user_id:
                matches = FirestoreService.query("employees", {"uid": str(user_id)})
                if matches:
                    user_data = matches[0]
            if not user_data and token_emp_id:
                matches = FirestoreService.query("employees", {"employeeId": str(token_emp_id)})
                if not matches:
                    matches = FirestoreService.query("employees", {"employee_id": str(token_emp_id)})
                if matches:
                    user_data = matches[0]

            if user_data:
                user_data = dict(user_data)
                user_data["role"] = "employee"
                emp_status = str(user_data.get("status", "active")).strip().lower()
                user_data["is_active"] = emp_status in ["active", "approved"]
                if emp_status in ["active", "approved"]:
                    user_data["approval_status"] = "APPROVED"
                elif emp_status == "rejected":
                    user_data["approval_status"] = "REJECTED"
                else:
                    user_data["approval_status"] = "PENDING"

                emp_pk = (
                    user_data.get("uid")
                    or user_data.get("_firestore_id")
                    or user_data.get("id")
                    or str(user_id)
                )
                user_data["id"] = emp_pk
                user_data["uid"] = emp_pk
                e_id = user_data.get("employee_id") or user_data.get("employeeId") or emp_pk
                user_data["employee_id"] = e_id
                user_data["employeeId"] = e_id
                user_data["name"] = user_data.get("name") or user_data.get("fullName") or user_data.get("full_name") or "Employee"
                user_data["fullName"] = user_data["name"]

                # Automatically synchronize to 'users' collection to guarantee consistent identity across collections
                try:
                    FirestoreService.save("users", str(emp_pk), {
                        "id": str(emp_pk),
                        "uid": str(emp_pk),
                        "email": str(user_data.get("email", clean_email)).lower().strip(),
                        "role": "employee",
                        "is_active": user_data["is_active"],
                        "approval_status": user_data["approval_status"],
                        "status": user_data.get("status", "approved"),
                        "employee_id": e_id,
                        "employeeId": e_id,
                        "name": user_data["name"],
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    })
                except Exception:
                    pass

        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User associated with this token was not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = DictEntity(user_data)
    else:
        # Fallback to PostgreSQL
        from app.models.user import User as PgUser
        try:
            uid = int(user_id) if user_id and str(user_id).isdigit() else None
        except Exception:
            uid = None

        user = db.query(PgUser).filter(PgUser.id == uid).first() if uid else None
        if not user and email:
            user = db.query(PgUser).filter(PgUser.email == email.lower().strip()).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User associated with this token was not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        u_role = str(getattr(user, "role", "employee")).strip().lower()
        if u_role != "admin":
            from app.models.employee import Employee as PgEmployee
            pg_emp = None
            if uid:
                pg_emp = db.query(PgEmployee).filter(PgEmployee.user_id == uid).first()
            if not pg_emp and email:
                pg_emp = db.query(PgEmployee).filter(PgEmployee.email == email.lower().strip()).first()
            if pg_emp:
                setattr(user, "employee_id", pg_emp.employee_id)
                setattr(user, "employeeId", pg_emp.employee_id)
            elif token_emp_id:
                setattr(user, "employee_id", token_emp_id)
                setattr(user, "employeeId", token_emp_id)


    # Validate role (case-insensitive)
    role = str(getattr(user, "role", "employee")).strip().lower()
    if token_role and str(token_role).strip().lower() != role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token role does not match account privileges",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate approval status for employees
    approval_status = str(getattr(user, "approval_status", "APPROVED")).strip().upper()
    if role == "employee" and approval_status != "APPROVED":
        if approval_status == "PENDING":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your registration is pending Admin approval. Please wait until your account is approved.",
            )
        elif approval_status == "REJECTED":
            detail = "Your registration request was not approved. Please contact company administration."
            if getattr(user, "rejection_reason", None):
                detail += f" Reason: {user.rejection_reason}"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account is pending Admin approval or was rejected",
            )

    is_active = getattr(user, "is_active", True)
    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account has been deactivated or is unapproved",
        )

    return user


def get_current_admin(
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Verify administrator authorization."""
    role = str(getattr(current_user, "role", "")).strip().lower()
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required to perform this action",
        )
    return current_user


def get_current_employee(
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Get active Employee entity for the authenticated user across Firebase or PostgreSQL."""
    role = str(getattr(current_user, "role", "")).strip().lower()
    if role != "employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employee privileges required. Administrator accounts cannot access employee-specific resources.",
        )

    user_id = getattr(current_user, "id", None) or getattr(current_user, "uid", None)
    email = getattr(current_user, "email", "")
    emp_code = getattr(current_user, "employee_id", None) or getattr(current_user, "employeeId", None)

    if settings.DATABASE_BACKEND == "firebase":
        emp_data = None
        clean_email = email.lower().strip() if email else ""

        # 1. Lookup by ID/UID in employees collection
        if user_id:
            emp_data = FirestoreService.get_by_id("employees", str(user_id))
        # 2. Lookup by employeeId/code
        if not emp_data and emp_code:
            emp_data = FirestoreService.get_by_id("employees", str(emp_code))
        # 3. Lookup by email
        if not emp_data and clean_email:
            matches = FirestoreService.query("employees", {"email": clean_email})
            if matches:
                emp_data = matches[0]
        # 4. Lookup by UID field
        if not emp_data and user_id:
            matches = FirestoreService.query("employees", {"uid": str(user_id)})
            if matches:
                emp_data = matches[0]
        # 5. Lookup by user_id field
        if not emp_data and user_id:
            matches = FirestoreService.query("employees", {"user_id": user_id})
            if matches:
                emp_data = matches[0]
        # 6. Fall back to current_user raw data if it represents an employee
        if not emp_data and hasattr(current_user, "_data") and current_user._data.get("employeeId"):
            emp_data = current_user._data

        if not emp_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee record not found for authenticated user",
            )

        emp_dict = dict(emp_data)
        e_id = emp_dict.get("employee_id") or emp_dict.get("employeeId") or (emp_code if emp_code else str(user_id))
        emp_dict["employee_id"] = e_id
        emp_dict["employeeId"] = e_id
        emp_dict["uid"] = emp_dict.get("uid") or emp_dict.get("id") or str(user_id)
        emp_dict["id"] = emp_dict["uid"]
        emp_dict["name"] = emp_dict.get("name") or emp_dict.get("fullName") or emp_dict.get("full_name") or "Employee"
        emp_dict["full_name"] = emp_dict["name"]
        emp_dict["fullName"] = emp_dict["name"]
        emp_dict["location"] = emp_dict.get("location") or "HQ Office"
        emp_dict["department"] = emp_dict.get("department") or "Operations"
        emp_dict["designation"] = emp_dict.get("designation") or "Operations Associate"

        employee = DictEntity(emp_dict)
    else:
        from app.models.employee import Employee as PgEmployee
        employee = db.query(PgEmployee).filter(PgEmployee.user_id == user_id).first() if user_id else None
        if not employee:
            employee = db.query(PgEmployee).filter(PgEmployee.email == email).first()

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee record not found for authenticated user",
            )

    # Case-insensitive approval & status check (both 'active' and 'approved' are authorized)
    status_val = str(getattr(employee, "status", "active")).strip().lower()
    if status_val not in ["active", "approved"]:
        if status_val == "pending":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your registration is pending Admin approval. Please wait until your account is approved.",
            )
        elif status_val == "rejected":
            detail = "Your registration request was not approved. Please contact company administration."
            if getattr(employee, "rejection_reason", None):
                detail += f" Reason: {employee.rejection_reason}"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your employee account is currently inactive. Please contact administration.",
            )

    return employee
