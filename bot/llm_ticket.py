import ollama
import json
from typing import Dict, List, Optional

def llm_route(user_message: str, session: Dict) -> Dict:
    """
    Enhanced LLM routing with better washing machine issue detection.
    Returns dict with action and info (e.g., {"action": "kb_answer", "info": ""})
    """
    last_problem = session.get("problem", "")
    clarification_asked = session.get("clarification_asked", False)
    state = session.get("state", "awaiting_problem")

    prompt = f"""
You are a washing machine support bot controller. Analyze this message and choose the best action:

[USER MESSAGE]
{user_message}

[CONTEXT]
Previous problem: "{last_problem}"
Clarification asked: {"Yes" if clarification_asked else "No"}
Current state: {state}

[ACTIONS]
help - User requests help commands
greeting - Hello/thanks/small talk
clarify - Need more details about washing machine issue (ask only once)
kb_answer - Washing machine problem detected (provide troubleshooting)
create_ticket - Escalate to support ticket
ticket_status - Check ticket status
close_ticket - Close a ticket (extract ID if possible)
delete_ticket - Delete a ticket (extract ID if possible)
out_of_scope - Not washing machine related
security - Sensitive information request

Respond ONLY with JSON like this:
{{"action": "action_name", "info": "additional_details"}}
"""

    try:
        response = ollama.chat(
            model="mistral",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.3}  # More focused
        )
        action = json.loads(response['message']['content'])
        
        # Validation
        valid_actions = ["help", "greeting", "clarify", "kb_answer", "create_ticket", 
                        "ticket_status", "close_ticket", "delete_ticket", "out_of_scope", "security"]
        if action.get("action") not in valid_actions:
            return {"action": "kb_answer", "info": ""}
            
        return action
    except Exception:
        return {"action": "kb_answer", "info": ""}


def llm_parse_ticket_fields(problem_desc: str, projects: List[Dict], categories_by_project: Dict) -> Optional[Dict]:
    """
    Improved ticket field parsing with washing machine-specific guidance.
    Returns: {"summary": "...", "description": "...", "project_name": "...", "category_name": "..."}
    """
    projects_text = "\n".join([f"- {p['name']} (ID: {p['id']})" for p in projects])
    
    categories_text = ""
    for pid, cats in categories_by_project.items():
        pname = next((p['name'] for p in projects if str(p['id']) == str(pid)), f"Project {pid}")
        categories_text += f"{pname}:\n" + "\n".join([f"  - {c['name']}" for c in cats]) + "\n"

    prompt = f"""
You're a washing machine support specialist creating a ticket. Extract:

1. Concise technical summary (under 60 chars)
2. Full problem description
3. Most relevant project
4. Most specific category

[PROBLEM DESCRIPTION]
{problem_desc}

[AVAILABLE PROJECTS]
{projects_text}

[AVAILABLE CATEGORIES]
{categories_text}

Reply ONLY with JSON like this:
{{
  "summary": "Short problem summary",
  "description": "Detailed problem description",
  "project_name": "Exact project name match",
  "category_name": "Exact category name match"
}}
"""
    try:
        response = ollama.chat(
            model="mistral",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.2}  # More precise
        )
        result = json.loads(response['message']['content'])
        
        # Validate project exists
        if not any(p['name'] == result['project_name'] for p in projects):
            return None
            
        return result
    except Exception:
        return None


def llm_pick_ticket_id(user_command: str, open_tickets: List[Dict]) -> Optional[int]:
    """
    Enhanced ticket ID detection from natural language commands.
    Returns ticket ID if confident match found.
    """
    tickets_text = "\n".join([
        f"ID: {t['id']} | Summary: {t.get('summary','')} | Created: {t.get('created_at','')}"
        for t in open_tickets
    ])

    prompt = f"""
User wants to reference a washing machine support ticket. Identify which one:

[USER COMMAND]
"{user_command}" 

[OPEN TICKETS]
{tickets_text}

Rules:
1. Match based on problem description, timing, or explicit ID
2. If uncertain, return "null"
3. Otherwise return ONLY the ticket ID as integer

Respond with either:
- The ticket ID number (e.g., 123)
- "null" if uncertain
"""
    try:
        response = ollama.chat(
            model="mistral",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1}  # Highly deterministic
        )
        content = response['message']['content'].strip()
        return int(content) if content.isdigit() else None
    except Exception:
        return None


def llm_troubleshoot(problem: str, clarification_mode: bool = False) -> Optional[str]:
    """
    Enhanced washing machine troubleshooting with step-by-step guidance.
    Returns formatted troubleshooting steps or None if escalation needed.
    """
    prompt = f"""
As a washing machine technician, provide troubleshooting steps for:

[PROBLEM]
{problem}

Guidelines:
1. Provide 3-5 clear steps
2. Include safety warnings if needed
3. If problem requires professional help, state that
4. Format with clear numbering
5. Keep response under 300 characters

{"[NOTE] User already provided clarification" if clarification_mode else ""}

Respond with either:
- Detailed troubleshooting steps
- "ESCALATE" if professional help needed
"""
    try:
        response = ollama.chat(
            model="mistral",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.5}
        )
        content = response['message']['content'].strip()
        return None if "ESCALATE" in content else content
    except Exception:
        return None