"""
Business logic service for managing tool configurations.
Provides high-level operations and encapsulates business rules.
"""

import asyncio
from datetime import datetime
import json
from typing import Any, List, Optional
from diting_core.cases.llm_case import LLMCaseParams
from diting_inspect.models.case_model import CaseRepository, LLMCaseData
from diting_inspect.models.toolconfig_repository import Tool, ToolConfigRepository
from diting_inspect.models.toolexecution_model import (
    ToolExecutionRepository,
    ToolExecutionResult,
)
from diting_inspect.utils import has_jinja2_syntax_parser
import httpx
from jinja2 import Environment, Template, TemplateError


class ToolConfigService:
    """
    Service class for managing tool configurations.

    Encapsulates business logic and provides a clean interface for
    tool configuration management operations. Separates business rules from data access.
    """

    def __init__(
        self,
        repository: ToolConfigRepository,
        case_repository: Optional[CaseRepository] = None,
        toolexecution_repository: Optional[ToolExecutionRepository] = None,
        max_concurrent_evaluations: int = 10,
    ):
        """
        Initialize service with repository dependency.

        Args:
            repository: Tool configuration repository for data persistence
        """
        self._repository = repository
        self._case_repository = case_repository
        self._toolexecute_repository = toolexecution_repository
        self._max_concurrent = max_concurrent_evaluations

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
                response_body = json.loads(answer[0][6:])

        response_dict = {
            "status_code": response.status_code,
            "headers": response_headers,
            "body": response_body,
        }
        if tool.config.schema.response and has_jinja2_syntax_parser(
            tool.config.schema.response
        ):
            env = Environment()
            ast = env.parse(tool.config.schema.response)
            assert len(ast.body) > 0, "error schema response jinja2 syntax"
            response_type = ast.body[0].nodes[0].node.name  # type: ignore
            response_key = ast.body[0].nodes[0].attr  # type: ignore
            if response_type == "Response" and isinstance(response_body, dict):
                response_dict["body"] = response_body.get(response_key, None)  # type: ignore
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

    async def run_tool(
        self,
        tool_execution_id: str,
        input: LLMCaseParams,
        tool_id: str,
        output: LLMCaseParams,
        case_ids: List[str],
    ):
        """
        Run tool execution on specified cases with given tool.

        Args:
            tool_execution_id: Unique identifier for this tool execution
            input: Input parameters for the tool
            tool_id: Unique identifier for the tool
            output: Expected output parameters for the tool
            case_ids: List of test case IDs to evaluate
        """
        started_at = datetime.now()
        try:
            # Initialize tracking
            initial_result = ToolExecutionResult(
                id=tool_execution_id,
                case_ids=case_ids,
                results=[],
                status="in_progress",
                started_at=started_at,
                completed_at=None,
                error=None,
            )
            if self._toolexecute_repository:
                await self._toolexecute_repository.save(initial_result)

            # Get test cases
            cases: list[LLMCaseData] = []
            if self._case_repository:
                for case_id in case_ids:
                    case = await self._case_repository.get_by_id(case_id)
                    if case:
                        cases.append(case)

            if not cases:
                raise ValueError("No valid test cases found")

            # Create a semaphore to limit concurrent evaluations
            semaphore = asyncio.Semaphore(self._max_concurrent)

            async def execute_case(case: LLMCaseData):
                async with semaphore:
                    print("execute case:", case)
                    func_input: str = ""
                    match input:
                        case LLMCaseParams.USER_INPUT:
                            func_input = case.input or ""
                        case LLMCaseParams.ACTUAL_OUTPUT:
                            func_input = case.actual_output or ""
                        case LLMCaseParams.EXPECTED_OUTPUT:
                            func_input = case.expected_output or ""
                        case LLMCaseParams.CONTEXT:
                            func_input = " ".join(case.context) if case.context else ""
                        case LLMCaseParams.RETRIEVAL_CONTEXT:
                            func_input = (
                                " ".join(case.retrieval_context)
                                if case.retrieval_context
                                else ""
                            )
                    func_input_format = f'{{ "{input.value}": "{func_input}" }}'
                    func_return: dict[str, Any] = await self.input_tool_output(
                        tool_id, func_input_format
                    )
                    func_output: Any = func_return.get("body", "")
                    match output:
                        case LLMCaseParams.USER_INPUT:
                            case.input = str(func_output)
                        case LLMCaseParams.ACTUAL_OUTPUT:
                            case.actual_output = str(func_output)
                        case LLMCaseParams.EXPECTED_OUTPUT:
                            case.expected_output = str(func_output)
                        case LLMCaseParams.CONTEXT:
                            if isinstance(func_output, list):
                                case.context = [str(o) for o in func_output]  # type: ignore
                            else:
                                case.context = list(func_output)
                        case LLMCaseParams.RETRIEVAL_CONTEXT:
                            if isinstance(func_output, list):
                                case.retrieval_context = [str(o) for o in func_output]  # type: ignore
                            else:
                                case.retrieval_context = list(func_output)
                    if self._case_repository:
                        await self._case_repository.update(case.id, case)
                    return func_return

            # Run tool executions concurrently using TaskGroup
            tasks: list[asyncio.Task[Any]] = []
            async with asyncio.TaskGroup() as tg:
                for case in cases:
                    task = tg.create_task(execute_case(case))
                    tasks.append(task)

            # Process results
            tool_results: List[Any] = []
            for task in tasks:
                try:
                    result = await task
                    if result:
                        tool_results.append(result)
                except Exception as e:
                    print(f"Error processing task: {e}")

            # Save final results
            final_result = ToolExecutionResult(
                id=tool_execution_id,
                case_ids=case_ids,
                results=tool_results,
                status="completed",
                started_at=started_at,
                completed_at=datetime.now(),
                error=None,
            )
            if self._toolexecute_repository:
                await self._toolexecute_repository.save(final_result)

        except Exception as e:
            print(f"Tool execution {tool_execution_id} failed: {e}")

            # Save failure result
            final_result = ToolExecutionResult(
                id=tool_execution_id,
                case_ids=case_ids,
                results=[],
                status="failed",
                started_at=started_at,
                completed_at=datetime.now(),
                error=str(e),
            )
            if self._toolexecute_repository:
                await self._toolexecute_repository.save(final_result)
