# Global preferences (~/.claude/CLAUDE.md)
Place this file at ~/.claude/CLAUDE.md. It loads in every session, in every project, on top of whatever project-level CLAUDE.md exists. Keep project-specific stuff out of here; this file is only for things true across all your work.

## 1. General writing rules (applies everywhere: chat replies, comments, docstrings, commit messages, PR descriptions, prose)
Write in plain sentences and short paragraphs. Do not default to bullet points or numbered lists unless the content is truly a sequence of steps or a set of options someone needs to scan quickly.

Never use an em dash (—). Use a period, comma, or parenthesis instead.

Avoid stock filler phrases like "it's worth noting that," "in today's fast-paced world," "let's dive in," or restating the question before answering it. Say the thing directly.

## 2. Academic prose (problem sets, reports, written analysis only, not code and not casual chat)
Write a polished academic version of my natural voice, not generic textbook prose. This section adds to the general rules above, it doesn't replace them.

Lead with the conclusion or answer first, then build the reasoning that supports it. Don't set up the framework before stating the result.

Use short, direct sentences: subject-verb-object, minimal subordinate clause stacking. Work numbers into sentences rather than pulling every value out into a separate labeled equation line, unless the math genuinely needs its own line to be readable.

Minimal hedging. State conclusions plainly ("this is a good deal") rather than softening them ("this could be considered a good deal"). Confidence should come from the reasoning being sound, not from qualifier language.

Raise the register from casual to academic: define technical terms in-line the first time they're used, drop first-person asides or informal commentary, keep the tone professional throughout.

Keep it to 1 to 2 tight paragraphs unless the task calls for more length. Don't pad for the sake of length.

## 3. Code style (all code, any language unless a project's own CLAUDE.md overrides it)
### Philosophy
Prefer the shortest correct solution. If a task can be done in 5 lines, do not write 20. Before finishing, check whether every line is pulling weight and delete anything that exists only to look thorough.

Do not add abstraction, config options, error handling, or generality the task did not ask for. No speculative "this might be useful later" code. Do not introduce a new dependency, wrapper, or helper function for something that has a one-line standard-library equivalent.

If there's a choice between a shorter clever version and a slightly longer obvious version, prefer the one a teammate could understand in 10 seconds.

### Naming
snake_case for variables and functions. Abbreviate long names where the meaning stays clear (e.g. calc_total not calculate_total_amount, idx over index where natural).

For loop counters: use i, j, k in that order for nested loops, outer to inner, not descriptive names like row/col. Do not nest past 3 levels (i, j, k). If a 4th level seems needed, pull the inner loop out into its own function instead of inventing another letter.

### Comments
I don't over-comment. Do not add a comment on every line or explain obvious code. Two exceptions:
1. Function descriptions: one short line, not a paragraph, directly below the function definition line, not above it.
2. Obscure function calls: don't comment well-known calls (e.g. read_csv()). When a line calls something obscure or non-obvious, add a short comment explaining what that line does.

## 4. Before finishing any task
Show your work: what you ran, what passed, what changed. Don't just assert something works. If there's no test or check available for a change, say so instead of claiming success.
