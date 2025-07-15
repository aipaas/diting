from uuid import uuid4
from diting_inspect.models.model_pickle_persistence import PicklePersistentMixin
from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import Optional, Dict, Any, List, Literal
from enum import Enum
import asyncio
from abc import ABC, abstractmethod


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class AuthenticationType(str, Enum):
    NONE = "none"
    BEARER = "bearer"
    BASIC = "basic"
    API_KEY = "api-key"
    OAUTH2 = "oauth2"


class KeyValuePair(BaseModel):
    id: Optional[int] = None
    key: str = Field(..., min_length=1, description="Parameter or header key")
    value: str = Field(..., description="Parameter or header value")

    class Config:
        json_schema_extra = {
            "example": {"id": 1, "key": "Content-Type", "value": "application/json"}
        }


class AuthenticationCredentials(BaseModel):
    token: Optional[str] = Field(None, description="Bearer token for authentication")
    username: Optional[str] = Field(None, description="Username for basic auth")
    password: Optional[str] = Field(None, description="Password for basic auth")
    api_key: Optional[str] = Field(None, description="API key for authentication")
    header_name: Optional[str] = Field(
        "X-API-Key", description="Header name for API key"
    )
    client_id: Optional[str] = Field(None, description="OAuth2 client ID")
    client_secret: Optional[str] = Field(None, description="OAuth2 client secret")
    access_token: Optional[str] = Field(None, description="OAuth2 access token")
    refresh_token: Optional[str] = Field(None, description="OAuth2 refresh token")
    token_url: Optional[str] = Field(None, description="OAuth2 token endpoint")

    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "header_name": "Authorization",
            }
        }


class Authentication(BaseModel):
    type: AuthenticationType = Field(
        AuthenticationType.NONE, description="Type of authentication"
    )
    credentials: AuthenticationCredentials = Field(
        default_factory=lambda: AuthenticationCredentials(),  # type:ignore
    )

    # @field_validator('credentials')
    # def validate_credentials(cls, v: AuthenticationCredentials, values):
    #     auth_type = values.get('type')

    #     if auth_type == AuthenticationType.BEARER and not v.token:
    #         raise ValueError("Bearer token is required for bearer authentication")
    #     elif auth_type == AuthenticationType.BASIC and not v.username:
    #         raise ValueError("Username is required for basic authentication")
    #     elif auth_type == AuthenticationType.API_KEY and not v.api_key:
    #         raise ValueError("API key is required for API key authentication")
    #     elif auth_type == AuthenticationType.OAUTH2 and not (v.client_id and v.client_secret):
    #         raise ValueError("Client ID and secret are required for OAuth2 authentication")

    #     return v


class JsonSchema(BaseModel):
    request: Optional[str] = Field(
        None, description="JSON schema for request validation"
    )
    response: Optional[str] = Field(
        None, description="JSON schema for response validation"
    )

    # @field_validator("request", "response")
    # def validate_json_schema(cls, v: str):
    #     if v and v.strip():
    #         try:
    #             json.loads(v)
    #         except json.JSONDecodeError:
    #             raise ValueError("Invalid JSON schema format")
    #     return v

    # class Config:
    #     json_schema_extra = {
    #         "example": {
    #             "request": '{"type": "object", "properties": {"name": {"type": "string"}}}',
    #             "response": '{"type": "object", "properties": {"id": {"type": "integer"}}}',
    #         }
    #     }


class HttpToolConfig(BaseModel):
    method: HttpMethod = Field(HttpMethod.GET, description="HTTP method")
    url: HttpUrl = Field(..., description="Target URL for the HTTP request")
    headers: List[KeyValuePair] = Field(  # type: ignore
        default_factory=list, description="HTTP headers"
    )
    params: List[KeyValuePair] = Field(  # type: ignore
        default_factory=list, description="Query parameters"
    )
    body: Optional[str] = Field(None, description="Request body content")
    timeout: int = Field(
        30000, ge=1000, le=300000, description="Request timeout in milliseconds"
    )
    retries: int = Field(3, ge=0, le=10, description="Number of retry attempts")
    authentication: Authentication = Field(default_factory=Authentication)  # type: ignore
    schema: JsonSchema = Field(default_factory=JsonSchema)  # type: ignore

    # @field_validator('body')
    # def validate_body_for_method(cls, v: Optional[str], values):
    #     method = values.get('method')
    #     if method in [HttpMethod.GET, HttpMethod.HEAD] and v:
    #         raise ValueError(f"Body is not allowed for {method} requests")
    #     return v

    @field_validator("headers", "params")
    def validate_unique_keys(cls, v: list[KeyValuePair]):
        keys = [item.key for item in v if item.key]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate keys are not allowed")
        return v


class ToolType(str, Enum):
    HTTP = "http"
    WEBHOOK = "webhook"
    API = "api"
    GRAPHQL = "graphql"
    WEBSOCKET = "websocket"


class Tool(BaseModel):
    id: Optional[str] = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for the tool",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Human-readable name for the tool",
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Optional description of the tool"
    )
    type: ToolType = Field(ToolType.HTTP, description="Type of tool")
    config: HttpToolConfig = Field(..., description="Tool configuration")
    enabled: bool = Field(True, description="Whether the tool is enabled")
    tags: List[str] = Field(default_factory=list, description="Tags for organization")
    created_at: Optional[str] = Field(
        None, description="ISO timestamp when tool was created"
    )
    updated_at: Optional[str] = Field(
        None, description="ISO timestamp when tool was last updated"
    )

    @field_validator("name")
    def validate_name(cls, v: str):
        if not v.strip():
            raise ValueError("Tool name cannot be empty")
        return v.strip()

    @field_validator("tags")
    def validate_tags(cls, v: list[str]):
        return list(set(tag.strip() for tag in v if tag.strip()))

    class Config:
        json_schema_extra = {  # type: ignore
            "example": {
                "id": "743e4834-0845-4c7d-99e9-3aae475fd5b6",
                "name": "JSONPlaceholder Posts API",
                "description": "Retrieve posts from JSONPlaceholder test API",
                "type": "http",
                "enabled": True,
                "tags": ["test", "api", "json"],
                "config": {
                    "method": "GET",
                    "url": "https://jsonplaceholder.typicode.com/posts",
                    "headers": [
                        {"key": "Content-Type", "value": "application/json"},
                        {"key": "User-Agent", "value": "MyApp/1.0"},
                    ],
                    "params": [{"key": "userId", "value": "1"}],
                    "timeout": 30000,
                    "retries": 3,
                    "authentication": {"type": "none", "credentials": {}},
                    "schema": {
                        "response": '{"type": "array", "items": {"type": "object"}}'
                    },
                },
            }
        }


class ToolResponse(BaseModel):
    success: bool
    data: Optional[Tool] = None
    message: Optional[str] = None
    errors: Optional[List[str]] = None


class ToolListResponse(BaseModel):
    success: bool
    data: List[Tool]
    total: int
    page: int = 1
    per_page: int = 10
    message: Optional[str] = None


class ToolCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    type: ToolType = Field(ToolType.HTTP)
    config: HttpToolConfig
    enabled: bool = Field(True)
    tags: List[str] = Field(default_factory=list)


class ToolUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    type: Optional[ToolType] = None
    config: Optional[HttpToolConfig] = None
    enabled: Optional[bool] = None
    tags: Optional[List[str]] = None


class TestResult(BaseModel):
    tool_id: int
    status: Literal["success", "error", "timeout"]
    execution_time_ms: int
    request_url: str
    request_method: str
    request_headers: Dict[str, str]
    request_body: Optional[str] = None
    response_status: Optional[int] = None
    response_headers: Optional[Dict[str, str]] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: str


class TestResultResponse(BaseModel):
    success: bool
    data: Optional[TestResult] = None
    message: Optional[str] = None


def validate_tool_config(tool_data: dict[str, Any]) -> Tool:
    """Validate tool configuration and return Tool instance"""
    try:
        return Tool(**tool_data)
    except Exception as e:
        raise ValueError(f"Invalid tool configuration: {str(e)}")


class ToolConfigRepository(ABC):
    """
    Abstract repository interface for Tool Configurations.

    Defines the contract for data persistence operations on tool configurations.
    Implementations can use different storage backends (database, file, etc).
    """

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Tool]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, config_id: str) -> Optional[Tool]:
        raise NotImplementedError

    @abstractmethod
    async def create(self, config: Tool) -> Tool:
        raise NotImplementedError

    @abstractmethod
    async def update(self, config_id: str, updates: Tool) -> Optional[Tool]:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, config_id: str) -> bool:
        raise NotImplementedError


class InMemoryToolConfigRepository(ToolConfigRepository, PicklePersistentMixin):
    """
    In-memory implementation of ToolConfigRepository for development/testing.

    Stores tool configurations in memory using a dictionary. Data is lost when
    application restarts. Suitable for development and testing purposes.
    """

    def __init__(self, pickle_file: str = "data/tools.pkl"):
        """Initialize empty in-memory storage."""
        super().__init__(pickle_file)
        self._configs: Dict[str, Tool] = self.load_from_pickle({})
        self._lock = asyncio.Lock()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Tool]:
        async with self._lock:
            return list(self._configs.values())[skip : skip + limit]

    async def get_by_id(self, config_id: str) -> Optional[Tool]:
        async with self._lock:
            return self._configs.get(config_id)

    async def create(self, config: Tool) -> Tool:
        assert config.id
        async with self._lock:
            self._configs[config.id] = config
            self.save_to_pickle(self._configs)
            return config

    async def update(self, config_id: str, updates: Tool) -> Optional[Tool]:
        async with self._lock:
            if config_id in self._configs:
                # for key, value in updates.items():
                #     setattr(self._configs[config_id], key, value)
                self._configs[config_id] = updates
                self.save_to_pickle(self._configs)
                return self._configs[config_id]
            return None

    async def delete(self, config_id: str) -> bool:
        async with self._lock:
            if config_id in self._configs:
                del self._configs[config_id]
                self.save_to_pickle(self._configs)
                return True
            return False
