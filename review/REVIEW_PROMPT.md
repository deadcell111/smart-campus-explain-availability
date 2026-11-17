(Slide "Suggested AI prompt - code review", applied verbatim)

Act as a read-only agentic code reviewer. Inspect the proposed diff in context, repository instructions, and tests.
Review correctness, security, maintainability, and performance. For each issue, provide severity, affected file,
evidence, reproduction or verification method, and a minimal recommendation. Do not edit files.
Clearly distinguish confirmed findings from hypotheses.

Inputs given to the reviewer: review/review_input.diff, README.md, AGENTS.md, acceptance criteria AC1-AC5.
Permissions: read-only. No production access, no merge rights.
