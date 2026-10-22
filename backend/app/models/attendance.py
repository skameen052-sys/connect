from datetime import datetime, date, timezone
from typing import Optional
from sqlalchemy import Integer, String, Boolean, Date, DateTime, Float, ForeignKey, UniqueConstraint, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Attendance(Base):
    __tablename__ = "attendance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("employees.employee_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True, default=date.today)
    check_in_time: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g. "09:05 AM"
    check_out_time: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g. "06:15 PM"
    check_in_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    check_out_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    work_mode: Mapped[str] = mapped_column(String(20), default="WFO", nullable=False)  # "WFO" or "WFH"
    status: Mapped[str] = mapped_column(String(50), default="Present", nullable=False)  # "Present", "Late", "Absent"
    duration: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="In Progress")
    is_late: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    late_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    late_reason_submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Photo storage keys (relative to storage/attendance_photos)
    check_in_photo_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    check_out_photo_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Direct database photo persistence (PostgreSQL BYTEA)
    check_in_photo_data: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    check_out_photo_data: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    check_in_photo_mime: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    check_out_photo_mime: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # GPS Location fields
    check_in_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    check_in_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    check_in_location_accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    check_out_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    check_out_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    check_out_location_accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Calculated working duration in seconds
    working_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @property
    def attendance_date(self) -> date:
        return self.date

    @property
    def check_in_at(self) -> Optional[datetime]:
        return self.check_in_timestamp

    @property
    def check_out_at(self) -> Optional[datetime]:
        return self.check_out_timestamp

    __table_args__ = (
        UniqueConstraint("employee_id", "date", name="uq_attendance_employee_date"),
    )

    employee = relationship("Employee", back_populates="attendances")
    photos = relationship("AttendancePhoto", back_populates="attendance", cascade="all, delete-orphan")
