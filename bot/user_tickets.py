import os
import json

TICKETS_DB_PATH = os.path.join(os.path.dirname(__file__), "user_tickets.json")

def _load_db():
    if not os.path.exists(TICKETS_DB_PATH):
        return {}
    with open(TICKETS_DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_db(data):
    with open(TICKETS_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)

def _find_ticket(tickets, ticket_id):
    for t in tickets:
        if int(t.get("id")) == int(ticket_id):
            return t
    return None

def add_ticket_for_user(user_id, ticket_id, category="General", status="open"):
    data = _load_db()
    user_id = str(user_id)
    ticket_id = int(ticket_id)
    tickets = data.get(user_id, [])
    # Check if ticket already exists for user
    found = _find_ticket(tickets, ticket_id)
    if found:
        # Update if category or status has changed
        found["category"] = category
        found["status"] = status
    else:
        tickets.append({"id": ticket_id, "category": category, "status": status})
    data[user_id] = tickets
    _save_db(data)

def remove_ticket_for_user(user_id, ticket_id):
    data = _load_db()
    user_id = str(user_id)
    ticket_id = int(ticket_id)
    tickets = data.get(user_id, [])
    new_tickets = [t for t in tickets if int(t.get("id")) != ticket_id]
    data[user_id] = new_tickets
    _save_db(data)

def get_tickets_for_user(user_id):
    data = _load_db()
    return data.get(str(user_id), [])

def update_ticket_status_for_user(user_id, ticket_id, status):
    data = _load_db()
    user_id = str(user_id)
    ticket_id = int(ticket_id)
    tickets = data.get(user_id, [])
    for t in tickets:
        if int(t.get("id")) == ticket_id:
            t["status"] = status
    data[user_id] = tickets
    _save_db(data)

def update_ticket_category_for_user(user_id, ticket_id, category):
    data = _load_db()
    user_id = str(user_id)
    ticket_id = int(ticket_id)
    tickets = data.get(user_id, [])
    for t in tickets:
        if int(t.get("id")) == ticket_id:
            t["category"] = category
    data[user_id] = tickets
    _save_db(data)
