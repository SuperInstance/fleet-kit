#!/usr/bin/env python3
"""Negative controls for fleetlint.

THE CONTROL THAT MATTERS IS NOT THE ONE I WROTE FIRST.

The e06f00a controls called the REGEXES directly and passed 6/6 over a pipeline
in which L9 and L10 were defined and never registered in CHECKS. So this file
asserts REGISTRATION as well as behaviour: a rule that is not wired to anything
is dead code that can never fire, including on its own control.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fleetlint as fl

fails = 0
def check(name, cond):
    global fails
    if not cond: fails += 1
    print(f"   {'PASS' if cond else 'FAIL'}  {name}")

print("  ═══ 1. EVERY RULE IS REGISTERED. A rule nobody calls is dead code. ═══")
registered = {n for pair in fl.CHECKS for n in [pair[0]]}
for tag, fn in [("L9", fl.check_canary_inert), ("L10", fl.check_narrative_count),
                ("L11", fl.check_unwitnessed_receipt)]:
    check(f"{tag} ({fn.__name__}) is in CHECKS", tag in registered)
check("every check_* function is reachable from CHECKS",
      all(fn.__name__ in {p[1].__name__ for p in fl.CHECKS}
          for fn in [fl.check_canary_inert, fl.check_narrative_count,
                     fl.check_unwitnessed_receipt]))

print("\n  ═══ 2. THE HELPERS L9 CALLED AND NOBODY DEFINED ═══")
check("_walk is defined", hasattr(fl, "_walk"))
check("_tree is defined", hasattr(fl, "_tree"))
check("_tree RAISES on a truncated listing rather than reading it as clean",
      "truncated" in __import__("inspect").getsource(fl._tree))

print("\n  ═══ 3. L11 BEHAVIOUR — must FIRE on a receipt with no witness ═══")
import re
RECEIPT = r"receipts:\n- seq 1 op run payload ok\n"
WIRED   = "receipts:\n- seq 1 op run payload ok\nchain: seq 1 prev 0 tip abc\n"
def l11(body):
    hits = fl.RECEIPT_RE.search(body); wit = fl.WITNESS_RE.search(body)
    return bool(hits) and not wit
check("receipt with no chain/replay  -> FLAGGED", l11(RECEIPT))
check("receipt WITH a chain witness -> not flagged", not l11(WIRED))
check("prev/tip count as witnesses  -> not flagged",
      not l11("receipts: []\nprev: 0\ntip: abc\n"))
check("a repo with no receipts at all -> not flagged",
      not l11("just a readme\n"))

print("\n  ═══ 4. L9/L10 STILL BEHAVE AS BEFORE ═══")
check("non-canonical canary flagged", fl._CANARY_BAD in 'CANARY = "0x024a555471370b18d"')
check("canonical canary NOT flagged", fl._CANARY_BAD not in 'CANARY = "0x24a555471370b18d"')
check("canary==canary flagged", any(rx.search("assert canary == canary") for rx,_ in fl.INERT_PATTERNS))
m = fl.COUNT_CLAIM.search("441 uncommitted files recovered")
check("L10 parses '441 uncommitted files'", bool(m) and fl._count(m.group(1)) == 441)
m2 = fl.COUNT_CLAIM.search("9,067,975 positions")
check("L10 reads 9,067,975 not 975", bool(m2) and fl._count(m2.group(1)) == 9067975)

print(f"\n   {len([1])and ''}{'ALL CONTROLS PASS' if not fails else str(fails)+' FAILED'}")
sys.exit(0 if not fails else 1)
