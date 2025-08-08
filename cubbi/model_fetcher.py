"""
Model fetching utilities for OpenAI-compatible providers.
"""

import json
import logging
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class ModelFetcher:
    """Fetches model lists from OpenAI-compatible API endpoints."""

    def __init__(self, timeout: int = 30):
        """Initialize the model fetcher.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout

    def fetch_models(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, str]]:
        """Fetch models from an OpenAI-compatible /v1/models endpoint.

        Args:
            base_url: Base URL of the provider (e.g., "https://api.openai.com" or "https://api.litellm.com")
            api_key: Optional API key for authentication
            headers: Optional additional headers

        Returns:
            List of model dictionaries with 'id' and 'name' keys

        Raises:
            requests.RequestException: If the request fails
            ValueError: If the response format is invalid
        """
        # Construct the models endpoint URL
        models_url = self._build_models_url(base_url)

        # Prepare headers
        request_headers = self._build_headers(api_key, headers)

        logger.info(f"Fetching models from {models_url}")

        try:
            response = requests.get(
                models_url, headers=request_headers, timeout=self.timeout
            )
            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            # Validate response structure
            if not isinstance(data, dict) or "data" not in data:
                raise ValueError(
                    f"Invalid response format: expected dict with 'data' key, got {type(data)}"
                )

            models_data = data["data"]
            if not isinstance(models_data, list):
                raise ValueError(
                    f"Invalid models data: expected list, got {type(models_data)}"
                )

            # Process models
            models = []
            for model_item in models_data:
                if not isinstance(model_item, dict):
                    continue

                model_id = model_item.get("id", "")
                if not model_id:
                    continue

                # Skip models with * in their ID as requested
                if "*" in model_id:
                    logger.debug(f"Skipping model with wildcard: {model_id}")
                    continue

                # Create model entry
                model = {
                    "id": model_id,
                }
                models.append(model)

            logger.info(f"Successfully fetched {len(models)} models from {base_url}")
            return models

        except requests.exceptions.Timeout:
            logger.error(f"Request timed out after {self.timeout} seconds")
            raise requests.RequestException(f"Request to {models_url} timed out")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise requests.RequestException(f"Failed to connect to {models_url}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e}")
            if e.response.status_code == 401:
                raise requests.RequestException(
                    "Authentication failed: invalid API key"
                )
            elif e.response.status_code == 403:
                raise requests.RequestException(
                    "Access forbidden: check API key permissions"
                )
            else:
                raise requests.RequestException(
                    f"HTTP {e.response.status_code} error from {models_url}"
                )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise ValueError(f"Invalid JSON response from {models_url}")

    def _build_models_url(self, base_url: str) -> str:
        """Build the models endpoint URL from a base URL.

        Args:
            base_url: Base URL of the provider

        Returns:
            Complete URL for the /v1/models endpoint
        """
        # Remove trailing slash if present
        base_url = base_url.rstrip("/")

        # Add /v1/models if not already present
        if not base_url.endswith("/v1/models"):
            if base_url.endswith("/v1"):
                base_url += "/models"
            else:
                base_url += "/v1/models"

        return base_url

    def _build_headers(
        self,
        api_key: Optional[str] = None,
        additional_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Build request headers.

        Args:
            api_key: Optional API key for authentication
            additional_headers: Optional additional headers

        Returns:
            Dictionary of headers
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Add authentication header if API key is provided
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # Add any additional headers
        if additional_headers:
            headers.update(additional_headers)

        return headers


def fetch_provider_models(
    provider_config: Dict, timeout: int = 30
) -> List[Dict[str, str]]:
    """Convenience function to fetch models for a provider configuration.

    Args:
        provider_config: Provider configuration dictionary
        timeout: Request timeout in seconds

    Returns:
        List of model dictionaries

    Raises:
        ValueError: If provider is not OpenAI-compatible or missing required fields
        requests.RequestException: If the request fails
    """
    import os

    provider_type = provider_config.get("type", "")
    base_url = provider_config.get("base_url")
    api_key = provider_config.get("api_key", "")

    if api_key.startswith("${") and api_key.endswith("}"):
        env_var_name = api_key[2:-1]
        api_key = os.environ.get(env_var_name, "")

    if provider_type != "openai" and not base_url:
        raise ValueError(
            "Provider is not OpenAI-compatible (must have type='openai' or base_url)"
        )

    if not base_url:
        raise ValueError("No base_url specified for OpenAI-compatible provider")

    fetcher = ModelFetcher(timeout=timeout)
    return fetcher.fetch_models(base_url, api_key)
