from typing import Optional, Any, Dict
from pydantic import BaseModel, EmailStr, ConfigDict


class LoginRequest(BaseModel):
    email: str
    password: str


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    fullName: Optional[str] = None
    full_name: Optional[str] = None
    employeeId: Optional[str] = None
    employee_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = "--"
    password: Optional[str] = None
    confirmPassword: Optional[str] = None
    confirm_password: Optional[str] = None
    department: Optional[str] = "Operations"
    designation: Optional[str] = "Employee"


class UserProfileResponse(BaseModel):
    id: int
    email: str
    role: str
    name: str
    employeeId: str
    department: Optional[str] = "Operations"
    designation: Optional[str] = "Employee"
    phone: Optional[str] = "--"
    status: Optional[str] = "Active"

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user: Dict[str, Any]
