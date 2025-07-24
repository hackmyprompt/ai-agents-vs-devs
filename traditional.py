import os
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

from loguru import logger
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

# === ⚙️ CONFIG & LOGGING ===
logger.remove()
logger.add(lambda m: print(m, end=""), level="INFO",
           format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{message}</level>")

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar"]
GOOGLE_TOKEN_FILE = "token.json"
GOOGLE_CREDENTIALS_FILE = "credentials.json"
ALLOWED_METHODS = {"list", "insert"}
ALLOWED_RESOURCES = {"events"}

DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


def _save_credentials(creds: Credentials) -> None:
    """Persist credentials to disk."""
    with open(GOOGLE_TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
    logger.info(f"✅ Credentials saved to {GOOGLE_TOKEN_FILE}")


def get_calendar_service() -> Any:
    """Loads or refreshes credentials and returns a Calendar API client."""
    creds = None
    if os.path.exists(GOOGLE_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_FILE, GOOGLE_SCOPES)

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
        creds = flow.run_local_server(port=0)
        logger.info("🔐 New credentials obtained.")
        _save_credentials(creds)

    return build("calendar", "v3", credentials=creds)


def calendar_api_call(resource: str, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Executes a Calendar API call and returns its JSON response."""
    if resource not in ALLOWED_RESOURCES or method not in ALLOWED_METHODS:
        return {"error": "Method or resource not allowed."}
    try:
        service = get_calendar_service()
        method_obj = getattr(getattr(service, resource)(), method)
        return method_obj(**params).execute()
    except Exception as e:
        logger.error(f"❌ Calendar API error: {e}")
        return {"error": str(e)}


def prompt_date(prompt: str) -> datetime:
    """Ask user for a YYYY-MM-DD date, validate via regex, return datetime.date."""
    while True:
        s = input(f"{prompt} (YYYY-MM-DD): ").strip()
        if DATE_REGEX.match(s):
            try:
                return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
            except ValueError:
                logger.error("Invalid date (out of range). Try again.")
        else:
            logger.error("Wrong format. Please use YYYY-MM-DD.")


def prompt_emails() -> List[Dict[str, str]]:
    """Ask user for comma-separated emails, validate each."""
    while True:
        raw = input("Attendees emails (comma-separated, or leave blank): ").strip()
        if not raw:
            return []
        parts = [e.strip() for e in raw.split(",")]
        if all(EMAIL_REGEX.match(e) for e in parts):
            return [{"email": e} for e in parts]
        logger.error("One or more emails invalid. Please retry.")


def fetch_events_for_date(date_dt: datetime) -> None:
    """List events on a given date."""
    start = date_dt.isoformat()
    end = (date_dt + timedelta(days=1)).isoformat()
    params = {
        "calendarId": "primary",
        "timeMin": start,
        "timeMax": end,
        "singleEvents": True,
        "orderBy": "startTime",
    }
    result = calendar_api_call("events", "list", params)
    items = result.get("items", [])
    if not items:
        logger.info(f"No events found on {date_dt.date()}.")
        return
    logger.info(f"Events on {date_dt.date()}:")
    for ev in items:
        st = ev["start"].get("dateTime", ev["start"].get("date"))
        logger.info(f" • {st} — {ev.get('summary','(no title)')}")


def insert_event() -> None:
    """Prompt user for event details and insert into calendar."""
    title = input("Title: ").strip() or "No Title"
    description = input("Description (optional): ").strip()
    date_str = input("Date (YYYY-MM-DD): ").strip()
    time_str = input("Start time (HH:MM, 24h): ").strip()
    tz = input("Time zone (e.g. America/Los_Angeles): ").strip() or "UTC"
    # Basic datetime build
    try:
        dt_start = datetime.fromisoformat(f"{date_str}T{time_str}").astimezone(timezone.utc)
        dt_end = dt_start + timedelta(hours=1)
    except Exception:
        logger.error("Invalid date/time. Aborting insert.")
        return

    attendees = prompt_emails()
    body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": dt_start.isoformat(), "timeZone": tz},
        "end": {"dateTime": dt_end.isoformat(), "timeZone": tz},
        "attendees": attendees,
    }
    params = {"calendarId": "primary", "body": body}
    resp = calendar_api_call("events", "insert", params)
    if resp.get("id"):
        logger.info(f"✅ Event created: {resp['htmlLink']}")
    else:
        logger.error(f"Failed to create event: {resp}")


def main() -> None:
    """Interactive loop: choose fetch, insert, or exit."""
    logger.info("=== Google Calendar CLI ===")
    while True:
        cmd = input("\nChoose action [fetch/insert/exit]: ").strip().lower()
        if cmd == "fetch":
            date_dt = prompt_date("Enter date to fetch")
            fetch_events_for_date(date_dt)
        elif cmd == "insert":
            insert_event()
        elif cmd in {"exit", "quit"}:
            logger.info("👋 Goodbye.")
            break
        else:
            logger.error("Unknown command. Choose fetch, insert, or exit.")


if __name__ == "__main__":
    main()
