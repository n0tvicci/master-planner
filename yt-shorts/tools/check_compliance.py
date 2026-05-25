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

    scores = script.get("scores", {})
    compliance = script.get("compliance", {})

    failures = []
    if scores["originality"] < 7:
        failures.append(f"Originality {scores['originality']}/10 (minimum 7)")
    if scores["advertiser_friendliness"] < 8:
        failures.append(f"Advertiser-friendliness {scores['advertiser_friendliness']}/10 (minimum 8)")
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
        f"Originality: {scores['originality']}/10, "
        f"Advertiser: {scores['advertiser_friendliness']}/10, "
        f"US Resonance: {scores['us_resonance']}/10"
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
