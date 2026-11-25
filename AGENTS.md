# Instructions for a GPT or coding agent

Read `GIL_PROSE_RULES.md` first. Write following those rules.

Then run:

```bash
python check_gates.py --strict <file>
```

The checker uses the Python standard library only. No extra packages are required.

Fix every hit before you return the text.

If you cannot run code, apply the rules in `GIL_PROSE_RULES.md` and `REVISION_GATES.md` by hand.
