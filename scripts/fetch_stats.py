"""
fetch_stats.py — Fetches live DSA stats and rewrites README.md sections in-place.

Strategy (no HTML comments inside URLs or table cells):
  - DSA table:    rebuilds entire block between <!-- DSA_TABLE_START --> and <!-- DSA_TABLE_END -->
  - TUF sheets:   rebuilds entire block between <!-- TUF_SHEETS_START --> and <!-- TUF_SHEETS_END -->
  - TUF topics:   rebuilds entire block between <!-- TUF_TOPICS_START --> and <!-- TUF_TOPICS_END -->
  - whoami line:  replaces the single line containing ← TOTAL_SOLVED_LINE sentinel
"""

import re
import sys
import json
import logging
import urllib.request
import urllib.error
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

README = Path(__file__).parent.parent / "README.md"

# ── helpers ──────────────────────────────────────────────────────────────────

def _get(url: str, headers: dict | None = None, timeout: int = 15) -> dict | None:
    req = urllib.request.Request(url, headers=headers or {
        "User-Agent": "Mozilla/5.0 (compatible; readme-stats-bot/1.0)"
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        log.warning(f"GET {url} failed: {e}")
        return None


def _post(url: str, payload: dict, headers: dict | None = None, timeout: int = 15) -> dict | None:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; readme-stats-bot/1.0)",
        **(headers or {}),
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        log.warning(f"POST {url} failed: {e}")
        return None


def _badge(label: str, value: str | int, color: str, style: str = "flat-square") -> str:
    """Return a shields.io badge markdown image (no HTML comments anywhere)."""
    label_enc = str(label).replace(" ", "_").replace("-", "--")
    value_enc = str(value).replace(" ", "_").replace("-", "--").replace("%", "%25")
    return f"![](https://img.shields.io/badge/{label_enc}-{value_enc}-{color}?style={style}&labelColor=0d0d0d)"


# ── fetchers ─────────────────────────────────────────────────────────────────

def fetch_leetcode() -> dict:
    """Returns total, easy, medium, hard for LeetCode user RaySatish."""
    query = """
    query getUserProfile($username: String!) {
      matchedUser(username: $username) {
        submitStats: submitStatsGlobal {
          acSubmissionNum { difficulty count }
        }
      }
    }
    """
    data = _post(
        "https://leetcode.com/graphql",
        {"query": query, "variables": {"username": "RaySatish"}},
        headers={"Referer": "https://leetcode.com"},
    )
    defaults = {"total": 153, "easy": 62, "medium": 80, "hard": 11}
    if not data:
        log.warning("LeetCode: using cached defaults")
        return defaults
    try:
        nums = data["data"]["matchedUser"]["submitStats"]["acSubmissionNum"]
        d = {x["difficulty"].lower(): x["count"] for x in nums}
        return {
            "total": d.get("all", defaults["total"]),
            "easy":  d.get("easy", defaults["easy"]),
            "medium": d.get("medium", defaults["medium"]),
            "hard":  d.get("hard", defaults["hard"]),
        }
    except Exception as e:
        log.warning(f"LeetCode parse error: {e}")
        return defaults


def fetch_tuf() -> dict:
    """Returns solved counts, sheet %, topic % for TakeUForward user RaySatish."""
    defaults = {
        "total": 305, "easy": 97, "medium": 120, "hard": 88,
        "sheets": {
            "A2Z Sheet": 74, "DSA Concept Revision": 73,
            "DSA Quick Revision": 63, "Blind 75": 48,
            "Striver 79": 68, "SDE Sheet": 47,
        },
        "topics": {
            "Linked Lists": 100, "Trees": 91, "Graphs": 89,
            "Binary Search": 85, "Dynamic Programming": 27,
        },
    }
    data = _get("https://takeuforward.org/api/profile/RaySatish")
    if not data:
        log.warning("TUF: using cached defaults")
        return defaults

    try:
        result = dict(defaults)

        # solved counts
        solved = data.get("data", {}).get("solvedProblems", {})
        if solved:
            result["total"]  = solved.get("total",  defaults["total"])
            result["easy"]   = solved.get("easy",   defaults["easy"])
            result["medium"] = solved.get("medium", defaults["medium"])
            result["hard"]   = solved.get("hard",   defaults["hard"])

        # sheet progress
        sheets_raw = data.get("data", {}).get("sheets", [])
        if sheets_raw:
            sheet_map = {}
            for s in sheets_raw:
                name = s.get("name", "")
                total_q = s.get("totalQuestions", 0)
                solved_q = s.get("solvedQuestions", 0)
                if total_q > 0:
                    sheet_map[name] = round(solved_q / total_q * 100)
            # map API names → display names
            name_map = {
                "A2Z Sheet": "A2Z Sheet",
                "DSA Concept Revision": "DSA Concept Revision",
                "DSA Quick Revision": "DSA Quick Revision",
                "Blind 75": "Blind 75",
                "Striver 79": "Striver 79",
                "SDE Sheet": "SDE Sheet",
            }
            merged = dict(defaults["sheets"])
            for api_name, display_name in name_map.items():
                if api_name in sheet_map:
                    merged[display_name] = sheet_map[api_name]
            result["sheets"] = merged

        # topic mastery
        topics_raw = data.get("data", {}).get("topics", [])
        if topics_raw:
            topic_map = {}
            for t in topics_raw:
                name = t.get("name", "")
                total_q = t.get("totalQuestions", 0)
                solved_q = t.get("solvedQuestions", 0)
                if total_q > 0:
                    topic_map[name] = round(solved_q / total_q * 100)
            display_topics = ["Linked Lists", "Trees", "Graphs", "Binary Search", "Dynamic Programming"]
            merged_topics = dict(defaults["topics"])
            for dn in display_topics:
                if dn in topic_map:
                    merged_topics[dn] = topic_map[dn]
            result["topics"] = merged_topics

        return result

    except Exception as e:
        log.warning(f"TUF parse error: {e}")
        return defaults


def fetch_gfg() -> dict:
    """Returns total, easy, medium, hard for GeeksForGeeks user raysatish."""
    defaults = {"total": 50, "easy": 16, "medium": 32, "hard": 2}
    data = _get("https://geeks-for-geeks-stats-api.vercel.app/?raw=Y&userName=raysatish")
    if not data or data.get("status") == "error":
        log.warning("GFG: using cached defaults")
        return defaults
    try:
        info = data.get("info", {})
        easy   = int(info.get("School", 0)) + int(info.get("Basic", 0)) + int(info.get("Easy", 0))
        medium = int(info.get("Medium", 0))
        hard   = int(info.get("Hard", 0))
        return {
            "total":  easy + medium + hard or defaults["total"],
            "easy":   easy  or defaults["easy"],
            "medium": medium or defaults["medium"],
            "hard":   hard  or defaults["hard"],
        }
    except Exception as e:
        log.warning(f"GFG parse error: {e}")
        return defaults


# ── section builders ──────────────────────────────────────────────────────────

def build_dsa_table(lc: dict, tuf: dict, gfg: dict) -> str:
    """Builds the full DSA stats markdown table (no HTML comments)."""
    combined = lc["total"] + tuf["total"] + gfg["total"]

    def row(platform: str, d: dict, link: str) -> str:
        return (
            f"| **{platform}** "
            f"| {_badge('solved', d['total'], 'e8f55a')} "
            f"| {_badge('easy', d['easy'], '5af5c8')} "
            f"| {_badge('medium', d['medium'], 'f5a623')} "
            f"| {_badge('hard', d['hard'], 'ff6b6b')} "
            f"| [↗]({link}) |"
        )

    lines = [
        "| Platform | Total | 🟢 Easy | 🟡 Medium | 🔴 Hard | Link |",
        "|:---:|:---:|:---:|:---:|:---:|:---:|",
        row("LeetCode",     lc,  "https://leetcode.com/u/RaySatish/"),
        row("TakeUForward", tuf, "https://takeuforward.org/profile/RaySatish"),
        row("GeeksForGeeks",gfg, "https://www.geeksforgeeks.org/user/raysatish/"),
        f"| **✨ Combined** | {_badge('total', combined, '6C5CE7')} | — | — | — | — |",
    ]
    return "\n".join(lines)


def build_tuf_sheets(tuf: dict) -> str:
    """Builds the TUF sheet progress table (no HTML comments)."""
    icons = {
        "A2Z Sheet": "📘",
        "DSA Concept Revision": "🔁",
        "DSA Quick Revision": "⚡",
        "Blind 75": "👁",
        "Striver 79": "🎯",
        "SDE Sheet": "🗂",
    }
    label_map = {
        "A2Z Sheet": "A2Z_Sheet",
        "DSA Concept Revision": "Concept_Revision",
        "DSA Quick Revision": "Quick_Revision",
        "Blind 75": "Blind_75",
        "Striver 79": "Striver_79",
        "SDE Sheet": "SDE_Sheet",
    }
    color_map = {
        "A2Z Sheet": "e8f55a",
        "DSA Concept Revision": "e8f55a",
        "DSA Quick Revision": "5af5c8",
        "Blind 75": "5af5c8",
        "Striver 79": "f5a623",
        "SDE Sheet": "f5a623",
    }
    lines = [
        "| Sheet | Progress | % |",
        "|:---|:---:|:---:|",
    ]
    for name, pct in tuf["sheets"].items():
        icon  = icons.get(name, "📋")
        label = label_map.get(name, name.replace(" ", "_"))
        color = color_map.get(name, "e8f55a")
        badge = _badge(label, f"{pct}%25", color, style="for-the-badge").replace("%2525", "%25")
        lines.append(f"| {icon} {name} | {badge} | {pct}% |")
    return "\n".join(lines)


def build_tuf_topics(tuf: dict) -> str:
    """Builds the topic mastery table (no HTML comments)."""
    icons = {
        "Linked Lists": "🔗",
        "Trees": "🌲",
        "Graphs": "🕸",
        "Binary Search": "🔍",
        "Dynamic Programming": "🧮",
    }
    color_fn = lambda p: "e8f55a" if p >= 80 else ("5af5c8" if p >= 60 else "f5a623")
    lines = [
        "| Topic | % | Mastery |",
        "|:---|:---:|:---:|",
    ]
    for name, pct in tuf["topics"].items():
        icon  = icons.get(name, "📌")
        label = name.replace(" ", "_")
        badge = _badge(label, f"{pct}%25", color_fn(pct)).replace("%2525", "%25")
        lines.append(f"| {icon} {name} | {pct}% | {badge} |")
    return "\n".join(lines)


# ── README patcher ────────────────────────────────────────────────────────────

def replace_section(content: str, start_marker: str, end_marker: str, new_body: str) -> str:
    """Replaces everything between start_marker and end_marker (exclusive) with new_body."""
    pattern = re.compile(
        rf"({re.escape(start_marker)}\n)(.*?)(\n{re.escape(end_marker)})",
        re.DOTALL,
    )
    replacement = rf"\g<1>{new_body}\g<3>"
    updated, n = pattern.subn(replacement, content)
    if n == 0:
        log.warning(f"Section marker not found: {start_marker}")
    return updated


def replace_total_line(content: str, total: int) -> str:
    """Replaces the whoami line containing ← TOTAL_SOLVED_LINE sentinel."""
    pattern = re.compile(r"^(→ )(\d+\+?)(.*← TOTAL_SOLVED_LINE.*)$", re.MULTILINE)
    updated, n = pattern.subn(rf"\g<1>{total}\g<3>", content)
    if n == 0:
        log.warning("TOTAL_SOLVED_LINE sentinel not found in README")
    return updated


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> bool:
    log.info("Fetching stats...")
    lc  = fetch_leetcode()
    tuf = fetch_tuf()
    gfg = fetch_gfg()

    combined = lc["total"] + tuf["total"] + gfg["total"]
    log.info(f"LC={lc['total']}  TUF={tuf['total']}  GFG={gfg['total']}  Combined={combined}")

    original = README.read_text(encoding="utf-8")
    content  = original

    # 1. Whoami total line
    content = replace_total_line(content, combined)

    # 2. DSA table
    content = replace_section(
        content,
        "<!-- DSA_TABLE_START -->",
        "<!-- DSA_TABLE_END -->",
        build_dsa_table(lc, tuf, gfg),
    )

    # 3. TUF sheets
    content = replace_section(
        content,
        "<!-- TUF_SHEETS_START -->",
        "<!-- TUF_SHEETS_END -->",
        build_tuf_sheets(tuf),
    )

    # 4. TUF topics
    content = replace_section(
        content,
        "<!-- TUF_TOPICS_START -->",
        "<!-- TUF_TOPICS_END -->",
        build_tuf_topics(tuf),
    )

    if content == original:
        log.info("No changes — README already up to date.")
        print("changed=false")
        return False

    README.write_text(content, encoding="utf-8")
    log.info(f"README updated → {README}")
    print("changed=true")
    return True


if __name__ == "__main__":
    sys.exit(0 if main() else 0)
