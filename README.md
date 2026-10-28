# Fabrilec Tender & Delivery Intelligence

An end-to-end AI and data platform that turns messy Moroccan public tender dossiers into a structured, searchable knowledge base, queryable through a hybrid-RAG AI agent.

Built during an end-of-year internship project (PFA) at **Fabrilec**, an electrical infrastructure company (HTB/HTA/BT, substations, rural electrification) operating in Morocco, Cameroon and Burkina Faso.

> No data was provided by the company. The project was built on **real public tenders** downloaded from [marchespublics.gov.ma](https://www.marchespublics.gov.ma).

---

## Problem

Public tender dossiers are slow to analyse: nested ZIP archives, native and scanned PDFs, legacy `.doc` files, and inconsistent naming. Finding a requirement, a technical specification or a price line means opening dozens of files by hand.

## Solution

A fully automated pipeline: drop in a tender ZIP and it is extracted, stored, transformed, indexed, and made available to an AI agent, a chat UI and a BI dashboard, with no manual steps.

```
Tender ZIP
   │
   ▼
Extraction (pdfplumber / OCR / Word COM)
   │
   ▼
PostgreSQL (raw_documents)
   │
   ▼
dbt (staging + marts, tested)
   │
   ▼
RAG index (ChromaDB + BM25, RRF fusion)
   │
   ├──► AI agent (SQL + document search tools)
   │       ├──► Streamlit chat UI
   │       └──► MCP server
   └──► Power BI dashboard
```

Orchestrated by **Apache Airflow** (Docker) with dynamic task mapping per dossier.

## Features

- **Type-aware extraction**
  - Native-text PDFs via `pdfplumber`
  - Scanned PDFs via OCR (Tesseract + poppler)
  - `.doc` files via MS Word automation (`win32com`)
  - Recursive handling of nested ZIPs
- **Idempotent loading** into PostgreSQL
- **dbt models** (staging + summary mart) with 16/16 passing tests
- **Hybrid retrieval**: semantic search (ChromaDB) + BM25 keyword search combined with Reciprocal Rank Fusion
- **Tool-calling agent** that chooses between SQL queries (`query_database`) and content search (`search_documents`)
- **One-click ingestion**: Streamlit page to upload a new tender ZIP and run the whole pipeline (extraction → Postgres → dbt → RAG reindex)
- **MCP server** (FastMCP, stdio) exposing the tools to MCP-compatible clients
- **Power BI dashboard**: KPI cards, stacked bar, donut, completeness table
- **Deployment**: Docker Compose for the pipeline, Kubernetes (Minikube) slice for PostgreSQL
- **Evaluation**: retrieval benchmark and LLM-as-judge scoring of answer faithfulness and correctness

## Results

| Retrieval strategy | Top-3 accuracy (14-question eval set) |
|---|---|
| Semantic only | 57.1% |
| **Hybrid (semantic + BM25, RRF)** | **85.7%** |

## Tech stack

| Layer | Tools |
|---|---|
| Language | Python |
| Extraction | pdfplumber, Tesseract, poppler, pywin32 |
| Storage | PostgreSQL |
| Transformation | dbt (dbt-postgres) |
| Orchestration | Apache Airflow, Docker Compose |
| Retrieval | ChromaDB, BM25 |
| LLM | Ollama (local), Groq-hosted models via OpenAI-compatible API |
| Interfaces | Streamlit, FastMCP, Power BI |
| Infra | Docker, Kubernetes (Minikube) |

## Project structure

```
.
├── src/fabrilec/
│   ├── extraction/      # document parsing, OCR
│   ├── loading/         # PostgreSQL loading
│   ├── rag/             # index building, hybrid retrieval
│   ├── agent/           # tool-calling agent
│   ├── mcp_server/      # FastMCP server
│   ├── pages/           # Streamlit pages (new tender upload)
│   ├── config.py        # anchored project paths
│   └── app.py           # Streamlit chat UI
├── airflow/
│   ├── dags/            # fabrilec_pipeline.py
│   └── docker-compose.yaml
├── fabrilec_dbt/        # dbt project
├── k8s/                 # Kubernetes manifests (Postgres)
└── tests/               # incl. agent security / prompt-injection tests
```

## Getting started

### Prerequisites

- Python 3.11+
- PostgreSQL
- Tesseract OCR and poppler (for scanned PDFs)
- Microsoft Word (Windows only, for `.doc` files)
- Docker (for Airflow)
- Ollama, or a Groq API key

### Installation

```bash
git clone https://github.com/cuervo0102/<repo-name>.git
cd <repo-name>
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file with your database and LLM settings (see `.env.example`).

### Run

```bash
# Build the RAG index
python -m src.fabrilec.rag.build_index

# Launch the chat UI
streamlit run src\fabrilec\app.py
```

Run all commands from the project root.

### Airflow pipeline

```bash
cd airflow
docker-compose up --build
```

The DAG chains extraction → Postgres → `dbt run` → RAG reindex automatically.

## Challenges solved

- Corrupted LibreOffice install, replaced by Word COM automation for `.doc` files
- Unstable local LLM inference, mitigated by moving to hosted OpenAI-compatible APIs
- Agent wrongly claiming a tender "doesn't exist" when content search found nothing, fixed by forcing a database lookup first

## Known limitations

- OCR can drop decimals in scanned tables
- `search_documents` has no tender-reference filter, so retrieval can be imprecise when a question's identifier doesn't appear in document text
- Document-type classification (CPS/CCTP/RC/bordereau) is filename-based and does not generalise to other naming schemes (e.g. KfW-style)
- Occasional LLM hallucinations (documented in the evaluation)

## Roadmap


- Multi-agent orchestration
- Monitoring and CI/CD
- Delay forecasting (Prophet / MLflow)

## Authors

- **Siham Essaji** ([@cuervo0102](https://github.com/cuervo0102))

