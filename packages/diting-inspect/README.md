# DiTing Inspect

DiTing Inspect is a comprehensive toolset for managing cases, models, and evaluations.

## Getting Started

To start the diting-inspect service, use the following command:

`docker-compose -f docker/docker-compose-diting-inspect.yml up -d`


## Development

To local dev, use the following command:

- **Backend**: `uv run packages/diting-inspect/backend/diting_inspect/main.py`
- **Frontend**: `cd packages/diting-inspect/frontend && pnpm install && pnpm dev`
