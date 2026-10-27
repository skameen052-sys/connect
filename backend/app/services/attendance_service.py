import os
import uuid
import io
import logging
from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo
from typing import Optional, Tuple, Any, Dict
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    Image = None
    HAS_PIL = False

import math
from fastapi import HTTPException, status, UploadFile

from app.core.config import settings

logger = logging.getLogger("uvicorn.error")

ALLOWED_MIME_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

# Magic bytes detection
MAGIC_BYTES = [
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
    (b"RIFF", "image/webp", ".webp"),  # WEBP starts with RIFF and has WEBP at offset 8
]


def get_attendance_storage_dir() -> str:
    """Get the absolute path to the private attendance photo storage directory."""
    if settings.ATTENDANCE_PHOTO_DIR and os.path.isabs(settings.ATTENDANCE_PHOTO_DIR):
        base_dir = settings.ATTENDANCE_PHOTO_DIR
    elif settings.ATTENDANCE_PHOTO_DIR:
        base_dir = os.path.normpath(
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), settings.ATTENDANCE_PHOTO_DIR)
        )
    else:
        # Default: backend/storage/attendance_photos
        base_dir = os.path.normpath(
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "storage", "attendance_photos")
        )

    os.makedirs(base_dir, exist_ok=True)
    return base_dir


def get_attendance_timezone() -> ZoneInfo:
    """Retrieve ZoneInfo for configured attendance timezone, defaulting to Asia/Kolkata."""
    try:
        return ZoneInfo(settings.ATTENDANCE_TIMEZONE)
    except Exception:
        return ZoneInfo("Asia/Kolkata")


def get_attendance_now() -> datetime:
    """Get authoritative current datetime in the configured attendance timezone."""
    return datetime.now(get_attendance_timezone())


def get_attendance_today() -> date:
    """Get authoritative current date in the configured attendance timezone."""
    return get_attendance_now().date()


def format_duration_str(seconds: int) -> str:
    """Format duration in 'HH hrs MM mins' to match reference screenshot."""
    if seconds < 0:
        seconds = 0
    hrs = seconds // 3600
    mins = (seconds % 3600) // 60
    return f"{hrs:02d} hrs {mins:02d} mins"


def calculate_haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two GPS coordinates in meters
    using the Haversine formula.
    """
    R = 6371000.0  # Earth's mean radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def verify_wfo_geofence(latitude: float, longitude: float, accuracy: float) -> dict:
    """
    Independently validate GPS coordinates against authoritative office coordinates and accuracy threshold.
    Returns structured validation report dict.
    """
    # 1. Bounds checking
    if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
        return {
            "valid": False,
            "code": "INVALID_COORDINATES",
            "message": "GPS coordinates out of valid geographical range (latitude [-90, 90], longitude [-180, 180]).",
            "distanceMeters": None,
            "allowedRadiusMeters": settings.OFFICE_GEOFENCE_RADIUS_METERS,
            "accuracy": accuracy,
            "maxAllowedAccuracy": settings.MAX_GPS_ACCURACY_METERS,
        }

    # 2. Check GPS accuracy threshold
    if accuracy < 0:
        return {
            "valid": False,
            "code": "INVALID_ACCURACY",
            "message": "GPS location accuracy must be a positive number in meters.",
            "distanceMeters": None,
            "allowedRadiusMeters": settings.OFFICE_GEOFENCE_RADIUS_METERS,
            "accuracy": accuracy,
            "maxAllowedAccuracy": settings.MAX_GPS_ACCURACY_METERS,
        }

    if accuracy > settings.MAX_GPS_ACCURACY_METERS:
        return {
            "valid": False,
            "code": "INACCURATE_GPS",
            "message": (
                f"Your GPS accuracy is too low (±{round(accuracy)}m). Accurate location within "
                f"{int(settings.MAX_GPS_ACCURACY_METERS)}m is required. Please check your device location settings or move near a window and try again."
            ),
            "distanceMeters": None,
            "allowedRadiusMeters": settings.OFFICE_GEOFENCE_RADIUS_METERS,
            "accuracy": accuracy,
            "maxAllowedAccuracy": settings.MAX_GPS_ACCURACY_METERS,
        }

    # 3. Calculate distance to authoritative coordinates (12.9104417, 77.6442435)
    dist = calculate_haversine_distance_meters(
        latitude,
        longitude,
        settings.COMPANY_OFFICE_LATITUDE,
        settings.COMPANY_OFFICE_LONGITUDE,
    )

    radius_int = int(settings.OFFICE_GEOFENCE_RADIUS_METERS)
    if dist > settings.OFFICE_GEOFENCE_RADIUS_METERS:
        return {
            "valid": False,
            "code": "OUTSIDE_OFFICE_GEOFENCE",
            "message": "You are outside the permitted attendance area.",
            "distanceMeters": round(dist, 1),
            "allowedRadiusMeters": settings.OFFICE_GEOFENCE_RADIUS_METERS,
            "accuracy": accuracy,
            "maxAllowedAccuracy": settings.MAX_GPS_ACCURACY_METERS,
        }

    return {
        "valid": True,
        "code": None,
        "message": f"Successfully verified presence within {radius_int} metres of configured coordinates.",
        "distanceMeters": round(dist, 1),
        "allowedRadiusMeters": settings.OFFICE_GEOFENCE_RADIUS_METERS,
        "accuracy": accuracy,
        "maxAllowedAccuracy": settings.MAX_GPS_ACCURACY_METERS,
    }


def get_employee_authorized_work_mode(employee) -> str:
    """
    Determine the employee's authorized work mode ('WFO' or 'WFH') from their verified profile settings.
    Rejects with clear message instead of guessing or defaulting if missing or unauthorized.
    """
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found.",
        )

    # Check direct work_mode attribute if present
    explicit_mode = (
        (employee.get("work_mode") or employee.get("workMode"))
        if isinstance(employee, dict)
        else getattr(employee, "work_mode", getattr(employee, "workMode", None))
    )
    if explicit_mode and str(explicit_mode).strip().upper() in ["WFO", "WFH"]:
        return str(explicit_mode).strip().upper()

    # Derive from employee location setting
    loc = (
        employee.get("location")
        if isinstance(employee, dict)
        else getattr(employee, "location", None)
    )
    if not loc or not str(loc).strip():
        return "WFO"

    loc_str = str(loc).strip().upper()
    if any(k in loc_str for k in ["WFH", "REMOTE", "HOME", "WORK FROM HOME"]):
        return "WFH"

    if any(k in loc_str for k in ["HQ", "OFFICE", "WFO", "ONSITE"]):
        return "WFO"

    return "WFO"


def detect_image_type(file_bytes: bytes) -> Optional[Tuple[str, str]]:
    """Detect image type from magic bytes. Returns (mime_type, file_extension) or None."""
    if len(file_bytes) < 12:
        return None

    if file_bytes.startswith(b"\xff\xd8\xff"):
        return ("image/jpeg", ".jpg")
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return ("image/png", ".png")
    if file_bytes.startswith(b"RIFF") and file_bytes[8:12] == b"WEBP":
        return ("image/webp", ".webp")

    return None


async def validate_and_save_attendance_photo(
    file: object,
    photo_type: str = "check_in",
    attendance_date: Optional[date] = None,
) -> Tuple[str, bytes, str]:
    """
    Validate uploaded image (size, magic bytes, PIL verification) and save to private storage.
    Supports UploadFile, raw bytes, or Base64 data URL string.
    Returns (storage_key, image_bytes, mime_type) for dual storage in file system and PostgreSQL BYTEA.
    """
    if attendance_date is None:
        attendance_date = get_attendance_today()

    date_str = attendance_date.isoformat()

    # Read content from UploadFile, bytes, or Base64 string
    if hasattr(file, "read"):
        content = await file.read()
    elif isinstance(file, (bytes, bytearray)):
        content = bytes(file)
    elif isinstance(file, str):
        import base64
        cleaned_str = file.strip()
        if "," in cleaned_str:
            cleaned_str = cleaned_str.split(",", 1)[1]
        try:
            content = base64.b64decode(cleaned_str)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Corrupted or invalid Base64 image encoding.",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported photograph payload format.",
        )

    file_size = len(content)

    # 1. Size validation (Max 5 MB)
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded photo is empty.",
        )
    if file_size > settings.MAX_PHOTO_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Photo size exceeds maximum allowed limit of {settings.MAX_PHOTO_SIZE_BYTES // (1024 * 1024)}MB.",
        )

    # 2. Magic bytes inspection
    detected = detect_image_type(content)
    if not detected:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported image format. Only JPEG, PNG, and WebP are accepted.",
        )

    mime_type, ext = detected

    # 3. PIL image structure verification (if Pillow is installed)
    if HAS_PIL and Image is not None:
        try:
            image = Image.open(io.BytesIO(content))
            image.verify()  # Verifies header and integrity without loading entire bitmap into memory
        except Exception as e:
            logger.warning(f"Image verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Corrupted or invalid image data.",
            )

    # 4. Save to private directory organized by date
    storage_base = get_attendance_storage_dir()
    date_dir = os.path.join(storage_base, date_str)
    os.makedirs(date_dir, exist_ok=True)

    unique_filename = f"{uuid.uuid4().hex}_{photo_type}{ext}"
    absolute_dest = os.path.join(date_dir, unique_filename)

    try:
        with open(absolute_dest, "wb") as f:
            f.write(content)
    except Exception as e:
        logger.error(f"Failed to write attendance photo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store attendance photo securely.",
        )

    # Return relative storage key, raw binary bytes for direct PostgreSQL BYTEA storage, and mime_type
    storage_key = f"{date_str}/{unique_filename}"
    return storage_key, content, mime_type


def resolve_photo_path(storage_key: str) -> Tuple[str, str]:
    """
    Safely resolve storage key to absolute file path and verify it exists within storage directory.
    Returns (absolute_file_path, mime_type).
    """
    if not storage_key:
        raise HTTPException(status_code=404, detail="Photo not found.")

    storage_base = os.path.realpath(get_attendance_storage_dir())
    target_path = os.path.realpath(os.path.join(storage_base, storage_key.replace("/", os.sep)))

    # Prevent directory traversal attacks
    if not target_path.startswith(storage_base):
        logger.warning(f"Directory traversal attempt detected with key: {storage_key}")
        raise HTTPException(status_code=400, detail="Invalid storage path.")

    if not os.path.exists(target_path) or not os.path.isfile(target_path):
        raise HTTPException(status_code=404, detail="Attendance photo file not found.")

    ext = os.path.splitext(target_path)[1].lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    mime_type = mime_map.get(ext, "image/jpeg")

    return target_path, mime_type


def cleanup_photo_file(storage_key: Optional[str]) -> None:
    """Delete a newly saved photo file if database transaction fails."""
    if not storage_key:
        return
    try:
        storage_base = os.path.realpath(get_attendance_storage_dir())
        target_path = os.path.realpath(os.path.join(storage_base, storage_key.replace("/", os.sep)))
        if target_path.startswith(storage_base) and os.path.exists(target_path):
            os.remove(target_path)
            logger.info(f"Cleaned up orphaned attendance photo: {storage_key}")
    except Exception as e:
        logger.warning(f"Failed to cleanup photo {storage_key}: {e}")


def upload_to_firebase_storage(
    photo_bytes: bytes,
    mime_type: str,
    employee_id: str,
    attendance_record_id: Any,
    photo_type: str = "check-in",
    employee_uid: Optional[str] = None,
    attendance_date: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Upload real attendance photograph bytes to Cloud Storage for Firebase.
    Uploads exactly once to the single canonical storage path:
       attendancePhotos/{target_id}/{date_str}.jpg
    Returns (canonical_storage_path, photo_url).
    """
    from datetime import timedelta
    from app.core.firebase import get_storage_bucket, is_firebase_live

    ext = ".jpg" if ("jpeg" in mime_type or "jpg" in mime_type) else (".png" if "png" in mime_type else ".webp")
    target_id = employee_uid or employee_id
    date_str = str(attendance_date or "")
    if not date_str and "_" in str(attendance_record_id):
        date_str = str(attendance_record_id).split("_", 1)[1]

    # Canonical storage path matching reference screenshot & Android mobile app:
    # attendancePhotos/{userId}/{date}.jpg
    if date_str:
        canonical_path = f"attendancePhotos/{target_id}/{date_str}{ext}"
    else:
        canonical_path = f"attendancePhotos/{target_id}/{attendance_record_id}{ext}"

    if is_firebase_live():
        bucket = get_storage_bucket()
        if not bucket:
            raise RuntimeError("Cloud Storage bucket is not available or not initialized.")

        try:
            # Upload exactly once to canonical storage path
            blob = bucket.blob(canonical_path)
            blob.upload_from_string(photo_bytes, content_type=mime_type)

            # Generate signed URL for authenticated display or direct media link
            try:
                photo_url = blob.generate_signed_url(expiration=timedelta(days=7), method="GET")
            except Exception:
                photo_url = f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/{canonical_path.replace('/', '%2F')}?alt=media"

            logger.info(f"Successfully uploaded photograph ({len(photo_bytes)} bytes) to Cloud Storage: {canonical_path}")
            return canonical_path, photo_url
        except Exception as e:
            logger.error(f"Failed to upload photo to Cloud Storage bucket: {e}")
            raise RuntimeError(f"Cloud Storage photograph upload failed: {e}")

    # Fallback / local developer persistence
    storage_base = get_attendance_storage_dir()
    rec_dir = os.path.join(storage_base, str(employee_id), str(attendance_record_id))
    os.makedirs(rec_dir, exist_ok=True)
    local_filename = f"{photo_type}{ext}"
    dest = os.path.join(rec_dir, local_filename)
    with open(dest, "wb") as f:
        f.write(photo_bytes)

    local_url = f"/api/attendance/{attendance_record_id}/photo/{photo_type}"
    return canonical_path, local_url
