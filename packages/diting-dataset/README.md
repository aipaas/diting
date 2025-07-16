# 📊 diting-dataset: Dataset Management for DiTing Evaluation Framework  

`diting-dataset` is a core submodule of the **DiTing** framework, dedicated to dataset management for LLM application evaluation. It provides tools for creating, curating, and manipulating evaluation datasets, enabling seamless integration with DiTing's evaluation pipelines. This module bridges raw data, synthetic evaluation cases, and structured datasets to support robust LLM application testing.  


## 🎯 Core Purpose  

`diting-dataset` focuses on three key objectives:  
1. **Standardize Evaluation Data**: Define unified schemas for evaluation cases across LLM tasks (QA, generation, classification, etc.).  
2. **Simplify Data Synthesis**: Generate high-quality evaluation cases from raw corpora using automated tools.  
3. **Enable Flexible Dataset Management**: Support import/export, versioning, and customization of evaluation datasets.  


## 🔍 Key Components  

### 1. Dataset Module  
The `dataset` submodule acts as the central hub for managing evaluation data, with `EvaluationDataset` as its core class. It enables seamless handling of evaluation cases (stored as `LLMCase` objects) and supports integration with common data formats and tools.  

#### Core Features:  
- **Unified Data Structure**: Wraps a list of `LLMCase` objects to standardize evaluation data across tasks.  
- **Multi-format Compatibility**: Import/export data from/to JSONL, CSV, pandas DataFrames, and Hugging Face `Dataset` objects.  
- **Validation**: Ensures consistency in the structure of evaluation cases (via `LLMCase` schema validation).  
- **Track dataset versions and lineage**: Trace the origin of cases (e.g., which synthesizer generated them) and manage different iterations of the dataset.  


#### Key Methods of `EvaluationDataset`:  

| Method | Description |  
|--------|-------------|  
| `from_list(data)` | Create a dataset from a list of dictionaries (each dict represents an `LLMCase`). |  
| `from_jsonl(path)` | Load data from a JSONL file (one `LLMCase` per line). |  
| `from_pandas(dataframe)` | Convert a pandas DataFrame into an `EvaluationDataset`. |  
| `from_hf_dataset(hf_dataset)` | Import data from a Hugging Face `Dataset` object. |  
| `to_jsonl(path)` | Export the dataset to a JSONL file. |  
| `to_csv(path)` | Save the dataset as a CSV file. |  
| `to_hf_dataset()` | Convert to a Hugging Face `Dataset` for integration with NLP workflows. |  
| `to_pandas()` | Convert to a pandas DataFrame for data analysis. |  


#### Example Workflow:  
```python
from diting_dataset.dataset import EvaluationDataset

# Load from JSONL
dataset = EvaluationDataset.from_jsonl("qa_evaluation_cases.jsonl")
print(f"Loaded {len(dataset.testcases)} evaluation cases")

# Export to Hugging Face Dataset
hf_dataset = dataset.to_hf_dataset()
hf_dataset.push_to_hub("my-org/llm-qa-eval")  # Share with the community

# Convert to pandas for analysis
df = dataset.to_pandas()
print(df.head())  # Inspect first 5 cases
```

### 2. Corpus Module  
The `corpus` submodule handles the definition and generation of raw text corpora, which serve as the foundation for creating evaluation cases.  

#### Core Definitions:  
- **GraphBasedCorpus**: A structured representation of raw text data with the following attributes:  
  - `context`: List of background information strings (the core content of the corpus).  
  - `scenario`: Optional scenario description (e.g., "customer support", "medical consultation") to contextualize the corpus.  
  - `style`: Optional `QueryStyle` enum to define language style (e.g., `MISSPELLED`, `PERFECT_GRAMMAR`, `WEB_SEARCH_LIKE`).  
  - `length`: Optional `QueryLength` enum to specify text length (`LONG`, `MEDIUM`, `SHORT`).  
  - `persona`: Optional `Persona` (from `knowledge_graph.persona`) to simulate a specific speaker/writer’s identity.  
  - Additional custom attributes (via `model_config = ConfigDict(extra="allow")`).  

- **QueryStyle Enum**: Defines language styles for corpora:  
  - `MISSPELLED`: Contains typos or spelling errors.  
  - `PERFECT_GRAMMAR`: Formal, grammatically correct text.  
  - `POOR_GRAMMAR`: Informal or grammatically inconsistent text.  
  - `WEB_SEARCH_LIKE`: Short, keyword-focused text (e.g., search queries).  

- **QueryLength Enum**: Specifies corpus length:  
  - `LONG`: Extended text (e.g., paragraphs).  
  - `MEDIUM`: Moderate-length text (e.g., sentences).  
  - `SHORT`: Brief text (e.g., phrases or keywords).  


#### KnowledgeGraph Generators:  
`KnowledgeGraphCorpusGenerator` is an implementation of base class `BaseCorpusGenerator` for generating `BaseCorpus` instances. Its core workflow includes:  
1. Building a knowledge graph from raw data.  
2. Aggregating graph nodes to form clusters.  
3. Generating subgraphs from clusters.  
4. Constructing `BaseCorpus` objects from subgraphs.  


### 4. Knowledge Graph Module  
The `knowledge_graph` submodule structures domain knowledge to enhance evaluation case quality. It includes:  
-** Persona **: Defines simulated identities (e.g., "a tech support agent", "a student") to add realism to corpora.  
-** Schema Definitions **: Formalize entities (e.g., "person", "organization") and relationships (e.g., "works_at") for graph-based corpus generation.  
-** Graph Builders **: Tools to construct knowledge graphs from unstructured text, enabling structured corpus synthesis.  


## 🚀 Quickstart  

### 1. Installation  
```bash
# Install via pip (ensure Python 3.10+)
pip install diting-dataset

# Or install from source (for development)
git clone git@your-repo.com:org/diting.git
cd diting/packages/diting-dataset
uv install .  # Uses uv for fast dependency management
```  


### 2. Basic Workflow  

#### Workflow 1
##### Step 1: Generate a Corpus

```python
from diting_dataset.corpus import KnowledgeGraphCorpusGenerator
from diting_dataset.knowledge_graph import (
  KnowledgeGraph,
  Node,
  NodeType,
  default_transforms,
  apply_transforms
)
from diting_core.models.llms.factory import llm_factory
from diting_core.models.embeddings.factory import embedding_factory

# Prepare KnowledgeGraph
from langchain_community.document_loaders import DirectoryLoader
path = "markdown/"
loader = DirectoryLoader(path, glob="**/*.md")
documents = await loader.aload()
nodes: List[Node] = []
for doc in documents:
    node = Node(
        type=NodeType.DOCUMENT,
        properties={
            "page_content": doc.page_content,
            "document_metadata": doc.metadata,  # type: ignore
        },
    )
    nodes.append(node)

kg = KnowledgeGraph(nodes=nodes)
# apply transforms and update the knowledge graph
llm = llm_factory()
embedding_model=embedding_factory()
transforms = default_transforms(
    documents=list(documents),
    llm=llm,
    embedding_model=embedding_model
)
apply_transforms(kg, transforms)
# Using a KnowledgeGraph corpus generator
generator = KnowledgeGraphCorpusGenerator(knowledge_graph=kg,llm=llm)
# Generate 5 knowledge-graph-related corpora
corpora = await generator.generate_corpora(num_corpora=5)
```

##### Step 2: Synthesize Evaluation Cases

```python
from diting_core.synthesis import QASynthesizer
from diting_core.models.llms.factory import llm_factory

# Initialize with an LLM client
synthesizer = QASynthesizer(model=llm_factory())

# Generate QA pairs
cases = [await synthesizer.apply(corpus) for corpus in corpora]
```

##### Step 3: Build a Dataset  
```python
from diting_dataset.dataset import EvaluationDataset

# Create a dataset and validate cases
dataset = EvaluationDataset(testcases=cases)

# Export to JSON
dataset.to_jsonl("science_qa_dataset.json")
```

#### Workflow 2
```python
from diting_dataset.dataset import DataSetGenerator
from diting_core.models.llms.factory import llm_factory
from diting_core.models.embeddings.factory import embedding_factory

# Create a dataset generator
llm = llm_factory()
embedding_model = embedding_factory()
ds_generator = DataSetGenerator(llm=llm, embedding_model=embedding_model)

# Create a dataset and validate cases by dataset generator
path = "markdown/"
dataset = await ds_generator.generate_dataset_from_docs(
    [path], [], verbose=True
)

# Export to JSON
dataset.to_jsonl("science_qa_dataset.json")
```

## 🛠️ Development Guide  

### Environment Setup  
-** Python Version **: 3.10+  
-** Dependency Management **: Use `uv` (install with `pip install uv`).  

### Project Structure  
```
diting-dataset/
├── dataset/                  # Core dataset management
│   ├── dataset.py            # class for EvaluationDataset
│   └── dataset_generator.py  # Task-specific generator for EvaluationDataset
├── synthesis/                # Evaluation case synthesis
│   ├── base_synthesizer.py   # BaseSynthesizer abstract class
│   └── qa/                   # QA-specific synthesizer
├── corpus/                   # Corpus generation
│   ├── base_corpus.py        # BaseCorpus and BaseCorpusGenerator
│   └── default/              # Default corpus generator implement by knowledge_graph
└── knowledge_graph/          # Knowledge graph integration
    ├── schema.py             # Entity/relationship definitions
    └── transforms/           # Tools to construct knowledge graphs
```  


## 🔄 Integration with DiTing  

`diting-dataset` seamlessly works with other DiTing modules:  
- Generated datasets can be directly passed to `diting-core` for evaluation using metrics like accuracy or relevance.  
- Custom synthesizers/processors can leverage `diting-core`’s LLM clients for consistent text generation.  
- Corpus generators use `diting-core`’s callback managers (via `new_group`) to track progress and logs during generation.  


## 📄 License  
This module is part of the DiTing project and is licensed under the [MIT License](LICENSE).  


For more details, see the main [DiTing documentation](https://your-repo.com/org/diting) or contact the maintainers.