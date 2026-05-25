import re
from datetime import datetime


def make_job_id(topic_title: str) -> str:
    date = datetime.now().strftime("%Y%m%d")
    slug = re.sub(r"[^a-z0-9]+", "-", topic_title.lower())
    slug = "-".join(slug.split("-")[:5]).strip("-")
    return f"{date}-{slug}"
