# prose-gates-public

A small Python checker for prose revision gates. Point it at HTML, Markdown, TeX, text or YAML and it flags hedges, filler openers, pointer subjects, positional framing, promise lines, hype, arrows, semicolons, banned dashes, contrast frames and percent ranges written as "N to M%".

The script uses the Python standard library only. No extra packages are required.

## Use it

Read `GIL_PROSE_RULES.md` first and write to those rules. Then run:

```bash
python check_gates.py --strict path/to/draft.md
```

Fix every hit before you treat the draft as done. If you cannot run code, apply the rules in `GIL_PROSE_RULES.md` and `REVISION_GATES.md` by hand.

`AGENTS.md` states the same instructions for a GPT or coding agent.

```bash
python tests/test_gates.py
python check_gates.py --fix path/to/draft.md
```

`--fix` applies the approved serial-comma remedies and rewrites `N to M%` or `N to M percent` as `N–M%`. Review the diff before you keep it.
