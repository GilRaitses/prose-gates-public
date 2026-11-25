# Revision Gates

A revision gate is a pass or fail check that a written artifact must clear before it counts as revised. An artifact reaches the revised state once it clears every hard-fail gate and a reviewer has signed off the manual gates. The checker `check_gates.py` automates the gates that a pattern can verify and lists the rest for human review.

Pass file or directory paths to the checker. The script uses the Python standard library only.

## Gates

### Hard fail (automated)

| Gate | Rule | Why |
|---|---|---|
| G1 | No "rather than" or "instead of" constructions | These frame a point by contrast against what it is not, which weakens the affirmative claim. |
| G2 | No em-dash, no double-hyphen and no en-dash except between digits | The house style writes with periods and commas. An en dash is allowed only between two digits in a number range such as 60–70%. Every em dash and a spaced double-hyphen still fail. |
| G3 | No filler or smug devices | "actually", "perhaps", "could lead to", "might result in", "what if I told you", "what emerges", "let's see what happens", "it's not just", and the "not just ... -" contrast template add tone without information. |
| NAME | Listed project tokens stay lowercase in narrative | The token list is empty by default and is set in `NAMING_TOKENS` inside `check_gates.py`. Uppercase is allowed only inside filenames, URLs and paths. |
| COLON | No colons in prose or titles | The house style does not use the colon as a prose connector or in titles. A colon is allowed only where syntax strictly requires it: a time or ratio (digit:digit) and a URL scheme (scheme://, mailto:, doi:, tel:). YAML files are exempt, since "key: value" is structural. |
| OXFORD | No serial comma and no comma-before-`and` between clauses | No `, X, and Y` list form. No `, and` between independent clauses. A comma before `while` is allowed when the second clause is subordinate. |
| G5 | No narrative sentence under 12 words on HTML/MD | Short crumbs read as fragment marketing. Merge into a full claim. An exception requires prior permission and a row in `SHORT_SENTENCE_EXCEPTIONS.md`. |
| HEDGE | No hedge words beyond the G3 list | "might", "possibly", "likely", "probably", "seem", "seems", "appears to", "tends to", "arguably" and "somewhat" weaken a claim. "perhaps" and "might result in" already fail G3. |
| OPENER | No filler sentence openers | A sentence may not start with Each, This, Here, These, Those, Also, Overall, Additionally or Moreover. |
| POINTER | No demonstrative or "it" as a light-verb subject | "this", "that", "it", "these" or "those" followed by is, was, are, does, means, shows, makes, keeps, lets or has names no real subject. |
| FRAME | No positional framing | "the team holds", "we believe", "the project argues" and "the authors hold" announce a stance instead of stating the claim. |
| PROMISE | No promise lines | "I will", "we will", "would again" and "next time we would" defer work that the sentence should already report. |
| HYPE | No hype or vague praise | Words such as robust, seamless, leverage, landscape, great and impressive add tone without information. The full list is in `check_gates.py`. Bibliography environments, `\bibitem` lines, TeX chapter or section titles named References or Bibliography and markdown `## References` sections are skipped so a cited title is not flagged. |
| ARROW | No arrows in prose | Arrow glyphs and digraphs (→, ->, =>, ⟶, ←, ⇒) are banned in prose. Code fences and TeX commands are stripped first. |
| SEMICOLON | No semicolons in prose | A period or a comma carries the break. |
| RANGE | No "N to M percent" or "N to M%" | Write the range as N–M%. `check_gates.py --fix` applies that rewrite. |

### Serial comma and range remedies (approved)

When OXFORD or RANGE fails, use one of these fixes. Do not swap in a construction that
fails another gate.

| Violation | Approved fix | Example |
|---|---|---|
| Three-item list with serial comma | Drop the comma before the final coordinator | `scope, decisions, and checks` becomes `scope, decisions and checks` |
| Two independent clauses joined with `, and` | Use `, while` when the second clause is subordinate | `scrollback, and every session must` becomes `scrollback, while every session must` |
| Two independent clauses joined with `, and` | Split into two sentences | The first clause ends. The second clause starts. |
| List buildup in a lead | Replace the inventory with one integrative noun | `scope, decisions, checks and paths` becomes `the alignment record` |
| "N to M%" or "N to M percent" | Use an en dash and a percent sign | `60 to 70 percent` becomes `60–70%` |

`check_gates.py --fix` applies the list and `, and` to `, while` rewrites on prose
lines it flags. It also rewrites `N to M%` and `N to M percent` as `N–M%`. Review
the diff before landing.

### Review (automated, warn)

| Gate | Rule | Why |
|---|---|---|
| G4 | Negation framing flagged for review | "is not", "does not", "cannot", "without claiming", "not only", "not every", "not a" often define a thing by what it is not. A reviewer confirms each one earns its place, with extra weight on section leads. |
| G6 | Scope leakage on listed tokens | The token list is empty by default and is set in `INTERNAL_TOKENS` inside `check_gates.py`. |

### Manual (reviewer checklist)

| Gate | Rule | Why |
|---|---|---|
| G7 | Every factual claim traces to a real source | A claim with no source behind it does not ship. |
| G8 | No overclaim, and timelines stay honest | Recent work is labeled recent. A practice that postdates the work it describes says so. |
| G9 | Public-safe | Public surfaces carry no private projects, internal paths or confidential detail. |

## Usage

```bash
# Check specific files
python check_gates.py path/to/file.html path/to/other.md

# Promote warnings to failures
python check_gates.py --strict path/to/file.md

# Apply approved OXFORD and RANGE rewrites
python check_gates.py --fix path/to/file.md

# Run the fixture tests (stdlib unittest, no extra dependencies)
python tests/test_gates.py
```

The checker prints `path:line` with the matched text and the gate id. It exits nonzero when a hard-fail gate triggers, and under `--strict` when any gate triggers. Manual gates G7 to G9 stay with the reviewer, since a pattern cannot confirm them.
