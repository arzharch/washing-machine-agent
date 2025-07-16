import json
import os
import ollama

KB_PATH = os.path.join(os.path.dirname(__file__), 'knowledge_base.json')

with open(KB_PATH, encoding='utf-8') as f:
    KB_DATA = json.load(f)

OUT_OF_SCOPE_KEYWORDS = [
    "joke", "funny", "laugh", "weather", "news", "song", "music", "python", "java", "write code", "script", "draw", "art"
]

def is_out_of_scope(text):
    lowered = text.lower()
    return any(kw in lowered for kw in OUT_OF_SCOPE_KEYWORDS)

def llm_troubleshoot(user_message, kb_data=KB_DATA, clarification_mode=False):
    if is_out_of_scope(user_message):
        return "Sorry, I can only help with washing machine problems. Please describe your washing machine issue."

    kb_snippets = []
    for issue in kb_data["issues"].values():
        kb_snippets.append(
            f"{issue['title']}: {issue['description']} (Keywords: {', '.join(issue['keywords'])})"
        )
    kb_text = "\n".join(kb_snippets)

    prompt = f"""
You are a washing machine support assistant.

Rules:
- If the user's question is NOT about washing machines, reply only with: "Sorry, I can only help with washing machine problems."
- If the user is asking for jokes, music, weather, or code, reply only with: "Sorry, I can only help with washing machine problems."
- {"If the user's description is too vague or unclear, reply with: 'Can you please clarify your washing machine issue with more detail?' (do this only once per problem)." if not clarification_mode else ""}
- Otherwise, use the knowledge base below to provide the most helpful advice, using the KB as a reference. If you cannot find a relevant problem, reply only with: "NO_KB_MATCH".

User Question:
\"\"\"{user_message}\"\"\"

Knowledge Base:
{kb_text}
    """

    response = ollama.chat(model='mistral', messages=[
        {'role': 'user', 'content': prompt}
    ])
    answer = response['message']['content'].strip()
    if answer == "NO_KB_MATCH":
        return None
    return answer

def llm_parse_ticket_fields(user_message, projects, categories_by_project):
    """
    Parse user message to extract ticket fields using LLM.
    
    Args:
        user_message (str): The user's support request message
        projects (list): List of project dictionaries containing 'id' and 'name'
        categories_by_project (dict): Dictionary mapping project IDs to category lists
        
    Returns:
        dict: Parsed ticket fields or None if parsing fails
    """
    # Prepare structured context for LLM
    projects_text = "\n".join([f"- {p['name']}" for p in projects])
    categories_text = ""
    for pid, cats in categories_by_project.items():
        pname = next((p['name'] for p in projects if str(p['id']) == str(pid)), pid)
        categories_text += f"{pname}: {', '.join([c['name'] for c in cats])}\n"

    prompt = f"""
You are a customer support assistant for washing machines.  
Given the user's request, and the available projects and categories, generate a JSON object like:

{{
  "summary": "...",           // short summary for support staff
  "description": "...",       // full user message
  "project_name": "...",      // choose the best project
  "category_name": "..."      // choose the best category for the problem
}}

If you cannot confidently pick a category, reply only with: "UNCERTAIN".

Projects:
{projects_text}

Categories by project:
{categories_text}

User message:
\"\"\"{user_message}\"\"\"
"""
    response = ollama.chat(model="mistral", messages=[
        {"role": "user", "content": prompt}
    ])
    answer = response['message']['content'].strip()
    
    if answer == "UNCERTAIN":
        return None
        
    try:
        return json.loads(answer)
    except Exception:
        return None

