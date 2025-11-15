# Editors and Validators (Markdown, YAML, JSON)

Recommended IDEs:
- VS Code
  - Extensions: Markdown All in One, markdownlint, YAML (Red Hat), Prettier, Python
  - JSON: Built-in schema support; install JSON Tools if needed
- JetBrains (PyCharm/IntelliJ)
  - Plugins: Markdown, YAML/Ansible, JSON Helper

CLI validators:
- Markdown: markdownlint-cli2
- YAML: yamllint
- JSON: python -m json.tool or jq

Formatting tips:
- Markdown: keep lines short, use fenced code blocks with language IDs
- YAML: 2-space indents, no tabs, quote special values
- JSON: use double quotes only, validate with python -m json.tool

MCP/agent inputs:
- Supply canonical book, knowledge_packages/*.json|yaml, and DMAIC_V3_OUTPUT/reports/*.json as context.
- Prefer JSON for structured prompts; use YAML for human-edited configs.
