"""
Business logic service for managing tool configurations.
Provides high-level operations and encapsulates business rules.
"""

import json
from typing import Any, List, Optional
from diting_inspect.models.toolconfig_repository import Tool, ToolConfigRepository
from diting_inspect.utils import has_jinja2_syntax_parser
import httpx
from jinja2 import Template, TemplateError


class ToolConfigService:
    """
    Service class for managing tool configurations.

    Encapsulates business logic and provides a clean interface for
    tool configuration management operations. Separates business rules from data access.
    """

    def __init__(self, repository: ToolConfigRepository):
        """
        Initialize service with repository dependency.

        Args:
            repository: Tool configuration repository for data persistence
        """
        self._repository = repository

    async def get_tool_configs(self, skip: int = 0, limit: int = 100) -> List[Tool]:
        """
        Retrieve paginated list of tool configurations.

        Args:
            skip: Number of configurations to skip for pagination
            limit: Maximum number of configurations to return (max 1000)

        Returns:
            List of tool configurations

        Raises:
            ValueError: If limit exceeds maximum allowed
        """
        if limit > 1000:
            raise ValueError("Limit cannot exceed 1000 configurations")

        return await self._repository.get_all(skip=skip, limit=limit)

    async def get_tool_config(self, config_id: str) -> Optional[Tool]:
        """
        Retrieve a specific tool configuration by ID.

        Args:
            config_id: Unique identifier for the tool configuration

        Returns:
            Tool configuration if found, None otherwise
        """
        if not config_id or not config_id.strip():
            return None

        return await self._repository.get_by_id(config_id.strip())

    async def create_tool_config(self, config: Tool) -> Tool:
        """
        Create a new tool configuration with validation.

        Args:
            config: Tool configuration to create

        Returns:
            Created tool configuration

        Raises:
            ValueError: If configuration data is invalid
        """
        self._validate_tool_config(config)
        return await self._repository.create(config)

    async def update_tool_config(self, config_id: str, updates: Tool) -> Optional[Tool]:
        """
        Update an existing tool configuration.

        Args:
            config_id: Unique identifier for the tool configuration
            updates: Dictionary of fields to update

        Returns:
            Updated tool configuration if found, None otherwise

        Raises:
            ValueError: If update data is invalid
        """
        if not config_id or not config_id.strip():
            return None

        return await self._repository.update(config_id.strip(), updates)

    async def delete_tool_config(self, config_id: str) -> bool:
        """
        Delete a tool configuration.

        Args:
            config_id: Unique identifier for the tool configuration

        Returns:
            True if configuration was deleted, False if not found
        """
        if not config_id or not config_id.strip():
            return False

        return await self._repository.delete(config_id.strip())

    async def input_tool_output(self, tool_id: str, input: str) -> Any:
        tool = await self.get_tool_config(tool_id)
        if not tool:
            raise ValueError("Tool cannot be empty")
        if isinstance(tool, dict):
            try:
                tool = Tool(**tool)  # type: ignore
            except Exception:
                raise ValueError("Tool configuration is invalid")
        if not tool.enabled:
            raise ValueError("Tool disable")
        if not hasattr(tool, "config") or not tool.config:
            raise ValueError("Tool configuration is missing")
        if not tool.config.url:
            raise ValueError("Tool URL is not configured")
        method = getattr(tool.config, "method", "GET").upper()
        url = str(tool.config.url)
        headers: dict[str, Any] = {}
        if hasattr(tool.config, "headers") and tool.config.headers:
            headers.update({header.key: header.value for header in tool.config.headers})
        params: dict[str, Any] = {}
        if hasattr(tool.config, "params") and tool.config.params:
            params.update({param.key: param.value for param in tool.config.params})

        body = None
        if hasattr(tool.config, "body") and tool.config.body:
            try:
                if has_jinja2_syntax_parser(tool.config.body):
                    try:
                        input_data: Any = json.loads(input) if input else {}
                    except json.JSONDecodeError:
                        input_data = {}

                    # Render template
                    template = Template(tool.config.body)
                    rendered_body = template.render(input_data)
                    body = json.loads(rendered_body)
                else:
                    try:
                        body = json.loads(tool.config.body)
                    except json.JSONDecodeError:
                        body = tool.config.body
            except (TemplateError, json.JSONDecodeError) as e:
                print(f"Body template rendering failed for {tool_id}: {e}")
                raise ValueError("Failed to process request body template")
        elif input:
            try:
                body = json.loads(input)
            except json.JSONDecodeError:
                body = input.decode("utf-8")  # type: ignore

        if body is not None and "content-type" not in headers:
            if isinstance(body, (dict, list)):
                headers["content-type"] = "application/json"
            else:
                headers["content-type"] = "text/plain"

        timeout = getattr(tool.config, "timeout", 30.0)
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=body if isinstance(body, (dict, list)) else None,  # type: ignore
                    content=body if isinstance(body, (str, bytes)) else None,
                    timeout=timeout,
                    follow_redirects=True,
                )
            except httpx.TimeoutException:
                raise ValueError("Request to target service timed out")
            except httpx.RequestError as e:
                print(f"Request error for {tool_id}: {e}")
                raise ValueError("Failed to connect to target service")

        # Process response
        response_headers = dict(response.headers)

        # Remove headers that shouldn't be forwarded
        headers_to_remove = ["content-encoding", "transfer-encoding", "connection"]
        for header in headers_to_remove:
            response_headers.pop(header, None)

        # Determine response content
        content_type = response.headers.get("content-type", "").lower()

        if "application/json" in content_type:
            try:
                response_body = response.json()
            except json.JSONDecodeError:
                response_body = response.text
        else:
            response_body = response.text
        # aipaas parser
        if "api/v1/conversation" in url and isinstance(response_body, str):
            response_answer = response_body.split("\r\n")
            answer = [r for r in response_answer if r.startswith("data:")]
            if answer:
                response_body = json.loads(answer[0][6:]).get("answer")

        response_dict = {
            "status_code": response.status_code,
            "headers": response_headers,
            "body": response_body,
        }
        if tool.config.schema.response and has_jinja2_syntax_parser(
            tool.config.schema.response
        ):
            return Template(tool.config.schema.response).render(**response_dict)
        # Return structured response
        return response_dict

    def _validate_tool_config(self, config: Tool) -> None:
        """
        Validate tool configuration data.

        Args:
            config: Tool configuration to validate

        Raises:
            ValueError: If configuration data is invalid
        """
        if not config.name or not config.name.strip():
            raise ValueError("Tool configuration name is required and cannot be empty")
