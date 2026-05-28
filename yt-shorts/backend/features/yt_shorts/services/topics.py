import json
import uuid
from anthropic import Anthropic
from backend.features.yt_shorts.models.topic import Topic

_PROMPT = """Generate exactly 10 YouTube Shorts topic ideas for a military and historical weapons education channel targeting US audiences.

Respond with valid JSON only — no markdown, no prose:
{
  "topics": [
    {
      "title": "Why do real snipers never aim for center mass?",
      "misconception": "Movies always show snipers targeting the chest",
      "real_answer": "Real snipers target the medulla oblongata for instant incapacitation",
      "us_curiosity_score": 9
    }
  ]
}

Requirements:
- Exactly 10 topics
- Title formula: "Why do real [X] actually [Y]?" or "Why [common assumption] is completely wrong?"
- Focus: firearms engineering, historical warrior weapons, military tactics, equipment design, combat technology
- Avoid: active ongoing conflicts, graphic casualties, named political figures
- Sort by us_curiosity_score descending"""


def generate_topics(api_key: str) -> list[Topic]:
    client = Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{"role": "user", "content": _PROMPT}],
    )
    raw = json.loads(message.content[0].text)
    return [Topic(id=str(uuid.uuid4()), **item) for item in raw["topics"]]
