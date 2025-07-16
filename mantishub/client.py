# mantishub/client.py

import requests
from config.settings import MANTIS_API_BASE, MANTIS_API_TOKEN
from mantishub.exceptions import (
    MantisHubAPIError,
    MantisHubNotFound,
    MantisHubUnauthorized,
)

class MantisHubClient:
    def __init__(self):
        self.base = MANTIS_API_BASE.rstrip("/")
        self.headers = {
            "Authorization": MANTIS_API_TOKEN,
            "Content-Type": "application/json",
        }

    def _request(self, method, path, **kwargs):
        url = f"{self.base}{path}"
        try:
            resp = requests.request(method, url, headers=self.headers, timeout=10, **kwargs)
            if resp.status_code == 401:
                raise MantisHubUnauthorized("Invalid or missing API token")
            if resp.status_code == 404:
                raise MantisHubNotFound(f"Resource not found: {url}")
            if not resp.ok:
                raise MantisHubAPIError(f"API Error {resp.status_code}: {resp.text}")
            if resp.content:
                return resp.json()
            return {}
        except requests.exceptions.RequestException as e:
            raise MantisHubAPIError(f"Request failed: {str(e)}")

    def create_ticket(self, summary, description, project_id, category=None, category_id=None, custom_fields=None):
        """
        Create a new issue (ticket) in MantisHub.
        Parameters:
        - summary: string (required)
        - description: string (required)
        - project_id: integer (required)
        - category: string (name, preferred)
        - category_id: integer (alternative to category name)
        - custom_fields: list of dicts (optional)
        """
        path = "/issues"
        
        # Handle category - prioritize name over ID if both provided
        if category is not None:
            cat_payload = {"name": str(category)}
        elif category_id is not None:
            cat_payload = {"id": int(category_id)}
        else:
            cat_payload = {"name": "General"}  # Default fallback

        payload = {
            "summary": summary,
            "description": description,
            "project": {"id": int(project_id)},
            "category": cat_payload
        }
        
        if custom_fields:
            payload["custom_fields"] = custom_fields
            
        return self._request("POST", path, json=payload)

    def get_ticket(self, ticket_id):
        """Fetch details of a single ticket by its numeric ID."""
        path = f"/issues/{ticket_id}"
        response = self._request("GET", path)
        return response.get("issue", response)

    def update_ticket(self, ticket_id, updates):
        """
        Update a ticket (patch). 
        Example updates:
        - {"status": {"id": 90}}  # Close ticket
        - {"note": "Closing ticket via API"}
        - {"handler": {"id": 123}}  # Assign to user
        """
        path = f"/issues/{ticket_id}"
        return self._request("PATCH", path, json=updates)

    def delete_ticket(self, ticket_id):
        """Delete a ticket by ID."""
        path = f"/issues/{ticket_id}"
        self._request("DELETE", path)
        return True

    def list_projects(self):
        """List all projects (to get their IDs and names)."""
        path = "/projects"
        data = self._request("GET", path)
        return data.get("projects", [])

    def list_categories(self, project_id):
        """
        List all categories for a project, by project_id.
        Returns a list of dicts with both name and id for each category.
        """
        path = f"/projects/{project_id}/categories"
        try:
            data = self._request("GET", path)
            return data.get("categories", [])
        except MantisHubNotFound:
            # Fallback to default categories if endpoint not available
            return [{"id": 1, "name": "General"}]

    def add_note_to_ticket(self, ticket_id, note_text):
        """Add a note to an existing ticket."""
        path = f"/issues/{ticket_id}"
        payload = {"note": note_text}
        return self._request("PATCH", path, json=payload)

    def assign_ticket(self, ticket_id, user_id):
        """Assign a ticket to a handler by user_id."""
        path = f"/issues/{ticket_id}"
        payload = {"handler": {"id": user_id}}
        return self._request("PATCH", path, json=payload)

# Optional: Quick smoke test
if __name__ == "__main__":
    client = MantisHubClient()
    print("Projects:", client.list_projects())
    # Example: print categories for first project (if any)
    projects = client.list_projects()
    if projects:
        print("Categories:", client.list_categories(projects[0]['id']))