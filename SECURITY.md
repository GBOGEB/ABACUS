# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 4.4.x   | ✅ Active support   |
| 4.0.x   | ⚠️ Security fixes only |
| < 4.0   | ❌ End of life      |

## Reporting a Vulnerability

If you discover a security vulnerability in ABACUS, please report it responsibly:

1. **Do NOT open a public issue.** Security issues must be reported privately.
2. **Email**: Send details to the repository owner via GitHub's private vulnerability reporting feature, or contact [@GBOGEB](https://github.com/GBOGEB) directly.
3. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Response Timeline

| Action                  | Timeframe       |
| ----------------------- | --------------- |
| Acknowledgement         | Within 48 hours |
| Initial assessment      | Within 1 week   |
| Fix or mitigation plan  | Within 2 weeks  |
| Public disclosure       | After fix is deployed |

## Security Best Practices in This Repository

- **GitHub Actions**: Workflows use pinned action versions (`@v4`, `@v5`) and least-privilege `permissions` blocks.
- **Dependabot**: Automated dependency updates are enabled via `.github/dependabot.yml`.
- **Branch Protection**: See `.github/BRANCH_PROTECTION_RECOMMENDATIONS.md` for recommended rules.
- **No secrets in code**: All sensitive values use GitHub Secrets or environment variables.

## Scope

This policy covers:
- The ABACUS repository source code
- CI/CD workflows and configuration
- Documentation site (`docs/`)
- DMAIC toolkit (`DMAIC_V3/`)

Third-party dependencies are covered by their own security policies.
