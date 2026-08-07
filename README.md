# Auto-Eval Research 🔬

Automated research pipeline for LLM Agent evaluation in car-control scenarios.

## What This Is

An auto-research portal that:
- 🔍 **Automatically searches** academic APIs (Semantic Scholar, arXiv) for relevant papers
- 📊 **Structures & summarizes** findings with LLM assistance
- 🚗 **Applies insights** to car-control agent evaluation design
- 🌐 **Publishes** results as a public research dashboard

## Quick Start

```bash
# 1. Run the research pipeline (curated data, no API calls)
python3 auto_research.py

# 2. Run with live API search (includes Semantic Scholar + arXiv)
python3 auto_research.py --api

# 3. Generate the website
python3 generate_site.py

# 4. Open in browser
open index.html
```

## Project Structure

```
auto_eval/
├── index.html              # Research dashboard (GitHub Pages)
├── papers.json             # Structured paper database
├── insights.json           # Cross-paper insights & gap analysis
├── auto_research.py        # Automated research pipeline
├── generate_site.py        # Website generator
└── README.md               # This file
```

## Research Topics Covered

| Topic | Focus |
|-------|-------|
| LLM Agent Evaluation | AgentBench, HELM, SWE-bench, GAIA, survey papers |
| Function Calling & Tool-Use | BFCL, ToolBench, API-Bank, ToolSandbox, τ²-bench, TRAJECT-Bench |
| Car & Embodied Agent | CAR-bench, CarMem, VehicleMemBench |
| Evaluation Methodology | StableToolBench, APIGen, MetaTool, rubric design |
| Chinese Voice Agent | Multilingual/Chinese agent evaluation |

## Data Sources

- [Semantic Scholar API](https://api.semanticscholar.org) — 220M+ papers, free
- [arXiv API](https://arxiv.org/help/api) — 2.5M+ preprints, free

## Methodology

Inspired by GPT Researcher, PaperQA2, STORM, and other auto-research tools.

Pipeline: **Multi-source retrieval → Dedup & merge → Structured summarization → Cross-paper insight extraction → Car-control application mapping → Website generation**

## License

MIT
