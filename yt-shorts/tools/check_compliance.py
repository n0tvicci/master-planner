import json
from pathlib import Path


def run(job_id: str, project_root: Path) -> dict:
    script_file = project_root / "scripts" / job_id / "script.json"
    if not script_file.exists():
        raise FileNotFoundError(f"Script not found: {script_file}. Run generate_script first.")
    try:
        script = json.loads(script_file.read_text())
    except (json.JSONDecodeError, OSError) as e:
        raise RuntimeError(f"Could not read script for job {job_id}: {e}") from e

    # Short-circuit if topic was rejected during script generation
    if script.get("status") == "TOPIC_REJECTED":
        return {"status": "REVISION_REQUIRED", "notes": f"Topic rejected during script generation: {script.get('reason', 'no reason given')}"}

    scores = script.get("scores", {})
    compliance = script.get("compliance", {})

    originality = scores.get("originality", 0)
    advertiser_friendliness = scores.get("advertiser_friendliness", 0)

    failures = []
    if originality < 7:
        failures.append(f"Originality {originality}/10 (minimum 7)")
    if advertiser_friendliness < 8:
        failures.append(f"Advertiser-friendliness {advertiser_friendliness}/10 (minimum 8)")
    if compliance.get("sensitive_content") == "FLAG":
        failures.append("Sensitive content flagged")

    revision_required = (
        failures
        or compliance.get("originality") == "REVISION REQUIRED"
        or compliance.get("advertiser_friendliness") == "REVISION REQUIRED"
    )

    if revision_required:
        notes = compliance.get("revision_notes") or "; ".join(failures)
        print(f"\n❌ REVISION REQUIRED for job {job_id}:")
        print(f"   {notes}")
        print(f"\n💡 Fix: python pipeline.py --job {job_id} --revise\n")
        return {"status": "REVISION_REQUIRED", "notes": notes}

    print(
        f"✅ Compliance PASS — "
        f"Originality: {originality}/10, "
        f"Advertiser: {advertiser_friendliness}/10, "
        f"US Resonance: {scores.get('us_resonance', 0)}/10"
    )
    return {"status": "PASS"}


if __name__ == "__main__":
    import sys
    from pathlib import Path
    job_id = sys.argv[1]
    project_root = Path(__file__).parent.parent
    result = run(job_id, project_root)
    if result["status"] != "PASS":
        sys.exit(1)
