import json
from typing import List, Any
from diting_inspect.models.toolconfig_repository import Tool
from diting_inspect.utils import has_jinja2_syntax_parser
from fastapi import APIRouter, HTTPException, Request
import httpx
from jinja2 import Template, TemplateError
from diting_inspect.models.repository_service import toolconfig_service

router = APIRouter(prefix="/api", tags=["tools"])


# ToolConfig endpoints
@router.post("/toolconfigs", response_model=Tool)
async def create_toolconfig(tool_config: Tool):
    return await toolconfig_service.create_tool_config(tool_config)


@router.get("/toolconfigs/{tool_config_id}", response_model=Tool)
async def get_toolconfig(tool_config_id: str):
    tool_config = await toolconfig_service.get_tool_config(tool_config_id)
    if not tool_config:
        raise HTTPException(status_code=404, detail="ToolConfig not found")
    return tool_config


@router.put("/toolconfigs/{tool_config_id}", response_model=Tool)
async def update_toolconfig(tool_config_id: str, tool_config: Tool):
    updated_tool_config = await toolconfig_service.update_tool_config(
        tool_config_id, tool_config
    )
    if not updated_tool_config:
        raise HTTPException(status_code=404, detail="ToolConfig not found")
    return updated_tool_config


@router.delete("/toolconfigs/{tool_config_id}")
async def delete_toolconfig(tool_config_id: str):
    success = await toolconfig_service.delete_tool_config(tool_config_id)
    if not success:
        raise HTTPException(status_code=404, detail="ToolConfig not found")
    return {"message": "ToolConfig deleted successfully"}


@router.get("/toolconfigs", response_model=List[Tool])
async def list_toolconfigs():
    return await toolconfig_service.get_tool_configs()


@router.post("/proxy/{tool_id}")
async def proxy_request(tool_id: str, request: Request):
    """
    Proxy endpoint that forwards requests to configured tools.

    Args:
        tool_id: The ID of the tool to proxy to
        request: The incoming FastAPI request

    Returns:
        Response with proxied data

    Raises:
        HTTPException: 404 if tool not found/disabled, 500 for other errors
    """
    try:
        # Get tool configuration with better error handling
        tool = await toolconfig_service.get_tool_config(tool_id)

        # Handle case where tool is None or empty
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_id}' not found")

        # Convert dict to Tool object if needed
        if isinstance(tool, dict):
            try:
                tool = Tool(**tool)  # type: ignore
            except Exception as e:
                print(f"Failed to create Tool object for {tool_id}: {e}")
                raise HTTPException(
                    status_code=500, detail="Tool configuration is invalid"
                )

        # Check if tool is enabled
        if not tool.enabled:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_id}' is disabled")

        # Validate required tool configuration
        if not hasattr(tool, "config") or not tool.config:
            raise HTTPException(status_code=500, detail="Tool configuration is missing")

        if not tool.config.url:
            raise HTTPException(status_code=500, detail="Tool URL is not configured")

        # Get request body
        request_body = await request.body()

        # Prepare request parameters
        method = getattr(tool.config, "method", "GET").upper()
        url = str(tool.config.url)

        # Build headers with proper handling
        headers: dict[str, Any] = {}

        # Add configured headers
        if hasattr(tool.config, "headers") and tool.config.headers:
            headers.update({header.key: header.value for header in tool.config.headers})

        # Merge request headers (avoid overriding tool config headers)
        for key, value in request.headers.items():
            key_lower = key.lower()
            # Skip headers that shouldn't be forwarded
            if key_lower not in ["host", "content-length"] and key_lower not in headers:
                headers[key] = value

        # Build query parameters
        params: dict[str, Any] = {}
        if hasattr(tool.config, "params") and tool.config.params:
            params.update({param.key: param.value for param in tool.config.params})

        # Handle request body with better error handling
        body = None
        if hasattr(tool.config, "body") and tool.config.body:
            try:
                if has_jinja2_syntax_parser(tool.config.body):
                    # Parse request body as JSON for template rendering
                    try:
                        request_data: Any = (
                            json.loads(request_body) if request_body else {}
                        )
                    except json.JSONDecodeError:
                        request_data = {}

                    # Render template
                    template = Template(tool.config.body)
                    rendered_body = template.render(request_data)
                    body = json.loads(rendered_body)
                else:
                    # Use configured body as-is
                    try:
                        body = json.loads(tool.config.body)
                    except json.JSONDecodeError:
                        body = tool.config.body
            except (TemplateError, json.JSONDecodeError) as e:
                print(f"Body template rendering failed for {tool_id}: {e}")
                raise HTTPException(
                    status_code=500, detail="Failed to process request body template"
                )
        elif request_body:
            # Use original request body if no template configured
            try:
                body = json.loads(request_body)
            except json.JSONDecodeError:
                body = request_body.decode("utf-8")

        # Set appropriate content-type if not already set
        if body is not None and "content-type" not in headers:
            if isinstance(body, (dict, list)):
                headers["content-type"] = "application/json"
            else:
                headers["content-type"] = "text/plain"

        # Get timeout configuration
        timeout = getattr(tool.config, "timeout", 30.0)

        # Make the proxied request
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
                raise HTTPException(
                    status_code=504, detail="Request to target service timed out"
                )
            except httpx.RequestError as e:
                print(f"Request error for {tool_id}: {e}")
                raise HTTPException(
                    status_code=502, detail="Failed to connect to target service"
                )

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

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
