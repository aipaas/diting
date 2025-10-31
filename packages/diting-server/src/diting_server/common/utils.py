import os
from typing import Any, Optional
from urllib.parse import urlparse


def resolve_model_config(
    model: str, base_url: Optional[str] = None, api_key: Optional[str] = None
) -> dict[str, Any]:
    if not base_url and not api_key:
        endpoint = os.getenv("AIPROXY_API_ENDPOINT")
        if endpoint is None:
            raise ValueError("AIPROXY_API_ENDPOINT is not set")
        base_url = endpoint.rstrip("/") + "/v1"

        token = os.getenv("AIPROXY_API_TOKEN")
        if token is None:
            raise ValueError("AIPROXY_API_TOKEN is not set")
        api_key = token

    if base_url:
        parsed = urlparse(base_url)
        if parsed.path and parsed.path != "/v1":
            if "/v1/" in parsed.path:
                # URL contains /v1/ followed by more path, truncate to /v1
                v1_index = parsed.path.find("/v1/")
                truncated_path = parsed.path[: v1_index + 3]  # +3 to include "/v1"
                base_url = f"{parsed.scheme}://{parsed.netloc}{truncated_path}"
            elif parsed.path.endswith("/v1"):
                # URL ends with /v1, use as-is
                base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            else:
                # Append /v1 to the existing path
                base_url = (
                    f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
                    + "/v1"
                )

    return {"model": model, "base_url": base_url, "api_key": api_key}
