# ProjectBrain Requirements

## Product Requirements

- Provide installable CLI command `projectbrain`.
- Provide local-only stdio MCP server.
- Import local CodeGraph facts into `.projectbrain/`.
- Generate Context Packs for a task.
- Generate Impact Analysis for changed files/symbols.
- Analyze Git diffs without manual changed-file entry.
- Preserve private code boundaries.
- Document client-side privacy risks.
- Support human experience claims.
- Avoid returning source code body by default.

## Engineering Requirements

- Python standard library first.
- Optional FastAPI extras only for API skeleton.
- Tests run with `python -m unittest discover -s tests`.
- CI runs on Python 3.11 and 3.12.
- Real private code and generated private facts must remain ignored.
- Public examples must be synthetic.

## Non-Requirements

- No visual dashboard in the near term.
- No hosted ProjectBrain service.
- No automatic code editing.
- No source snippet output by default.
