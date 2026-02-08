# OpenClaw Skills Collection

A curated collection of skills for [OpenClaw](https://github.com/openclaw/openclaw) - a self-hosted AI gateway connecting messaging apps to AI agents.

## Skills

| Skill | Description | Install |
|-------|-------------|---------|
| [openclaw-whisperer](./openclaw-whisperer/) | Diagnostic, error-fixing, and skill recommendation tool for OpenClaw | `npx clawhub@latest install openclaw-whisperer` |
| [skill-hub](./skill-hub/) | Skill discovery, security vetting, and installation hub (3000+ curated skills) | `npx clawhub@latest install skill-hub` |

## openclaw-whisperer

Comprehensive troubleshooting suite for OpenClaw. Automated error diagnosis across 10 categories, auto-fix for 40+ common issues, smart skill recommendations from ClawHub, deep health checks, and interactive setup wizard.

```bash
python3 openclaw-whisperer/scripts/enhanced-doctor.py         # Full diagnostics
python3 openclaw-whisperer/scripts/error-fixer.py --auto-fix  # Auto-fix safe issues
python3 openclaw-whisperer/scripts/skill-recommender.py --auto-detect  # Skill recommendations
```

See [openclaw-whisperer/SKILL.md](./openclaw-whisperer/SKILL.md) for full documentation.

## skill-hub

Unified skill discovery, security vetting, and installation for OpenClaw. Searches 3000+ curated skills from ClawHub registry and awesome-openclaw-skills catalog. Scores credibility, detects prompt injection and malicious patterns, manages installations.

```bash
python3 skill-hub/scripts/skill-hub-search.py --query "spreadsheet"  # Search skills
python3 skill-hub/scripts/skill-hub-vet.py --slug google-sheets      # Security vet
python3 skill-hub/scripts/skill-hub-status.py                        # Status dashboard
```

See [skill-hub/SKILL.md](./skill-hub/SKILL.md) for full documentation.

## Requirements

- Python 3.8+
- OpenClaw installed and configured
- Dependencies: `pip install click rich requests beautifulsoup4`

## License

MIT License - See [LICENSE](./LICENSE) for details.
