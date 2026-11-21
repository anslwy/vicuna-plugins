#!/usr/bin/env python3
"""Validate index.json (shape) and, unless --offline, each source repo's
vicuna-plugin.json. Mirrors the rules Vicuna applies (src-tauri/src/plugins.rs):
Vicuna drops any entry that fails them, so a bad entry would just vanish."""
import json, re, sys, urllib.request, urllib.error, os

ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
IMG = re.compile(r"^https://(raw\.githubusercontent\.com|github\.com)/[^\s\"'<>\\]+$")
KINDS = {"theme", "panel", "harness"}
# harness rules mirror src-tauri/src/plugin_harness.rs
CMD = re.compile(r"^[A-Za-z0-9_+][A-Za-z0-9._+-]{0,63}$")
BAD_ARG = set("`$;|&<>\"'\\")

def harness_errors(h):
    out = []
    hid = h.get("id") if isinstance(h, dict) else None
    if not isinstance(hid, str) or not re.match(r"^[a-z0-9-]{1,40}$", hid):
        return [f"harness id {hid!r} must be lowercase letters, digits, dashes"]
    lab = h.get("label")
    if not isinstance(lab, str) or not lab.strip() or len(lab) > 40:
        out.append(f"harness {hid}: label must be 1-40 characters")
    acp = h.get("acp") or {}
    cmd = acp.get("command")
    if not isinstance(cmd, str) or not CMD.match(cmd) or ".." in cmd:
        out.append(f"harness {hid}: acp.command must be a bare program name found on PATH (no paths)")
    args = acp.get("args", [])
    if not isinstance(args, list) or len(args) > 32:
        out.append(f"harness {hid}: acp.args must be a list of at most 32 strings")
    else:
        for a in args:
            if not isinstance(a, str) or len(a) > 256 or any(c in BAD_ARG or ord(c) < 32 for c in a):
                out.append(f"harness {hid}: argument {a!r} is not allowed (no shell metacharacters)")
    url = h.get("installUrl")
    if url is not None and not (isinstance(url, str) and url.startswith("https://")):
        out.append(f"harness {hid}: installUrl must be https")
    return out
LIMITS = {"name": 60, "description": 300, "author": 60}
errors = []

def err(msg):
    errors.append(msg)
    print("ERROR:", msg)

def gh(url, accept):
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "vicuna-plugins-ci"})
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise

def manifest_for(source):
    rel = gh(f"https://api.github.com/repos/{source}/releases/latest", "application/vnd.github+json")
    if rel:
        for a in json.loads(rel).get("assets", []):
            if a.get("name") == "vicuna-plugin.json":
                b = gh(a["url"], "application/octet-stream")
                if b:
                    return json.loads(b)
    b = gh(f"https://api.github.com/repos/{source}/contents/vicuna-plugin.json", "application/vnd.github.raw")
    return json.loads(b) if b else None

def main():
    offline = "--offline" in sys.argv
    with open("index.json", encoding="utf-8") as f:
        idx = json.load(f)
    if idx.get("version") != 1 or not isinstance(idx.get("plugins"), list):
        err('index.json must be {"version": 1, "plugins": [...]}')
        return
    seen = set()
    for i, p in enumerate(idx["plugins"]):
        where = f"plugins[{i}] ({p.get('id', '?')})"
        if not isinstance(p, dict):
            err(f"{where}: not an object"); continue
        if not isinstance(p.get("id"), str) or not ID.match(p["id"]):
            err(f"{where}: id must be lowercase letters, digits, dashes")
        elif p["id"] in seen:
            err(f"{where}: duplicate id")
        seen.add(p.get("id"))
        for k, n in LIMITS.items():
            v = p.get(k)
            if not isinstance(v, str) or not v.strip() or len(v) > n:
                err(f"{where}: {k} must be a 1-{n} character string")
        if not isinstance(p.get("source"), str) or not REPO.match(p["source"]):
            err(f"{where}: source must be owner/repo")
        kinds = p.get("kinds")
        if not isinstance(kinds, list) or not kinds or not set(kinds) <= KINDS:
            err(f"{where}: kinds must be a non-empty list of {sorted(KINDS)}")
        for k in ("icon", "screenshot"):
            if k in p and (not isinstance(p[k], str) or not IMG.match(p[k])):
                err(f"{where}: {k} must be an https URL on raw.githubusercontent.com or github.com")
        tags = p.get("tags", [])
        if not isinstance(tags, list) or len(tags) > 8 or not all(isinstance(t, str) and 0 < len(t) <= 24 for t in tags):
            err(f"{where}: tags must be up to 8 strings of 1-24 characters")
        mv = p.get("minVicuna")
        if mv is not None and not (isinstance(mv, str) and re.match(r"^\d+\.\d+\.\d+$", mv)):
            err(f"{where}: minVicuna must look like 0.0.45")
        if offline or not isinstance(p.get("source"), str):
            continue
        m = manifest_for(p["source"])
        if m is None:
            err(f"{where}: no vicuna-plugin.json in {p['source']} (latest release asset or default branch)"); continue
        if m.get("id") != p.get("id"):
            err(f"{where}: manifest id {m.get('id')!r} does not match")
        if not m.get("name") or not m.get("version"):
            err(f"{where}: manifest needs a name and a version")
        has = {"theme"} if m.get("themes") else set()
        if m.get("panels"):
            has.add("panel")
        hs = m.get("harnesses") or []
        if hs:
            has.add("harness")
            if not isinstance(hs, list) or len(hs) > 4:
                err(f"{where}: at most 4 harnesses")
            else:
                ids = [h.get("id") for h in hs if isinstance(h, dict)]
                if len(set(ids)) != len(ids):
                    err(f"{where}: duplicate harness ids")
                for h in hs:
                    for e in harness_errors(h):
                        err(f"{where}: {e}")
        if isinstance(kinds, list) and set(kinds) != has:
            err(f"{where}: kinds {kinds} but the manifest provides {sorted(has)}")
        print(f"ok  {p['id']}: {p['source']} v{m.get('version')}")

main()
sys.exit(1 if errors else 0)
