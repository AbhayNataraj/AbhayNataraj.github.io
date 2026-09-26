"""Builds the portfolio site into _site/.

Projects come from two places:
  - GitHub: every public, non-fork repo of yours that has the topic "portfolio"
  - content/projects.yml: hand-written cards (these always show unless hidden: true)

Run locally:  python build/build.py            (needs internet)
Offline test: python build/build.py --fixture build/fixture.json
"""

import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
import urllib.request
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"
TOPIC = "portfolio"


# ---------- GitHub ----------

def gh_get(url, raw=False):
    headers = {"User-Agent": "portfolio-build", "Accept": "application/vnd.github+json"}
    if raw:
        headers["Accept"] = "application/vnd.github.raw"
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        body = r.read().decode("utf-8", errors="replace")
    return body if raw else json.loads(body)


def fetch_repos(user):
    repos = gh_get(f"https://api.github.com/users/{user}/repos?per_page=100&type=owner&sort=pushed")
    for repo in repos:
        repo["readme"] = None
    return repos


def fetch_readme(repo):
    try:
        return gh_get(f"https://api.github.com/repos/{repo['full_name']}/readme", raw=True)
    except Exception:
        return ""


# ---------- README helpers (for auto-added projects) ----------

BADGE_HINTS = ("shields.io", "badge.svg", "/badge", "badgen.net", "actions/workflows")


def first_readme_image(readme, repo):
    if not readme:
        return None
    candidates = re.findall(r"!\[[^\]]*\]\(([^)\s]+)", readme) + re.findall(r'<img[^>]+src="([^"]+)"', readme)
    for src in candidates:
        if any(h in src for h in BADGE_HINTS):
            continue
        if src.startswith("http"):
            return src
        path = src.lstrip("./")
        return f"https://raw.githubusercontent.com/{repo['full_name']}/{repo['default_branch']}/{path}"
    return None


def first_readme_paragraph(readme):
    if not readme:
        return ""
    readme = re.sub(r"```.*?```", "", readme, flags=re.S)
    for block in re.split(r"\n\s*\n", readme):
        text = block.strip()
        if not text or text.startswith(("#", "!", "[!", "<", "|", "-", "*", ">", "`", "---")):
            continue
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)   # links -> text
        text = re.sub(r"[*_`]", "", text)
        text = " ".join(text.split())
        if len(text) > 40:
            return text if len(text) <= 260 else text[:257].rsplit(" ", 1)[0] + "…"
    return ""


def pretty_name(name):
    words = re.split(r"[-_]+", name)
    return " ".join(w if any(c.isupper() for c in w) else w.capitalize() for w in words)


# ---------- merge ----------

def build_projects(curated, repos, get_readme):
    by_name = {r["name"].lower(): r for r in repos}
    projects, seen = [], set()

    for entry in curated:
        entry = dict(entry)
        repo = by_name.get(str(entry.get("repo", "")).lower())
        if entry.get("repo"):
            seen.add(entry["repo"].lower())
        if entry.get("hidden"):
            continue
        if repo:
            entry.setdefault("title", pretty_name(repo["name"]))
            entry.setdefault("summary", repo.get("description") or "")
            entry["code_url"] = repo["html_url"]
            entry["updated"] = repo.get("pushed_at")
        elif entry.get("repo"):
            entry["code_url"] = f"https://github.com/{PROFILE['github_user']}/{entry['repo']}"
        entry["links"] = [l for l in entry.get("links", []) if l.get("url")]
        projects.append(entry)

    for repo in repos:
        name = repo["name"].lower()
        if name in seen or repo.get("fork") or repo.get("archived") or repo.get("private"):
            continue
        if TOPIC not in (repo.get("topics") or []):
            continue
        readme = get_readme(repo)
        links = []
        if repo.get("homepage"):
            links.append({"label": "Live demo", "url": repo["homepage"]})
        tags = [t.replace("-", " ") for t in repo.get("topics", []) if t != TOPIC]
        if repo.get("language") and repo["language"].lower() not in [t.lower() for t in tags]:
            tags.insert(0, repo["language"])
        projects.append({
            "repo": repo["name"],
            "title": pretty_name(repo["name"]),
            "summary": repo.get("description") or first_readme_paragraph(readme),
            "image": first_readme_image(readme, repo),
            "tags": tags[:6],
            "links": links,
            "code_url": repo["html_url"],
            "updated": repo.get("pushed_at"),
            "featured": False,
            "auto": True,
        })

    featured = [p for p in projects if p.get("featured")]
    more = sorted((p for p in projects if not p.get("featured")),
                  key=lambda p: p.get("updated") or "", reverse=True)
    return featured, more


# ---------- render ----------

def fmt_month(iso):
    if not iso:
        return ""
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%b %Y")


def main():
    global PROFILE
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", help="JSON file of repos to use instead of calling GitHub")
    args = ap.parse_args()

    PROFILE = yaml.safe_load((ROOT / "content/profile.yml").read_text(encoding="utf-8"))
    curated = yaml.safe_load((ROOT / "content/projects.yml").read_text(encoding="utf-8")) or []

    if args.fixture:
        repos = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
        get_readme = lambda r: r.get("readme") or ""
    else:
        try:
            repos = fetch_repos(PROFILE["github_user"])
        except Exception as e:  # don't publish a half-empty site if GitHub is down
            sys.exit(f"Could not reach GitHub: {e}")
        get_readme = fetch_readme

    featured, more = build_projects(curated, repos, get_readme)

    env = Environment(loader=FileSystemLoader(ROOT / "build"), autoescape=select_autoescape(["html"]))
    env.filters["month"] = fmt_month
    html = env.get_template("template.html").render(
        p=PROFILE, featured=featured, more=more,
        has_resume=bool(PROFILE.get("resume")) and (ROOT / PROFILE["resume"]).exists(),
        built=dt.datetime.now(dt.timezone.utc).strftime("%d %b %Y"),
        year=dt.date.today().year,
    )

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "assets", OUT / "assets")
    (OUT / "index.html").write_text(html, encoding="utf-8")
    (OUT / "projects.json").write_text(json.dumps(featured + more, indent=2, default=str), encoding="utf-8")
    print(f"Built {len(featured)} featured + {len(more)} more projects -> {OUT}")


if __name__ == "__main__":
    main()
