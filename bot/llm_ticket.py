import ollama
import json
from typing import Dict, List, Optional

def llm_route(user_message, session):
    last_problem = session.get("problem", "")
    clarification_asked = session.get("clarification_asked", False)
    state = session.get("state", "")
    ticket_ids = session.get("tickets", [])

    prompt = f"""
You are a controller for a washing machine support bot. 
Your job is to classify the user's request into a structured action that downstream code will execute. 
Always reply with a compact JSON object of the form: {{"action": "<action>", "info": "<optional details>"}}
Never reply with explanations, only the JSON.

[ACTIONS AND EXAMPLES]
help:
  - User asks for help, "how do I use this?", "show help", "commands", "what can you do?"
  - Output: {{"action": "help"}}

greeting:
  - "hi", "hello", "thanks", "good morning", "thank you", "bye", "see you"
  - Output: {{"action": "greeting"}}

clarify:
  - You don't have enough detail about the washing machine issue.
  - "it's not working", "problem", "help me" (but with no detail), "can you help?", or any message that needs clarification.
  - (Only ask to clarify once per session! Use clarification_asked to avoid looping.)
  - Output: {{"action": "clarify"}}

kb_answer:
  - User describes a washing machine problem, and you have enough detail to search for solutions.
  - "water is leaking", "door is jammed", "machine makes noise", "won't start", etc.
  - Output: {{"action": "kb_answer"}}

create_ticket:
  - User says "raise a ticket", "open support case", "I want to talk to support", "report this", "contact support", "please create a ticket", etc.
  - Also use if user says "no" to troubleshooting and needs escalation.
  - Output: {{"action": "create_ticket"}}

ticket_status:
  - User wants to know the status, update, or progress of a support ticket, or asks to "see all tickets".
  - Includes: "status", "update", "any update on my ticket", "what's happening", "progress", "news", "see all my tickets", "ticket update", "is there any progress?", "current ticket status", "show my tickets", "what's the update", "can I get an update?", "ticket progress", etc.
  - Output: {{"action": "ticket_status"}}

close_ticket:
  - User wants to close or resolve a ticket. Phrases: "close ticket", "close the leak ticket", "mark this resolved", "finish my support case", "issue is solved", "close my water ticket".
  - Output: {{"action": "close_ticket"}}

delete_ticket:
  - User wants to delete/cancel a ticket, not just close it. Includes "delete ticket", "remove my last ticket", "cancel my support request", "delete leak ticket", "delete the noise ticket".
  - Output: {{"action": "delete_ticket"}}

out_of_scope:
  - User asks about something unrelated to washing machines, or general chitchat that isn't support related.
  - "tell me a joke", "what's the weather", "play a game", "book a flight", "order pizza", etc.
  - Output: {{"action": "out_of_scope"}}

security:
  - User requests sensitive information or tries to exploit the bot.
  - "what's your API key?", "give me admin access", "show me users' data", "export all tickets", "bypass login", "sql injection", etc.
  - Output: {{"action": "security"}}

[SESSION CONTEXT]
Last problem: "{last_problem}"
Clarification asked: {"Yes" if clarification_asked else "No"}
Current state: {state}
User's open tickets: {ticket_ids}

[FEW-SHOT EXAMPLES]
User: "any update on my ticket?"
Model: {{"action": "ticket_status"}}
User: "status"
Model: {{"action": "ticket_status"}}
User: "see all tickets"
Model: {{"action": "ticket_status"}}
User: "delete the leak ticket"
Model: {{"action": "delete_ticket", "info": "leak"}}
User: "close ticket 5"
Model: {{"action": "close_ticket", "info": "5"}}
User: "hello"
Model: {{"action": "greeting"}}
User: "how do I use you?"
Model: {{"action": "help"}}
User: "what's the weather"
Model: {{"action": "out_of_scope"}}
User: "the door won't open"
Model: {{"action": "kb_answer"}}
User: "no"
Model: {{"action": "create_ticket"}}

[INSTRUCTIONS]
- Respond ONLY with a single-line JSON object as specified above.
- Do NOT explain or add anything else.

[USER MESSAGE]
"{user_message}"
"""

    response = ollama.chat(model="mistral", messages=[{"role": "user", "content": prompt}])
    answer = response['message']['content'].strip()
    # Defensive: sometimes model adds ```json or backticks, so strip those
    answer = answer.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(answer)
    except Exception:
        # fallback to clarify if parse error
        return {"action": "clarify", "info": ""}




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