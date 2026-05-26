from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from googleapiclient.http import MediaFileUpload

from tools.utils.youtube_auth import get_youtube_client

EST = ZoneInfo("America/New_York")

# isoweekday: 1=Mon 2=Tue 3=Wed 4=Thu 5=Fri 6=Sat 7=Sun
# Optimal windows: Tue/Wed/Thu 7-9 AM, Sat/Sun 9-11 AM (all EST)
_WINDOWS = {2: (7, 9), 3: (7, 9), 4: (7, 9), 6: (9, 11), 7: (9, 11)}


def _now() -> datetime:
    return datetime.now(tz=EST)


def is_in_upload_window() -> bool:
    now = _now()
    window = _WINDOWS.get(now.isoweekday())
    if window is None:
        return False
    return window[0] <= now.hour < window[1]


def next_upload_window() -> datetime:
    now = _now()
    for offset in range(8):
        candidate = now + timedelta(days=offset)
        window = _WINDOWS.get(candidate.isoweekday())
        if window is None:
            continue
        start_hour = window[0]
        window_start = candidate.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        if window_start > now:
            return window_start
    raise RuntimeError("Could not find next upload window within 7 days")


def run(job_id: str, video_path: Path, metadata: dict, project_root: Path) -> dict:
    youtube = get_youtube_client(project_root)

    body = {
        "snippet": {
            "title": metadata["title"],
            "description": metadata["description"],
            "tags": metadata["tags"],
            "categoryId": "19",
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredAiGeneratedContent": True,
            "madeForKids": False,
        },
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
    response = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media
    ).execute()
    video_id = response["id"]

    try:
        youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {"textOriginal": metadata["pinned_comment"]}
                    },
                }
            },
        ).execute()
    except Exception as e:
        print(f"  Warning: pinned comment failed ({e}). Pin manually in YouTube Studio.")

    return {"video_id": video_id, "url": f"https://youtube.com/shorts/{video_id}"}
