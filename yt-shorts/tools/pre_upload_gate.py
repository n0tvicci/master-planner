CHECKS = [
    "Loop confirmed — first frame matches last frame?",
    "Clip count is 22–25?",
    "Total length 54–60 sec?",
    "Captions syllable-synced?",
    "No copyrighted audio audible?",
]


def run() -> dict:
    print("\nHUMAN SIGN-OFF REQUIRED before upload:")
    failed = []
    for check in CHECKS:
        ans = input(f"  □ {check}  [y/n]: ").strip().lower()
        if ans != "y":
            failed.append(check)

    if failed:
        print("\nThe following checks did not pass:")
        for c in failed:
            print(f"  ✗ {c}")
        print("\nFix issues and re-run publish.py to retry.")
        return {"status": "FAIL", "failed_checks": failed}

    confirm = input("\nType YES to confirm all checks passed, or NO to abort upload: ").strip()
    if confirm == "YES":
        return {"status": "PASS"}

    return {"status": "FAIL", "failed_checks": ["Final confirmation not given"]}


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2))
