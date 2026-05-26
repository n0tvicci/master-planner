from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# All scopes needed by upload_youtube.py and pull_analytics.py combined.
# Requesting them together means one OAuth consent and one token.json.
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def get_credentials(project_root: Path) -> Credentials:
    creds_file = project_root / "credentials.json"
    token_file = project_root / "token.json"
    if not creds_file.exists():
        raise FileNotFoundError(
            "credentials.json not found.\n"
            "Download OAuth 2.0 Desktop credentials from Google Console "
            "(APIs & Services → Credentials → Create OAuth client → Desktop) "
            "and place the file in the project root."
        )
    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
            creds = flow.run_local_server(port=0)
        token_file.write_text(creds.to_json())
    return creds


def get_youtube_client(project_root: Path):
    return build("youtube", "v3", credentials=get_credentials(project_root))


def get_analytics_client(project_root: Path):
    return build("youtubeAnalytics", "v2", credentials=get_credentials(project_root))
