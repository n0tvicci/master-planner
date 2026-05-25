"""Generate YouTube Shorts topic ideas using Claude API.

Usage:
    python tools/generate_topics.py

Reads from .env:
    ANTHROPIC_API_KEY

Writes to:
    topics/queue.json  — appends new pending topics

Outputs 20 topic ideas scored by US audience familiarity and emotional paradox.
Only Tier 1 (score 8-10) and Tier 2 (score 6-7) topics are kept and queued.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
import anthropic

SYSTEM_PROMPT = """You are a topic researcher for a military and historical weapons
YouTube Shorts channel targeting US audiences.

Generate exactly 20 topic ideas. For each topic:

1. Write 3 title options using these formulas:
   - "Why did/do [group] [surprising behavior] with [familiar object]?"
   - "Why did [historical group] use [object] to [surprising action]?"
   - "Why [common military assumption] is completely wrong?"

2. Name the hook object and answer:
   "Would a non-military American recognize this object on sight?"
   YES / NO / MAYBE — with one sentence explanation

3. Describe the emotional paradox in one sentence:
   "The paradox is that [familiar/harmless thing] was actually [surprising truth]"

4. Score the topic using this rubric (0–10):
   - Object familiarity to non-military American: 0–3
   - Paradox is visual/emotional not just logical: 0–3
   - Stakes feel personally relatable: 0–2
   - Strong US military connection: 0–2

5. Assign tier:
   - Tier 1 (score 8–10): pursue immediately
   - Tier 2 (score 6–7): acceptable filler
   - Tier 3 (score <6): reject

DIVERSITY RULES — reject any topic that:
- Covers the same equipment type as a topic already in this list
- Involves geopolitical country comparisons
- Involves active conflicts from the last 5 years
- Requires knowledge of obscure military hardware to appreciate the hook

Sort output by tier score descending.
Output valid JSON array only. No preamble, no markdown."""


def load_published_titles(project_root: Path) -> list[str]:
    published_file = project_root / "topics" / "published.json"
    if not published_file.exists():
        return []
    entries = json.loads(published_file.read_text())
    return [e["title"] for e in entries[-30:]]


def run(config: dict, project_root: Path | None = None) -> list[dict]:
    client = anthropic.Anthropic(api_key=config["anthropic_api_key"])

    user_content = "Generate the 20 topics now."
    if project_root:
        published = load_published_titles(project_root)
        if published:
            avoid_list = "\n".join(f"- {t}" for t in published)
            user_content += f"\n\nAVOID topics similar to these already-published titles:\n{avoid_list}"

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_content}],
    )
    if not response.content:
        raise RuntimeError("Claude API returned empty response content")
    try:
        topics = json.loads(response.content[0].text)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Claude returned non-JSON response: {e}\n"
            f"Raw response: {response.content[0].text[:200]}"
        ) from e
    # Only return Tier 1 and Tier 2 topics
    return [t for t in topics if t.get("tier") in ("1", "2", 1, 2)]


def append_to_queue(topics: list[dict], project_root: Path) -> None:
    queue_file = project_root / "topics" / "queue.json"
    queue_file.parent.mkdir(exist_ok=True)
    if queue_file.exists():
        try:
            existing = json.loads(queue_file.read_text())
        except (json.JSONDecodeError, OSError):
            existing = []
    else:
        existing = []
    now = datetime.now(timezone.utc).isoformat()
    for topic in topics:
        topic["id"] = str(uuid.uuid4())[:8]
        topic["status"] = "pending"
        topic["created_at"] = now
        # Flatten: use best title option as the canonical title
        if "title_options" in topic and not topic.get("title"):
            topic["title"] = topic["title_options"][0]
    existing.extend(topics)
    queue_file.write_text(json.dumps(existing, indent=2))


if __name__ == "__main__":
    from tools.utils.config import load_config
    project_root = Path(__file__).parent.parent
    cfg = load_config()
    topics = run(cfg, project_root)
    append_to_queue(topics, project_root)
    print(f"Added {len(topics)} topics to queue.json")
    for t in topics[:5]:
        tier = t.get("tier", "?")
        score = t.get("tier_score", "?")
        print(f"  [Tier {tier} | {score}/10] {t.get('title', t.get('title_options', ['?'])[0])}")
