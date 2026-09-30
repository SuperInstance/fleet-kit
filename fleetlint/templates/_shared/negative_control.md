## The negative control (required — do not merge without one)

A check that has never been observed to fail has not been shown to work. Before merging,
prove it fires:

```bash
# 1. break the thing on purpose
sed -i "s/'MERGE'/'MERGER'/" src/canary.js
# 2. the test MUST fail
npm test   # expect: FAIL
# 3. restore, and the test MUST pass
git checkout src/canary.js && npm test   # expect: PASS
```

Paste both outputs in the PR. "Tests pass" is not evidence; "tests fail when I break the
thing, and pass when I restore it" is.

## A canary compared as TEXT disagrees between runtimes

The canary is a 64-bit integer. Its *printed* form does not round-trip identically:

| runtime | printed | leading zero? |
|---|---|---|
| Python `hex()` | `0x24a555471370b18d` | stripped |
| Rust `{:X}` | `24A555471370B18D` | stripped |
| JS `.toString(16)` | `24a555471370b18d` | stripped |
| the value everyone writes down | `0x024a555471370b18d` | present |

`0x024a555471370b18d` and `0x24a555471370b18d` are the same integer and different strings.
Three runtimes that all computed the right answer will fail a text comparison against each
other. **Compare the integer, or pad to 16 digits explicitly.** This is the same species of
bug as the digest preimage: the number is fine, the serialisation is the trap.
