#!/usr/bin/env python3

import os
import stat
from pathlib import Path

from cubbi_init import ToolPlugin, cubbi_config, set_ownership


class AiderPlugin(ToolPlugin):
    @property
    def tool_name(self) -> str:
        return "aider"

    def _get_aider_config_dir(self) -> Path:
        return Path("/home/cubbi/.aider")

    def _get_aider_cache_dir(self) -> Path:
        return Path("/home/cubbi/.cache/aider")

    def _ensure_aider_dirs(self) -> tuple[Path, Path]:
        config_dir = self._get_aider_config_dir()
        cache_dir = self._get_aider_cache_dir()

        self.create_directory_with_ownership(config_dir)
        self.create_directory_with_ownership(cache_dir)

        return config_dir, cache_dir

    def is_already_configured(self) -> bool:
        config_dir = self._get_aider_config_dir()
        env_file = config_dir / ".env"
        return env_file.exists()

    def configure(self) -> bool:
        self.status.log("Setting up Aider configuration...")

        config_dir, cache_dir = self._ensure_aider_dirs()

        env_vars = self._create_environment_config()

        if env_vars:
            env_file = config_dir / ".env"
            success = self._write_env_file(env_file, env_vars)
            if success:
                self.status.log("✅ Aider environment configured successfully")
            else:
                self.status.log("⚠️ Failed to write Aider environment file", "WARNING")
        else:
            self.status.log(
                "ℹ️ No API keys found - Aider will run without pre-configuration", "INFO"
            )
            self.status.log(
                "   You can configure API keys later using environment variables",
                "INFO",
            )

        if not cubbi_config.mcps:
            self.status.log("No MCP servers to integrate")
            return True

        self.status.log(
            f"Found {len(cubbi_config.mcps)} MCP server(s) - no direct integration available for Aider"
        )

        return True

    def _create_environment_config(self) -> dict[str, str]:
        env_vars = {}

        provider_config = cubbi_config.get_provider_for_default_model()
        if provider_config and cubbi_config.defaults.model:
            _, model_name = cubbi_config.defaults.model.split("/", 1)

            env_vars["AIDER_MODEL"] = model_name
            self.status.log(f"Set Aider model to {model_name}")

            if provider_config.type == "anthropic":
                env_vars["AIDER_ANTHROPIC_API_KEY"] = provider_config.api_key
                self.status.log("Configured Anthropic API key for Aider")

            elif provider_config.type == "openai":
                env_vars["AIDER_OPENAI_API_KEY"] = provider_config.api_key
                if provider_config.base_url:
                    env_vars["AIDER_OPENAI_API_BASE"] = provider_config.base_url
                    self.status.log(
                        f"Set Aider OpenAI API base to {provider_config.base_url}"
                    )
                self.status.log("Configured OpenAI API key for Aider")

            elif provider_config.type == "google":
                env_vars["GEMINI_API_KEY"] = provider_config.api_key
                self.status.log("Configured Google/Gemini API key for Aider")

            elif provider_config.type == "openrouter":
                env_vars["OPENROUTER_API_KEY"] = provider_config.api_key
                self.status.log("Configured OpenRouter API key for Aider")

            else:
                self.status.log(
                    f"Provider type '{provider_config.type}' not directly supported by Aider plugin",
                    "WARNING",
                )
        else:
            self.status.log(
                "No default model or provider configured - checking legacy environment variables",
                "WARNING",
            )

            api_key_mappings = {
                "OPENAI_API_KEY": "AIDER_OPENAI_API_KEY",
                "ANTHROPIC_API_KEY": "AIDER_ANTHROPIC_API_KEY",
                "DEEPSEEK_API_KEY": "DEEPSEEK_API_KEY",
                "GEMINI_API_KEY": "GEMINI_API_KEY",
                "OPENROUTER_API_KEY": "OPENROUTER_API_KEY",
            }

            for env_var, aider_var in api_key_mappings.items():
                value = os.environ.get(env_var)
                if value:
                    env_vars[aider_var] = value
                    provider = env_var.replace("_API_KEY", "").lower()
                    self.status.log(f"Added {provider} API key from environment")

            openai_url = os.environ.get("OPENAI_URL")
            if openai_url:
                env_vars["AIDER_OPENAI_API_BASE"] = openai_url
                self.status.log(
                    f"Set OpenAI API base URL to {openai_url} from environment"
                )

            model = os.environ.get("AIDER_MODEL")
            if model:
                env_vars["AIDER_MODEL"] = model
                self.status.log(f"Set model to {model} from environment")

        additional_keys = os.environ.get("AIDER_API_KEYS")
        if additional_keys:
            try:
                for pair in additional_keys.split(","):
                    if "=" in pair:
                        provider, key = pair.strip().split("=", 1)
                        env_var_name = f"{provider.upper()}_API_KEY"
                        env_vars[env_var_name] = key
                        self.status.log(f"Added {provider} API key from AIDER_API_KEYS")
            except Exception as e:
                self.status.log(f"Failed to parse AIDER_API_KEYS: {e}", "WARNING")

        auto_commits = os.environ.get("AIDER_AUTO_COMMITS", "true")
        if auto_commits.lower() in ["true", "false"]:
            env_vars["AIDER_AUTO_COMMITS"] = auto_commits

        dark_mode = os.environ.get("AIDER_DARK_MODE", "false")
        if dark_mode.lower() in ["true", "false"]:
            env_vars["AIDER_DARK_MODE"] = dark_mode

        for proxy_var in ["HTTP_PROXY", "HTTPS_PROXY"]:
            value = os.environ.get(proxy_var)
            if value:
                env_vars[proxy_var] = value
                self.status.log(f"Added proxy configuration: {proxy_var}")

        return env_vars

    def _write_env_file(self, env_file: Path, env_vars: dict[str, str]) -> bool:
        try:
            content = "\n".join(f"{key}={value}" for key, value in env_vars.items())

            with open(env_file, "w") as f:
                f.write(content)
                f.write("\n")

            set_ownership(env_file)
            os.chmod(env_file, stat.S_IRUSR | stat.S_IWUSR)

            self.status.log(f"Created Aider environment file at {env_file}")
            return True
        except Exception as e:
            self.status.log(f"Failed to write Aider environment file: {e}", "ERROR")
            return False


PLUGIN_CLASS = AiderPlugin
