from datetime import date, datetime
from typing import Optional, List, Union, Any
from pydantic import BaseModel, ConfigDict


class AttendanceCheckInRequest(BaseModel):
    employeeId: Optional[str] = None
    workMode: Optional[str] = "WFO"  # "WFO" or "WFH"


class AttendanceCheckOutRequest(BaseModel):
    employeeId: Optional[str] = None


class AttendanceRecordUpdate(BaseModel):
    status: Optional[str] = None
    workMode: Optional[str] = None
    checkIn: Optional[str] = None
    checkOut: Optional[str] = None
    lateReason: Optional[str] = None


class LateReasonSubmissionRequest(BaseModel):
    attendanceId: Optional[Union[int, str]] = None
    date: Optional[str] = None
    reason: str


class AttendanceResponse(BaseModel):
    id: Union[int, str]
    employeeId: str
    employeeName: str
    department: str
    date: str
    day: str
    checkIn: str
    checkOut: str
    workMode: str
    status: str
    duration: str
    isLate: bool
    lateReason: Optional[str] = None
    lateReasonStatus: Optional[str] = None
    lateReasonSubmittedAt: Optional[str] = None
    checkInLatitude: Optional[float] = None
    checkInLongitude: Optional[float] = None
    checkInLocationAccuracy: Optional[float] = None
    hasCheckInPhoto: Optional[bool] = False
    hasCheckOutPhoto: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True)


class AttendanceTodayStatusResponse(BaseModel):
    id: Optional[Union[int, str]] = None
    hasRecord: bool = False
    isCheckedIn: bool
    isCompleted: bool = False
    checkInTime: str
    checkOutTime: str
    workMode: str
    authorizedWorkMode: Optional[str] = "WFO"
    workingDuration: str
    status: str
    date: str
    isLate: Optional[bool] = False
    lateReason: Optional[str] = None
    lateReasonStatus: Optional[str] = None
    lateReasonSubmittedAt: Optional[str] = None
    checkInTimestamp: Optional[str] = None
    checkOutTimestamp: Optional[str] = None
    checkInLatitude: Optional[float] = None
    checkInLongitude: Optional[float] = None
    checkInLocationAccuracy: Optional[float] = None
    hasCheckInPhoto: Optional[bool] = False
    hasCheckOutPhoto: Optional[bool] = False
    canCheckIn: bool = True
    canCheckOut: bool = False


class OfficeLocationResponse(BaseModel):
    officeName: Optional[str] = None
    address: Optional[str] = None
    latitude: float
    longitude: float
    radiusMeters: float
    maxAccuracyMeters: float
    timezone: str


class LocationValidationRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy: Optional[float] = None
    workMode: Optional[str] = "WFO"


class AttendanceSummaryResponse(BaseModel):
    totalPresent: int
    wfo: int
    wfh: int
    late: int
    daysPresent: int
    daysWfo: int
    daysWfh: int
