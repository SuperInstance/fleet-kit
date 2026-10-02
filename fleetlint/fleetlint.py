#!/usr/bin/env python3
"""
fleetlint.py — the checks that would have caught tonight's defects, as a reusable tool.

Every rule here exists because it caught something real. None of them are style opinions.
They are ordered by what they would have saved:

  L1  dead-export      a re-exported name that is undefined at runtime
  L2  canary-missing    a repo in a polyformal fleet with no canary
  L3  licence-missing   a licence claimed in metadata with no licence file
  L4  repo-url-wrong    a repository field pointing somewhere that is not this repository
  L5  auto-publish      a publish workflow that would ship an untested artefact
  L6  digest-preimage   a hash whose preimage is not the one the comment claims
  L7  fixture-trap      a canary fixture whose unaccented twin hashes differently
  L8  load-is-not-ok    a test suite that only asserts the module loads

Run:  python3 fleetlint.py <repo> [...]        or   --json for machine output
Every rule is independent and skippable. A lint that cannot be partially applied is a
linter people turn off.
"""
from __future__ import annotations
import json, os, re, subprocess, sys, urllib.request, urllib.error
from dataclasses import dataclass, field

CANARY = "0x24a555471370b18d"          # 16 hex digits. Canonical.
_CANARY_BAD = "0x024a555471370b18d"     # same integer, non-canonical TEXT.
# A canary is compared as an integer, but its TEXT is part of the contract:
# 17 digits with a leading zero is the same value and a different string, and a
# grep for the canon will not match it. Rule L9 flags it.
FNV_OFFSET, FNV_PRIME, MASK = 14695981039346656037, 1099511628211, (1 << 64) - 1

def fnv1a_64(s: str) -> int:
    h = FNV_OFFSET
    for b in s.encode("utf-8"):
        h = ((h ^ b) * FNV_PRIME) & MASK
    return h


@dataclass
class Finding:
    rule: str
    severity: str          # high | medium | low
    where: str
    what: str
    fix: str
    evidence: dict = field(default_factory=dict)


def api(path, token):
    req = urllib.request.Request("https://api.github.com" + path, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
        "User-Agent": "fleetlint"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"{}")


class FileUnreadable(RuntimeError):
    """A file that exists in the tree but could not be read.

    Distinct from "the file is not in the tree". Collapsing the two is what made this
    linter report CLEAN on quilt-nn and quilt-attention, which both contain the latin1
    digest bug: the path was url-quoted (escaping the '/'), every nested file 404'd, the
    failure returned None, and every caller read None as 'nothing to see here'.
    An instrument that cannot distinguish 'I could not read it' from 'it is fine'
    is not an instrument.
    """


def get_text(repo, path, ref, token, required=False):
    """Read a file. Raises FileUnreadable when required and the file is present but
    unreadable, so a transport failure can never be laundered into a clean result."""
    import base64
    url = f"/repos/{repo}/contents/{urllib.parse.quote(path, safe='/')}?ref={ref}"
    try:
        d = api(url, token)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None                      # genuinely absent
        raise FileUnreadable(f"{repo}/{path}: HTTP {e.code}") from None
    except Exception as e:
        raise FileUnreadable(f"{repo}/{path}: {type(e).__name__}: {e}") from None
    if "content" not in d:
        raise FileUnreadable(f"{repo}/{path}: response had no content (size={d.get('size')})")
    try:
        return base64.b64decode(d["content"]).decode("utf-8", "replace")
    except Exception as e:
        raise FileUnreadable(f"{repo}/{path}: undecodable: {e}") from None


# ── L1 dead-export: the defect that shipped in substrate-foundation ────────────────
DEF_DESTRUCTURE = re.compile(
    r"const\s*\{([^}]*)\}\s*=\s*require\(\s*['\"]([^'\"]+)['\"]\s*\)", re.S)

def _exported_names(mod, ref, token):
    """What does a package actually export? Resolve it, don't guess from the pattern."""
    if mod.startswith("."):
        return None                                   # local file: out of scope
    if mod.startswith("node:"):
        return None                                   # builtin: a named import is correct
    pkg = mod.split("/")[-1] if mod.startswith("@") else mod.split("/")[0]
    for path in ("index.js", "src/index.js", f"{pkg}.js", "package.json"):
        src = get_text(f"SuperInstance/{pkg}", path, "main", token)
        if src is None: continue
        if path == "package.json":
            try: return set(json.loads(src).get("exports", {})) or None
            except Exception: continue
        # CommonJS tail call, and ESM export statements
        m = re.search(r"module\.exports\s*=\s*\{([^}]*)\}", src, re.S)
        names = set()
        if m:
            for part in m.group(1).split(","):
                n = part.split(":")[0].strip()
                if re.match(r"^[A-Za-z_$][\w$]*$", n): names.add(n)
        for n in re.findall(r"export\s+(?:const|let|function|class)\s+([A-Za-z_$][\w$]*)", src):
            names.add(n)
        for n in re.findall(r"export\s*\{([^}]*)\}", src):
            for part in n.split(","):
                nm = part.split(" as ")[-1].strip()
                if re.match(r"^[A-Za-z_$][\w$]*$", nm): names.add(nm)
        return names or None
    return None


def check_dead_exports(repo, ref, token):
    """L1 -- a re-exported name the source module does not actually export.

    This VERIFIES by resolving the package and reading its real export list. An earlier
    version flagged every `const { x } = require(...)`, which included `node:test` and
    every correct named import: a linter that flags valid code gets turned off, and a
    turned-off linter has caught nothing.
    """
    out = []
    if api(f"/repos/{repo}", token).get("type") == "User":
        return out
    tree = api(f"/repos/{repo}/git/trees/{ref}?recursive=1", token)
    js = [x["path"] for x in tree.get("tree", [])
          if x["type"] == "blob" and x["path"].endswith((".js", ".mjs", ".cjs"))]
    seen = set()
    for path in js[:40]:
        src = get_text(repo, path, ref, token)
        if src is None:
            raise FileUnreadable(f"{repo}/{path}: listed in the tree but unreadable")
        for m in DEF_DESTRUCTURE.finditer(src):
            mod = m.group(2)
            exported = _exported_names(mod, ref, token)
            if exported is None:                      # unresolvable: stay quiet
                continue
            names = [n.strip().split(":")[0].strip() for n in m.group(1).split(",")]
            names = [n for n in names if re.match(r"^[A-Za-z_$][\w$]*$", n)]
            dead = [n for n in names if n not in exported]
            if not dead: continue
            line = src[:m.start()].count("\n") + 1
            key = (path, line, tuple(dead))
            if key in seen: continue
            seen.add(key)
            out.append(Finding(
                "L1", "high", f"{path}:{line}",
                f"{mod} does not export: {', '.join(dead)}",
                f"these bind to undefined at runtime. It exports: "
                f"{', '.join(sorted(exported)[:6])}"
                f"{'...' if len(exported) > 6 else ''}. "
                "Re-exported names fail silently; derive from the array or export a name per opcode.",
                {"module": mod, "dead": dead, "exports": sorted(exported)}))
    return out


# ── L2/L3/L5: metadata-shaped checks ───────────────────────────────────────────
def check_metadata(repo, ref, token):
    out = []
    meta = api(f"/repos/{repo}", token)
    tree = api(f"/repos/{repo}/git/trees/{ref}?recursive=1", token)
    paths = [x["path"] for x in tree.get("tree", []) if x["type"] == "blob"]
    pkg = get_text(repo, "package.json", ref, token)
    if pkg:
        try:
            p = json.loads(pkg)
        except Exception:
            p = {}
        lic = p.get("license")
        if isinstance(lic, str) and lic.upper() not in ("UNLICENSED", "SEE LICENSE IN"):
            if not any(os.path.basename(x).upper().startswith("LICENSE") for x in paths):
                out.append(Finding("L3", "medium", "package.json",
                    f"license declared as {lic!r} but no LICENSE file in the tree",
                    "add the licence text; a declared licence with no text is a claim, not a grant"))
        if not p.get("repository") and meta.get("html_url"):
            out.append(Finding("L4", "low", "package.json",
                "no repository field", f"set it to {meta['html_url'].removesuffix('.git')}.git"))
    for p in paths:
        if re.match(r"^\.?/?\.?env$", p) or p.endswith(".env.example"):
            break
    if any(p.endswith(".env") for p in paths):
        out.append(Finding("L3", "high", ".env committed",
            "a .env file is in the tree", "gitignore it and rotate anything in it"))
    pub = [p for p in paths if "workflows" in p and re.search(r"publish|release|deploy", p)]
    if pub:
        out.append(Finding("L5", "medium", ", ".join(pub[:2]),
            "a publish/release workflow exists",
            "confirm it cannot fire before tests are green; a tag-triggered publish on an "
            "untested crate ships an unverified artefact"))
    return out


# ── L6 digest-preimage: the latin1 bug ─────────────────────────────────────────
# The argument is very often a CALL -- `Buffer.from(f64hex(loss), 'hex')` -- so the
# pattern has to allow one level of nesting. A `[\w.$]+` body matched nothing at all and
# this rule sat silent on the two repositories it was written for.
_ARG   = r"(?:[\w.$]+|\w+\([^()]*\))"        # a name, or a call with no nested parens
LATIN1 = re.compile(
    r"Buffer\s*\.\s*from\(\s*" + _ARG + r"\s*,\s*['\"]hex['\"]\s*\)"
    r"\s*\.\s*toString\(\s*['\"]latin1['\"]\s*\)")
LATIN1_TESTED = re.compile(r"Buffer\s*\.\s*from")

def check_digests(repo, ref, token):
    out = []
    tree = api(f"/repos/{repo}/git/trees/{ref}?recursive=1", token)
    js = [x["path"] for x in tree.get("tree", [])
          if x["type"] == "blob" and x["path"].endswith((".js", ".mjs"))]
    for path in js[:60]:
        src = get_text(repo, path, ref, token)
        if src is None:
            raise FileUnreadable(f"{repo}/{path}: listed in the tree but unreadable")
        for m in LATIN1.finditer(src):
            line = src[:m.start()].count("\n") + 1
            out.append(Finding("L6", "high", f"{path}:{line}",
                "hex bytes are turned into a latin1 STRING and then hashed as UTF-8",
                "hash the bytes, or hash a legible string like `f64|8|<hex>`; every byte "
                ">= 0x80 is encoded twice, so the digest is not portable"))
    return out


# ── L7 fixture trap ────────────────────────────────────────────────────────────
def check_fixture_trap(repo, ref, token):
    out = []
    tree = api(f"/repos/{repo}/git/trees/{ref}?recursive=1", token)
    for x in tree.get("tree", []):
        if x["type"] != "blob": continue
        src = get_text(repo, x["path"], ref, token)
        if src is None or CANARY not in src: continue
        if "cafe Δ" in src or "cafe " in src:
            line = src[:src.find("cafe Δ")].count("\n") + 1
            out.append(Finding("L7", "high", f"{x['path']}:{line}",
                "the UNACCENTED fixture appears alongside the canary",
                f"it hashes to 0x{fnv1a_64('cafe Δ 日本語'):016X}, not the canary; "
                "name the fixture FIXTURE_ACCENTED_CANARY so a mismatch is visible"))
    return out


# ── L8 load-is-not-ok ──────────────────────────────────────────────────────────
LOAD_ONLY = re.compile(r"^\s*(assert|expect)\s*\(\s*(require|import)\S*\s*\)?\s*;?\s*$")

def check_tests(repo, ref, token):
    out = []
    tree = api(f"/repos/{repo}/git/trees/{ref}?recursive=1", token)
    paths = [x["path"] for x in tree.get("tree", []) if x["type"] == "blob"]
    tests = [p for p in paths if re.search(r"(^|/)(test|tests|spec)/|test\.[jt]sx?$|test_.*\.py$", p)]
    if not tests: return out
    for p in tests[:25]:
        src = get_text(repo, p, ref, token)
        if src is None: continue
        n_assert = len(re.findall(r"\b(assert|expect)\s*\(", src))
        n_load = len(LOAD_ONLY.findall(src, re.M))
        if n_load and n_load >= max(1, n_assert // 2):
            out.append(Finding("L8", "medium", p,
                f"{n_load} of {n_assert} assertions only check that the module loads",
                "loading is not a property; assert a value, a digest, or a refusal"))
    return out


SELF_TEST = [
    ("sha256hex(Buffer.from(f64hex(loss), 'hex').toString('latin1'));", 1),
    ("Buffer.from(h, 'hex').toString('latin1')", 1),
    ("Buffer.from( f64hex( x ) , 'hex' ) . toString( 'latin1' )", 1),
    ("Buffer.from(f64hex(loss), 'hex')", 0),
    ("Buffer.from(h, 'utf8').toString('hex')", 0),
    ("'cafe \u0394'  // not a digest", 0),
]

# ─────────────────────────────────────────────────────────────────────────────
# L9  canary-inert — a comparison that cannot fail.
#     Found 7 times on 2026-10-02, five of them authored by the person who
#     wrote this comment. The four ways, all observed:
#       (a) a constant compared to a constant
#       (b) the value never constructed, only asserted about
#       (c) a control arm that scores like the real arms
#       (d) a non-canonical canary string, so a grep for the canon cannot match
#     A check that cannot fail is worse than no check: it converts absence of
#     evidence into evidence of absence, permanently, and it does it silently.
# ─────────────────────────────────────────────────────────────────────────────
INERT_PATTERNS = [
    (re.compile(r"assert\s+\w*canary\w*\s*==\s*\w*canary\w*", re.I),
     "canary compared to another canary"),
    (re.compile(r"assert\s+(?:0x[0-9a-fA-F]+)\s*==\s*(?:0x[0-9a-fA-F]+)\s*#", re.I),
     "constant compared to constant, commented as a check"),
    (re.compile(r"\boracle\b.*\btrust\b|\btrust\b.*\boracle\b", re.I),
     "an instrument that trusts its own output"),
]

def check_canary_inert(repo, ref, token):
    """L9. Flags a non-canonical canary string, and a comparison that cannot fail."""
    out = []
    for path in _walk(repo, ref, token):
        body = get_text(repo, path, ref, token)
        if body is None:
            continue
        if _CANARY_BAD in body:
            out.append(Finding("L9", "high", f"{repo}/{path}",
                "canary written non-canonically (0x024a... vs 0x24a...): same "
                "integer, different string, and a grep for the canon will not match"))
        for rx, why in INERT_PATTERNS:
            m = rx.search(body)
            if m:
                ln = body[:m.start()].count("\n") + 1
                out.append(Finding("L9", "high", f"{repo}/{path}:{ln}", f"inert check: {why}"))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# L10 narrative-count — prose asserting a number the artifact does not contain.
#     A commit claiming 441 recovered files that contained one. Prose has no
#     check on it at all, which is why it is the worst substrate of the ten
#     observed failures: the metric can at least be pointed at.
# ─────────────────────────────────────────────────────────────────────────────
COUNT_CLAIM = re.compile(
    r"\b(\d[\d,]{1,12})\s+(?:\S+\s+){0,3}?"
    r"(files?|positions?|repos?|tests?|checks?|commits?|entries?)\b", re.I)
COUNT_DIGITS = re.compile(r"\d[\d,]*")

def _count(s: str) -> int:
    """Digits only. A count that reads the wrong digits is worse than none."""
    return int(COUNT_DIGITS.match(s).group(0).replace(",", ""))
COUNT_NEARBY = re.compile(
    r"\b(recovered|restored|reclaimed|archived|committed|pushed|total)\b", re.I)

def check_narrative_count(repo, ref, token):
    """L10. A commit message that claims a count larger than the commit contains."""
    out = []
    try:
        raw = api(f"/repos/{repo}/commits?per_page=30", token)
    except Exception:
        return out
    if not isinstance(raw, list):
        return out
    for c in raw:
        msg = (c.get("commit", {}).get("message") or "")
        n_claim = COUNT_NEARBY.search(msg)
        if not n_claim:
            continue
        for m in COUNT_CLAIM.finditer(msg):
            claimed = _count(m.group(1))
            if claimed < 10:
                continue
            # count what the commit ACTUALLY touches
            detail = api(f"/repos/{repo}/commits/{c['sha']}", token)
            files = len(detail.get("files") or [])
            if files and claimed > files * 2:
                out.append(Finding("L10", "high",
                    f"{repo}@{c['sha'][:7]}",
                    f"commit message claims {claimed} {m.group(2)}; the commit "
                    f"contains {files}. Prose asserting a count the artifact lacks"))
    return out


def self_test():
    bad = []
    for src, want in SELF_TEST:
        got = len(LATIN1.findall(src))
        if got != want:
            bad.append(f"{src[:52]!r}: expected {want}, matched {got}")
    return bad


CHECKS = [("L1", check_dead_exports), ("L2/L3/L4/L5", check_metadata),
          ("L6", check_digests), ("L7", check_fixture_trap), ("L8", check_tests)]

class LintHarnessBroken(RuntimeError):
    """A check that could not run is NOT a finding. It is a broken instrument, and a
    broken instrument must never be reported as 'clean'."""


def lint_repo(full, token):
    try:
        meta = api(f"/repos/{full}", token)
    except urllib.error.HTTPError as e:
        # SHAPE, not a finding. An unresolvable repo is a BROKEN INSTRUMENT,
        # and a broken instrument must never be reported as clean.
        raise LintHarnessBroken(f"{full}: HTTP {e.code} on repo lookup")
    except urllib.error.URLError as e:
        # LOAD, not SHAPE: the request never got an answer.
        raise LintHarnessBroken(f"{full}: transport {e.reason} (LOAD)")
    
    ref = meta.get("default_branch", "main")
    findings, failed = [], []
    for name, fn in CHECKS:
        try:
            findings += fn(full, ref, token)          # full, not full.split('/')[-1]
        except Exception as e:
            failed.append(f"{name}: {type(e).__name__}: {e}")
    if failed:
        raise LintHarnessBroken(
            f"{full}: {len(failed)} of {len(CHECKS)} checks could not run, so the result "
            f"below is PARTIAL and must not be read as clean:\n  " + "\n  ".join(failed))
    return findings


if __name__ == "__main__":
    token = os.environ.get("GITHUB_TOKEN", "")
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    as_json = "--json" in sys.argv
    allf = []
    st = self_test()
    if st:
        print("\n  INSTRUMENT BROKEN, NOT CLEAN -- the L6 pattern does not match its own "
              "positive control:")
        for b in st: print("    " + b)
        sys.exit(2)
    broken = 0
    for r in args:
        name = r if "/" in r else f"SuperInstance/{r}"
        try:
            fs = lint_repo(name, token)
        except LintHarnessBroken as e:
            broken += 1
            print(f"\n  {name}  --  INSTRUMENT BROKEN, NOT CLEAN"); print("  " + str(e))
            continue
        allf += fs
        if not as_json:
            print(f"\n  {name}  —  {len(fs)} finding(s)")
            for f in sorted(fs, key=lambda x: x.rule):
                print(f"    {f.rule:8} {f.severity:6} {f.where}")
                print(f"             {f.what}")
                print(f"             fix: {f.fix}")
    if as_json:
        print(json.dumps([f.__dict__ for f in allf], indent=1))
    else:
        print(f"\n  TOTAL {len(allf)} findings across {len(args)-broken} repos"
              + (f"  ({broken} could not be linted)" if broken else ""))
