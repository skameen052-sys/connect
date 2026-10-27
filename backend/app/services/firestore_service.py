import os
import json
import logging
import threading
from datetime import datetime, date, timezone
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.core.firebase import get_firestore_client, is_firebase_live

logger = logging.getLogger("uvicorn.error")

_local_db_lock = threading.Lock()
LOCAL_DB_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "firestore_local_db.json"
)


def _serialize_val(val: Any) -> Any:
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    return val


def _serialize_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    return {k: _serialize_val(v) for k, v in d.items()}


def _load_local_db() -> Dict[str, List[Dict[str, Any]]]:
    """Load local JSON store used when live Firebase credentials have not yet been provided."""
    with _local_db_lock:
        def _ensure_target_collections(d: dict):
            if "admins" not in d:
                d["admins"] = [u for u in d.get("users", []) if u.get("role") == "admin"]
            if "attendance" not in d:
                d["attendance"] = d.get("attendances", [])
            if "notifications" not in d:
                d["notifications"] = d.get("announcements", [])
            if "officeSettings" not in d:
                d["officeSettings"] = d.get("office_timings", [])
            if "settings" not in d:
                d["settings"] = []
            if "chat_messages" not in d:
                d["chat_messages"] = []
            if "chat_channels" not in d:
                d["chat_channels"] = []
            return d

        if os.path.exists(LOCAL_DB_FILE):
            try:
                with open(LOCAL_DB_FILE, "r", encoding="utf-8") as f:
                    return _ensure_target_collections(json.load(f))
            except Exception as e:
                logger.warning(f"Error loading local db file: {e}")

        # Seed from postgres_backup_data.json if available
        seed_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "postgres_backup_data.json"
        )
        if os.path.exists(seed_path):
            try:
                with open(seed_path, "r", encoding="utf-8") as f:
                    data = _ensure_target_collections(json.load(f))
                    with open(LOCAL_DB_FILE, "w", encoding="utf-8") as out:
                        json.dump(data, out, indent=2)
                    return data
            except Exception as e:
                logger.warning(f"Error seeding local db: {e}")

        default_data = {
            "admins": [],
            "employees": [],
            "attendance": [],
            "notifications": [],
            "officeSettings": [
                {
                    "id": 1,
                    "timing_type": "REGULAR",
                    "startTime": "09:30",
                    "endTime": "18:30",
                    "graceMinutes": 2,
                    "start_time": "09:30",
                    "end_time": "18:30",
                    "grace_minutes": 2,
                    "special_date": None,
                    "special_occasion": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
            "settings": [],
            "users": [],
            "attendances": [],
            "leaves": [],
            "holidays": [],
            "meetings": [],
            "announcements": [],
            "teams": [],
            "assignments": [],
            "work_updates": [],
            "registration_requests": [],
            "office_timings": [],
            "audit_logs": [],
        }
        try:
            with open(LOCAL_DB_FILE, "w", encoding="utf-8") as out:
                json.dump(default_data, out, indent=2)
        except Exception:
            pass
        return default_data


def _save_local_db(data: Dict[str, List[Dict[str, Any]]]) -> None:
    with _local_db_lock:
        try:
            with open(LOCAL_DB_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving local db: {e}")


class FirestoreService:
    """
    Unified Data Access Layer for Cloud Firestore with named database support
    (FIREBASE_DATABASE_NAME) and transparent local resilience.
    """

    @staticmethod
    def get_collection_name(entity: str) -> str:
        """Map canonical entity names to existing Firestore collections."""
        mapping = {
            "admin": "admins",
            "admins": "admins",
            "employee": "employees",
            "employees": "employees",
            "user": "users",
            "users": "users",
            "attendance": "attendance",
            "attendances": "attendance",
            "notification": "notifications",
            "notifications": "notifications",
            "announcement": "announcements",
            "announcements": "announcements",
            "office_timing": "officeSettings",
            "office_timings": "officeSettings",
            "office_config": "officeSettings",
            "officesettings": "officeSettings",
            "officeSettings": "officeSettings",
            "setting": "settings",
            "settings": "settings",
            "leave": "leaves",
            "leaves": "leaves",
            "holiday": "holidays",
            "holidays": "holidays",
            "meeting": "meetings",
            "meetings": "meetings",
            "team": "teams",
            "teams": "teams",
            "assignment": "workAssignments",
            "assignments": "workAssignments",
            "work_assignment": "workAssignments",
            "work_assignments": "workAssignments",
            "workAssignments": "workAssignments",
            "work_update": "work_updates",
            "work_updates": "work_updates",
            "registration_request": "registration_requests",
            "registration_requests": "registration_requests",
            "audit_log": "audit_logs",
            "audit_logs": "audit_logs",
            "chat_message": "chat_messages",
            "chat_messages": "chat_messages",
            "chat_channel": "chat_channels",
            "chat_channels": "chat_channels",
        }
        return mapping.get(entity.lower(), entity)

    @classmethod
    def collection_group(cls, group_id: str, filters: Optional[List[tuple]] = None) -> List[Dict[str, Any]]:
        """Stream documents from all subcollections matching group_id across all parent documents."""
        fs = get_firestore_client()
        if is_firebase_live() and fs is not None:
            try:
                cg = fs.collection_group(group_id)
                if filters:
                    for f in filters:
                        if len(f) == 3:
                            cg = cg.where(f[0], f[1], f[2])
                results = []
                for doc in cg.stream():
                    d = doc.to_dict()
                    d["_firestore_id"] = doc.id
                    d["_doc_path"] = doc.reference.path
                    if doc.reference.parent and doc.reference.parent.parent:
                        d["_parent_id"] = doc.reference.parent.parent.id
                    if "id" not in d:
                        d["id"] = doc.id
                    results.append(d)
                return results
            except Exception as e:
                logger.error(f"Firestore collection_group error on '{group_id}': {e}")

        # Local fallback
        db = _load_local_db()
        results = []
        for k in [group_id, f"cg_{group_id}"]:
            if k in db:
                for item in db[k]:
                    matches = True
                    if filters:
                        for f in filters:
                            if len(f) == 3 and f[1] == "==":
                                if item.get(f[0]) != f[2]:
                                    matches = False
                                    break
                    if matches:
                        results.append(item)
        return results

    @classmethod
    def save_subdocument(cls, collection: str, doc_id: Any, subcollection: str, subdoc_id: Any, data: Dict[str, Any]) -> Dict[str, Any]:
        """Save a document into a subcollection (e.g., attendance/{uid}/records/{date} or leaves/{uid}/requests/{id})."""
        col_name = cls.get_collection_name(collection)
        str_doc_id = str(doc_id)
        str_subdoc_id = str(subdoc_id)
        serialized = _serialize_dict(data)
        serialized["updated_at"] = datetime.now(timezone.utc).isoformat()

        fs = get_firestore_client()
        if is_firebase_live() and fs is not None:
            try:
                fs.collection(col_name).document(str_doc_id).collection(subcollection).document(str_subdoc_id).set(serialized, merge=True)
                serialized["_firestore_id"] = str_subdoc_id
            except Exception as e:
                logger.error(f"Firestore save_subdocument error on '{col_name}/{str_doc_id}/{subcollection}/{str_subdoc_id}': {e}")

        # Local fallback
        db = _load_local_db()
        cg_key = f"cg_{subcollection}"
        if cg_key not in db:
            db[cg_key] = []
        found = False
        for i, item in enumerate(db[cg_key]):
            if str(item.get("id")) == str_subdoc_id or (item.get("date") == serialized.get("date") and item.get("employeeId") == str_doc_id):
                db[cg_key][i] = {**item, **serialized}
                found = True
                break
        if not found:
            if "id" not in serialized:
                serialized["id"] = str_subdoc_id
            db[cg_key].append(serialized)
        _save_local_db(db)
        return serialized

    @classmethod
    def update_subdocument(cls, collection: str, doc_id: Any, subcollection: str, subdoc_id: Any, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update fields on a subcollection document."""
        col_name = cls.get_collection_name(collection)
        str_doc_id = str(doc_id)
        str_subdoc_id = str(subdoc_id)
        serialized = _serialize_dict(updates)
        serialized["updated_at"] = datetime.now(timezone.utc).isoformat()

        fs = get_firestore_client()
        if is_firebase_live() and fs is not None:
            try:
                fs.collection(col_name).document(str_doc_id).collection(subcollection).document(str_subdoc_id).update(serialized)
            except Exception as e:
                logger.error(f"Firestore update_subdocument error on '{col_name}/{str_doc_id}/{subcollection}/{str_subdoc_id}': {e}")

        db = _load_local_db()
        cg_key = f"cg_{subcollection}"
        if cg_key in db:
            for i, item in enumerate(db[cg_key]):
                if str(item.get("id")) == str_subdoc_id or (item.get("date") == serialized.get("date") and item.get("employeeId") == str_doc_id):
                    db[cg_key][i].update(serialized)
                    break
            _save_local_db(db)
        return serialized

    @classmethod
    def delete_subdocument(cls, collection: str, doc_id: Any, subcollection: str, subdoc_id: Any) -> bool:
        """Delete a subcollection document."""
        col_name = cls.get_collection_name(collection)
        str_doc_id = str(doc_id)
        str_subdoc_id = str(subdoc_id)

        fs = get_firestore_client()
        if is_firebase_live() and fs is not None:
            try:
                fs.collection(col_name).document(str_doc_id).collection(subcollection).document(str_subdoc_id).delete()
            except Exception as e:
                logger.error(f"Firestore delete_subdocument error on '{col_name}/{str_doc_id}/{subcollection}/{str_subdoc_id}': {e}")

        db = _load_local_db()
        cg_key = f"cg_{subcollection}"
        if cg_key in db:
            db[cg_key] = [
                item for item in db[cg_key]
                if not (str(item.get("id")) == str_subdoc_id or (item.get("date") == str_subdoc_id and item.get("employeeId") == str_doc_id))
            ]
            _save_local_db(db)
            return True
        return False

    @classmethod
    def list_all(cls, entity: str) -> List[Dict[str, Any]]:
        """Retrieve all documents from a Firestore collection."""
        col_name = cls.get_collection_name(entity)
        fs = get_firestore_client()

        if is_firebase_live() and fs is not None:
            try:
                docs = fs.collection(col_name).stream()
                results = []
                for doc in docs:
                    d = doc.to_dict()
                    d["_firestore_id"] = doc.id
                    if "id" not in d:
                        d["id"] = doc.id
                    results.append(d)
                return results
            except Exception as e:
                logger.error(f"Firestore list_all error on '{col_name}': {e}")

        # Local fallback
        db = _load_local_db()
        key = "attendances" if col_name == "attendance" else col_name
        if key not in db:
            key = col_name
        return list(db.get(key, []))

    @classmethod
    def get_all(cls, entity: str) -> List[Dict[str, Any]]:
        """Alias for list_all."""
        return cls.list_all(entity)

    @classmethod
    def create(cls, entity: str, data: Dict[str, Any], doc_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a document in Firestore with auto-generated ID if omitted."""
        cid = doc_id or (str(data.get("id")) if data.get("id") else f"{entity[:3].upper()}-{int(datetime.now(timezone.utc).timestamp() * 1000)}")
        if "id" not in data:
            data["id"] = cid
        return cls.save(entity, cid, data)

    @classmethod
    def get_by_id(cls, entity: str, doc_id: Any) -> Optional[Dict[str, Any]]:
        """Retrieve single document by ID, checking document ID and secondary fields."""
        col_name = cls.get_collection_name(entity)
        fs = get_firestore_client()
        str_id = str(doc_id).strip()

        if is_firebase_live() and fs is not None:
            try:
                doc_ref = fs.collection(col_name).document(str_id).get()
                if doc_ref.exists:
                    d = doc_ref.to_dict()
                    d["_firestore_id"] = doc_ref.id
                    if "id" not in d:
                        d["id"] = doc_ref.id
                    return d

                # Secondary field matching if document ID did not match directly
                fields_to_check = [
                    "employeeId", "employee_id", "email", "uid",
                    "request_code", "leave_code", "holiday_code",
                    "meeting_code", "announcement_code", "task_code", "update_code"
                ]
                for field in fields_to_check:
                    val = str_id.lower() if field == "email" else str_id
                    docs = list(fs.collection(col_name).where(field, "==", val).limit(1).stream())
                    if not docs and field in ["employeeId", "employee_id"]:
                        docs = list(fs.collection(col_name).where(field, "==", str_id.upper()).limit(1).stream())
                    if docs:
                        d = docs[0].to_dict()
                        d["_firestore_id"] = docs[0].id
                        if "id" not in d:
                            d["id"] = docs[0].id
                        return d

                # If searching leaves collection and not found in top-level, check requests subcollection
                if col_name == "leaves":
                    for c_doc in fs.collection_group("requests").stream():
                        c_dict = c_doc.to_dict()
                        if (
                            c_doc.id == str_id
                            or str(c_dict.get("id")) == str_id
                            or str(c_dict.get("leave_code")) == str_id
                            or str(c_dict.get("leaveCode")) == str_id
                            or str(c_dict.get("_firestore_id")) == str_id
                        ):
                            c_dict["_firestore_id"] = c_doc.id
                            c_dict["_doc_path"] = c_doc.reference.path
                            if c_doc.reference.parent and c_doc.reference.parent.parent:
                                c_dict["_parent_id"] = c_doc.reference.parent.parent.id
                            if "id" not in c_dict:
                                c_dict["id"] = c_doc.id
                            return c_dict
            except Exception as e:
                logger.error(f"Firestore get_by_id error on '{col_name}/{str_id}': {e}")

        # Local fallback
        items = cls.list_all(col_name)
        for item in items:
            if (
                str(item.get("id")) == str_id
                or str(item.get("uid")) == str_id
                or str(item.get("_firestore_id")) == str_id
                or str(item.get("employee_id")).upper() == str_id.upper()
                or str(item.get("employeeId")).upper() == str_id.upper()
                or str(item.get("email", "")).lower() == str_id.lower()
                or str(item.get("request_code")) == str_id
                or str(item.get("leave_code")) == str_id
                or str(item.get("holiday_code")) == str_id
                or str(item.get("meeting_code")) == str_id
                or str(item.get("announcement_code")) == str_id
                or str(item.get("task_code")) == str_id
                or str(item.get("update_code")) == str_id
            ):
                return item

        if col_name == "leaves":
            cg_items = cls.collection_group("requests")
            for item in cg_items:
                if (
                    str(item.get("id")) == str_id
                    or str(item.get("_firestore_id")) == str_id
                    or str(item.get("leave_code")) == str_id
                    or str(item.get("leaveCode")) == str_id
                ):
                    return dict(item)

        return None

    @classmethod
    def save(cls, entity: str, doc_id: Any, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or replace a document in Firestore."""
        col_name = cls.get_collection_name(entity)
        str_id = str(doc_id)
        serialized = _serialize_dict(data)
        serialized["updated_at"] = datetime.now(timezone.utc).isoformat()

        fs = get_firestore_client()
        if is_firebase_live() and fs is not None:
            try:
                fs.collection(col_name).document(str_id).set(serialized, merge=True)
                serialized["_firestore_id"] = str_id
            except Exception as e:
                logger.error(f"Firestore save error on '{col_name}/{str_id}': {e}")

        # Sync local fallback store
        db = _load_local_db()
        key = "attendances" if col_name == "attendance" else col_name
        if key not in db:
            db[key] = []

        found = False
        for i, item in enumerate(db[key]):
            if (
                str(item.get("id")) == str_id
                or str(item.get("employee_id")) == str_id
                or str(item.get("employeeId")) == str_id
                or str(item.get("email", "")).lower() == str_id.lower()
                or str(item.get("request_code")) == str_id
                or str(item.get("leave_code")) == str_id
                or str(item.get("holiday_code")) == str_id
                or str(item.get("meeting_code")) == str_id
                or str(item.get("announcement_code")) == str_id
                or str(item.get("task_code")) == str_id
                or str(item.get("update_code")) == str_id
            ):
                db[key][i] = {**item, **serialized}
                found = True
                break
        if not found:
            if "id" not in serialized:
                serialized["id"] = doc_id
            db[key].append(serialized)
        _save_local_db(db)

        return serialized

    @classmethod
    def update(cls, entity: str, doc_id: Any, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update fields on an existing document."""
        col_name = cls.get_collection_name(entity)
        str_id = str(doc_id)
        serialized = _serialize_dict(updates)
        serialized["updated_at"] = datetime.now(timezone.utc).isoformat()

        fs = get_firestore_client()
        if is_firebase_live() and fs is not None:
            try:
                fs.collection(col_name).document(str_id).update(serialized)
            except Exception as e:
                logger.error(f"Firestore update error on '{col_name}/{str_id}': {e}")

        # Sync local
        db = _load_local_db()
        key = "attendances" if col_name == "attendance" else col_name
        if key not in db:
            db[key] = []

        updated_item = None
        for i, item in enumerate(db[key]):
            if (
                str(item.get("id")) == str_id
                or str(item.get("employee_id")) == str_id
                or str(item.get("employeeId")) == str_id
                or str(item.get("email", "")).lower() == str_id.lower()
                or str(item.get("request_code")) == str_id
                or str(item.get("leave_code")) == str_id
                or str(item.get("holiday_code")) == str_id
                or str(item.get("meeting_code")) == str_id
                or str(item.get("announcement_code")) == str_id
                or str(item.get("task_code")) == str_id
                or str(item.get("update_code")) == str_id
            ):
                db[key][i].update(serialized)
                updated_item = db[key][i]
                break

        _save_local_db(db)
        return updated_item

    @classmethod
    def delete(cls, entity: str, doc_id: Any) -> bool:
        """Delete document by ID."""
        col_name = cls.get_collection_name(entity)
        str_id = str(doc_id)

        fs = get_firestore_client()
        if is_firebase_live() and fs is not None:
            try:
                fs.collection(col_name).document(str_id).delete()
            except Exception as e:
                logger.error(f"Firestore delete error on '{col_name}/{str_id}': {e}")

        db = _load_local_db()
        key = "attendances" if col_name == "attendance" else col_name
        if key in db:
            db[key] = [
                item for item in db[key]
                if not (
                    str(item.get("id")) == str_id
                    or str(item.get("employee_id")) == str_id
                    or str(item.get("request_code")) == str_id
                    or str(item.get("leave_code")) == str_id
                    or str(item.get("holiday_code")) == str_id
                    or str(item.get("task_code")) == str_id
                )
            ]
            _save_local_db(db)
            return True
        return False

    @classmethod
    def query(cls, entity: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter documents matching exact field values."""
        items = cls.list_all(entity)
        results = []
        for item in items:
            matches = True
            for k, v in filters.items():
                if v is None:
                    continue
                item_val = item.get(k)
                if isinstance(item_val, str) and isinstance(v, str):
                    if item_val.lower().strip() != v.lower().strip():
                        matches = False
                        break
                elif item_val != v:
                    matches = False
                    break
            if matches:
                results.append(item)
        return results

    @classmethod
    def add_audit_log(cls, actor_uid: str, action: str, target_record: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record an administrative or employee audit log entry in Firestore."""
        log_id = f"LOG-{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        log_entry = {
            "id": log_id,
            "actor_uid": actor_uid,
            "action": action,
            "target_record": target_record,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        cls.save("audit_logs", log_id, log_entry)


class FirestoreServiceWrapper:
    @staticmethod
    def list_documents(collection: str, filters: Optional[List[tuple]] = None) -> List[Dict[str, Any]]:
        if not filters:
            return FirestoreService.list_all(collection)
        query_dict = {}
        for f in filters:
            if len(f) == 3 and f[1] == "==":
                query_dict[f[0]] = f[2]
        if query_dict:
            return FirestoreService.query(collection, query_dict)
        return FirestoreService.list_all(collection)

    @staticmethod
    def get_document(collection: str, doc_id: Any) -> Optional[Dict[str, Any]]:
        return FirestoreService.get_by_id(collection, str(doc_id))

    @staticmethod
    def create_document(collection: str, data: Dict[str, Any]) -> str:
        doc_id = str(data.get("id")) if data.get("id") else f"{collection[:3].upper()}-{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        if "id" not in data:
            data["id"] = doc_id
        FirestoreService.save(collection, doc_id, data)
        return doc_id

    @staticmethod
    def update_document(collection: str, doc_id: Any, updates: Dict[str, Any]) -> bool:
        res = FirestoreService.update(collection, str(doc_id), updates)
        return res is not None

    @staticmethod
    def delete_document(collection: str, doc_id: Any) -> bool:
        return FirestoreService.delete(collection, str(doc_id))


firestore_service = FirestoreServiceWrapper()
