#!/usr/bin/env python3
"""
Pre-edit pipeline orchestrator.

Usage:
  python pipeline.py                         run full pipeline with next approved topic
  python pipeline.py --topics-only           generate and queue topics, then exit
  python pipeline.py --job <id>              resume a specific job
  python pipeline.py --job <id> --revise     re-run script generation after compliance failure
  python pipeline.py --job <id> --voice <id> use alternate ElevenLabs voice for this job
"""
import argparse
import json
import sys
from pathlib import Path

import os as _os
PROJECT_ROOT = Path(_os.environ["PIPELINE_PROJECT_ROOT"]) if "PIPELINE_PROJECT_ROOT" in _os.environ else Path(__file__).parent


def _get_next_approved_topic(project_root: Path) -> dict | None:
    queue_file = project_root / "topics" / "queue.json"
    if not queue_file.exists():
        return None
    try:
        queue = json.loads(queue_file.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    approved = [t for t in queue if t.get("status") == "approved"]
    return approved[0] if approved else None


def _set_topic_status(topic_id: str, status: str, project_root: Path) -> None:
    queue_file = project_root / "topics" / "queue.json"
    try:
        queue = json.loads(queue_file.read_text())
    except (json.JSONDecodeError, OSError):
        return
    for t in queue:
        if t["id"] == topic_id:
            t["status"] = status
    queue_file.write_text(json.dumps(queue, indent=2))


def _interactive_approve_topics(project_root: Path) -> None:
    queue_file = project_root / "topics" / "queue.json"
    if not queue_file.exists():
        print("No topics queue found. Run --topics-only first.")
        return
    try:
        queue = json.loads(queue_file.read_text())
    except (json.JSONDecodeError, OSError):
        print("Could not read topics queue.")
        return
    pending = [t for t in queue if t.get("status") == "pending"]
    if not pending:
        print("No pending topics to approve.")
        return

    print(f"\n{len(pending)} pending topics:\n")
    for t in pending:
        tier = t.get("tier", "?")
        score = t.get("tier_score", "?")
        print(f"  [Tier {tier} | {score}/10] {t['title']}")
        ans = input("  Approve? [y/n]: ").strip().lower()
        if ans == "y":
            t["status"] = "approved"
            print("  -> Approved\n")
        else:
            print("  -> Skipped\n")

    queue_file.write_text(json.dumps(queue, indent=2))
    approved = sum(1 for t in queue if t.get("status") == "approved")
    print(f"{approved} topic(s) approved in queue.")


def main(project_root: Path | None = None) -> None:
    import pipeline as _self_module
    if project_root is None:
        project_root = _self_module.PROJECT_ROOT

    parser = argparse.ArgumentParser(description="YT Shorts pre-edit pipeline")
    parser.add_argument("--topics-only", action="store_true",
                        help="Generate and queue topics, then exit")
    parser.add_argument("--approve-topics", action="store_true",
                        help="Interactively approve pending topics from queue.json")
    parser.add_argument("--job", help="Resume or target specific job ID")
    parser.add_argument("--revise", action="store_true",
                        help="Re-run script generation after compliance failure")
    parser.add_argument("--voice", help="ElevenLabs voice ID override for this job")
    parser.add_argument("--max-ai-clips", type=int, default=5,
                        help="Max Runway API generations per job (default 5, ~$1.25)")
    parser.add_argument("--strict-props", action="store_true",
                        help="Halt on prop-library gaps instead of attempting Runway fallback")
    args = parser.parse_args()

    sys.path.insert(0, str(PROJECT_ROOT))

    from tools.utils.config import load_config
    from tools.utils.state import load_state, mark_complete, is_complete, save_state
    from tools.utils.job import make_job_id
    import tools.generate_topics as generate_topics
    import tools.generate_script as generate_script
    import tools.check_compliance as check_compliance
    import tools.generate_voiceover as generate_voiceover
    import tools.select_music as select_music
    import tools.search_footage as search_footage
    import tools.clear_footage as clear_footage
    import tools.check_footage_gaps as check_footage_gaps
    import tools.generate_ai_footage as generate_ai_footage
    import tools.package_assets as package_assets

    config = load_config()

    # -- approve-topics mode --------------------------------------------------
    if args.approve_topics:
        _interactive_approve_topics(project_root)
        return

    # -- topics-only mode -----------------------------------------------------
    if args.topics_only:
        print("Generating topics...")
        topics = generate_topics.run(config, project_root)
        generate_topics.append_to_queue(topics, project_root)
        print("\nRun: python pipeline.py --approve-topics")
        return

    # -- determine job ID and topic -------------------------------------------
    if args.job:
        job_id = args.job
        state = load_state(job_id, project_root)
        topic = state.get("topic")
        if not topic:
            print(f"No state found for job {job_id}. Check .tmp/{job_id}/state.json")
            sys.exit(1)
    else:
        topic = _get_next_approved_topic(project_root)
        if not topic:
            print("No approved topics in queue.")
            print("   Run: python pipeline.py --topics-only")
            print("   Then open topics/queue.json and set status -> \"approved\"")
            sys.exit(0)
        job_id = make_job_id(topic["title"])
        state = {
            "job_id": job_id,
            "topic": topic,
            "topic_id": topic["id"],
            "completed_steps": [],
        }
        if args.voice:
            state["voice_id"] = args.voice
        save_state(state, project_root)
        _set_topic_status(topic["id"], "in_progress", project_root)
        print(f"\nJob: {job_id}")
        print(f"   Topic: {topic['title']}\n")

    # -- revise mode ----------------------------------------------------------
    if args.revise:
        script_file = project_root / "scripts" / job_id / "script.json"
        revision_notes = None
        if script_file.exists():
            try:
                saved = json.loads(script_file.read_text())
                revision_notes = saved.get("compliance", {}).get("revision_notes")
            except (json.JSONDecodeError, OSError):
                pass
        state["completed_steps"] = [
            s for s in state["completed_steps"]
            if s not in ("generate_script", "check_compliance")
        ]
        state["revision_notes"] = revision_notes
        save_state(state, project_root)
        print("Revision mode -- re-running script generation with failure context\n")

    # -- pipeline steps -------------------------------------------------------
    if not is_complete("generate_script", state):
        print("Generating script...")
        revision_context = state.get("revision_notes") if args.revise else None
        generate_script.run(job_id, topic, config, project_root, revision_context)
        state = mark_complete("generate_script", state, project_root)
        scripts_dir = project_root / "scripts" / job_id
        script_path = scripts_dir / "script.json"
        if script_path.exists():
            with open(script_path) as f:
                script_data = json.load(f)
            if script_data.get("status") == "TOPIC_REJECTED":
                print(f"Topic rejected during script generation: {script_data.get('reason', '')}")
                print("Run pipeline.py --topics-only to queue a new topic.")
                sys.exit(0)
    else:
        print("Script: already done")

    if not is_complete("check_compliance", state):
        print("Checking compliance...")
        MAX_COMPLIANCE_RETRIES = 3
        for attempt in range(MAX_COMPLIANCE_RETRIES):
            result = check_compliance.run(job_id, project_root)
            if result["status"] == "PASS":
                break
            if attempt < MAX_COMPLIANCE_RETRIES - 1:
                print(f"   Auto-retry {attempt + 1}/{MAX_COMPLIANCE_RETRIES - 1} -- regenerating script with revision context...")
                try:
                    saved = json.loads((project_root / "scripts" / job_id / "script.json").read_text())
                    revision_context = saved.get("compliance", {}).get("revision_notes") or result.get("notes")
                except (json.JSONDecodeError, OSError, FileNotFoundError):
                    revision_context = result.get("notes")
                generate_script.run(job_id, topic, config, project_root, revision_context)
            else:
                print(f"\nScript failed compliance after {MAX_COMPLIANCE_RETRIES} attempts.")
                print(f"   Manual fix: python pipeline.py --job {job_id} --revise")
                sys.exit(1)
        state = mark_complete("check_compliance", state, project_root)
    else:
        print("Compliance: already done")

    if not is_complete("generate_voiceover", state):
        print("Generating voiceover...")
        voice_id = state.get("voice_id") or args.voice
        generate_voiceover.run(job_id, config, project_root, voice_id)
        state = mark_complete("generate_voiceover", state, project_root)
    else:
        print("Voiceover: already done")

    if not is_complete("select_music", state):
        print("Selecting background music...")
        try:
            select_music.run(job_id, project_root)
            state = mark_complete("select_music", state, project_root)
        except FileNotFoundError as e:
            print(f"  {e}")
            print("   Add MP3 tracks to music/tense/, music/dramatic/, or music/suspenseful/")
            print("   Then re-run: python pipeline.py --job", job_id)
            sys.exit(1)
    else:
        print("Music: already done")

    if not is_complete("search_footage", state):
        print("Searching footage...")
        search_footage.run(job_id, config, project_root)
        state = mark_complete("search_footage", state, project_root)
    else:
        print("Footage: already done")

    if not is_complete("clear_footage", state):
        print("Stripping audio from clips...")
        clear_footage.run(job_id, project_root)
        state = mark_complete("clear_footage", state, project_root)
    else:
        print("Footage cleared: already done")

    if not is_complete("check_footage_gaps", state):
        print("Checking for footage gaps...")
        gap_result = check_footage_gaps.run(job_id, project_root)
        state = mark_complete("check_footage_gaps", state, project_root)
        state["gap_result"] = gap_result
        save_state(state, project_root)
    else:
        print("Gaps checked: already done")
        gap_result = state.get("gap_result", {"ai_gaps": [], "prop_library_gaps": []})

    prop_gaps = gap_result.get("prop_library_gaps", [])
    if prop_gaps and args.strict_props:
        print(f"\nPAUSED -- {len(prop_gaps)} prop library clip(s) need manual filming.")
        print(f"   Instructions: assets/{job_id}/footage-gaps.md")
        print(f"   Film the props, save to footage/{job_id}/gaps/, then re-run:")
        print(f"   python pipeline.py --job {job_id}")
        sys.exit(0)

    if not is_complete("generate_ai_footage", state):
        ai_gaps = gap_result.get("ai_gaps", [])
        if ai_gaps:
            print(f"Auto-generating {len(ai_gaps)} AI footage gap(s) via Runway...")
        try:
            results = generate_ai_footage.run(
                job_id, ai_gaps, project_root, max_clips=args.max_ai_clips
            )
        except RuntimeError as e:
            print(f"\n{e}")
            sys.exit(1)
        if ai_gaps:
            failed = [r for r in results if r["status"] == "failed"]
            if failed:
                print(f"{len(failed)} Runway generation(s) failed -- see footage-gaps.md")
                sys.exit(1)
        state = mark_complete("generate_ai_footage", state, project_root)
        save_state(state, project_root)
    else:
        print("AI footage: already done")

    if prop_gaps:
        print(f"Attempting Runway fallback for {len(prop_gaps)} prop-library gap(s)...")
        try:
            prop_results = generate_ai_footage.run(
                job_id, prop_gaps, project_root, max_clips=args.max_ai_clips
            )
            failed_props = [r for r in prop_results if r["status"] == "failed"]
            if failed_props:
                print(f"  {len(failed_props)} prop gap(s) unresolved -- film manually or review footage-gaps.md")
        except RuntimeError as e:
            print(f"\n  Runway cap hit for prop gaps: {e}")
            print(f"   Film manually or raise cap: --max-ai-clips N --strict-props to halt instead")

    if not is_complete("package_assets", state):
        print("Packaging assets...")
        package_assets.run(job_id, project_root)
        state = mark_complete("package_assets", state, project_root)
        topic_id = state.get("topic_id")
        if topic_id:
            _set_topic_status(topic_id, "used", project_root)
        else:
            print("Warning: topic_id not found in state, skipping topic status update")
    else:
        print(f"Assets already packaged -- open: assets/{job_id}/")
        print(f"   Next: python publish.py --job {job_id}")


if __name__ == "__main__":
    main()
