# Global prose rules

Automated means a checker fails it. Manual means the reviewer must check by hand on every review.

1. Never open a sentence with a vague noun that points back at earlier content, such as "The findings led me" or "After that". Rewrite from scratch. (Manual. check_gates OPENER catches sentence-initial Each, This, Here, These, Those, Also, Overall, Additionally and Moreover.)
2. Never fix a banned construction by deleting it or swapping in a near-synonym, such as "instead of" to "without". Restructure the sentence. (Manual.)
3. Never use "plus" as a conjunction. Use "and". (Manual.)
4. Never put a comma right before "and" or "or", in any context. (Automated: check_gates OXFORD.)
5. When a writer corrects a word or phrase, use those exact words. (Manual.)
6. Run all text through `python check_gates.py --strict <file>` before returning it. If you cannot run code, apply the rules by hand. (Process.)
7. Never hedge with might, possibly, likely, probably, seem, seems, appears to, tends to, arguably or somewhat. (Automated: check_gates HEDGE. "perhaps" and "might result in" already fail G3.)
8. Never use this, that, it, these or those as the subject of is, was, are, does, means, shows, makes, keeps, lets or has. Name the real subject. (Automated: check_gates POINTER.)
9. Never frame a claim as "the team holds", "we believe", "the project argues" or "the authors hold". State the claim. (Automated: check_gates FRAME.)
10. Never promise in the line with "I will", "we will", "would again" or "next time we would". (Automated: check_gates PROMISE.)
11. Never use hype or vague praise such as robust, seamless, leverage, landscape, great or impressive. The full list lives in check_gates.py. Bibliography and References sections are skipped so a cited title can contain a word such as landscape. (Automated: check_gates HYPE.)
12. Never use an arrow or a semicolon in prose. (Automated: check_gates ARROW and SEMICOLON.)
13. Write a percent range as 60–70%, not "60 to 70%" or "60 to 70 percent". An en dash is allowed only between two digits. Other en dashes and every em dash still fail G2. (Automated: check_gates RANGE and G2.)
14. Never use "rather than" or "instead of". (Automated: check_gates G1.)
15. Never use an em dash or a spaced double-hyphen. (Automated: check_gates G2.)
16. Never use filler or smug devices such as actually, perhaps, could lead to, what if I told you, what emerges, let's see what happens or it's not just. (Automated: check_gates G3.)
17. Never use a colon as a prose connector or in a title. A colon is allowed only in a time or ratio (digit:digit) and in a URL scheme. YAML files are exempt. (Automated: check_gates COLON.)
18. Keep narrative sentences on HTML and Markdown at 12 words or more unless an exception is listed in SHORT_SENTENCE_EXCEPTIONS.md with prior permission. (Automated: check_gates G5.)
