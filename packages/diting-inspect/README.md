# DiTing Inspect

DiTing Inspect is a powerful toolset designed for managing AI model evaluations, cases, and synthesis in a streamlined manner. It offers a user-friendly interface and robust functionalities to facilitate the evaluation and synthesis of AI models.

## Key Features

- **Model Management**: Efficiently organize and oversee various AI models.
- **Case Management**: Create, edit, and manage evaluation cases with ease.
- **Evaluation Tools**: Evaluate models against expected outputs and track performance metrics.
- **Synthesis Capabilities**: Generate new cases and insights based on existing data.

## Architecture Overview

The architecture of DiTing Inspect is designed to facilitate seamless interactions between different components:

```
          模型管理
           ↗     ↖
        Synthesis   Evaluate
         合成数据    算法评估
              ↘
               Case
              ↙     ↖
           输入输出   Tool
```

## Getting Started

To start the `diting-inspect` service, use the following commands:

**Backend**: 
```bash
uv run packages/diting-inspect/backend/diting_inspect/main.py
```

**Frontend**: 
```bash
cd packages/diting-inspect/frontend && pnpm install && pnpm dev
```

## Contribution Guidelines

1. Submit issues for bug reports or feature requests.
2. Fork the repository and submit pull requests.
3. Adhere to code standards: `make all`.

## License

This project is licensed under the [MIT License](LICENSE).

## Contact Us

For questions, please open an issue or contact the maintainers directly.
