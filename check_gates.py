#!/usr/bin/env python3
"""Prose revision-gate checker.

Reads the gates defined in REVISION_GATES.md and flags violations in written
artifacts. Hard-fail gates verify automatically. Review gates print for a
person to judge. Manual gates stay with the reviewer.

Usage:
  python check_gates.py <file-or-dir> [...]
  python check_gates.py --strict <file-or-dir> [...]
  python check_gates.py --fix path/to/file.md   # apply approved OXFORD and RANGE remedies

Stdlib only. No third-party packages are required.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SUPPORTED = {".html", ".htm", ".md", ".tex", ".txt", ".yaml", ".yml"}

# Optional internal tokens flagged as G6 when the list is non-empty. Empty by default.
INTERNAL_TOKENS: list[str] = []

# Hard-fail patterns.
G1 = re.compile(r"\b(rather than|instead of)\b", re.IGNORECASE)
G3_PATTERNS = [
    re.compile(r"\bactually\b", re.IGNORECASE),
    re.compile(r"\bperhaps\b", re.IGNORECASE),
    re.compile(r"could lead to", re.IGNORECASE),
    re.compile(r"might result in", re.IGNORECASE),
    re.compile(r"what if i told you", re.IGNORECASE),
    re.compile(r"what emerges", re.IGNORECASE),
    re.compile(r"let's see what happens", re.IGNORECASE),
    re.compile(r"it's not just", re.IGNORECASE),
    re.compile(r"not just\b.*[\u2013\u2014-]", re.IGNORECASE),
]
# Review patterns (G4).
G4_PATTERNS = [
    re.compile(r"\bis not\b", re.IGNORECASE),
    re.compile(r"\bdoes not\b", re.IGNORECASE),
    re.compile(r"\bdo not\b", re.IGNORECASE),
    re.compile(r"\bcannot\b", re.IGNORECASE),
    re.compile(r"without claiming", re.IGNORECASE),
    re.compile(r"\bnot only\b", re.IGNORECASE),
    re.compile(r"\bnot every\b", re.IGNORECASE),
    re.compile(r"\bnot a\b", re.IGNORECASE),
]
# Naming gate: project tokens that must stay lowercase in narrative.
# The list is empty by default. Add exact uppercase or mixed-case forms to flag,
# such as "ACME" or "Acme". Uppercase is allowed only inside URLs and paths,
# which the slash lookarounds exclude.
NAMING_TOKENS: list[str] = []


def _naming_pattern(tokens: list[str]) -> re.Pattern[str] | None:
    if not tokens:
        return None
    alt = "|".join(re.escape(t) for t in tokens)
    return re.compile(rf"(?<![/\w])({alt})(?![/\w])")


NAMING = _naming_pattern(NAMING_TOKENS)
# Colon gate: the house style forbids colons in prose and titles. A colon is
# allowed only where syntax strictly requires it: time or ratio (digit:digit),
# and URL schemes (scheme://, mailto:, doi:, tel:). These are blanked before the
# check so a remaining colon is a prose colon. YAML files are exempt entirely,
# since "key: value" is structural there.
COLON_ALLOWED = re.compile(r"[A-Za-z][\w.+-]*://|\b(?:mailto|tel|doi):|\d\s*:\s*\d", re.IGNORECASE)
SEP_LINE = re.compile(r"^[\s|:+\-]+$")
# Prose double-hyphen used as a dash (spaces both sides). This deliberately
# does not match CLI flags like "--check", which are technical content.
ASCII_DASH = re.compile(r"\s--\s")
# En dash is allowed only between two digits (60–70%). Any other en dash fails G2.
# Em dashes still fail everywhere.
EN_DASH_NAKED = re.compile(r"(?<!\d)\u2013|\u2013(?!\d)")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
WORD = re.compile(r"\b[\w']+\b")
LIST_OR_TABLE = re.compile(r"^([-*+]\s|\d+[.)]\s|\|)")
# Public / narrative prose sentences shorter than this hard-fail (G5).
# Exceptions require prior operator permission and an allowlist entry.
MIN_SENTENCE_WORDS = 12
SHORT_SENTENCE_EXCEPTIONS_PATH = Path(__file__).resolve().parent / "SHORT_SENTENCE_EXCEPTIONS.md"
# Oxford / serial comma (OXFORD). Comma before while is allowed; comma before and is not.
OXFORD_LIST = re.compile(r",(\s+[^,]+),\s+(and|or)\s", re.IGNORECASE)
COMMA_AND = re.compile(r",\s+and\s", re.IGNORECASE)

# Hedges beyond the existing G3 list. "perhaps" and "might result in" stay on G3.
HEDGE = re.compile(
    r"\b(might|possibly|likely|probably|seems?|appears\s+to|tends\s+to|arguably|somewhat)\b",
    re.IGNORECASE,
)
# Sentence-initial filler openers. The capital forms are the ones that start a sentence.
OPENER = re.compile(
    r"(?:^|[.!?]\s+)(Each|This|Here|These|Those|Also|Overall|Additionally|Moreover)\b"
)
# A demonstrative or "it" standing in as the subject of a light verb.
POINTER = re.compile(
    r"(?:^|[.!?]\s+|[,:]\s+|\b(?:and|but|so)\s+)(this|that|it|these|those)\s+"
    r"(is|was|are|does|means|shows|makes|keeps|lets|has)\b",
    re.IGNORECASE,
)
FRAME = re.compile(
    r"\b(the\s+team\s+holds|we\s+believe|the\s+project\s+argues|the\s+authors\s+hold)\b",
    re.IGNORECASE,
)
PROMISE = re.compile(
    r"\b(I\s+will|we\s+will|would\s+again|next\s+time\s+we\s+would)\b",
    re.IGNORECASE,
)
# Hype and vague praise. Bibliography and References sections are skipped.
HYPE = re.compile(
    r"\b(seamless(ly)?|powerful|cutting.edge|robust|leverag\w*|unlock|game.changer|"
    r"simply|just|really|very|incredible|amazing|delve|dive|journey|harness|elevate|"
    r"comprehensive|innovative|state.of.the.art|magic|effortless(ly)?|stunning|"
    r"beautiful|crucial(ly)?|furthermore|pivotal|vital|invaluable|holistic|synerg\w*|"
    r"tapestry|landscape|realm|showcas\w*|underscore\w*|testament|navigat\w*|foster\w*|"
    r"empower\w*|streamline\w*|meticulous\w*|transformative|paramount|key\s+insight|"
    r"great|excellent|impressive|outstanding|remarkable|exceptional|valuable|"
    r"wonderful|successful(ly)?)\b",
    re.IGNORECASE,
)
ARROW = re.compile(r"→|->|=>|⟶|←|⇒")
SEMICOLON = re.compile(r";")
RANGE = re.compile(
    r"\b\d+(?:\.\d+)?\s+to\s+\d+(?:\.\d+)?\s*(?:%|percent\b)",
    re.IGNORECASE,
)
RANGE_FIX = re.compile(
    r"\b(\d+(?:\.\d+)?)\s+to\s+(\d+(?:\.\d+)?)\s*(?:%|percent\b)",
    re.IGNORECASE,
)


def _blank_preserving(text: str, pattern: re.Pattern) -> str:
    """Remove regex matches but keep newline count so line numbers survive."""
    def repl(m: re.Match) -> str:
        return "\n" * m.group(0).count("\n")
    return pattern.sub(repl, text)


HTML_BLOCK = re.compile(r"<(style|script)\b.*?</\1>|<!--.*?-->", re.IGNORECASE | re.DOTALL)
HTML_TAG = re.compile(r"<[^>]*>")
MD_FENCE = re.compile(r"```.*?```", re.DOTALL)
MD_INLINE_CODE = re.compile(r"`[^`]*`")
MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
TEX_COMMENT = re.compile(r"(?<!\\)%.*$")
TEX_CMD = re.compile(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?")
TEX_BEGIN_BIB = re.compile(r"\\begin\{thebibliography\}")
TEX_END_BIB = re.compile(r"\\end\{thebibliography\}")
TEX_BIBITEM = re.compile(r"\\bibitem\b")
# A TeX sectioning command whose title is References or Bibliography.
TEX_SECTION_LEVELS = {
    "chapter": 1,
    "section": 2,
    "subsection": 3,
    "subsubsection": 4,
}
TEX_REF_HEAD = re.compile(
    r"\\(" + "|".join(TEX_SECTION_LEVELS) + r")\*?\{[^}]*\b(References|Bibliography)\b[^}]*\}",
    re.IGNORECASE,
)
TEX_HEADING = re.compile(r"\\(" + "|".join(TEX_SECTION_LEVELS) + r")\*?\{")
MD_REFERENCES_HEAD = re.compile(r"^(#{1,6})\s+References\b", re.IGNORECASE)
MD_HEADING = re.compile(r"^(#{1,6})\s+")

ENTITIES = {"&amp;": "&", "&lt;": "<", "&gt;": ">", "&nbsp;": " ", "&#39;": "'", "&quot;": '"'}


def decode_entities(s: str) -> str:
    for k, v in ENTITIES.items():
        s = s.replace(k, v)
    return s


def visible_lines(path: Path, text: str) -> list[tuple[int, str]]:
    """Return (lineno, visible_text) with line numbers preserved."""
    ext = path.suffix.lower()
    if ext in (".html", ".htm"):
        text = _blank_preserving(text, HTML_BLOCK)
        out = []
        for i, line in enumerate(text.split("\n"), 1):
            out.append((i, decode_entities(HTML_TAG.sub("", line)).strip()))
        return out
    if ext == ".md":
        text = _blank_preserving(text, MD_FENCE)
        out = []
        for i, line in enumerate(text.split("\n"), 1):
            v = MD_INLINE_CODE.sub("", line)
            v = MD_LINK.sub(r"\1", v)
            out.append((i, v.strip()))
        return out
    if ext == ".tex":
        lines = text.split("\n")
        doc_start = 0
        for idx, line in enumerate(lines):
            if "\\begin{document}" in line:
                doc_start = idx
                break
        out = []
        for i, line in enumerate(lines, 1):
            if i - 1 <= doc_start:
                out.append((i, ""))  # blank the preamble so it is not scanned as prose
                continue
            v = TEX_COMMENT.sub("", line)
            v = TEX_CMD.sub("", v)
            v = v.replace("{", "").replace("}", "").replace("\\&", "&").replace("\\$", "$")
            # Drop TeX spacing commands that would otherwise leave a bare semicolon.
            v = v.replace("\\;", " ").replace("\\,", " ").replace("\\:", " ").replace("\\!", " ")
            out.append((i, v.strip()))
        return out
    # yaml, yml, txt and anything else: as-is.
    return [(i, line.strip()) for i, line in enumerate(text.split("\n"), 1)]


def bibliography_lines(path: Path, text: str) -> set[int]:
    """Line numbers in a bibliography or References section.

    HYPE skips these so a cited title can contain a word such as landscape.
    TeX covers \\begin{thebibliography}...\\end{thebibliography}, \\bibitem
    lines, and a chapter/section/subsection titled References or Bibliography
    through the next heading of the same or higher level. Markdown covers a
    References heading through the next heading of the same or higher level.
    """
    skip: set[int] = set()
    ext = path.suffix.lower()
    lines = text.split("\n")
    if ext == ".tex":
        in_bib = False
        bib_level = 0
        for i, line in enumerate(lines, 1):
            ref_head = TEX_REF_HEAD.search(line)
            if ref_head:
                in_bib = True
                bib_level = TEX_SECTION_LEVELS[ref_head.group(1).lower()]
                skip.add(i)
                continue
            if in_bib:
                other = TEX_HEADING.search(line)
                if other and TEX_SECTION_LEVELS[other.group(1).lower()] <= bib_level:
                    in_bib = False
                    # This new heading is not itself a references heading (those
                    # were handled above), so do not skip it.
                else:
                    skip.add(i)
                    continue
            if TEX_BEGIN_BIB.search(line):
                in_bib = True
                bib_level = 0  # consume through \end{thebibliography}
            if in_bib or TEX_BIBITEM.search(line):
                skip.add(i)
            if TEX_END_BIB.search(line):
                skip.add(i)
                in_bib = False
        return skip
    if ext == ".md":
        in_ref = False
        ref_level = 0
        for i, line in enumerate(lines, 1):
            raw = line.strip()
            head = MD_REFERENCES_HEAD.match(raw)
            if head:
                in_ref = True
                ref_level = len(head.group(1))
                skip.add(i)
                continue
            if in_ref:
                other = MD_HEADING.match(raw)
                if other and len(other.group(1)) <= ref_level:
                    in_ref = False
                else:
                    skip.add(i)
        return skip
    return skip


def heading_lines(path: Path, text: str) -> set[int]:
    ext = path.suffix.lower()
    heads = set()
    for i, line in enumerate(text.split("\n"), 1):
        s = line.strip()
        if ext in (".html", ".htm") and re.search(r"<h[1-6]\b", s, re.IGNORECASE):
            heads.add(i)
        elif ext == ".md" and re.match(r"#{1,6}\s", s):
            heads.add(i)
        elif ext == ".tex" and re.search(r"\\section\*?\b", s):
            heads.add(i)
    return heads


def oxford_remedy(snippet: str) -> str:
  if COMMA_AND.search(snippet):
    return "try: replace ', and' with ', while' or split into two sentences"
  if OXFORD_LIST.search(snippet):
    return "try: remove the comma before the final and/or in the list"
  return ""


def range_remedy(snippet: str) -> str:
    m = RANGE_FIX.search(snippet)
    if m:
        return f"try: write {m.group(1)}\u2013{m.group(2)}%"
    return ""


def apply_oxford_fixes(text: str) -> tuple[str, int]:
  """Apply approved OXFORD remedies from REVISION_GATES.md. Returns (text, change_count)."""
  changes = 0
  fixed, n = OXFORD_LIST.subn(r"\1 \2 ", text)
  changes += n
  # Clause join: ", and" -> ", while" (approved remedy; does not match ", while").
  fixed, n = COMMA_AND.subn(", while ", fixed)
  changes += n
  return fixed, changes


def apply_range_fixes(text: str) -> tuple[str, int]:
    """Rewrite 'N to M percent' and 'N to M%' as 'N–M%'."""
    fixed, n = RANGE_FIX.subn(lambda m: f"{m.group(1)}\u2013{m.group(2)}%", text)
    return fixed, n


def check_line_oxford(txt: str) -> bool:
  if COMMA_AND.search(txt):
    return True
  return bool(OXFORD_LIST.search(txt))


def lead_blocks(vlines: list[tuple[int, str]], heads: set[int]) -> list[tuple[int, str]]:
    """Return (lineno, first-sentence) for prose blocks that open a section."""
    blocks = []
    cur, start = [], None
    last_blank_or_head_was_head = False
    saw_head_before_block = False
    for lineno, txt in vlines:
        is_head = lineno in heads
        is_list = bool(txt) and bool(LIST_OR_TABLE.match(txt))
        if not txt or is_head or is_list:
            if cur:
                blocks.append((start, " ".join(cur), saw_head_before_block))
                cur, start = [], None
            if is_head:
                last_blank_or_head_was_head = True
            elif is_list:
                # A list or table that opens a section consumes the lead slot.
                last_blank_or_head_was_head = False
            continue
        if not cur:
            start = lineno
            saw_head_before_block = last_blank_or_head_was_head
            last_blank_or_head_was_head = False
        cur.append(txt)
    if cur:
        blocks.append((start, " ".join(cur), saw_head_before_block))
    leads = []
    for start, body, is_lead in blocks:
        if is_lead:
            first = SENTENCE_SPLIT.split(body)[0]
            leads.append((start, first))
    return leads


def load_short_sentence_exceptions() -> set[str]:
    """Normalized sentences that may be shorter than MIN_SENTENCE_WORDS.

    Operator permission is required before any entry is added. Accept lines that
    are not comments / headers; normalize by collapsing whitespace and lowercasing.
    """
    path = SHORT_SENTENCE_EXCEPTIONS_PATH
    if not path.is_file():
        return set()
    out: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("|"):
            continue
        # Table rows: | sentence | rationale | ...
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if cells and cells[0].lower() not in {"sentence", "---", ""}:
                line = cells[0]
            else:
                continue
        out.add(" ".join(WORD.findall(line.lower())))
    return out


def prose_blocks(vlines: list[tuple[int, str]], heads: set[int]) -> list[tuple[int, str]]:
    """Return (start_lineno, block_text) for contiguous non-heading prose."""
    blocks: list[tuple[int, str]] = []
    cur: list[str] = []
    start: int | None = None
    for lineno, txt in vlines:
        is_head = lineno in heads
        is_list = bool(txt) and bool(LIST_OR_TABLE.match(txt))
        if not txt or is_head or is_list:
            if cur and start is not None:
                blocks.append((start, " ".join(cur)))
                cur, start = [], None
            continue
        if start is None:
            start = lineno
        cur.append(txt)
    if cur and start is not None:
        blocks.append((start, " ".join(cur)))
    return blocks


def short_sentence_findings(
    path: Path,
    vlines: list[tuple[int, str]],
    heads: set[int],
    exceptions: set[str],
) -> list[tuple[str, str, int, str]]:
    """Hard-fail G5 on narrative sentences under MIN_SENTENCE_WORDS."""
    if path.suffix.lower() not in (".html", ".htm", ".md"):
        return []
    findings: list[tuple[str, str, int, str]] = []
    for start, body in prose_blocks(vlines, heads):
        for sent in SENTENCE_SPLIT.split(body):
            s = sent.strip()
            if not s:
                continue
            # Skip fragments with no terminal punctuation (UI crumbs / titles).
            if not re.search(r"[.!?]$", s):
                continue
            words = WORD.findall(s)
            wc = len(words)
            if wc == 0 or wc >= MIN_SENTENCE_WORDS:
                continue
            key = " ".join(w.lower() for w in words)
            if key in exceptions:
                continue
            findings.append(
                (
                    "G5",
                    "fail",
                    start,
                    f"sentence has {wc} words (min {MIN_SENTENCE_WORDS}; needs prior operator exception): {s}",
                )
            )
    return findings


def check_file(path: Path, strict: bool) -> list[tuple[str, str, int, str]]:
    findings = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [("READ", "fail", 0, f"could not read: {exc}")]

    vlines = visible_lines(path, text)
    exceptions = load_short_sentence_exceptions()
    bib = bibliography_lines(path, text)

    for lineno, txt in vlines:
        if not txt:
            continue
        if SEP_LINE.match(txt):
            continue
        if G1.search(txt):
            findings.append(("G1", "fail", lineno, txt))
        if "\u2014" in txt or EN_DASH_NAKED.search(txt) or ASCII_DASH.search(txt):
            findings.append(("G2", "fail", lineno, txt))
        for pat in G3_PATTERNS:
            if pat.search(txt):
                findings.append(("G3", "fail", lineno, txt))
                break
        if NAMING is not None and NAMING.search(txt):
            findings.append(("NAME", "fail", lineno, txt))
        if path.suffix.lower() not in (".yaml", ".yml") and ":" in COLON_ALLOWED.sub(" ", txt):
            findings.append(("COLON", "fail", lineno, txt))
        if check_line_oxford(txt):
            findings.append(("OXFORD", "fail", lineno, txt))
        if HEDGE.search(txt):
            findings.append(("HEDGE", "fail", lineno, txt))
        if OPENER.search(txt):
            findings.append(("OPENER", "fail", lineno, txt))
        if POINTER.search(txt):
            findings.append(("POINTER", "fail", lineno, txt))
        if FRAME.search(txt):
            findings.append(("FRAME", "fail", lineno, txt))
        if PROMISE.search(txt):
            findings.append(("PROMISE", "fail", lineno, txt))
        if lineno not in bib and HYPE.search(txt):
            findings.append(("HYPE", "fail", lineno, txt))
        if ARROW.search(txt):
            findings.append(("ARROW", "fail", lineno, txt))
        if SEMICOLON.search(txt):
            findings.append(("SEMICOLON", "fail", lineno, txt))
        if RANGE.search(txt):
            findings.append(("RANGE", "fail", lineno, txt))
        for pat in G4_PATTERNS:
            if pat.search(txt):
                findings.append(("G4", "warn", lineno, txt))
                break
        for tok in INTERNAL_TOKENS:
            if re.search(r"\b" + re.escape(tok) + r"\b", txt, re.IGNORECASE):
                findings.append(("G6", "warn", lineno, f"[{tok}] {txt}"))
                break

    # G5 short-sentence hard-fail on HTML/MD narrative surfaces.
    if path.suffix.lower() in (".html", ".htm", ".md"):
        heads = heading_lines(path, text)
        findings.extend(short_sentence_findings(path, vlines, heads, exceptions))

    return findings


def gather(paths: list[Path]) -> list[Path]:
    out = []
    for p in paths:
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.suffix.lower() in SUPPORTED:
                    out.append(f)
        elif p.is_file():
            out.append(p)
        else:
            print(f"warning: path not found: {p}", file=sys.stderr)
    return out


def fix_files(paths: list[Path]) -> int:
    total = 0
    for path in paths:
        if not path.is_file() or path.suffix.lower() not in SUPPORTED:
            print(f"skip: {path}", file=sys.stderr)
            continue
        original = path.read_text(encoding="utf-8", errors="replace")
        fixed, n_ox = apply_oxford_fixes(original)
        fixed, n_range = apply_range_fixes(fixed)
        n = n_ox + n_range
        if n:
            path.write_text(fixed, encoding="utf-8")
            bits = []
            if n_ox:
                bits.append(f"{n_ox} OXFORD")
            if n_range:
                bits.append(f"{n_range} RANGE")
            print(f"fixed {path}: {' + '.join(bits)} rewrite(s)")
            total += n
        else:
            print(f"unchanged: {path}")
    return 0 if total else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Prose revision-gate checker.")
    ap.add_argument("paths", nargs="*", help="files or directories to check")
    ap.add_argument("--strict", action="store_true", help="promote warnings to failures")
    ap.add_argument(
        "--fix",
        action="store_true",
        help="apply approved OXFORD and RANGE remedies (list de-serialization, ', and' -> ', while', 'N to M%' -> 'N–M%')",
    )
    args = ap.parse_args()

    if args.fix:
        if not args.paths:
            ap.error("--fix requires explicit file paths")
        fix_files([Path(p) for p in args.paths])
        return 0

    targets: list[Path] = [Path(p) for p in args.paths]
    if not targets:
        ap.error("provide file/dir paths")

    files = gather(targets)
    fails = warns = 0
    for f in files:
        findings = check_file(f, args.strict)
        if not findings:
            continue
        print(f"\n{f}")
        for gate, sev, lineno, snippet in findings:
            tag = "FAIL" if sev == "fail" else "warn"
            print(f"  {tag} {gate} L{lineno}: {snippet[:140]}")
            if gate == "OXFORD":
                hint = oxford_remedy(snippet)
                if hint:
                    print(f"         \u2192 {hint}")
            if gate == "RANGE":
                hint = range_remedy(snippet)
                if hint:
                    print(f"         \u2192 {hint}")
            if sev == "fail":
                fails += 1
            else:
                warns += 1

    print(f"\nChecked {len(files)} file(s): {fails} hard-fail, {warns} review.")
    if fails or (args.strict and warns):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
