"""
generate_script.py — Generate a YouTube Shorts script via Claude API.

Usage:
    python tools/generate_script.py <job_id> '<topic_json>'

Args:
    job_id      — Unique job identifier (e.g. 20260524-abc123)
    topic_json  — JSON string with keys: id, title, misconception, real_answer

Outputs:
    scripts/<job_id>/script.json — Full script with sentences, scores, compliance
"""

import json
from pathlib import Path
import anthropic

SYSTEM_PROMPT = """You are a professional YouTube Shorts script writer for a military and
historical weapons education channel. Write viral, myth-busting scripts that reveal
the surprising truth behind common assumptions about military equipment and history.

Output valid JSON only. No preamble, no markdown, no explanation.

═══════════════════════════════════════════
CRITICAL RULES — NEVER VIOLATE THESE
═══════════════════════════════════════════

RULE 1 — WORD COUNT
Every script must be exactly 168–183 words. Count precisely. Target: 178 words.
Below 168 or above 183: REVISION REQUIRED.

RULE 2 — ZERO SILENCE RULE
Write sentences of varying length to force natural pacing at 183 WPM with zero
pause gaps. Sentence tails should flow directly into the next sentence.

RULE 3 — FAMILIAR OBJECT HOOK
The hook object must be recognizable to any average American who has never served
in the military. Test: would someone who has never studied military history instantly
recognize this object from the hook sentence alone?
If NO → output {"status":"TOPIC_REJECTED","reason":"...","alternative_topics":["x3"]}

RULE 4 — IRONIC CONSEQUENCE TWIST
The final twist must start with: "But the final twist is that..."
It must describe a CONSEQUENCE or IRONIC FAILURE of the main answer — never just
an additional surprising fact. If the twist is just a fact → REVISION REQUIRED.

RULE 5 — NO BANNED CONTENT
Instantly reject topics containing: blood/gore/injury visualization, country vs
country geopolitical comparisons, active conflicts (within last 5 years), named
living political figures in military context, torture or war crimes descriptions.
If any present → {"status":"TOPIC_REJECTED","reason":"..."}

═══════════════════════════════════════════
THE 4-PART SCRIPT STRUCTURE
═══════════════════════════════════════════

SECTION 1 — HOOK (5–6 sec | 15–20 words)
Format: "Why did/do [group] [surprising behavior] with/involving [familiar object]?"
The object must look harmless, ordinary, or unexpected given the military context.

SECTION 2 — MISCONCEPTION (9–11 sec | 25–35 words)
Validate why the wrong assumption makes complete sense. Never mock the assumption.
Start with: "Most people assume..." or "At first glance..." or "Everyone assumed..."

SECTION 3 — TRUTH (22–34 sec | 70–95 words)
Must include at least one specific fact (date, number, name, or measurement).
Clear cause-and-effect explanation. Never use passive voice.
Do NOT start with "However" alone — add texture: "However, the real engineering truth..."

SECTION 4 — FINAL TWIST (10–17 sec | 35–55 words)
Must start with: "But the final twist is that..."
Must describe how the solution created a new problem, or how the strength became
a weakness. This drives comments, replays, and shares.

═══════════════════════════════════════════
PER-SENTENCE REQUIREMENTS
═══════════════════════════════════════════

For every sentence output:
- pexels_query: 3–5 word footage search query
- pixabay_query: 3–5 word alternative query
- needs_prop_library: true if this sentence needs a self-filmed desk prop close-up
- prop_description: describe exactly which prop and shot angle (null if not needed)
- needs_ai_video: true if no stock footage exists for this concept
- runway_prompt: complete Runway ML prompt (null if not needed)
- overlay: 1–3 words ALL CAPS (most visceral word in the sentence)
- color_pop_words: 1–2 words to flash neon yellow or red (most emotionally charged)

Timestamp calculation: 183 WPM. First sentence = 0:00.
Increment by (word_count / 183 * 60) seconds per sentence, formatted as M:SS.

═══════════════════════════════════════════
SCORING REQUIREMENTS
═══════════════════════════════════════════

ORIGINALITY SCORE (0–10):
+2 — Corrects a specific named common misconception
+2 — References a specific historical period, event, name, or measurement
+2 — Explains a non-obvious mechanism or technical detail
+2 — Final twist is an ironic consequence not just a surprising fact
+2 — Information cannot be learned just by watching the footage
Minimum passing score: 7/10

ADVERTISER-FRIENDLINESS SCORE (0–10):
Start at 10. Deduct:
-3 — Any graphic violence description or injury visualization
-3 — Any geopolitical country comparison
-2 — Coverage of active conflicts within last 5 years
-2 — Any named living political figure in military context
-1 — Any reference to casualties by name or number
Minimum passing score: 8/10

US RESONANCE SCORE (0–10):
+3 — US military branch, weapon, or historical event featured
+2 — Topic covered in a standard US history class
+2 — Paradox relatable to general American civilian life
+2 — No cultural references excluding American audience
+1 — Final twist has personal stakes
Target: 8+/10

Output PASS only if ALL three scores meet minimums.
Output REVISION REQUIRED if any score fails, with specific sentence-by-sentence notes."""


def _count_words(script: dict) -> int:
    return sum(len(s["text"].split()) for s in script.get("sentences", []))


def run(
    job_id: str,
    topic: dict,
    config: dict,
    project_root: Path,
    revision_context: str | None = None,
) -> dict:
    client = anthropic.Anthropic(api_key=config["anthropic_api_key"])

    user_content = (
        f"TOPIC: {topic['title']}\n"
        f"Misconception to correct: {topic['misconception']}\n"
        f"Real answer direction: {topic['real_answer']}"
    )
    if revision_context:
        user_content += (
            f"\n\nPREVIOUS REVISION REQUIRED:\n{revision_context}\n\n"
            "Please revise the script to address these issues."
        )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_content}],
    )

    if not response.content:
        raise RuntimeError("Claude API returned empty response content")
    try:
        script = json.loads(response.content[0].text)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Claude returned non-JSON response: {e}\n"
            f"Raw: {response.content[0].text[:200]}"
        ) from e

    # Word count validation — auto-regenerate once if outside 168–183
    if script.get("status") != "TOPIC_REJECTED":
        wc = _count_words(script)
        if not (168 <= wc <= 183):
            delta = abs(wc - 183) if wc > 183 else abs(168 - wc)
            direction = "trimming" if wc > 183 else "adding"
            correction = (
                f"WORD COUNT CORRECTION: Your previous script had {wc} words. "
                f"Target is exactly 168–183 words (target: 178). "
                f"Please rewrite by {direction} approximately {delta} words."
            )
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=3000,
                system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
                messages=[
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": response.content[0].text},
                    {"role": "user", "content": correction},
                ],
            )
            if not response.content:
                raise RuntimeError("Claude API returned empty response on word count retry")
            try:
                script = json.loads(response.content[0].text)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Claude returned non-JSON on retry: {e}") from e

    script["job_id"] = job_id
    script["topic"] = topic

    out_dir = project_root / "scripts" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "script.json").write_text(json.dumps(script, indent=2))
    return script


if __name__ == "__main__":
    import sys
    from tools.utils.config import load_config
    project_root = Path(__file__).parent.parent
    job_id, topic_json = sys.argv[1], sys.argv[2]
    result = run(job_id, json.loads(topic_json), load_config(), project_root)
    print(f"Script saved: scripts/{job_id}/script.json")
