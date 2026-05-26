import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tools.utils.youtube_auth import get_analytics_client


def run(job_id: str, video_id: str, project_root: Path) -> dict:
    analytics = get_analytics_client(project_root)

    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

    response = analytics.reports().query(
        ids="channel==MINE",
        startDate=start_date,
        endDate=end_date,
        metrics="views",
        dimensions="country",
        filters=f"video=={video_id}",
        sort="-views",
    ).execute()

    rows = response.get("rows", [])
    total = sum(int(r[1]) for r in rows)
    us_views = next((int(r[1]) for r in rows if r[0] == "US"), 0)
    us_share = us_views / total if total > 0 else 0.0

    if us_share > 0.5:
        flag = "GREEN"
        notes = "US share >50% — target met"
    elif us_share >= 0.4:
        flag = "YELLOW"
        notes = "US share 40-50% — review upload timing"
    else:
        flag = "RED"
        notes = "US share <40% — review topic tier"

    report = {
        "video_id": video_id,
        "job_id": job_id,
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "us_share": round(us_share, 4),
        "flag": flag,
        "notes": notes,
        "country_breakdown": {r[0]: int(r[1]) for r in rows},
    }

    log_dir = project_root / "compliance-logs" / job_id
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "audience-report.json").write_text(json.dumps(report, indent=2))
    return report
