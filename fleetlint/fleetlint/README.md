# fleetlint — the checks that caught tonight's defects, as reusable tooling

> **This directory is additive.** It does not touch the `fleet_kit` package, the
> `examples/`, or the existing test suite. It is a verifier and a set of repo templates
> that live alongside them because they solve a different problem: not "call the fleet",
> but "check the fleet". See the note at the bottom about a README this clobbered on its
> way in.

Three things, deliberately separate:

| | what it is | when you use it |
|---|---|---|
| `fleetlint.py` | a checker for 8 defect classes, each of which caught something real | in CI, as a gate |
| `templates/` | minimal correct starting points for 4 repo shapes | when starting a repo |
| `templates/_shared/negative_control.md` | the rule that a check must be seen to fail | before you merge any check |

## The defects, and what each one cost

| rule | what it catches | where it had already bitten |
|---|---|---|
| **L1** dead-export | a re-exported name the source module does not export, so it is `undefined` at runtime | 11 opcodes in `substrate-foundation`, inherited by every `substrate-*` repo |
| **L2** canary-missing | a polyformal repo with no canary | ~20 repos carry one; the rest are silent |
| **L3** licence-missing | a declared licence with no licence text | a claim, not a grant |
| **L4** repo-url-wrong | no `repository` field | `quilt-attention` |
| **L5** auto-publish | a publish workflow that can fire before tests are green | auto-publish removed from 126 crates |
| **L6** digest-preimage | hex bytes turned into a latin1 string and then hashed as UTF-8 | `quilt-nn`, `quilt-attention`, `quilt-ml-recipes` |
| **L7** fixture-trap | an unaccented canary fixture beside the accented one | `0xfee9cf40962b966` ≠ `0x024a555471370b18d`, seen 3 times |
| **L8** load-is-not-ok | a test suite that only asserts the module loads | every one of these defects passed "it loads" |

## Use

```bash
python3 fleetlint.py SuperInstance/quilt-nn SuperInstance/cellgraph
python3 fleetlint.py SuperInstance/your-repo --json     # machine-readable
```

**A broken check aborts the run.** If a check cannot execute, fleetlint raises and prints
`INSTRUMENT BROKEN, NOT CLEAN` rather than returning a short list. It will not launder a
transport failure into a passing result — see below, that was the third bug in this file.

## The alphabet canary — the one that was missing

The byte canary hashes a **fixture string**. It has never once been applied to the
**opcode names**. That is how `MERGER` survived in the package that defines the canon.

```
0xe5c271ee5c13e9c7   FNV-1a 64 over the sorted canon opcodes joined by '|'
```

One line, pinned in CI, and a rename fails the same day. `templates/` ship it for
Python, Node, and Rust, each with a test that renames `MERGE` to `MERGER` and asserts the
pin moves.

## Three things this file got wrong, and what they cost

Recorded because the failures are the point.

**1. A check that could not read a file reported the file as clean.** `get_text` returned
`None` on any failure and every caller read `None` as "nothing to see here". The cause was
a URL-quoted path that escaped the `/`, so *every nested file* 404'd. L6 sat silent on
`quilt-nn` and `quilt-attention` — the two repos it was written for. Transport failure and
absence are now different types.

**2. A regex that matched nothing.** `[\w.$]+` cannot span the nested parens in
`Buffer.from(f64hex(loss), 'hex')`, so the real code produced **zero** matches while
looking correct. It now has a self-test with its own positive control, and fleetlint
exits non-zero if that self-test fails.

**3. A linter that flagged everything.** The first L1 flagged every
`const { x } = require(...)`, including `node:test`. It now **verifies** by resolving the
package and reading its real export list, and stays quiet when the module cannot be
resolved. A linter that flags valid code gets switched off, and a switched-off linter has
caught nothing.

## The canary is not 16 digits

The fleet writes `0x024a555471370b18d` — **seventeen** hex digits. A `u64` prints sixteen.
The leading zero is insignificant to the value, which is exactly why it went unnoticed, but
it means a padded form and the fleet's own literal are different *strings* for the same
number, and Python `hex()`, Rust `{:X}` and JS `toString(16)` all strip it while every
hand-written copy keeps it.

**Compare the integer. Never compare the canary as text.** Same species as the digest
preimage: the number is fine, the serialisation is the trap.
