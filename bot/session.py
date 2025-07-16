import os
import json
import time

SESSIONS_DIR = os.path.join(os.path.dirname(__file__), 'sessions')
os.makedirs(SESSIONS_DIR, exist_ok=True)

SESSION_TIMEOUT = 600  # 10 minutes in seconds

def _session_path(user_id):
    return os.path.join(SESSIONS_DIR, f"{user_id}.json")

def session_exists(user_id):
    return os.path.exists(_session_path(user_id))

def create_session(user_id):
    data = {
        "user_id": user_id,
        "tickets": [],
        "history": [],
        "state": "awaiting_problem",
        "clarification_asked": False,
        "last_problem": "",
        "last_active": time.time()
    }
    with open(_session_path(user_id), 'w', encoding='utf-8') as f:
        json.dump(data, f)

def get_session(user_id):
    path = _session_path(user_id)
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def save_session(user_id, data):
    data['last_active'] = time.time()
    with open(_session_path(user_id), 'w', encoding='utf-8') as f:
        json.dump(data, f)

def clear_session(user_id):
    path = _session_path(user_id)
    if os.path.exists(path):
        os.remove(path)

def update_session(user_id, **kwargs):
    session = get_session(user_id)
    if not session:
        return
    session.update(kwargs)
    save_session(user_id, session)

def add_ticket_to_session(user_id, ticket_id):
    session = get_session(user_id)
    if not session:
        return
    tickets = session.get("tickets", [])
    if ticket_id not in tickets:
        tickets.append(ticket_id)
    session["tickets"] = tickets
    save_session(user_id, session)

def remove_ticket_from_session(user_id, ticket_id):
    session = get_session(user_id)
    if not session:
        return
    tickets = session.get("tickets", [])
    if ticket_id in tickets:
        tickets.remove(ticket_id)
    session["tickets"] = tickets
    save_session(user_id, session)

def log_history(user_id, from_role, text):
    session = get_session(user_id)
    if not session:
        return
    session.setdefault("history", []).append({"from": from_role, "text": text})
    save_session(user_id, session)

def session_expired(user_id):
    """
    Returns True if the session exists but is older than SESSION_TIMEOUT seconds.
    """
    session = get_session(user_id)
    if not session:
        return True
    last_active = session.get("last_active", 0)
    return (time.time() - last_active) > SESSION_TIMEOUT
