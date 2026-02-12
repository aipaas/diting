# Project Context

## Purpose
DiTing is a unified AI evaluation and data synthesis platform designed specifically for Large Language Model (LLM) scenarios. It provides comprehensive evaluation metrics and high-quality synthetic data generation capabilities to help data scientists, AI engineers, and system developers assess and improve AI system performance. The platform consists of three core packages: evaluation engine (diting-core), web API server (diting-server), and optimization algorithms (diting-optimizer).

## Tech Stack

### Core Technologies
- **Language**: Python 3.11+
- **Package Management**: `uv` (modern Python package manager)
- **Build System**: Hatchling with uv-dynamic-versioning
- **Workspace**: uv workspace for monorepo management

### Backend & API
- **Web Framework**: FastAPI >= 0.116.1
- **Data Validation**: Pydantic >= 2.0.0
- **ASGI Server**: Uvicorn >= 0.35.0
- **Configuration**: Pydantic-settings >= 2.10.1

### AI/ML Libraries
- **LLM Integration**: LangChain + OpenAI API
- **Embeddings**: OpenAI embeddings and custom models
- **Optimization**: Optuna >= 3.0.0
- **Data Processing**: NumPy >= 2.3.1

### Code Quality & Development
- **Formatting**: Ruff >= 0.12.1
- **Type Checking**: MyPy + Pyright
- **Testing**: Pytest >= 8.4.1 with coverage
- **Pre-commit**: Automated code quality checks
- **Linting**: Ruff for both linting and formatting

### Containerization
- **Docker**: Multi-stage builds for production
- **Base Image**: Python 3.11-slim-bookworm
- **Package Management**: uv in Docker containers

## Project Conventions

### Code Style
- **Formatting**: Ruff auto-formatting with consistent Python style (PEP 8)
- **Type Safety**: Strict type annotations required for all functions and classes
- **Naming Conventions**:
  - Classes: PascalCase (e.g., `LLMCase`, `BaseMetric`)
  - Functions/variables: snake_case
  - Constants: UPPER_SNAKE_CASE
  - Private members: underscore prefix
- **Docstrings**: Comprehensive docstrings for all public APIs
- **Import Organization**: Ruff-enforced import grouping and formatting
- **Line Length**: 88 characters (Ruff default)
- **Project Language**: English

### Architecture Patterns
- **Modular Monorepo**: Three independent packages (core, server, optimizer) with clear separation of concerns
- **Abstract Base Classes**: Extensible framework using abstract base classes for metrics, synthesizers, and optimizers
- **Async/Await**: FastAPI-based server with non-blocking async patterns
- **Plugin Architecture**: Extensible callback system for monitoring and customization
- **Layered Architecture**: Clear separation between API layer, service layer, and core logic
- **Dependency Injection**: Configuration-based dependency management
- **Factory Pattern**: Model and metric instantiation through factory methods

### Testing Strategy
- **Framework**: Pytest >= 8.4.1 with comprehensive coverage reporting
- **Test Structure**: Unit tests for each package, integration tests for API endpoints
- **Coverage Requirements**: High coverage expectations for core functionality
- **Pre-commit Testing**: Automated test execution on commit via pre-commit hooks
- **Test Organization**: Mirror source code structure in tests directory
- **Async Testing**: pytest-asyncio for testing FastAPI endpoints
- **Mock Strategy**: Isolated testing with mocked external dependencies (OpenAI API)
- **Performance Testing**: Load testing for evaluation and synthesis workloads

### Git Workflow
- **Branch Strategy**: Feature branches with descriptive names (e.g., `add-opik-based-optimizer`)
- **Main Branch**: `main` for stable releases
- **Commit Style**: Conventional commits with clear, descriptive messages
- **Pre-commit Hooks**: Automated code quality checks before each commit
- **Code Review**: Pull request workflow for major changes
- **Release Process**: Tagged releases with version bumping
- **Merge Strategy**: Squash and merge for clean commit history

## Domain Context

### LLM Evaluation Domain
- **Target Users**: Data scientists, AI engineers, system developers working with LLMs
- **Evaluation Scenarios**: RAG systems, QA systems, content generation, classification tasks
- **Key Metrics**: Accuracy, relevance, faithfulness, context precision/recall, semantic similarity
- **Data Types**: Question-answer pairs, retrieved contexts, ground truth responses

### Built-in Evaluation Metrics
1. **Answer Correctness**: F1 score + semantic similarity evaluation
2. **Answer Similarity**: Cosine similarity using embeddings
3. **Answer Relevancy**: Relevance assessment to user input
4. **Faithfulness**: Factual consistency for RAG systems
5. **Context Recall**: Completeness evaluation of retrieved context
6. **Context Precision**: Retrieval quality assessment
7. **QA Quality**: Comprehensive QA evaluation framework
8. **RAG Runtime**: Runtime RAG system evaluation
9. **Custom Metrics**: User-defined evaluation logic framework

### Optimization Domain
- **TPE Algorithm**: Tree-structured Parzen Estimator for prompt optimization
- **Hyperparameter Tuning**: LLM model configuration optimization
- **Real-time Monitoring**: History callbacks for optimization progress tracking
- **Optimization Targets**: Both prompt parameters and model configurations

## Important Constraints

### Technical Constraints
- **Python 3.11+**: Minimum Python version requirement for modern language features
- **API Key Management**: OpenAI API keys required for LLM operations
- **Memory Usage**: Evaluation workloads can be memory-intensive for large datasets
- **Async Requirements**: FastAPI server requires async patterns for scalability
- **Type Safety**: Strict typing enforced across all packages

### Performance Constraints
- **API Rate Limits**: OpenAI API rate limiting considerations
- **Concurrent Processing**: Design for parallel evaluation and synthesis operations
- **Resource Allocation**: Optuna optimization can be computationally expensive

### Business Constraints
- **Production Readiness**: Platform designed for enterprise-grade deployments
- **Scalability Requirements**: Must handle evaluation of large LLM systems
- **Integration Flexibility**: Both library and API deployment options

## External Dependencies

### Critical Dependencies
- **OpenAI API**: Core dependency for LLM operations and embeddings
  - API key required for all LLM interactions
  - Rate limits apply for evaluation and synthesis operations
- **LangChain**: Integration layer for LLM orchestration
  - Provides standardized interface for different LLM providers

### Development Dependencies
- **GitHub**: Code repository and CI/CD platform
- **PyPI**: Package distribution for Python packages
- **Docker Hub**: Container registry for deployment images

### Optional Integrations
- **Custom Embedding Models**: Support for alternative embedding providers
- **Additional LLM Providers**: Extensible architecture for non-OpenAI models
- **Monitoring Systems**: Callback system for integration with external monitoring

### Infrastructure Requirements
- **Python Package Index**: Access to PyPI for dependency installation
- **Container Runtime**: Docker for deployment and development
- **Web Server**: Production deployment requires ASGI server (Uvicorn recommended)
