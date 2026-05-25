"""
generate_ai_footage.py — Auto-generate footage clips for AI gaps using Runway API.

Usage (via pipeline):
    from tools.generate_ai_footage import run
    results = run(job_id, gaps, project_root)

Args:
    job_id       : str  — e.g. "20260524-sniper-laser"
    gaps         : list[dict] — ai_gaps from check_footage_gaps output
                   Each gap must have: sentence_idx, runway_prompt
    project_root : Path — project root directory
    max_clips    : int  — cost-cap guard (default 5); raises RuntimeError if exceeded

Outputs:
    footage/<job-id>/gaps/clip_<idx:02d>.mp4  — downloaded video clips

Returns:
    list[dict] with keys: idx, status ("generated"|"cached"|"failed"), path|error

Reads RUNWAYML_API_SECRET from environment automatically via the Runway SDK.
"""

import sys
from pathlib import Path
import requests
import runwayml as _runwayml
from runwayml import TaskFailedError


COST_PER_CLIP = 0.25   # gen4_turbo: 5 credits/sec × 5 sec × $0.01/credit


def run(
    job_id: str,
    gaps: list[dict],
    project_root: Path,
    max_clips: int = 5,
) -> list[dict]:
    """
    Auto-generates footage for ai_gaps using the Runway API (gen4_turbo, 720:1280).
    Skips clips already present in footage/<job-id>/gaps/.
    Halts before generating anything if uncached gap count exceeds max_clips.
    Returns list of {idx, status, path|error} per gap.
    Reads RUNWAYML_API_SECRET from environment automatically via the SDK.
    """
    if not gaps:
        return []

    # Pre-check: count clips that actually need generation (not already cached)
    gaps_dir = project_root / "footage" / job_id / "gaps"
    uncached = [
        g for g in gaps
        if not (gaps_dir / f"clip_{g['sentence_idx']:02d}.mp4").exists()
    ]

    if len(uncached) > max_clips:
        est_cost = len(uncached) * COST_PER_CLIP
        raise RuntimeError(
            f"Runway cost cap exceeded: {len(uncached)} clips needed "
            f"(~${est_cost:.2f}) but max_clips={max_clips} (~${max_clips * COST_PER_CLIP:.2f}).\n"
            f"Options:\n"
            f"  1. Approve: pipeline.py --job {job_id} --max-ai-clips {len(uncached)}\n"
            f"  2. Reduce AI gaps by improving stock footage search queries in script.json\n"
            f"  3. Film some clips yourself and drop in footage/{job_id}/gaps/"
        )

    client = _runwayml.RunwayML()
    results = []

    for gap in gaps:
        idx = gap["sentence_idx"]
        out_dir = project_root / "footage" / job_id / "gaps"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"clip_{idx:02d}.mp4"

        if out_path.exists():
            print(f"  [skip] Gap {idx:02d}: cached")
            results.append({"idx": idx, "status": "cached", "path": str(out_path)})
            continue

        print(f"  [gen]  Gap {idx:02d}: generating via Runway API (~${COST_PER_CLIP:.2f})...")
        try:
            task = client.image_to_video.create(
                model="gen4_turbo",
                prompt_text=gap["runway_prompt"],
                ratio="720:1280",   # 9:16 portrait for Shorts
                duration=5,
            ).wait_for_task_output()

            video_url = task.output[0]
            r = requests.get(video_url, timeout=60)
            r.raise_for_status()
            out_path.write_bytes(r.content)
            print(f"  [ok]   Gap {idx:02d}: generated -> {out_path.name}")
            results.append({"idx": idx, "status": "generated", "path": str(out_path)})

        except TaskFailedError as e:
            print(f"  [fail] Gap {idx:02d}: Runway task failed -- {e.task_details}")
            results.append({"idx": idx, "status": "failed", "error": str(e.task_details)})

    generated = sum(1 for r in results if r["status"] == "generated")
    failed = sum(1 for r in results if r["status"] == "failed")
    actual_cost = generated * COST_PER_CLIP
    print(
        f"\nAI footage: {generated}/{len(gaps)} generated "
        f"(~${actual_cost:.2f})"
        + (f", {failed} failed" if failed else "")
    )
    return results


if __name__ == "__main__":
    print("Run via pipeline.py, not standalone.")
    sys.exit(0)
