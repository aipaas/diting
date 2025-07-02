# ⚖️ DiTing: LLM Application Evaluation Framework  

DiTing is a critical component for deploying large language model (LLM) applications into production, analogous to testing frameworks in traditional software development. This package provides a starting point for writing evaluations for your LLM applications, enabling you to build custom evals tailored to specific use cases.  

> • **寓意核心：** 正如《西游记》所描述，谛听拥有无与伦比的洞察力，能瞬
      间分辨世间万物（山川、生灵、神仙）的善恶贤愚。这**完美契合智能评估
      系统的核心目标**——深入分析数据、洞察指标本质、准确判断优劣好坏、识
      别潜在问题或价值。 
> 
> • **项目关联：** 系统就像“谛听”一样，伏在数据之上，运用智能（AI/算法）
      去“听”取指标背后的声音，“察”看其内在逻辑，最终做出精准的“鉴”别和
      “判”断，区分指标是“善”（优秀、有效、可靠）还是“恶”（劣质、无效、不
      可靠），是“贤”（关键、有潜力）还是“愚”（冗余、无价值）。


### 🚀 Quickstart  

#### 1. Installation  

```bash
pip install diting
```  

#### 2. Local Development Setup  

##### Environment Dependencies  
```bash
# Create a conda environment (Python 3.11 recommended)
conda create -c conda-forge -n diting python=3.11 uv
conda activate diting
```  

##### Code Repository Configuration  
```bash
# Configure repository (replace with your actual URL)
git config --global url."git@your-repo.com:".insteadof "https://your-repo.com/"
git clone git@your-repo.com:org/diting.git
cd diting
```  

##### Start Service  
```bash
uv run main.py  # Launch Restful server TODO
```  

#### 3. Project Formatting Standards  

```bash
make install # Install the package, dependencies, and pre-commit for local development
make all # Run code formatting, linting, static type checks, and tests with coverage report generation
```  


### 🌟 Core Features  

- **Standardized Evaluation Templates**：Pre-built solutions for common LLM tasks (text generation, QA, classification, etc.)  
- **Custom Extension Metric**：Extend evaluations by inheriting from `BaseMetric` abstract classes


### 📚 Usage Example  

Here’s a simple evaluation workflow:

```python
# TODO 
```

### 🛠️ Development Guide  

#### Environment Requirements  
- **Python Version**：3.10+  
- **Dependency Management**：Use `uv` tool (`pip install uv`)  

#### Project Structure  
```
diting/
├── docs
├── src
│   ├── diting
│   │   ├── callbacks       回调管理，内置的handler/manager等
│   │   ├── common          公共包，工具类等
│   │   ├── tasks           任务管理，包括执行/进度/日志/错误等管理机制
│   │   └── cases           评估数据，定义多种评估数据schema
│   │   ├── dataset         评估数据集，聚合testcases并暴露导入导出接口
│   │   ├── metrics         评估指标，定义多种维度的评估实现
│   │   ├── evaluate        评估接口，集合cases、metrics、tasks等模块实现评估执行
│   │   ├── models          模型客户端
│   │   ├── synthesizers    数据合成
│   └── support             第三方支持
└── tests
    ├── benchmarks
    ├── e2e
    └── unit
```  


### 🤝 Contribution Guidelines  

1. Submit issues for bug reports or feature requests  
2. Fork the repository and submit pull requests  
3. Adhere to code standards: `make all`  


### 📜 License  

This project is licensed under the [MIT License](LICENSE).  


### 📬 Contact Us  

For questions, please open an issue or contact the maintainers directly.