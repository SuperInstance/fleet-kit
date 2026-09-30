# PKG — docs site

A documentation site is still a program. The four things that break:

| failure | symptom | the fix |
|---|---|---|
| a link to a page that does not exist | 404 in prod, fine locally | check every internal link in CI |
| a generated surface that is hand-edited | drift, silent | generate, never hand-edit |
| a canary in the prose only | the words are pinned, the bytes are not | one canary, asserted |
| the build passes on a stale cache | green CI, broken page | build from a clean clone |

CI must validate links and generated surfaces BEFORE merge. A preview build that
publishes only after the link check passes is the cheapest correctness net there is.
