#!/usr/bin/env python3
"""
Post-edit pipeline orchestrator.

Usage:
  python publish.py --job <id>              run full post-edit pipeline
  python publish.py --job <id> --dry-run    generate metadata, print preview, skip upload
  python publish.py --job <id> --immediate  skip upload window check
  python publish.py --job <id> --analytics  pull 72h audience analytics for uploaded video
"""
import argparse
import json
import sys
from pathlib import Path

import os as _os
PROJECT_ROOT = Path(_os.environ["PUBLISH_PROJECT_ROOT"]) if "PUBLISH_PROJECT_ROOT" in _os.environ else Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main(project_root: Path | None = None) -> None:
    if project_root is None:
        project_root = PROJECT_ROOT

    parser = argparse.ArgumentParser(description="YT Shorts post-edit pipeline")
    parser.add_argument("--job", required=True, help="Job ID to publish")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate metadata, print preview, skip upload")
    parser.add_argument("--immediate", action="store_true",
                        help="Skip upload window check")
    parser.add_argument("--analytics", action="store_true",
                        help="Pull 72h audience analytics for an uploaded video")
    args = parser.parse_args()

    job_id = args.job

    from tools.utils.config import load_config
    from tools.utils.state import load_state, save_state, mark_complete, is_complete
    import tools.pre_upload_gate as pre_upload_gate
    import tools.generate_metadata as generate_metadata
    import tools.upload_youtube as upload_youtube
    import tools.monitor_upload as monitor_upload
    import tools.pull_analytics as pull_analytics

    # -- analytics mode -------------------------------------------------------
    if args.analytics:
        state = load_state(job_id, project_root)
        video_id = state.get("video_id")
        if not video_id:
            print(f"No video_id in state for job {job_id}. Run without --analytics first.")
            sys.exit(1)
        print("Pulling audience analytics...")
        report = pull_analytics.run(job_id, video_id, project_root)
        flag = report["flag"]
        us_pct = round(report["us_share"] * 100, 1)
        print(f"\nAudience Report [{flag}] — US share: {us_pct}%")
        print(f"  {report['notes']}")
        print(f"  Full report: compliance-logs/{job_id}/audience-report.json")
        return

    # -- prerequisite ---------------------------------------------------------
    final_video = project_root / "output" / job_id / "final.mp4"
    if not final_video.exists():
        print(f"final.mp4 not found: output/{job_id}/final.mp4")
        print("Export the edited video from CapCut, save to that path, then re-run.")
        sys.exit(1)

    state = load_state(job_id, project_root)
    if not state:
        state = {"job_id": job_id, "completed_steps": []}
        save_state(state, project_root)

    # -- Step 1: pre_upload_gate ----------------------------------------------
    if not is_complete("pre_upload_gate", state):
        print("Pre-upload compliance gate...")
        result = pre_upload_gate.run()
        if result["status"] != "PASS":
            failed = result.get("failed_checks", [])
            print(f"\nGate failed ({len(failed)} check(s) did not pass). Upload aborted.")
            sys.exit(1)
        state = mark_complete("pre_upload_gate", state, project_root)
    else:
        print("Gate: already passed")

    config = load_config()

    # -- Step 2: generate_metadata --------------------------------------------
    if not is_complete("generate_metadata", state):
        print("Generating metadata...")
        generate_metadata.run(job_id, config, project_root)
        state = mark_complete("generate_metadata", state, project_root)
    else:
        print("Metadata: already done")

    metadata_path = project_root / "metadata" / job_id / "metadata.json"
    try:
        metadata = json.loads(metadata_path.read_text())
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Could not read metadata.json: {e}")
        sys.exit(1)

    if args.dry_run:
        print("\n[DRY RUN] Metadata preview:")
        print(json.dumps(metadata, indent=2))
        return

    # -- upload window check --------------------------------------------------
    if not args.immediate:
        if not upload_youtube.is_in_upload_window():
            nw = upload_youtube.next_upload_window()
            print(f"\nOutside optimal upload window.")
            print(f"  Next window: {nw.strftime('%A %b %d at %I:%M %p EST')}")
            print(f"  Re-run then:  python publish.py --job {job_id}")
            print(f"  Or skip:      python publish.py --job {job_id} --immediate")
            sys.exit(0)

    # -- Step 3: upload_youtube -----------------------------------------------
    if not is_complete("upload_youtube", state):
        print("Uploading to YouTube...")
        result = upload_youtube.run(job_id, final_video, metadata, project_root)
        state["video_id"] = result["video_id"]
        state["video_url"] = result["url"]
        save_state(state, project_root)
        state = mark_complete("upload_youtube", state, project_root)
    else:
        print("Upload: already done")

    # -- Step 4: monitor_upload -----------------------------------------------
    if not is_complete("monitor_upload", state):
        monitor_upload.run(job_id, state.get("video_id", ""), metadata["title"], project_root)
        state = mark_complete("monitor_upload", state, project_root)
    else:
        print(f"Monitoring card: youtube.com/shorts/{state.get('video_id', 'unknown')}")


if __name__ == "__main__":
    main()
