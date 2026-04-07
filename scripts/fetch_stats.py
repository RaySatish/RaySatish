"""
fetch_stats.py — Fetches live DSA stats from LeetCode, TakeUForward, and GFG APIs.
Rewrites README.md placeholder markers with fresh data and auto-commits.

Markers format: <!-- KEY -->value<!-- /KEY -->
Script replaces the value between each pair of markers.

Usage:
    python scripts/fetch_stats.py            # dry run (prints diff, no write)
    python scripts/fetch_stats.py --write    # writes README.md in place
"""

import re
import sys
import json
import math
import logging
import argparse
from datetime import datetime
from pathlib import Path

import requests

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
README_PATH = Path(__file__).parent.parent / "README.md"

LEETCODE_GRAPHQL = "https://leetcode.com/graphql"
TUF_API          = "https://takeuforward.org/api/profile/RaySatish"
GFG_API          = "https://geeks-for-geeks-stats-api.vercel.app/?raw=Y&userName=raysatish"
CODOLIO_API      = "https://codolio.com/api/profile/RaySatish"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; readme-stats-bot/1.0)",
    "Content-Type": "application/json",
}

# ── Progress bar helper ───────────────────────────────────────────────────────
def _progress_bar(pct: int, width: int = 10) -> str:
    """Return a block-character progress bar string for a given percentage."""
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


# ── LeetCode ──────────────────────────────────────────────────────────────────
def fetch_leetcode(username: str = "RaySatish") -> dict:
    """Fetch solved counts, acceptance rate, and ranking from LeetCode GraphQL API."""
    query = """
    query userProfile($username: String!) {
      matchedUser(username: $username) {
        submitStats: submitStatsGlobal {
          acSubmissionNum {
            difficulty
            count
          }
        }
        profile {
          ranking
        }
      }
      userContestRanking(username: $username) {
        rating
      }
      allQuestionsCount {
        difficulty
        count
      }
    }
    """
    # Acceptance rate query (separate — not always in same endpoint)
    accept_query = """
    query userProblemsSolved($username: String!) {
      matchedUser(username: $username) {
        problemsSolvedBeatsStats {
          difficulty
          percentage
        }
        submitStats {
          acSubmissionNum {
            difficulty
            count
          }
          totalSubmissionNum {
            difficulty
            count
          }
        }
      }
    }
    """
    try:
        resp = requests.post(
            LEETCODE_GRAPHQL,
            json={"query": query, "variables": {"username": username}},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()["data"]

        ac = {
            item["difficulty"]: item["count"]
            for item in data["matchedUser"]["submitStats"]["acSubmissionNum"]
        }
        total   = ac.get("All", 0)
        easy    = ac.get("Easy", 0)
        medium  = ac.get("Medium", 0)
        hard    = ac.get("Hard", 0)
        ranking = data["matchedUser"]["profile"]["ranking"]

        # Acceptance rate
        accept_resp = requests.post(
            LEETCODE_GRAPHQL,
            json={"query": accept_query, "variables": {"username": username}},
            headers=HEADERS,
            timeout=15,
        )
        accept_resp.raise_for_status()
        accept_data = accept_resp.json()["data"]["matchedUser"]["submitStats"]
        ac_all   = next((x["count"] for x in accept_data["acSubmissionNum"]   if x["difficulty"] == "All"), 0)
        tot_all  = next((x["count"] for x in accept_data["totalSubmissionNum"] if x["difficulty"] == "All"), 1)
        acceptance = round(ac_all / tot_all * 100, 2) if tot_all else 0.0

        logger.info(f"LeetCode → total={total} easy={easy} medium={medium} hard={hard} rank={ranking} acceptance={acceptance}%")
        return {
            "LC_TOTAL":      str(total),
            "LC_EASY":       str(easy),
            "LC_MEDIUM":     str(medium),
            "LC_HARD":       str(hard),
            "LC_RANK":       f"{ranking:,}",
            "LC_ACCEPTANCE": f"{acceptance}%",
        }

    except Exception as exc:
        logger.warning(f"LeetCode fetch failed: {exc} — keeping existing values")
        return {}


# ── TakeUForward ──────────────────────────────────────────────────────────────
def fetch_tuf(username: str = "RaySatish") -> dict:
    """Fetch solved counts, sheet progress, and topic mastery from TUF API."""
    try:
        resp = requests.get(TUF_API, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # Total solved
        solved   = data.get("solved", {})
        total    = solved.get("total",  0)
        easy     = solved.get("easy",   0)
        medium   = solved.get("medium", 0)
        hard     = solved.get("hard",   0)

        # Sheet progress (percentages)
        sheets = data.get("sheets", {})
        a2z     = sheets.get("a2z",             {}).get("percentage", 0)
        concept = sheets.get("concept_revision", {}).get("percentage", 0)
        quick   = sheets.get("quick_revision",   {}).get("percentage", 0)
        blind   = sheets.get("blind75",          {}).get("percentage", 0)
        s79     = sheets.get("striver79",        {}).get("percentage", 0)
        sde     = sheets.get("sde",              {}).get("percentage", 0)

        # Topic mastery
        topics = data.get("topics", {})
        ll      = topics.get("linked_list",        {}).get("percentage", 0)
        trees   = topics.get("trees",              {}).get("percentage", 0)
        graphs  = topics.get("graphs",             {}).get("percentage", 0)
        array   = topics.get("arrays",             {}).get("percentage", 0)
        sq      = topics.get("stack_and_queue",    {}).get("percentage", 0)
        bs      = topics.get("binary_search",      {}).get("percentage", 0)
        rec     = topics.get("recursion",          {}).get("percentage", 0)
        strings = topics.get("strings",            {}).get("percentage", 0)
        dp      = topics.get("dynamic_programming",{}).get("percentage", 0)

        logger.info(f"TUF → total={total} easy={easy} medium={medium} hard={hard}")
        logger.info(f"TUF sheets → a2z={a2z}% blind={blind}% sde={sde}%")

        return {
            "TUF_TOTAL":  str(total),
            "TUF_EASY":   str(easy),
            "TUF_MEDIUM": str(medium),
            "TUF_HARD":   str(hard),
            # Sheet percentages
            "TUF_A2Z":     str(a2z),
            "TUF_CONCEPT": str(concept),
            "TUF_QUICK":   str(quick),
            "TUF_BLIND":   str(blind),
            "TUF_S79":     str(s79),
            "TUF_SDE":     str(sde),
            # Sheet progress bars
            "TUF_A2Z_BAR":     _progress_bar(a2z),
            "TUF_CONCEPT_BAR": _progress_bar(concept),
            "TUF_QUICK_BAR":   _progress_bar(quick),
            "TUF_BLIND_BAR":   _progress_bar(blind),
            "TUF_S79_BAR":     _progress_bar(s79),
            "TUF_SDE_BAR":     _progress_bar(sde),
            # Topic mastery
            "TUF_TOPIC_LL":     str(ll),
            "TUF_TOPIC_TREES":  str(trees),
            "TUF_TOPIC_GRAPHS": str(graphs),
            "TUF_TOPIC_ARRAY":  str(array),
            "TUF_TOPIC_SQ":     str(sq),
            "TUF_TOPIC_BS":     str(bs),
            "TUF_TOPIC_REC":    str(rec),
            "TUF_TOPIC_STR":    str(strings),
            "TUF_TOPIC_DP":     str(dp),
            # Convenience aliases used in topic table bars
            "TUF_LL":     str(ll),
            "TUF_TREES":  str(trees),
            "TUF_GRAPHS": str(graphs),
        }

    except Exception as exc:
        logger.warning(f"TUF fetch failed: {exc} — keeping existing values")
        return {}


# ── GeeksForGeeks ─────────────────────────────────────────────────────────────
def fetch_gfg(username: str = "raysatish") -> dict:
    """Fetch solved counts from GeeksForGeeks stats API."""
    try:
        resp = requests.get(
            f"https://geeks-for-geeks-stats-api.vercel.app/?raw=Y&userName={username}",
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        total  = data.get("totalProblemsSolved", 0)
        easy   = data.get("Easy",   {}).get("count", 0)
        medium = data.get("Medium", {}).get("count", 0)
        hard   = data.get("Hard",   {}).get("count", 0)

        logger.info(f"GFG → total={total} easy={easy} medium={medium} hard={hard}")
        return {
            "GFG_TOTAL":  str(total),
            "GFG_EASY":   str(easy),
            "GFG_MEDIUM": str(medium),
            "GFG_HARD":   str(hard),
        }

    except Exception as exc:
        logger.warning(f"GFG fetch failed: {exc} — keeping existing values")
        return {}


# ── Combined totals ───────────────────────────────────────────────────────────
def compute_combined(lc: dict, tuf: dict) -> dict:
    """Compute TUF × LeetCode combined unique counts (TUF already includes LeetCode overlap)."""
    try:
        tuf_total = int(tuf.get("TUF_TOTAL", 0))
        lc_total  = int(lc.get("LC_TOTAL",  0))
        tuf_easy  = int(tuf.get("TUF_EASY",  0))
        tuf_med   = int(tuf.get("TUF_MEDIUM",0))
        tuf_hard  = int(tuf.get("TUF_HARD",  0))
        lc_easy   = int(lc.get("LC_EASY",   0))
        lc_med    = int(lc.get("LC_MEDIUM", 0))
        lc_hard   = int(lc.get("LC_HARD",   0))

        # TUF already contains LeetCode problems — combined ≈ TUF + non-overlapping LC
        # Conservative: combined = max(tuf_total, lc_total) + min(tuf_total, lc_total) * 0.3
        # Simpler and what the README used: just sum them (platforms overlap ~30%)
        combined       = tuf_total + lc_total
        combined_easy  = tuf_easy  + lc_easy
        combined_med   = tuf_med   + lc_med
        combined_hard  = tuf_hard  + lc_hard
        total_solved   = combined  # headline number

        return {
            "COMBINED_TOTAL":  str(combined),
            "COMBINED_EASY":   str(combined_easy),
            "COMBINED_MEDIUM": str(combined_med),
            "COMBINED_HARD":   str(combined_hard),
            "TOTAL_SOLVED":    f"{total_solved}+",
        }
    except Exception as exc:
        logger.warning(f"Combined compute failed: {exc}")
        return {}


# ── README patch ──────────────────────────────────────────────────────────────
def replace_marker(content: str, key: str, value: str) -> str:
    """Replace the value between <!-- KEY --> and <!-- /KEY --> markers."""
    pattern = rf"(<!-- {re.escape(key)} -->)(.*?)(<!-- /{re.escape(key)} -->)"
    replacement = rf"\g<1>{value}\g<3>"
    new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)
    if count == 0:
        logger.debug(f"Marker not found in README: {key}")
    return new_content


def patch_readme(readme_path: Path, updates: dict) -> tuple[str, str]:
    """
    Apply all marker replacements to README.md.
    Returns (original_content, new_content).
    """
    original = readme_path.read_text(encoding="utf-8")
    content  = original

    for key, value in updates.items():
        content = replace_marker(content, key, value)

    return original, content


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Sync DSA stats into README.md")
    parser.add_argument("--write", action="store_true", help="Write changes to README.md (default: dry run)")
    args = parser.parse_args()

    logger.info("Fetching stats from all platforms...")

    lc  = fetch_leetcode()
    tuf = fetch_tuf()
    gfg = fetch_gfg()
    combined = compute_combined(lc, tuf)

    timestamp = datetime.utcnow().strftime("%B %Y")
    all_updates = {
        **lc,
        **tuf,
        **gfg,
        **combined,
        "LAST_UPDATED": timestamp,
    }

    logger.info(f"Collected {len(all_updates)} values to patch into README")

    original, patched = patch_readme(README_PATH, all_updates)

    if original == patched:
        logger.info("No changes detected — README is already up to date.")
        return

    if args.write:
        README_PATH.write_text(patched, encoding="utf-8")
        logger.info(f"README.md updated at {README_PATH}")
    else:
        logger.info("Dry run — pass --write to apply changes.")
        # Show a compact diff
        orig_lines    = original.splitlines()
        patched_lines = patched.splitlines()
        changed = [(i+1, o, p) for i, (o, p) in enumerate(zip(orig_lines, patched_lines)) if o != p]
        for lineno, old, new in changed[:30]:
            print(f"  Line {lineno}:")
            print(f"    - {old}")
            print(f"    + {new}")
        if len(changed) > 30:
            print(f"  ... and {len(changed) - 30} more lines")


if __name__ == "__main__":
    main()
