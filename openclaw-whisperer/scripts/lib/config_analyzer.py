"""OpenClaw configuration validator and analyzer."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .utils import get_config


@dataclass
class ConfigIssue:
    """Represents a configuration validation issue."""
    severity: str  # "error" | "warning" | "info"
    path: str  # JSON path like "gateway.port"
    message: str
    fix_hint: str | None


class ConfigAnalyzer:
    """OpenClaw configuration validator and analyzer."""

    def __init__(self):
        """Initialize analyzer and load config."""
        self.config = get_config()

    def analyze(self) -> list[ConfigIssue]:
        """Run all configuration checks.

        Returns:
            List of issues sorted by severity (errors first)
        """
        from .config_security_checks import check_security

        issues = []
        issues.extend(self._check_gateway(self.config))
        issues.extend(self._check_channels(self.config))
        issues.extend(self._check_agents(self.config))
        issues.extend(self._check_skills(self.config))
        issues.extend(self._check_plugins(self.config))
        issues.extend(check_security(self.config))

        severity_order = {"error": 0, "warning": 1, "info": 2}
        issues.sort(key=lambda x: severity_order.get(x.severity, 3))
        return issues

    def _check_gateway(self, config: dict) -> list[ConfigIssue]:
        """Validate gateway configuration section."""
        issues = []
        gateway = config.get("gateway", {})

        port = gateway.get("port")
        if port is not None:
            if not isinstance(port, int) or port < 1 or port > 65535:
                issues.append(ConfigIssue(
                    severity="error",
                    path="gateway.port",
                    message=f"Invalid port number: {port}",
                    fix_hint="Port must be between 1 and 65535"
                ))

        # Support both flat "authMode" and nested "auth.mode" schemas
        auth_mode = gateway.get("authMode") or (gateway.get("auth", {}).get("mode") if isinstance(gateway.get("auth"), dict) else None)
        if not auth_mode:
            issues.append(ConfigIssue(
                severity="warning",
                path="gateway.authMode",
                message="Auth mode not set",
                fix_hint="Set gateway.auth.mode or gateway.authMode to 'password', 'token', or 'none'"
            ))

        bind = gateway.get("bind")
        if bind and not isinstance(bind, str):
            issues.append(ConfigIssue(
                severity="error",
                path="gateway.bind",
                message="Invalid bind address format",
                fix_hint="Bind address must be a string (e.g., '0.0.0.0' or '127.0.0.1')"
            ))

        return issues

    def _check_channels(self, config: dict) -> list[ConfigIssue]:
        """Validate channel configurations."""
        issues = []
        channels = config.get("channels", {})

        # Map channel -> required fields with alternates (any match = OK)
        required_fields = {
            "telegram": [["token", "botToken"]],  # accept either field name
            "discord": [["token"]],
            "slack": [["token"], ["appToken"]],
            "whatsapp": [["dmPolicy"]]
        }

        for channel_name, field_groups in required_fields.items():
            channel_config = channels.get(channel_name, {})
            enabled = channel_config.get("enabled", False)
            # Also check nested accounts for credentials
            accounts = channel_config.get("accounts", {})

            if enabled:
                for alternates in field_groups:
                    # Field present at top level or in any account
                    found = any(channel_config.get(f) for f in alternates) or any(
                        acc.get(f) for acc in accounts.values() if isinstance(acc, dict) for f in alternates
                    )
                    if not found:
                        display = "/".join(alternates)
                        issues.append(ConfigIssue(
                            severity="error",
                            path=f"channels.{channel_name}.{display}",
                            message=f"Missing required field '{display}' for enabled {channel_name} channel",
                            fix_hint=f"Add one of [{display}] to channels.{channel_name} or its accounts"
                        ))

        return issues

    def _check_agents(self, config: dict) -> list[ConfigIssue]:
        """Validate agent configuration. Supports both flat and nested schemas."""
        issues = []
        # Support flat "agent" and nested "agents.defaults" schemas
        agent = config.get("agent", {})
        agents = config.get("agents", {})
        defaults = agents.get("defaults", {})

        # Model: flat agent.model OR nested agents.defaults.model.primary
        model = agent.get("model")
        if not model:
            model_cfg = defaults.get("model", {})
            model = model_cfg.get("primary") if isinstance(model_cfg, dict) else model_cfg
        # Also check per-agent models in agents.list
        agent_list = agents.get("list", [])
        has_agent_model = any(a.get("model") for a in agent_list if isinstance(a, dict))

        if not model and not has_agent_model:
            issues.append(ConfigIssue(
                severity="error",
                path="agents.defaults.model.primary",
                message="No AI model configured",
                fix_hint="Set agents.defaults.model.primary or agent.model"
            ))

        # Workspace: flat or nested
        workspace = agent.get("workspace") or defaults.get("workspace")
        if workspace:
            workspace_path = Path(workspace).expanduser()
            if not workspace_path.exists():
                issues.append(ConfigIssue(
                    severity="warning",
                    path="agents.defaults.workspace",
                    message=f"Workspace directory does not exist: {workspace}",
                    fix_hint="Create the directory or update the path"
                ))

        # Sandbox: flat agent.sandboxMode or per-agent sandbox.mode
        sandbox = agent.get("sandboxMode")
        if sandbox and sandbox not in ["strict", "relaxed", "off"]:
            issues.append(ConfigIssue(
                severity="error",
                path="agent.sandboxMode",
                message=f"Invalid sandbox mode: {sandbox}",
                fix_hint="Must be 'strict', 'relaxed', or 'off'"
            ))

        return issues

    def _check_skills(self, config: dict) -> list[ConfigIssue]:
        """Validate skills configuration."""
        issues = []
        skills = config.get("skills", {})
        if not isinstance(skills, dict):
            issues.append(ConfigIssue(
                severity="error", path="skills",
                message="Skills configuration must be an object",
                fix_hint="Use {} for skills section"
            ))
        return issues

    def _check_plugins(self, config: dict) -> list[ConfigIssue]:
        """Validate plugins configuration. Accepts array or object with allow/entries."""
        issues = []
        plugins = config.get("plugins")
        if plugins is not None and not isinstance(plugins, (list, dict)):
            issues.append(ConfigIssue(
                severity="error", path="plugins",
                message="Plugins configuration must be an array or object with allow/entries",
                fix_hint="Use [] or {\"allow\": [...], \"entries\": {...}}"
            ))
        return issues

    def detect_channels(self) -> list[str]:
        """Detect enabled channel names."""
        channels = self.config.get("channels", {})
        return [name for name, cfg in channels.items() if cfg.get("enabled", False)]

    def detect_model(self) -> str | None:
        """Get configured AI model name (flat or nested schema)."""
        model = self.config.get("agent", {}).get("model")
        if not model:
            model_cfg = self.config.get("agents", {}).get("defaults", {}).get("model", {})
            model = model_cfg.get("primary") if isinstance(model_cfg, dict) else model_cfg
        return model

    def get_config_path(self, path: str):
        """Access config value using dot-notation path."""
        from .config_security_checks import get_config_path
        return get_config_path(self.config, path)
