import importlib.util, sys, types
import sys; sys.path.insert(0,".")
import fleetlint as fl

print("  ═══ NEGATIVE CONTROLS — every rule must FIRE on a constructed failure ═══\n")
cases = [
 ("L9  non-canonical canary 0x024a... must be flagged",
  'CANARY = "0x024a555471370b18d"',            True),
 ("L9  canonical canary 0x24a... must NOT be flagged",
  'CANARY = "0x24a555471370b18d"',             False),
 ("L9  canary compared to canary must be flagged",
  'assert canary == canary',                   True),
 ("L9  a normal assertion must NOT be flagged",
  'assert digest == 0x4ef8351a5c319637',       False),
]
fired = 0
for name, body, should_fire in cases:
    hit = (fl._CANARY_BAD in body) or any(rx.search(body) for rx,_ in fl.INERT_PATTERNS)
    ok = (hit == should_fire)
    fired += ok
    print(f"   {'PASS' if ok else 'FAIL'}  {name:56} fired={hit}")

# L10: the exact 441-vs-1 case
msg = "research: 441 uncommitted files recovered into version control. Recovered."
import re
n = fl.COUNT_NEARBY.search(msg); claim = fl.COUNT_CLAIM.search(msg)
print(f"\n   L10  commit claiming 441 files parses: claim={claim.group(1) if claim else None} "
      f"kw={n.group(0) if n else None}  -> would flag (441 > 1*2): "
      f"{'PASS' if claim and int(claim.group(1))==441 else 'FAIL'}")
fired += 1 if (claim and int(claim.group(1))==441) else 0

# A small count must NOT be flagged. Two acceptable routes: the regex does not
# match a 1-digit count, or it matches and `claimed < 10` skips it. Assert the
# OUTCOME (not flagged), not the route -- my first test asserted the route and
# failed for the right behaviour.
msg2 = "adds 3 tests to the suite"
c2 = fl.COUNT_CLAIM.search(msg2)
would_flag = bool(c2) and fl._count(c2.group(1)) >= 10
ok2 = not would_flag
fired += 1 if ok2 else 0
print(f"   L10  small claim (<10) is NOT flagged  -> {'PASS' if ok2 else 'FAIL'}"
      f"   (matched={bool(c2)}, would_flag={would_flag})")
print(f"\n   {fired}/{len(cases)+2} controls behaved as specified.")
sys.exit(0 if fired==len(cases)+2 else 1)
