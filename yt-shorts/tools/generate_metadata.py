import json
from pathlib import Path

import anthropic

SYSTEM_PROMPT = """You write YouTube metadata for a faceless military-and-historical-weapons Shorts channel.
Audience: US adults 25–55. Videos are 54–60 sec myth-busting educational shorts.

Return ONLY a JSON object — no markdown, no code fences, no explanation:
{
  "title": "<string, ≤100 chars, opens with a hook or surprising fact, no ALL-CAPS words, no '!!' or '???'>",
  "description": "<string, 3–5 sentences: first is keyword-rich for YouTube search, last is a CTA>",
  "tags": ["10 to 15 lowercase tags: include weapon type, historical era, and broad terms like 'military history', 'weapons facts', 'did you know'"],
  "pinned_comment": "<string, 1–2 sentences, ends with a question to drive replies>"
}"""


def run(job_id: str, config: dict, project_root: Path) -> dict:
    script_path = project_root / "scripts" / job_id / "script.json"
    if not script_path.exists():
        raise FileNotFoundError(f"script.json not found for job {job_id}")
    try:
        script = json.loads(script_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        raise RuntimeError(f"Could not read script.json: {e}") from e

    hook = script.get("hook", "")
    sentences = script.get("sentences", [])
    script_text = (hook + " " + " ".join(s.get("text", "") for s in sentences)).strip()

    client = anthropic.Anthropic(api_key=config["anthropic_api_key"])
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Script:\n{script_text}"}],
    )

    if not response.content:
        raise RuntimeError("Claude API returned empty response for metadata generation")

    try:
        metadata = json.loads(response.content[0].text)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Claude returned non-JSON response: {e}\nRaw: {response.content[0].text[:200]}"
        ) from e

    out_dir = project_root / "metadata" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
    return metadata


if __name__ == "__main__":
    import argparse
    from tools.utils.config import load_config

    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True)
    args = parser.parse_args()
    cfg = load_config()
    result = run(args.job, cfg, Path(__file__).parent.parent)
    print(json.dumps(result, indent=2))
