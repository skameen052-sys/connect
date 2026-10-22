from typing import Optional
from pydantic import BaseModel, ConfigDict


class RegistrationRequestUpdate(BaseModel):
    status: Optional[str] = None  # "Approved" or "Rejected"
    reason: Optional[str] = None
    rejection_reason: Optional[str] = None
    rejectionReason: Optional[str] = None

    def get_reason(self) -> Optional[str]:
        return self.reason or self.rejection_reason or self.rejectionReason


class RegistrationRequestResponse(BaseModel):
    id: str
    requestId: int
    name: str
    fullName: str
    employeeId: str
    email: str
    phone: str
    status: str
    requestedDate: str
    rejectionReason: Optional[str] = None
    reviewedBy: Optional[str] = None
    reviewedAt: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
