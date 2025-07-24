import os
import sys
from typing import Any, Dict
import json
from datetime import datetime, timezone

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from openai import OpenAI
from loguru import logger


# === 🔧 CONFIGURATION ===
GOOGLE_CREDENTIALS_FILE = "credentials.json"
GOOGLE_TOKEN_FILE = "token.json"
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar"]
OPENAI_API_KEY = ""
ALLOWED_RESOURCES = {"events"}
ALLOWED_METHODS = {"list", "insert", "update", "delete"}

# SETUP
logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{message}</level>",
    level="INFO",
)


# HELPER FUNCTIONS
def _save_credentials(creds: Credentials) -> None:
    """
    Persist user credentials to disk for future sessions.
    """
    with open(GOOGLE_TOKEN_FILE, "w") as token_file:
        token_file.write(creds.to_json())
    logger.info(f"✅ Credentials saved to {GOOGLE_TOKEN_FILE}")


# Calender function
def get_calendar_service() -> Any:
    """
    Loads, refreshes, or requests new Google Calendar credentials, returning a calendar service client.
    """
    creds = None

    # Load saved credentials
    if os.path.exists(GOOGLE_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_FILE, GOOGLE_SCOPES)

    # Refresh or prompt for credentials
    if creds and creds.valid:
        pass
    elif creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        logger.info("🔄 Credentials refreshed.")
        _save_credentials(creds)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            GOOGLE_CREDENTIALS_FILE, GOOGLE_SCOPES
        )
        creds = flow.run_local_server(
            port=3001,
            prompt="consent",
            authorization_prompt_message="Please authorize: {url}",
        )
        logger.info("🔐 New credentials obtained.")
        _save_credentials(creds)

    return build("calendar", "v3", credentials=creds)


def calendar_api_call(
    resource: str, method: str, params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Executes the requested Google Calendar API call.

    Args:
        resource: The calendar resource (e.g., "events").
        method: The method to perform (e.g., "list", "insert").
        params: The parameters required for the API call.

    Returns:
        The API response in JSON format, or an error dict.
    """
    if resource not in ALLOWED_RESOURCES or method not in ALLOWED_METHODS:
        return {"error": "Method or resource not allowed."}

    try:
        service = get_calendar_service()
        method_obj = getattr(getattr(service, resource)(), method)
        return method_obj(**params).execute()
    except Exception as e:
        logger.error(f"❌ Calendar API error: {e}")
        return {"error": str(e)}


# Call any function with name and args
def call_function(name: str, args: Dict[str, Any]) -> Any:
    """
    Dispatches function calls dynamically.

    Args:
        name: Name of the function to call.
        args: Arguments to pass to the function.

    Returns:
        Function result or error message.
    """
    if name == "calendar_api_call":
        return calendar_api_call(**args)
    return {"error": f"Function '{name}' not implemented."}


# OPENAI Client
client = OpenAI(api_key=OPENAI_API_KEY)

# Define calendar function metadata for OpenAI
calendar_function = {
    "type": "function",
    "function": {
        "name": "calendar_api_call",
        "description": "Call Google Calendar API with the given method and parameters.",
        "parameters": {
            "type": "object",
            "properties": {
                "resource": {
                    "type": "string",
                    "description": "Google Calendar resource to call, such as 'events'",
                },
                "method": {
                    "type": "string",
                    "description": "Method on the resource to call, such as 'list', 'insert', 'delete', etc.'",
                },
                "params": {
                    "type": "object",
                    "description": "Parameters to pass to the method, matching the Google Calendar API",
                },
            },
            "required": ["resource", "method", "params"],
            "additionalProperties": False,
        },
    },
}


# Process OPENAI Response
def process_response(response: Any) -> str:
    """
    Processes a ChatCompletion response, handling any function calls recursively.

    Args:
        response: The raw ChatCompletion object returned by client.chat.completions.create().

    Returns:
        The final assistant reply text (i.e., the content of the first choice once no more
        function calls are outstanding).
    """
    for choice in response.choices:
        message = choice.message

        # If the model wants to call a function...
        if (
            message.role == "assistant"
            and hasattr(message, "tool_calls")
            and message.tool_calls
        ):
            # Assuming tool_calls is a list of objects with name and arguments
            call = message.tool_calls[0]
            name = call.function.name
            args = json.loads(call.function.arguments or "{}")

            # Execute the tool
            result = call_function(name, args)

            # Append the original assistant message with tool_calls
            input_messages.append(
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": message.tool_calls,
                }
            )
            # Append the tool's output with the correct role and call_id
            input_messages.append(
                {
                    "role": "tool",
                    "tool_name": name,
                    "tool_call_id": call.id,
                    "content": json.dumps(result),
                }
            )

            # Call the model again
            new_resp = client.chat.completions.create(  # type: ignore
                model="gpt-4.1",
                messages=input_messages,
                tools=[calendar_function],
                tool_choice="auto",
            )
            return process_response(new_resp)

    # No function_call left—return the assistant's content
    return response.choices[0].message.content or ""


# PROMPT SETUP
current_time = datetime.now(timezone.utc).isoformat()
SYSTEM_PROMPT = """
Act as an assistant that helps users manage their Google Calendar, specifically using their primary calendar for all operations.

Keep the following guidelines in mind:
- Authenticate users securely via their Google accounts to access Calendar APIs.
- Support key operations: add, retrieve, update, and delete events from the user’s primary calendar.
- Use appropriate permission scopes to protect user privacy and ensure data integrity.
- Provide clear confirmation for every action, including the event’s date, time, day and use  timezone.
- IMPORTANT - Use today’s date — {} — as a reference for checking events.
- Do not include any email addresses by default. Only add an email if it is explicitly provided—this field is optional. Avoid using placeholder emails like @example.com.

### Example for each event paramters
Adding a New Event:
```
params_insert = {{
    "calendarId": "primary",
    "body": {{
        "summary": "Meeting with Bob",
        "location": "123 Main St, Conference Room A",
        "description": "Discuss quarterly earnings",
        "start": {{
            "dateTime": "2025-07-06T10:00:00-07:00",
            "timeZone": "America/Los_Angeles",
        }},
        "end": {{
            "dateTime": "2025-07-06T11:00:00-07:00",
            "timeZone": "America/Los_Angeles",
        }},
        "attendees": [
            {{"email": "bob@example.com"}},
        ],
    }},
}}
```

Retrieving Events:
```
params_list = {{
    "calendarId": "primary",
    "timeMin": "2025-07-05T00:00:00Z",
    "maxResults": 10,
    "singleEvents": True,
    "orderBy": "startTime",
}}
```

Update Events 
```
params_update = {{
    "calendarId": "primary",
    "eventId": "your_event_id_here",  # Replace with actual event ID
    "body": {{
        "summary": "Updated Meeting Title",
        "description": "Updated description here",
        "start": {{
            "dateTime": "2025-07-07T15:00:00-07:00",
            "timeZone": "America/Los_Angeles",
        }},
        "end": {{
            "dateTime": "2025-07-07T16:00:00-07:00",
            "timeZone": "America/Los_Angeles",
        }},
    }},
}}
```

Delete Events 
```
params_delete = {{
    "calendarId": "primary",
    "eventId": "your_event_id_here",  # Replace with actual event ID
}}
```
Remember to always indicate which calendar you are interacting with to avoid any confusion.

Please guide the user through these interactions step-by-step and ensure all communications are clear and user-friendly.
"""
input_messages = [{"role": "system", "content": SYSTEM_PROMPT.format(current_time)}]


# AI Agent
def chat_with_agent(user_input: str) -> str:
    """
    Handles user input, sends it to the assistant, and returns the assistant’s reply.

    Args:
        user_input: The user's message.

    Returns:
        Assistant's final text response.
    """
    input_messages.append({"role": "user", "content": user_input})
    response = client.chat.completions.create(  # type: ignore
        model="gpt-4.1",
        messages=input_messages,
        tools=[calendar_function],
        tool_choice="auto",
    )
    return process_response(response)


if __name__ == "__main__":
    logger.info("👉 Starting calendar assistant session")
    logger.info("🗓️  Asking: What is on my calendar tomorrow?")

    initial_response = chat_with_agent("What's on my calendar tomorrow?")
    logger.info(f"🤖 Assistant: {initial_response}")

    logger.info("\nType your message below (or type 'exit' to quit):\n")

    while True:
        try:
            message = input("You: ").strip()
            if message.lower() in {"exit", "quit"}:
                logger.info("👋 Exiting session.")
                break

            logger.info(f"🧑 You: {message}")
            response = chat_with_agent(message)
            logger.info(f"🤖 Assistant: {response}")

        except KeyboardInterrupt:
            logger.info("🚪 Session interrupted by user (KeyboardInterrupt).")
            break
