import json
import uuid
from anthropic import Anthropic
from backend.features.yt_shorts.models.script import Script, ScriptSentence

_SYSTEM = (
    "You are a military and historical weapons education script writer "
    "for a YouTube Shorts channel. Target audience: US military enthusiasts aged 18-45. "
    "Tone: conversational, confident, slightly conspiratorial. "
    "Never use filler words. Never add a CTA. Always end on the twist."
)


def _prompt(title: str, misconception: str) -> str:
    return f"""Write a complete production package for this YouTube Shorts video.

TITLE: {title}
MISCONCEPTION TO CORRECT: {misconception}

Respond with valid JSON only — no markdown, no prose outside the JSON:
{{
  "sentences": [
    {{
      "text": "sentence text here",
      "pexels_query": "sniper rifle scope close up",
      "pixabay_query": "military sniper weapon",
      "ai_needed": false,
      "ai_prompt": null,
      "keyword_overlay": "SNIPERS"
    }}
  ],
  "originality_score": 8,
  "advertiser_friendliness_score": 9,
  "us_resonance_score": 8,
  "music_mood": "tense, suspenseful",
  "compliance": {{
    "sensitive_content": "CLEAR",
    "sensitive_content_details": null,
    "ai_disclosure_required": true,
    "revision_notes": null
  }}
}}

Script requirements:
- Structure: Hook (0-3s) → Common belief validation (3-10s) → Historical/technical truth (10-35s) → Final unexpected twist (35-50s)
- 120-160 words total across all sentences
- American English, confident tone, no filler words, no CTA, end on the twist
- Originality score 1-10 (minimum 7 to pass): corrects misconception, references specifics, reveals non-obvious fact, ends on stronger twist
- Advertiser-friendliness score 1-10 (minimum 8 to pass): no graphic violence, no glorification of casualties, no active conflict coverage
- US resonance score 1-10: US military references, American English
- keyword_overlay: 1-3 words ALL CAPS per sentence"""


def generate_script(
    api_key: str,
    topic_title: str,
    misconception: str,
) -> tuple[Script, dict]:
    client = Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=_SYSTEM,
        messages=[{"role": "user", "content": _prompt(topic_title, misconception)}],
    )
    if not message.content:
        raise ValueError("Empty response from Claude API")
    try:
        raw = json.loads(message.content[0].text)
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Invalid JSON from Claude API: {e}") from e
    sentences = [
        ScriptSentence(id=str(uuid.uuid4()), **s)
        for s in raw["sentences"]
    ]
    full_text = " ".join(s.text for s in sentences)
    script = Script(
        sentences=sentences,
        full_text=full_text,
        originality_score=raw["originality_score"],
        advertiser_friendliness_score=raw["advertiser_friendliness_score"],
        us_resonance_score=raw["us_resonance_score"],
        music_mood=raw["music_mood"],
    )
    return script, raw.get("compliance", {})
