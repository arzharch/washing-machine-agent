import os
import discord
from dotenv import load_dotenv

from mantishub.client import MantisHubClient
from bot.session import (
    session_exists, create_session, get_session, save_session, clear_session,
    update_session, add_ticket_to_session, remove_ticket_from_session, log_history, session_expired
)
from bot.user_tickets import (
    add_ticket_for_user, remove_ticket_for_user, get_tickets_for_user,
    update_ticket_status_for_user, update_ticket_category_for_user
)
from bot.kb import llm_troubleshoot
from bot.llm_ticket import (
    llm_route,
    llm_parse_ticket_fields,
    llm_pick_ticket_id
)

load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.messages = True
intents.dm_messages = True

client = discord.Client(intents=intents)
mh_client = MantisHubClient()

def preserve_tickets_on_reset(user_id):
    session = get_session(user_id)
    old_tickets = session.get("tickets", []) if session else []
    clear_session(user_id)
    create_session(user_id)
    update_session(user_id, tickets=old_tickets)

def push_action(user_id, action):
    session = get_session(user_id)
    stack = session.get("action_stack", [])
    stack.append(action)
    update_session(user_id, action_stack=stack)

def pop_action(user_id):
    session = get_session(user_id)
    stack = session.get("action_stack", [])
    if stack:
        last_action = stack.pop()
        update_session(user_id, action_stack=stack)
        return last_action
    return None

def peek_action(user_id):
    session = get_session(user_id)
    stack = session.get("action_stack", [])
    return stack[-1] if stack else None

def clear_action_stack(user_id):
    update_session(user_id, action_stack=[])

def unpack_mantis_ticket(remote):
    if isinstance(remote, dict) and "issues" in remote and isinstance(remote["issues"], list) and len(remote["issues"]) > 0:
        return remote["issues"][0]
    return remote

async def send_help(dm):
    await dm.send(
        "**Washing-Machine Bot Help:**\n"
        "- Type your washing machine problem to get help or troubleshooting.\n"
        "- Say things like 'any update on my ticket', 'delete my leak ticket', 'close ticket 15', etc.\n"
        "- Type `status` to see your tickets, or `reset` to restart the session."
    )

@client.event
async def on_ready():
    print(f'Logged in as {client.user}!')

@client.event
async def on_message(message):
    if message.author == client.user or not isinstance(message.channel, discord.DMChannel):
        return

    user_id = str(message.author.id)
    discord_username = message.author.name
    msg = message.content.strip()
    session = get_session(user_id)

    # Session expiry (5 minutes inactivity), preserve tickets
    if session_expired(user_id):
        preserve_tickets_on_reset(user_id)
        clear_action_stack(user_id)
        await message.channel.send("🔒 Your previous session expired due to inactivity. Let's start fresh. What's your washing machine issue?")
        return

    if not session_exists(user_id) or msg.lower() == "reset":
        preserve_tickets_on_reset(user_id)
        clear_action_stack(user_id)
        await message.channel.send("👋 Hi! I’m Washing-Machine Bot. What’s the issue with your machine?")
        return

    session = get_session(user_id)

    # --- UNIVERSAL COMMANDS ---
    if msg.lower().startswith("help") or msg.lower().startswith("!help"):
        clear_action_stack(user_id)
        await send_help(message.channel)
        return

    # -------- YES/NO LOGIC, MAPPED TO ACTION STACK -----------
    if msg.lower() in ["yes", "y", "no", "n"]:
        last_action = peek_action(user_id)
        if last_action == "asked_kb":
            if msg.lower() in ["yes", "y"]:
                await message.channel.send("✅ Glad I could help! If you have another issue, just describe it.")
                clear_action_stack(user_id)
                preserve_tickets_on_reset(user_id)
                return
            else:  # "no"
                clear_action_stack(user_id)
                projects = mh_client.list_projects()
                if not projects:
                    await message.channel.send("⚠️ No projects found in MantisHub. Contact admin.")
                    return
                categories_by_project = {str(p['id']): mh_client.list_categories(p['id']) for p in projects}
                parsed = llm_parse_ticket_fields(session.get("problem", msg), projects, categories_by_project)
                if not parsed:
                    fallback_project = projects[0]
                    fallback_categories = categories_by_project.get(str(fallback_project['id']), [])
                    if fallback_categories:
                        fallback_category = fallback_categories[0]
                        ticket = mh_client.create_ticket(
                            summary=f"{discord_username}: {session.get('problem', msg)[:50]}",
                            description=session.get('problem', msg),
                            project_id=fallback_project['id'],
                            category=fallback_category['name']
                        )
                        ticket_id = ticket.get("issue", {}).get("id") or ticket.get("id")
                        add_ticket_for_user(
                            user_id, ticket_id,
                            category=fallback_category['name'], status="open"
                        )
                        await message.channel.send(f"🎫 Ticket created (default category)! Your ticket ID is `{ticket_id}`. You can check status by typing `status`.")
                        preserve_tickets_on_reset(user_id)
                        return
                    else:
                        await message.channel.send("Sorry, I couldn't create a ticket because there is no available category. Please contact support.")
                        return
                else:
                    project_id = next((p['id'] for p in projects if p['name'].lower() == parsed['project_name'].lower()), None)
                    category_id = None
                    if project_id:
                        categories = categories_by_project[str(project_id)]
                        category_id = next((c['id'] for c in categories if c['name'].lower() == parsed['category_name'].lower()), None)
                    if not (project_id and category_id):
                        await message.channel.send("Sorry, I couldn't match your issue to an exact project/category. Please try rephrasing or contact support.")
                        return
                    ticket = mh_client.create_ticket(
                        summary=f"{discord_username}: {parsed['summary']}",
                        description=parsed['description'],
                        project_id=project_id,
                        category=parsed['category_name']
                    )
                    ticket_id = ticket.get("issue", {}).get("id") or ticket.get("id")
                    add_ticket_for_user(
                        user_id, ticket_id,
                        category=parsed['category_name'], status="open"
                    )
                    await message.channel.send(f"🎫 Ticket created! Your ticket ID is `{ticket_id}`. You can check status by typing `status`.")
                    preserve_tickets_on_reset(user_id)
                    return

        elif last_action == "asked_ticket":
            if msg.lower() in ["yes", "y"]:
                await message.channel.send("🎫 Ticket created! You can check status by typing `status`.")
            else:
                await message.channel.send("👍 No ticket created. If you have another issue, just describe it.")
            clear_action_stack(user_id)
            preserve_tickets_on_reset(user_id)
            return

    # -------- LLM INTENT ROUTING FOR ALL CASES ----------
    route = llm_route(msg, session)
    action = route.get("action")
    info = route.get("info", "")

    if action == "help":
        clear_action_stack(user_id)
        await send_help(message.channel)
        return
    if action == "greeting":
        clear_action_stack(user_id)
        await message.channel.send("😊 Hi there! Let me know if you have any washing machine issues or questions!")
        return
    if action == "out_of_scope":
        clear_action_stack(user_id)
        await message.channel.send("Sorry, I can only help with washing machine problems.")
        return
    if action == "security":
        clear_action_stack(user_id)
        await message.channel.send("🚫 Sorry, I can't share sensitive information.")
        preserve_tickets_on_reset(user_id)
        return

    if action == "ticket_status":
        user_tickets = get_tickets_for_user(user_id)
        if not user_tickets:
            await message.channel.send("You have no open tickets.")
        else:
            lines = []
            for t in user_tickets:
                if isinstance(t, int):
                    tid = t
                    category = ""
                    status = ""
                else:
                    tid = t.get("id")
                    category = t.get("category", "")
                    status = t.get("status", "")
                try:
                    remote = mh_client.get_ticket(tid)
                    remote = unpack_mantis_ticket(remote)
                    summary = remote.get("summary", "No summary")
                    remote_status = remote.get("status", {}).get("name", "Unknown")
                    remote_category = remote.get("category", {}).get("name", "General")
                    notes = remote.get("notes", [])
                    if remote_status and remote_status != status:
                        update_ticket_status_for_user(user_id, tid, remote_status)
                        status = remote_status
                    if remote_category and remote_category != category:
                        update_ticket_category_for_user(user_id, tid, remote_category)
                        category = remote_category
                    update_text = ""
                    if notes:
                        update_text = "\n".join([f"- {n.get('text', '')}" for n in notes])
                    lines.append(f"\n――――――――――\nID: `{tid}` | {summary} | Status: {status} | Category: {category}\nUpdates:\n{update_text}")
                except Exception as e:
                    lines.append(f"\n――――――――――\nID: `{tid}` | Error fetching ticket: {str(e)}")
            await message.channel.send("Ticket updates/history:" + "\n".join(lines))
        clear_action_stack(user_id)
        return

    if action == "delete_ticket":
        user_tickets = get_tickets_for_user(user_id)
        tid = llm_pick_ticket_id(msg, user_tickets)
        if tid is None:
            await message.channel.send("Which ticket would you like to delete? Please specify the ticket ID or summary.")
            return
        try:
            mh_client.delete_ticket(tid)
            remove_ticket_for_user(user_id, tid)
            await message.channel.send(f"🗑️ Ticket `{tid}` deleted.")
        except Exception as e:
            await message.channel.send(f"Error deleting ticket: {e}")
        clear_action_stack(user_id)
        return

    if action == "close_ticket":
        user_tickets = get_tickets_for_user(user_id)
        tid = llm_pick_ticket_id(msg, user_tickets)
        if tid is None:
            await message.channel.send("Which ticket would you like to close? Please specify the ticket ID or summary.")
            return
        try:
            mh_client.update_ticket(tid, {"status": {"id": 90}})
            update_ticket_status_for_user(user_id, tid, "closed")
            await message.channel.send(f"✅ Ticket `{tid}` closed.")
        except Exception as e:
            await message.channel.send(f"Error closing ticket: {e}")
        clear_action_stack(user_id)
        return

    if action == "clarify":
        if session.get("clarification_asked", False):
            projects = mh_client.list_projects()
            if not projects:
                await message.channel.send("⚠️ No projects found in MantisHub. Contact admin.")
                return
            categories_by_project = {str(p['id']): mh_client.list_categories(p['id']) for p in projects}
            parsed = llm_parse_ticket_fields(session.get("problem", msg), projects, categories_by_project)
            if not parsed:
                fallback_project = projects[0]
                fallback_categories = categories_by_project.get(str(fallback_project['id']), [])
                if fallback_categories:
                    fallback_category = fallback_categories[0]
                    ticket = mh_client.create_ticket(
                        summary=f"{discord_username}: {session.get('problem', msg)[:50]}",
                        description=session.get('problem', msg),
                        project_id=fallback_project['id'],
                        category=fallback_category['name']
                    )
                    ticket_id = ticket.get("issue", {}).get("id") or ticket.get("id")
                    add_ticket_for_user(
                        user_id, ticket_id,
                        category=fallback_category['name'], status="open"
                    )
                    await message.channel.send(f"🎫 Ticket created (default category)! Your ticket ID is `{ticket_id}`. You can check status by typing `status`.")
                    preserve_tickets_on_reset(user_id)
                    return
                else:
                    await message.channel.send("Sorry, I couldn't create a ticket because there is no available category. Please contact support.")
                    return
            else:
                project_id = next((p['id'] for p in projects if p['name'].lower() == parsed['project_name'].lower()), None)
                category_id = None
                if project_id:
                    categories = categories_by_project[str(project_id)]
                    category_id = next((c['id'] for c in categories if c['name'].lower() == parsed['category_name'].lower()), None)
                if not (project_id and category_id):
                    await message.channel.send("Sorry, I couldn't match your issue to an exact project/category. Please try rephrasing or contact support.")
                    return
                ticket = mh_client.create_ticket(
                    summary=f"{discord_username}: {parsed['summary']}",
                    description=parsed['description'],
                    project_id=project_id,
                    category=parsed['category_name']
                )
                ticket_id = ticket.get("issue", {}).get("id") or ticket.get("id")
                add_ticket_for_user(
                    user_id, ticket_id,
                    category=parsed['category_name'], status="open"
                )
                await message.channel.send(f"🎫 Ticket created! Your ticket ID is `{ticket_id}`. You can check status by typing `status`.")
                preserve_tickets_on_reset(user_id)
                return
        else:
            await message.channel.send("Can you please clarify your washing machine issue with more detail?")
            update_session(user_id, clarification_asked=True)
            push_action(user_id, "asked_kb")
            return

    if action == "kb_answer":
        answer = llm_troubleshoot(msg, clarification_mode=session.get("clarification_asked", False))
        update_session(user_id, problem=msg, last_msg=msg)
        await message.channel.send(f"🧰 Possible Solution:\n\n{answer}\n\nDid this help? (yes/no)")
        update_session(user_id, state="awaiting_kb_confirm", kb_solution=answer, clarification_asked=False)
        push_action(user_id, "asked_kb")
        return

    if action == "create_ticket":
        projects = mh_client.list_projects()
        if not projects:
            await message.channel.send("⚠️ No projects found in MantisHub. Contact admin.")
            return
        categories_by_project = {str(p['id']): mh_client.list_categories(p['id']) for p in projects}
        parsed = llm_parse_ticket_fields(session.get("problem", msg), projects, categories_by_project)
        if not parsed:
            fallback_project = projects[0]
            fallback_categories = categories_by_project.get(str(fallback_project['id']), [])
            if fallback_categories:
                fallback_category = fallback_categories[0]
                ticket = mh_client.create_ticket(
                    summary=f"{discord_username}: {session.get('problem', msg)[:50]}",
                    description=session.get('problem', msg),
                    project_id=fallback_project['id'],
                    category=fallback_category['name']
                )
                ticket_id = ticket.get("issue", {}).get("id") or ticket.get("id")
                add_ticket_for_user(
                    user_id, ticket_id,
                    category=fallback_category['name'], status="open"
                )
                await message.channel.send(f"🎫 Ticket created (default category)! Your ticket ID is `{ticket_id}`. You can check status by typing `status`.")
                preserve_tickets_on_reset(user_id)
                return
            else:
                await message.channel.send("Sorry, I couldn't create a ticket because there is no available category. Please contact support.")
                return
        else:
            project_id = next((p['id'] for p in projects if p['name'].lower() == parsed['project_name'].lower()), None)
            category_id = None
            if project_id:
                categories = categories_by_project[str(project_id)]
                category_id = next((c['id'] for c in categories if c['name'].lower() == parsed['category_name'].lower()), None)
            if not (project_id and category_id):
                await message.channel.send("Sorry, I couldn't match your issue to an exact project/category. Please try rephrasing or contact support.")
                return
            ticket = mh_client.create_ticket(
                summary=f"{discord_username}: {parsed['summary']}",
                description=parsed['description'],
                project_id=project_id,
                category=parsed['category_name']
            )
            ticket_id = ticket.get("issue", {}).get("id") or ticket.get("id")
            add_ticket_for_user(
                user_id, ticket_id,
                category=parsed['category_name'], status="open"
            )
            await message.channel.send(f"🎫 Ticket created! Your ticket ID is `{ticket_id}`. You can check status by typing `status`.")
            preserve_tickets_on_reset(user_id)
            return

    # Fallback
    await message.channel.send("Sorry, I didn't understand. Please describe your washing machine problem, or type `help` for options.")

if __name__ == "__main__":
    client.run(DISCORD_BOT_TOKEN)
