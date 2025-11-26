"""Pytest configuration and fixtures for diting-web tests."""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from diting_web.config.settings import get_settings
from diting_web.db.base import Base
from diting_web.db.session import get_db
from diting_web.main import app

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://admin:password@localhost:5432/diting_web_test"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)

# Create test session factory
TestSessionLocal = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session.
    
    This fixture:
    1. Creates all tables before the test
    2. Provides a session for the test
    3. Rolls back changes after the test
    4. Drops all tables after the test
    """
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()

    # Drop tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client with database session override."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def mock_llm_config() -> dict:
    """Mock LLM configuration for testing."""
    return {
        "model_name": "gpt-4o-mini",
        "api_key": "sk-test-key",
        "base_url": "http://test-api.com",
        "timeout": 30.0,
        "temperature": 0.7,
    }


@pytest.fixture
def mock_embedding_config() -> dict:
    """Mock embedding configuration for testing."""
    return {
        "model_name": "text-embedding-ada-002",
        "api_key": "sk-test-key",
        "base_url": "http://test-api.com",
        "timeout": 30.0,
    }


@pytest.fixture
def mock_test_case_data() -> dict:
    """Mock test case data for evaluation testing."""
    return {
        "user_input": "What is Python?",
        "actual_output": "Python is a programming language.",
        "expected_output": "Python is a high-level, interpreted programming language.",
        "context": ["Python was created by Guido van Rossum."],
    }


@pytest.fixture
def mock_corpus_data() -> dict:
    """Mock corpus data for synthesis testing."""
    return {
        "context": [
            "Python is a high-level, interpreted programming language.",
            "Python was created by Guido van Rossum and first released in 1991.",
            "Python supports multiple programming paradigms.",
        ]
    }



