
# API Documentation

This document outlines the external APIs used in this application, with examples of how to interact with them.

## MantisHub API

The MantisHub API is used for managing support tickets. The base URL and API token are configured in the `.env` file.

### Endpoints

#### 1. List Projects

*   **Description:** Retrieves a list of all available projects in MantisHub.
*   **Method:** `GET`
*   **Path:** `/api/rest/projects`
*   **`curl` Example:**
    ```bash
    curl -X GET "https://<your_mantishub_domain>/api/rest/projects" \
         -H "Authorization: <your_api_token>"
    ```
*   **Example Response:**
    ```json
    {
      "projects": [
        {
          "id": 1,
          "name": "Project Alpha",
          "status": {
            "id": 10,
            "name": "development",
            "label": "development"
          },
          "enabled": true,
          "view_state": {
            "id": 10,
            "name": "public",
            "label": "public"
          },
          "access_level": {
            "id": 10,
            "name": "viewer",
            "label": "viewer"
          }
        }
      ]
    }
    ```

#### 2. Create Ticket

*   **Description:** Creates a new issue (ticket) in MantisHub.
*   **Method:** `POST`
*   **Path:** `/api/rest/issues`
*   **`curl` Example:**
    ```bash
    curl -X POST "https://<your_mantishub_domain>/api/rest/issues" \
         -H "Authorization: <your_api_token>" \
         -H "Content-Type: application/json" \
         -d '{
              "summary": "Washing machine is leaking",
              "description": "Water is leaking from the bottom of the machine.",
              "project": { "id": 1 },
              "category": { "name": "General" }
            }'
    ```
*   **Example Response:**
    ```json
    {
      "issue": {
        "id": 123,
        "summary": "Washing machine is leaking",
        "project": {
          "id": 1,
          "name": "Project Alpha"
        },
        "category": {
            "id": 1,
            "name": "General"
        }
      }
    }
    ```

#### 3. Get Ticket

*   **Description:** Retrieves the details of a specific ticket.
*   **Method:** `GET`
*   **Path:** `/api/rest/issues/{issue_id}`
*   **`curl` Example:**
    ```bash
    curl -X GET "https://<your_mantishub_domain>/api/rest/issues/123" \
         -H "Authorization: <your_api_token>"
    ```
*   **Example Response:**
    ```json
    {
      "issues": [
        {
          "id": 123,
          "summary": "Washing machine is leaking",
          "description": "Water is leaking from the bottom of the machine.",
          "project": {
            "id": 1,
            "name": "Project Alpha"
          }
        }
      ]
    }
    ```

#### 4. Update Ticket

*   **Description:** Updates an existing ticket.
*   **Method:** `PATCH`
*   **Path:** `/api/rest/issues/{issue_id}`
*   **`curl` Example (Close Ticket):**
    ```bash
    curl -X PATCH "https://<your_mantishub_domain>/api/rest/issues/123" \
         -H "Authorization: <your_api_token>" \
         -H "Content-Type: application/json" \
         -d '{ "status": { "name": "closed" } }'
    ```
*   **Example Response:**
    ```json
    {
      "issue": {
        "id": 123,
        "status": {
            "id": 90,
            "name": "closed",
            "label": "closed"
        }
      }
    }
    ```

#### 5. Delete Ticket

*   **Description:** Deletes a ticket.
*   **Method:** `DELETE`
*   **Path:** `/api/rest/issues/{issue_id}`
*   **`curl` Example:**
    ```bash
    curl -X DELETE "https://<your_mantishub_domain>/api/rest/issues/123" \
         -H "Authorization: <your_api_token>"
    ```
*   **Example Response:** (No content on success)

## Ollama API

The Ollama API is used for interacting with the Mistral language model for natural language understanding and generation. It is assumed to be running locally.

### Endpoints

#### 1. Chat Completions

*   **Description:** Generates a response from the language model based on a prompt.
*   **Method:** `POST`
*   **Path:** `/api/chat`
*   **`curl` Example:**
    ```bash
    curl -X POST "http://localhost:11434/api/chat" \
         -H "Content-Type: application/json" \
         -d '{
              "model": "mistral",
              "messages": [
                {
                  "role": "user",
                  "content": "Why is the sky blue?"
                }
              ]
            }'
    ```
*   **Example Response:**
    ```json
    {
        "model": "mistral",
        "created_at": "2023-08-04T19:22:45.499127Z",
        "message": {
            "role": "assistant",
            "content": "The sky appears blue because of a phenomenon called Rayleigh scattering..."
        },
        "done": true
    }
    ```

