# Markdown-Driven Execution (MD as Pipeline)

Concept
- Treat Markdown as the single source of truth that holds: parameters (YAML frontmatter), executable steps (fenced code blocks), assertions, outputs, and versioning.

Numbered ASCII workflow
1) Author MD
   - Frontmatter params and version
   - Fenced code blocks tagged as exec/assert
2) Parse
   - Extract blocks with info string containing "exec"
   - Build an execution plan
3) Execute
   - Run blocks in order (bash/python)
   - Capture stdout/stderr and exit codes
4) Validate
   - Blocks tagged "assert" must exit 0 (Python asserts or shell test)
5) Persist
   - Save stdout/stderr to DMAIC_V3_OUTPUT/md_exec/<doc>/*
   - Optionally write a processed MD with appended outputs
6) Version
   - If all asserts pass, bump patch
