"""
search_footage.py — Concurrent Pexels + Pixabay clip search with Claude fallback queries.

Usage:
    python tools/search_footage.py <job_id>

Reads:  scripts/<job_id>/script.json
Writes: footage/<job_id>/clip_NN.mp4  (one per sentence)

Returns a sorted list of result dicts:
    {"idx": int, "status": "found"|"cached"|"not_found", "source": str, "path": str}
"""

import json
import concurrent.futures
from pathlib import Path
import requests


def search_pexels(query: str, api_key: str) -> list[dict]:
    r = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": api_key},
        params={"query": query, "per_page": 3, "orientation": "portrait"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("videos", [])


def best_pexels_url(videos: list) -> str | None:
    for v in videos:
        files = sorted(v.get("video_files", []), key=lambda f: f.get("height", 0), reverse=True)
        for f in files:
            if f.get("height", 0) >= 720:
                return f["link"]
    return None


def search_pixabay(query: str, api_key: str) -> list[dict]:
    r = requests.get(
        "https://pixabay.com/api/videos/",
        params={"key": api_key, "q": query, "per_page": 3},
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("hits", [])


def best_pixabay_url(hits: list) -> str | None:
    for h in hits:
        for quality in ("full", "large", "medium"):
            url = h.get("videos", {}).get(quality, {}).get("url")
            if url:
                return url
    return None


def _download(url: str, out_path: Path) -> bool:
    r = requests.get(url, stream=True, timeout=30)
    if r.status_code == 200:
        out_path.write_bytes(r.content)
        return True
    return False


def _generate_fallback_queries(sentence: dict, config: dict) -> list[str]:
    import anthropic
    client = anthropic.Anthropic(api_key=config["anthropic_api_key"])
    prompt = (
        f"Generate 2 alternative stock footage search queries for:\n"
        f'"{sentence["text"]}"\n'
        f"Original queries returned no results: '{sentence['pexels_query']}', '{sentence['pixabay_query']}'\n"
        f"Rules: 3-5 words, no people, objects or environments only, visually dramatic.\n"
        f"Output JSON array of 2 strings only. No preamble."
    )
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(response.content[0].text)


def _search_one(idx: int, sentence: dict, job_id: str, config: dict, project_root: Path) -> dict:
    out_dir = project_root / "footage" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"clip_{idx:02d}.mp4"

    if out_path.exists():
        return {"idx": idx, "status": "cached", "path": str(out_path)}

    pexels = search_pexels(sentence["pexels_query"], config["pexels_api_key"])
    url = best_pexels_url(pexels)
    source = "pexels"

    if not url:
        pixabay = search_pixabay(sentence["pixabay_query"], config["pixabay_api_key"])
        url = best_pixabay_url(pixabay)
        source = "pixabay"

    if url and _download(url, out_path):
        return {"idx": idx, "status": "found", "source": source, "path": str(out_path)}

    # Both APIs empty — generate fallback queries via Claude and retry
    try:
        fallback_queries = _generate_fallback_queries(sentence, config)
        for fq in fallback_queries:
            pexels = search_pexels(fq, config["pexels_api_key"])
            url = best_pexels_url(pexels)
            if url and _download(url, out_path):
                return {"idx": idx, "status": "found", "source": "pexels_fallback", "path": str(out_path)}
    except Exception:
        pass  # Fallback failure is non-fatal — gap detection handles it

    return {"idx": idx, "status": "not_found", "query": sentence["pexels_query"]}


def run(job_id: str, config: dict, project_root: Path) -> list[dict]:
    script_file = project_root / "scripts" / job_id / "script.json"
    if not script_file.exists():
        raise FileNotFoundError(f"Script not found: {script_file}. Run generate_script first.")
    try:
        script = json.loads(script_file.read_text())
    except (json.JSONDecodeError, OSError) as e:
        raise RuntimeError(f"Could not read script for job {job_id}: {e}") from e

    sentences = script["sentences"]

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(_search_one, i, s, job_id, config, project_root): i
            for i, s in enumerate(sentences)
        }
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            status = result["status"]
            src = f" [{result.get('source', '')}]" if status == "found" else ""
            print(f"  Clip {result['idx']:02d}: {status}{src}")

    found = sum(1 for r in results if r["status"] in ("found", "cached"))
    print(f"\n  Footage: {found}/{len(sentences)} clips found")
    return sorted(results, key=lambda r: r["idx"])


if __name__ == "__main__":
    import sys
    from tools.utils.config import load_config
    project_root = Path(__file__).parent.parent
    run(sys.argv[1], load_config(), project_root)
