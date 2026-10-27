import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Set
from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.services.firestore_service import firestore_service, FirestoreService
from app.dependencies.auth import get_current_user
from app.core.security import decode_access_token
from app.core.firebase import verify_firebase_token

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/chat", tags=["Teams Chat"])


# ==============================================================================
# WebSocket Real-Time Connection Manager
# ==============================================================================
class ConnectionManager:
    """Manages active WebSocket connections for instant real-time dispatch."""

    def __init__(self):
        # Maps user key (str) -> Set of active WebSocket instances
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Set of currently active user keys (for presence)
        self.online_users: Set[str] = set()

    def _normalize_key(self, key: Any) -> str:
        return str(key).strip().lower() if key else ""

    async def connect(self, websocket: WebSocket, user_keys: List[str]):
        await websocket.accept()
        for k in user_keys:
            norm = self._normalize_key(k)
            if not norm:
                continue
            if norm not in self.active_connections:
                self.active_connections[norm] = set()
            self.active_connections[norm].add(websocket)
            self.online_users.add(norm)

    def disconnect(self, websocket: WebSocket, user_keys: List[str]):
        for k in user_keys:
            norm = self._normalize_key(k)
            if not norm:
                continue
            if norm in self.active_connections:
                self.active_connections[norm].discard(websocket)
                if not self.active_connections[norm]:
                    del self.active_connections[norm]
                    self.online_users.discard(norm)

    def is_user_online(self, user_key: Any) -> bool:
        norm = self._normalize_key(user_key)
        return norm in self.online_users and len(self.active_connections.get(norm, set())) > 0

    async def broadcast_to_keys(self, user_keys: List[str], event: dict):
        sent_sockets: Set[WebSocket] = set()
        for k in user_keys:
            norm = self._normalize_key(k)
            if norm in self.active_connections:
                for ws in list(self.active_connections[norm]):
                    if ws not in sent_sockets:
                        try:
                            await ws.send_text(json.dumps(event))
                            sent_sockets.add(ws)
                        except Exception as e:
                            logger.debug(f"Failed to send to socket: {e}")

    async def broadcast_all(self, event: dict):
        sent_sockets: Set[WebSocket] = set()
        for sockets in self.active_connections.values():
            for ws in list(sockets):
                if ws not in sent_sockets:
                    try:
                        await ws.send_text(json.dumps(event))
                        sent_sockets.add(ws)
                    except Exception:
                        pass


manager = ConnectionManager()


# ==============================================================================
# Helper functions to extract user identities
# ==============================================================================
def get_user_identifiers(user: Any) -> Dict[str, str]:
    """Extract primary ID, employee ID, email, role, and display name."""
    role = str(getattr(user, "role", "employee")).strip().lower()
    email = str(getattr(user, "email", "")).strip().lower()
    emp_id = str(getattr(user, "employee_id", None) or getattr(user, "employeeId", None) or "").strip()
    uid = str(getattr(user, "id", None) or getattr(user, "uid", None) or "").strip()
    name = (
        getattr(user, "full_name", None)
        or getattr(user, "fullName", None)
        or getattr(user, "name", None)
        or (email.split("@")[0].title() if email else "User")
    )

    primary_id = emp_id if emp_id else (uid if uid else email)
    if role == "admin" and not emp_id:
        primary_id = "ADM-001"

    return {
        "primary_id": primary_id,
        "employee_id": emp_id,
        "uid": uid,
        "email": email,
        "role": role,
        "name": name,
    }


def get_all_user_keys(identifiers: Dict[str, str]) -> List[str]:
    """Return all unique keys that represent this user in messaging."""
    keys = []
    for k in ["primary_id", "employee_id", "uid", "email", "name"]:
        val = identifiers.get(k)
        if val and str(val).strip():
            keys.append(str(val).strip().lower())
    if identifiers.get("role") == "admin":
        keys.extend(["admin", "adm-001", "administrator"])
    return list(set(keys))


def user_matches_target(identifiers: Dict[str, str], target: Any) -> bool:
    """Check if target string matches any of the user's keys."""
    if not target:
        return False
    target_norm = str(target).strip().lower()
    return target_norm in get_all_user_keys(identifiers)


# ==============================================================================
# Pydantic Schemas
# ==============================================================================
class MessageCreate(BaseModel):
    chat_type: str  # "direct" or "team"
    target_id: str  # recipient employee_id/email OR team_id
    content: str
    attachments: Optional[List[Dict[str, Any]]] = []
    reply_to: Optional[Dict[str, Any]] = None


class ReactionToggle(BaseModel):
    emoji: str


class MarkReadRequest(BaseModel):
    chat_type: str
    target_id: str


# ==============================================================================
# REST Endpoints
# ==============================================================================

@router.get("/contacts", response_model=List[Dict[str, Any]])
def get_contacts(current_user=Depends(get_current_user)):
    """
    List all available contacts for 1:1 direct chat, including registered employees
    and administrator accounts, with department, designation, and presence.
    """
    my_ids = get_user_identifiers(current_user)
    my_keys = set(get_all_user_keys(my_ids))

    contacts = []
    seen_ids = set()

    # 1. Administrator contact (available for all employees)
    admin_contact = {
        "id": "ADM-001",
        "employee_id": "ADM-001",
        "name": "Administrator",
        "email": "admin@arshith.com",
        "role": "admin",
        "department": "Administration",
        "designation": "Executive Administration",
        "avatar": "A",
        "is_online": manager.is_user_online("ADM-001") or manager.is_user_online("admin@arshith.com"),
    }
    if "adm-001" not in my_keys and "admin@arshith.com" not in my_keys:
        contacts.append(admin_contact)
        seen_ids.add("adm-001")
        seen_ids.add("admin@arshith.com")

    # 2. Registered Employees
    employees = firestore_service.list_documents("employees")
    for emp in employees:
        e_id = str(emp.get("employee_id") or emp.get("employeeId") or emp.get("id") or "").strip()
        e_email = str(emp.get("email", "")).strip().lower()
        e_name = emp.get("full_name") or emp.get("name") or "Employee"

        if not e_id and not e_email:
            continue

        # Skip self
        if e_id.lower() in my_keys or e_email in my_keys:
            continue

        # Avoid duplicates
        key_check = (e_id or e_email).lower()
        if key_check in seen_ids:
            continue
        seen_ids.add(key_check)
        if e_email:
            seen_ids.add(e_email)

        is_online = manager.is_user_online(e_id) or manager.is_user_online(e_email)

        contacts.append({
            "id": e_id or str(emp.get("id")),
            "employee_id": e_id,
            "name": e_name,
            "email": e_email,
            "role": "employee",
            "department": emp.get("department", "Operations"),
            "designation": emp.get("designation", "Staff Member"),
            "avatar": e_name[0].upper() if e_name else "E",
            "is_online": is_online,
        })

    contacts.sort(key=lambda c: (c["role"] != "admin", c["name"].lower()))
    return contacts


@router.get("/teams", response_model=List[Dict[str, Any]])
def get_teams_for_chat(current_user=Depends(get_current_user)):
    """
    List all teams accessible to the user for team channels.
    Admins have access to all teams; employees have access to teams they belong to
    plus company-wide general teams.
    """
    my_ids = get_user_identifiers(current_user)
    is_admin = my_ids["role"] == "admin"
    my_name = my_ids["name"].strip().lower()
    my_emp_id = my_ids["employee_id"].strip().lower()

    all_teams = firestore_service.list_documents("teams")
    accessible_teams = []

    for t in all_teams:
        t_id = str(t.get("id"))
        t_name = t.get("name") or t.get("teamName") or "Team"
        members = t.get("members", [])
        if not isinstance(members, list):
            members = []

        # Check membership
        is_member = False
        if is_admin:
            is_member = True
        elif "general" in t_name.lower() or "all company" in t_name.lower():
            is_member = True
        else:
            for m in members:
                m_str = str(m).strip().lower()
                if m_str == my_name or m_str == my_emp_id:
                    is_member = True
                    break

        if is_member:
            accessible_teams.append({
                "id": t_id,
                "name": t_name,
                "department": t.get("department", "Operations"),
                "description": t.get("description", ""),
                "leader": t.get("leader", "Unassigned"),
                "members": members,
                "member_count": len(members),
                "is_admin": is_admin,
            })

    accessible_teams.sort(key=lambda x: (not ("general" in x["name"].lower()), x["name"].lower()))
    return accessible_teams


@router.get("/conversations", response_model=List[Dict[str, Any]])
def get_conversations(current_user=Depends(get_current_user)):
    """
    Returns an aggregated list of conversations (Direct chats and Team channels)
    for the current user, complete with latest message preview, unread counts, and timestamps.
    """
    my_ids = get_user_identifiers(current_user)
    my_keys = set(get_all_user_keys(my_ids))
    is_admin = my_ids["role"] == "admin"

    # 1. Fetch all chat messages
    messages = firestore_service.list_documents("chat_messages")
    messages.sort(key=lambda m: str(m.get("created_at", "")), reverse=True)

    # 2. Fetch accessible teams
    accessible_teams = get_teams_for_chat(current_user)
    team_map = {str(t["id"]): t for t in accessible_teams}
    # Also map team by name
    for t in accessible_teams:
        team_map[t["name"].lower()] = t

    conversations_dict: Dict[str, Dict[str, Any]] = {}

    # Seed all accessible teams as conversation channels
    for t in accessible_teams:
        cid = f"team_{t['id']}"
        conversations_dict[cid] = {
            "conversation_id": cid,
            "type": "team",
            "target_id": str(t["id"]),
            "title": t["name"],
            "subtitle": f"{t.get('department', 'Company')} • {t.get('member_count', 0)} members",
            "avatar": "#",
            "leader": t.get("leader"),
            "last_message": "No messages yet",
            "last_message_sender": "",
            "last_message_at": t.get("created_at") or "",
            "unread_count": 0,
            "is_pinned": "general" in t["name"].lower(),
            "is_online": False,
        }

    # Track direct contacts who have exchanged messages
    direct_conversations: Dict[str, Dict[str, Any]] = {}

    for msg in messages:
        c_type = msg.get("chat_type", "direct")
        sender_id = str(msg.get("sender_id", "")).strip().lower()
        receiver_id = str(msg.get("receiver_id", msg.get("target_id", ""))).strip().lower()
        read_by = msg.get("read_by", [])
        if not isinstance(read_by, list):
            read_by = []
        read_by_norm = {str(r).strip().lower() for r in read_by}
        is_unread = not bool(my_keys.intersection(read_by_norm))

        if c_type == "team":
            # Match team conversation
            t_key = str(msg.get("team_id") or msg.get("target_id", "")).strip()
            cid = f"team_{t_key}"
            if cid in conversations_dict:
                conv = conversations_dict[cid]
                if conv["last_message"] == "No messages yet":
                    conv["last_message"] = msg.get("content", "")
                    conv["last_message_sender"] = msg.get("sender_name", "")
                    conv["last_message_at"] = msg.get("created_at", "")
                if is_unread and sender_id not in my_keys:
                    conv["unread_count"] += 1

        elif c_type == "direct":
            # Check if this user is a participant
            user_is_sender = sender_id in my_keys
            user_is_receiver = receiver_id in my_keys

            if user_is_sender or user_is_receiver:
                other_key = receiver_id if user_is_sender else sender_id
                cid = f"direct_{other_key}"

                if cid not in direct_conversations:
                    direct_conversations[cid] = {
                        "conversation_id": cid,
                        "type": "direct",
                        "target_id": other_key,
                        "title": msg.get("sender_name" if user_is_receiver else "receiver_name") or other_key.title(),
                        "subtitle": "Direct Chat",
                        "avatar": (msg.get("sender_name") or other_key)[0].upper(),
                        "last_message": msg.get("content", ""),
                        "last_message_sender": msg.get("sender_name", ""),
                        "last_message_at": msg.get("created_at", ""),
                        "unread_count": 0,
                        "is_pinned": False,
                        "is_online": manager.is_user_online(other_key),
                    }
                if is_unread and not user_is_sender:
                    direct_conversations[cid]["unread_count"] += 1

    # Enrich direct conversations with real contact details
    all_contacts = get_contacts(current_user)
    contact_lookup: Dict[str, Dict[str, Any]] = {}
    for c in all_contacts:
        contact_lookup[str(c["id"]).lower()] = c
        if c.get("employee_id"):
            contact_lookup[str(c["employee_id"]).lower()] = c
        if c.get("email"):
            contact_lookup[str(c["email"]).lower()] = c

    for cid, d_conv in direct_conversations.items():
        t_id = d_conv["target_id"].lower()
        if t_id in contact_lookup:
            c_info = contact_lookup[t_id]
            d_conv["title"] = c_info["name"]
            d_conv["subtitle"] = f"{c_info.get('designation', '')} • {c_info.get('department', '')}"
            d_conv["avatar"] = c_info["avatar"]
            d_conv["is_online"] = c_info["is_online"]

    # Combine teams and direct conversations
    results = list(conversations_dict.values()) + list(direct_conversations.values())

    # Sort: Pinned first, then newest message first
    results.sort(
        key=lambda c: (
            c.get("is_pinned", False),
            str(c.get("last_message_at", "")),
        ),
        reverse=True,
    )

    return results


@router.get("/messages", response_model=List[Dict[str, Any]])
def get_messages(
    chat_type: str = Query(..., description="'direct' or 'team'"),
    target_id: str = Query(..., description="Recipient ID or Team ID"),
    limit: int = Query(60, ge=1, le=200),
    current_user=Depends(get_current_user),
):
    """
    Retrieve message history for direct chat or team channel.
    Automatically marks incoming messages as read for the current user.
    """
    my_ids = get_user_identifiers(current_user)
    my_keys = set(get_all_user_keys(my_ids))
    target_clean = str(target_id).strip()
    target_norm = target_clean.lower()

    all_msgs = firestore_service.list_documents("chat_messages")
    filtered: List[Dict[str, Any]] = []
    messages_to_mark_read: List[str] = []

    for msg in all_msgs:
        m_type = msg.get("chat_type", "direct")
        if m_type != chat_type:
            continue

        if chat_type == "team":
            # Match team_id or target_id
            m_team_id = str(msg.get("team_id") or msg.get("target_id", "")).strip().lower()
            if m_team_id == target_norm:
                filtered.append(msg)
                # Check unread
                read_by = msg.get("read_by", [])
                if not isinstance(read_by, list):
                    read_by = []
                if not my_keys.intersection({str(r).lower() for r in read_by}):
                    messages_to_mark_read.append(str(msg.get("id")))

        elif chat_type == "direct":
            # Direct chat between current user and target
            sender = str(msg.get("sender_id", "")).strip().lower()
            receiver = str(msg.get("receiver_id", msg.get("target_id", ""))).strip().lower()

            is_my_msg = sender in my_keys and (receiver == target_norm or receiver in [target_norm, "adm-001", "admin@arshith.com"])
            is_their_msg = (sender == target_norm or sender in [target_norm, "adm-001", "admin@arshith.com"]) and receiver in my_keys

            if is_my_msg or is_their_msg:
                filtered.append(msg)
                if is_their_msg:
                    read_by = msg.get("read_by", [])
                    if not isinstance(read_by, list):
                        read_by = []
                    if not my_keys.intersection({str(r).lower() for r in read_by}):
                        messages_to_mark_read.append(str(msg.get("id")))

    # Mark as read in storage
    if messages_to_mark_read:
        for mid in messages_to_mark_read:
            doc = firestore_service.get_document("chat_messages", mid)
            if doc:
                r_list = doc.get("read_by", [])
                if not isinstance(r_list, list):
                    r_list = []
                if my_ids["primary_id"] not in r_list:
                    r_list.append(my_ids["primary_id"])
                    firestore_service.update_document("chat_messages", mid, {"read_by": r_list})

    # Sort chronologically (oldest to newest)
    filtered.sort(key=lambda m: str(m.get("created_at", "")))
    return filtered[-limit:]


@router.post("/messages", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
async def send_message(
    payload: MessageCreate,
    current_user=Depends(get_current_user),
):
    """
    Send a message in a 1:1 direct chat or a Team channel.
    Persists to database and immediately pushes via WebSocket to connected recipients.
    """
    content = payload.content.strip()
    if not content and not payload.attachments:
        raise HTTPException(status_code=400, detail="Message content or attachment is required.")

    my_ids = get_user_identifiers(current_user)
    now_iso = datetime.now(timezone.utc).isoformat()
    clean_target = payload.target_id.strip()

    team_name = ""
    recipient_name = ""
    recipient_keys: List[str] = []

    if payload.chat_type == "team":
        # Resolve team details and member keys
        team = firestore_service.get_document("teams", clean_target)
        if not team:
            all_teams = firestore_service.list_documents("teams")
            for t in all_teams:
                if str(t.get("id")) == clean_target or (t.get("name") or "").lower() == clean_target.lower():
                    team = t
                    break
        if team:
            team_name = team.get("name") or team.get("teamName") or "Team Channel"
            # Team broadcast targets: all members + administrators
            members = team.get("members", [])
            for m in members:
                recipient_keys.append(str(m).strip().lower())
        recipient_keys.extend(["admin", "adm-001", "admin@arshith.com"])

    else:
        # Direct message
        recipient_keys = [clean_target.lower()]
        # Resolve recipient display name
        if clean_target.lower() in ["admin", "adm-001", "admin@arshith.com"]:
            recipient_name = "Administrator"
            recipient_keys.extend(["admin", "adm-001", "admin@arshith.com"])
        else:
            emp = firestore_service.get_document("employees", clean_target)
            if not emp:
                emps = firestore_service.list_documents("employees", [("employee_id", "==", clean_target)])
                if emps:
                    emp = emps[0]
            if emp:
                recipient_name = emp.get("full_name") or emp.get("name") or clean_target
                if emp.get("employee_id"):
                    recipient_keys.append(str(emp["employee_id"]).lower())
                if emp.get("email"):
                    recipient_keys.append(str(emp["email"]).lower())

    msg_data = {
        "chat_type": payload.chat_type,
        "target_id": clean_target,
        "team_id": clean_target if payload.chat_type == "team" else None,
        "team_name": team_name,
        "sender_id": my_ids["primary_id"],
        "sender_name": my_ids["name"],
        "sender_role": my_ids["role"],
        "sender_avatar": my_ids["name"][0].upper() if my_ids["name"] else "U",
        "receiver_id": clean_target,
        "receiver_name": recipient_name or team_name,
        "content": content,
        "attachments": payload.attachments or [],
        "reply_to": payload.reply_to,
        "reactions": {},
        "is_pinned": False,
        "read_by": [my_ids["primary_id"]],
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    doc_id = firestore_service.create_document("chat_messages", msg_data)
    msg_data["id"] = doc_id

    # Broadcast real-time event via WebSocket
    event_payload = {
        "type": "new_message",
        "message": msg_data,
    }
    # Send to recipients + sender's own devices
    all_targets = list(set(recipient_keys + get_all_user_keys(my_ids)))
    await manager.broadcast_to_keys(all_targets, event_payload)

    return msg_data


@router.post("/messages/{message_id}/reactions", response_model=Dict[str, Any])
async def toggle_reaction(
    message_id: str,
    payload: ReactionToggle,
    current_user=Depends(get_current_user),
):
    """Toggle an emoji reaction (👍, ❤️, 👏, 🎉, 🚀) on a message."""
    my_ids = get_user_identifiers(current_user)
    user_key = my_ids["primary_id"]

    doc = firestore_service.get_document("chat_messages", message_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Message not found")

    reactions = doc.get("reactions", {})
    if not isinstance(reactions, dict):
        reactions = {}

    emoji = payload.emoji.strip()
    if not emoji:
        raise HTTPException(status_code=400, detail="Emoji character is required")

    user_list = reactions.get(emoji, [])
    if not isinstance(user_list, list):
        user_list = []

    if user_key in user_list:
        user_list.remove(user_key)
        if not user_list:
            del reactions[emoji]
        else:
            reactions[emoji] = user_list
    else:
        user_list.append(user_key)
        reactions[emoji] = user_list

    firestore_service.update_document("chat_messages", message_id, {"reactions": reactions})

    # Broadcast update
    event = {
        "type": "reaction_updated",
        "message_id": message_id,
        "reactions": reactions,
    }
    await manager.broadcast_all(event)

    return {"success": True, "reactions": reactions}


@router.post("/messages/{message_id}/pin", response_model=Dict[str, Any])
async def toggle_pin(
    message_id: str,
    current_user=Depends(get_current_user),
):
    """Toggle pinned status on a message."""
    doc = firestore_service.get_document("chat_messages", message_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Message not found")

    current_pinned = bool(doc.get("is_pinned", False))
    new_pinned = not current_pinned

    firestore_service.update_document("chat_messages", message_id, {"is_pinned": new_pinned})

    event = {
        "type": "pin_updated",
        "message_id": message_id,
        "is_pinned": new_pinned,
    }
    await manager.broadcast_all(event)

    return {"success": True, "is_pinned": new_pinned}


@router.delete("/messages/{message_id}", response_model=Dict[str, Any])
async def delete_message(
    message_id: str,
    current_user=Depends(get_current_user),
):
    """Delete a message (allowed by message author or administrator)."""
    my_ids = get_user_identifiers(current_user)
    my_keys = set(get_all_user_keys(my_ids))

    doc = firestore_service.get_document("chat_messages", message_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Message not found")

    sender_id = str(doc.get("sender_id", "")).strip().lower()
    is_admin = my_ids["role"] == "admin"

    if sender_id not in my_keys and not is_admin:
        raise HTTPException(status_code=403, detail="You can only delete your own messages.")

    firestore_service.delete_document("chat_messages", message_id)

    event = {
        "type": "message_deleted",
        "message_id": message_id,
    }
    await manager.broadcast_all(event)

    return {"success": True, "message": "Message deleted successfully."}


@router.post("/read", response_model=Dict[str, Any])
def mark_conversation_read(
    payload: MarkReadRequest,
    current_user=Depends(get_current_user),
):
    """Mark all unread messages in a conversation as read for the current user."""
    my_ids = get_user_identifiers(current_user)
    my_keys = set(get_all_user_keys(my_ids))
    target_clean = payload.target_id.strip()
    target_norm = target_clean.lower()

    messages = firestore_service.list_documents("chat_messages")
    updated_count = 0

    for msg in messages:
        if msg.get("chat_type") != payload.chat_type:
            continue

        should_mark = False
        if payload.chat_type == "team":
            m_team = str(msg.get("team_id") or msg.get("target_id", "")).strip().lower()
            if m_team == target_norm:
                should_mark = True
        elif payload.chat_type == "direct":
            sender = str(msg.get("sender_id", "")).strip().lower()
            receiver = str(msg.get("receiver_id", msg.get("target_id", ""))).strip().lower()
            if (sender == target_norm or sender in [target_norm, "adm-001", "admin@arshith.com"]) and receiver in my_keys:
                should_mark = True

        if should_mark:
            read_by = msg.get("read_by", [])
            if not isinstance(read_by, list):
                read_by = []
            if my_ids["primary_id"] not in read_by:
                read_by.append(my_ids["primary_id"])
                firestore_service.update_document("chat_messages", str(msg.get("id")), {"read_by": read_by})
                updated_count += 1

    return {"success": True, "marked_count": updated_count}


@router.get("/unread-count", response_model=Dict[str, int])
def get_unread_count(current_user=Depends(get_current_user)):
    """Fast check for total unread chat messages for application navbar badges."""
    my_ids = get_user_identifiers(current_user)
    my_keys = set(get_all_user_keys(my_ids))

    messages = firestore_service.list_documents("chat_messages")
    unread = 0

    for msg in messages:
        sender_id = str(msg.get("sender_id", "")).strip().lower()
        if sender_id in my_keys:
            continue

        read_by = msg.get("read_by", [])
        if not isinstance(read_by, list):
            read_by = []
        read_by_norm = {str(r).strip().lower() for r in read_by}

        if bool(my_keys.intersection(read_by_norm)):
            continue

        c_type = msg.get("chat_type", "direct")
        if c_type == "direct":
            receiver_id = str(msg.get("receiver_id", msg.get("target_id", ""))).strip().lower()
            if receiver_id in my_keys:
                unread += 1
        elif c_type == "team":
            unread += 1

    return {"total_unread": unread}


# ==============================================================================
# WebSocket Endpoint
# ==============================================================================
@router.websocket("/ws")
async def chat_websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    Real-time WebSocket connection for instant chat delivery, typing indicators,
    and online presence notifications.
    """
    # 1. Authenticate token
    user_data = None
    if token:
        payload = decode_access_token(token)
        if payload:
            user_data = {
                "id": payload.get("sub"),
                "role": payload.get("role", "employee"),
                "email": payload.get("email"),
                "employee_id": payload.get("employeeId") or payload.get("employee_id"),
            }
        else:
            fb = verify_firebase_token(token)
            if fb:
                user_data = {
                    "id": fb.get("uid"),
                    "role": fb.get("role") or ("admin" if fb.get("admin") else "employee"),
                    "email": fb.get("email"),
                }

    if not user_data:
        # Fallback for dev mode
        user_data = {"id": "ADM-001", "role": "admin", "email": "admin@arshith.com"}

    class TempUser:
        pass
    tu = TempUser()
    for k, v in user_data.items():
        setattr(tu, k, v)

    user_ids = get_user_identifiers(tu)
    user_keys = get_all_user_keys(user_ids)

    await manager.connect(websocket, user_keys)
    # Broadcast presence
    await manager.broadcast_all({
        "type": "presence",
        "user_id": user_ids["primary_id"],
        "status": "online",
    })

    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                data = json.loads(data_text)
                action = data.get("action")

                if action == "typing":
                    # Broadcast typing status to recipients
                    target_id = str(data.get("target_id", "")).strip().lower()
                    chat_type = data.get("chat_type", "direct")
                    event = {
                        "type": "typing",
                        "sender_id": user_ids["primary_id"],
                        "sender_name": user_ids["name"],
                        "chat_type": chat_type,
                        "target_id": target_id,
                        "is_typing": bool(data.get("is_typing", True)),
                    }
                    if chat_type == "direct":
                        await manager.broadcast_to_keys([target_id], event)
                    else:
                        await manager.broadcast_all(event)

                elif action == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_keys)
        await manager.broadcast_all({
            "type": "presence",
            "user_id": user_ids["primary_id"],
            "status": "offline",
        })
    except Exception as e:
        logger.debug(f"Chat websocket closed with error: {e}")
        manager.disconnect(websocket, user_keys)
