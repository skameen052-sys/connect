from typing import Dict, Any, Optional
from fastapi import HTTPException, status


class DuplicateFieldsException(HTTPException):
    """Exception raised when employee registration encounters duplicate unique fields."""

    def __init__(
        self,
        errors: Dict[str, str],
        detail: Optional[str] = None,
    ):
        if not detail:
            detail = list(errors.values())[0] if errors else "Employee registration failed due to duplicate fields."
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)
        self.errors = errors


class RegistrationValidationException(HTTPException):
    """Exception raised when employee registration encounters validation errors."""

    def __init__(
        self,
        errors: Dict[str, str],
        detail: Optional[str] = None,
    ):
        if not detail:
            detail = list(errors.values())[0] if errors else "Please correct the highlighted errors."
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
        self.errors = errors
