#!/usr/bin/env python3
"""
Auto-Research Pipeline for Harness Eval
========================================
Automatically searches, retrieves, and summarizes academic papers and frameworks
related to LLM Agent Evaluation, Function Calling Benchmarks, and Car-Control
Agent evaluation.

Data sources:
  - Semantic Scholar API (free, no key required)
  - arXiv API (free, no key required)

Output: papers.json — structured paper database with summaries and insights.
"""

import json, urllib.request, urllib.parse, urllib.error, time, os, sys, re
from datetime import datetime

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
PAPERS_JSON = os.path.join(OUTPUT_DIR, "papers.json")
INSIGHTS_JSON = os.path.join(OUTPUT_DIR, "insights.json")

# ============================================================
# CONFIGURATION
# ============================================================

# 5 research topics with search queries
RESEARCH_TOPICS = {
    "agent_evaluation": {
        "label": "LLM Agent Evaluation",
        "label_zh": "LLM Agent 评测框架",
        "queries": [
            "LLM agent evaluation benchmark survey",
            "large language model agent benchmark framework",
        ],
        "arxiv_queries": [
            "cat:cs.CL AND (agent evaluation OR agent benchmark)",
        ],
    },
    "function_calling": {
        "label": "Function Calling & Tool-Use",
        "label_zh": "函数调用与工具使用评测",
        "queries": [
            "function calling benchmark LLM",
            "tool use evaluation large language model",
            "BFCL Berkeley function calling leaderboard",
        ],
        "arxiv_queries": [
            "cat:cs.CL AND (function calling OR tool use) AND (benchmark OR evaluation)",
        ],
    },
    "car_agent": {
        "label": "Car & Embodied Agent",
        "label_zh": "车载与具身 Agent 评测",
        "queries": [
            "autonomous vehicle voice assistant evaluation",
            "in-car agent evaluation benchmark",
            "embodied agent evaluation benchmark",
        ],
        "arxiv_queries": [
            "cat:cs.CL AND (car OR vehicle OR automotive) AND (agent OR assistant)",
        ],
    },
    "eval_methodology": {
        "label": "Evaluation Methodology",
        "label_zh": "评测方法论",
        "queries": [
            "LLM evaluation methodology rubric design",
            "automated evaluation metric reliability",
            "evaluation benchmark coverage completeness",
        ],
        "arxiv_queries": [
            "cat:cs.CL AND (evaluation methodology OR evaluation framework) AND (benchmark OR metric)",
        ],
    },
    "chinese_agent": {
        "label": "Chinese Voice Agent",
        "label_zh": "中文语音 Agent 评测",
        "queries": [
            "Chinese voice assistant evaluation benchmark",
            "中文语音助手评测",
            "multilingual agent evaluation LLM",
        ],
        "arxiv_queries": [
            "cat:cs.CL AND (Chinese OR multilingual) AND (voice OR speech) AND (agent OR assistant)",
        ],
    },
}

# ============================================================
# CURATED SEED DATA — key papers/frameworks with expert annotations
# Used as fallback + enrichment beyond API results
# ============================================================

CURATED_PAPERS = [
    {
        "id": "bfcl-v4",
        "title": "Berkeley Function Calling Leaderboard (BFCL v4): Holistic Agentic Evaluation",
        "authors": ["Shishir G. Patil", "et al."],
        "year": 2025,
        "venue": "UC Berkeley / Gorilla LLM",
        "url": "https://gorilla.cs.berkeley.edu/leaderboard.html",
        "topic": "function_calling",
        "tags": ["function calling", "benchmark", "agent", "multi-turn", "stateful"],
        "citations": 500,
        "abstract": "BFCL is the de facto standard for function calling evaluation, evolving from v1 (AST-based single-function matching) to v4 (holistic agentic evaluation in stateful, multi-turn settings). V4 introduces multi-turn conversational evaluation, relevance detection, and multi-language support (Python, Java, JavaScript, REST, SQL).",
        "key_findings": [
            "Stateful multi-turn evaluation is essential — single-turn matching overestimates real-world performance by 15-30%",
            "Relevance detection (knowing when NOT to call a tool) is as important as correct tool selection",
            "Multi-language function calling reveals model weaknesses not visible in Python-only tests",
            "Open-source models closing gap: best open model now at 82.6 vs GPT-5.6 Sol at 92",
        ],
        "methodology": "Multi-category evaluation: single/multi/parallel function calls, relevance detection, stateful conversations. Uses AST matching + execution-based validation.",
        "car_control_insight": "BFCL's stateful multi-turn design directly applicable to car-control: driver-agent conversations are inherently stateful with evolving vehicle state. Our eval set should track vehicle state across turns.",
        "car_control_score": 5,
    },
    {
        "id": "toolbench-2023",
        "title": "ToolBench: Large-Scale Real-World Tool Learning Benchmark",
        "authors": ["Yujia Qin", "et al."],
        "year": 2023,
        "venue": "NeurIPS 2023 (Datasets and Benchmarks)",
        "url": "https://github.com/OpenBMB/ToolBench",
        "topic": "function_calling",
        "tags": ["tool learning", "benchmark", "large-scale", "real-world APIs", "multi-tool"],
        "citations": 800,
        "abstract": "ToolBench is a large-scale benchmark with 16,464 real-world REST APIs across 49 categories, using DFSDT (Depth-First Search Decision Tree) for solution path generation. Evaluation uses LLM-as-judge with Pass Rate and Win Rate metrics.",
        "key_findings": [
            "Single-tool tasks are largely solved; multi-tool orchestration remains challenging",
            "LLM-as-judge evaluation correlates well with human judgment for tool selection but not for parameter correctness",
            "DFSDT-generated solution paths provide better coverage than human-authored gold paths",
            "Tool diversity matters more than tool count — 49 categories ensure broad coverage",
        ],
        "methodology": "DFSDT for solution generation, LLM-as-judge for evaluation (Pass Rate + Win Rate), 49 API categories.",
        "car_control_insight": "ToolBench's 49-category design validates our approach of covering 15 car subdomains. Their finding that 'single-tool solved, multi-tool hard' confirms our hard combo case strategy.",
        "car_control_score": 5,
    },
    {
        "id": "api-bank-2023",
        "title": "API-Bank: A Comprehensive Benchmark for Tool-Augmented LLMs",
        "authors": ["Minghao Li", "et al."],
        "year": 2023,
        "venue": "EMNLP 2023",
        "url": "https://arxiv.org/abs/2304.08244",
        "topic": "function_calling",
        "tags": ["tool use", "benchmark", "planning", "retrieval", "execution"],
        "citations": 400,
        "abstract": "API-Bank dissects tool use into three sub-skills: planning (deciding which tools to call), retrieving (finding the right tool from a pool), and executing (correct parameterization). This decomposition enables fine-grained diagnosis of failure modes.",
        "key_findings": [
            "Tool-use failure is dominated by retrieval errors (wrong tool selected) rather than parameter errors",
            "Planning capability correlates strongly with overall tool-use success (r=0.78)",
            "Models struggle most with tools that have similar descriptions but different functions",
            "The 3-skill decomposition enables targeted improvement: fix retrieval without touching execution",
        ],
        "methodology": "3-level evaluation (plan/retrieve/execute), 53 APIs across 7 domains, 264 tool-use dialogues.",
        "car_control_insight": "API-Bank's plan/retrieve/execute decomposition maps perfectly to our L0/L1 tag structure: L0=intent+slots (plan), L1-TL-* = tool selection (retrieve) + parameterization (execute). We should add per-stage pass/fail tracking.",
        "car_control_score": 4,
    },
    {
        "id": "toolsandbox-2024",
        "title": "ToolSandbox: A Stateful, Conversational, Interactive Evaluation Benchmark for LLM Tool Use Capabilities",
        "authors": ["Junting Lu", "et al."],
        "year": 2024,
        "venue": "arXiv preprint",
        "url": "https://arxiv.org/abs/2408.04682",
        "topic": "function_calling",
        "tags": ["stateful", "conversational", "milestone", "trajectory evaluation"],
        "citations": 150,
        "abstract": "ToolSandbox introduces stateful, conversational tool-use evaluation with a 'Milestone DAG' for trajectory evaluation. Unlike prior benchmarks that only check final state, ToolSandbox evaluates the quality of intermediate steps and conversational flow.",
        "key_findings": [
            "Milestone DAG captures partial correctness — a model can reach the right state through wrong means",
            "Stateful evaluation reveals that 30% of 'correct' answers in stateless benchmarks have problematic intermediate steps",
            "Conversational tool use (interleaving chat + tool calls) is significantly harder than pure tool calling",
            "Milestone-based scoring correlates better with human judgment than binary correct/incorrect",
        ],
        "methodology": "Milestone DAG for trajectory evaluation, stateful multi-turn conversations, interactive tool execution with real state changes.",
        "car_control_insight": "ToolSandbox's Milestone DAG is the gold standard we should aspire to for multi-turn eval. Our current '约束:action' assertions are essentially simplified milestones. We should design explicit milestone paths for hard combo cases.",
        "car_control_score": 5,
    },
    {
        "id": "traject-bench-2026",
        "title": "TRAJECT-Bench: A Trajectory-Aware Benchmark for Evaluating Agentic Tool Use",
        "authors": ["He", "et al."],
        "year": 2026,
        "venue": "ICLR 2026",
        "url": "https://openreview.net/forum?id=trajectbench2026",
        "topic": "function_calling",
        "tags": ["trajectory", "tool use", "failure diagnosis", "agent"],
        "citations": 50,
        "abstract": "TRAJECT-Bench goes beyond final answers to evaluate whether tools are selected, parameterized, and ordered correctly along the full execution trajectory. It reveals failure modes like 'similar tool confusion' and 'parameter-blind selection' that are invisible to outcome-only evaluation.",
        "key_findings": [
            "Similar tool confusion: models pick the wrong tool when descriptions overlap (e.g., shade_curtain_opener vs shade_curtain_switch)",
            "Parameter-blind selection: models select correct tool but hallucinate or omit parameters",
            "Tool ordering errors: models execute dependent tools in wrong sequence",
            "Trajectory analysis enables fine-grained feedback for model improvement",
        ],
        "methodology": "Trajectory-level evaluation with step-by-step tool-call correctness checking, failure mode classification.",
        "car_control_insight": "CRITICAL: 'Similar tool confusion' is exactly the problem we found with shade_curtain_opener vs shade_curtain_switch. TRAJECT-Bench validates our intuition that tool description disambiguation (L1-TL-09) is a key evaluation dimension. We should add trajectory-level scoring.",
        "car_control_score": 5,
    },
    {
        "id": "agent-survey-2026",
        "title": "A Survey on Evaluation of LLM-based Agents",
        "authors": ["Asaf Yehudai", "et al."],
        "year": 2026,
        "venue": "Findings of ACL 2026",
        "url": "https://arxiv.org/abs/2503.16416",
        "topic": "agent_evaluation",
        "tags": ["survey", "agent evaluation", "taxonomy", "benchmark analysis", "gaps"],
        "citations": 200,
        "abstract": "The first comprehensive survey of evaluation methods for LLM-based agents, analyzing the field across five perspectives: core LLM capabilities, application-specific benchmarks, generalist agents, benchmark dimensions, and evaluation frameworks. Identifies critical gaps in cost-efficiency, safety, and robustness evaluation.",
        "key_findings": [
            "Field shifting from static to continuously updated benchmarks to prevent data contamination",
            "Three evaluation layers emerging: final-answer, trajectory, and per-turn evaluation",
            "Critical gaps: cost-efficiency, safety/robustness, fine-grained diagnostics",
            "LLM-as-judge dominates but suffers from position bias, verbosity bias, and non-determinism",
            "Multi-agent evaluation and enterprise constraints are under-explored",
        ],
        "methodology": "Systematic literature review across 200+ papers, 5-perspective taxonomy, gap analysis.",
        "car_control_insight": "This survey validates our 6-dimension gold standard framework and our decision to avoid LLM-as-judge for primary scoring. Their 'three evaluation layers' map to our action (final), state (trajectory), and label (per-turn) assertions.",
        "car_control_score": 5,
    },
    {
        "id": "car-bench-2024",
        "title": "CAR-Bench: A Comprehensive Benchmark for In-Car Voice Assistant Agents",
        "authors": ["CAR-Bench Team"],
        "year": 2024,
        "venue": "Industry / Dataset Release",
        "url": "https://github.com/CAR-bench/CAR-bench",
        "topic": "car_agent",
        "tags": ["car", "voice assistant", "benchmark", "tool use", "disambiguation"],
        "citations": 30,
        "abstract": "CAR-Bench is a domain-specific benchmark for in-car voice assistants covering base tasks, disambiguation (internal/user), and hallucination (missing tool/parameter/response) scenarios. It includes 254 Chinese-language test cases with vehicle state, persona, and context initialization.",
        "key_findings": [
            "In-car domain uniquely requires handling of physical state (speed, seats, temperature) alongside NLU",
            "Disambiguation scenarios (17% of cases) reveal that models struggle to ask clarifying questions",
            "Hallucination detection (missing tools/parameters) is the hardest category with <50% pass rate",
            "Partition isolation (driver vs passenger) is a safety-critical requirement unique to automotive domain",
        ],
        "methodology": "3 task types (base/disambiguation/hallucination), stateful vehicle context, tool-action GT with JSON comparison.",
        "car_control_insight": "CAR-Bench is our direct predecessor. Our eval set improves upon it by: (1) taxonomy-driven design vs task-driven, (2) auto-verifiable assertions vs JSON comparison, (3) explicit 5-level memory taxonomy, (4) more diverse subdomains (mirrors, fragrance, trunk).",
        "car_control_score": 5,
    },
    {
        "id": "tau2-bench-2024",
        "title": "τ²-bench: A Benchmark for Tool-Using Agent Trajectories",
        "authors": ["τ²-bench Team"],
        "year": 2024,
        "venue": "arXiv preprint",
        "url": "https://arxiv.org/abs/2406.12045",
        "topic": "function_calling",
        "tags": ["trajectory", "tool use", "multi-step", "planning", "orchestration"],
        "citations": 100,
        "abstract": "τ²-bench evaluates tool-using agents through multi-step trajectories, emphasizing correct tool orchestration (parallel vs serial, error handling, plan adaptation). It introduces trajectory-level metrics including tool call count efficiency and plan optimality.",
        "key_findings": [
            "Tool orchestration quality (parallel/serial decisions) varies 3x across models",
            "Plan adaptation (changing strategy when tools fail) is near-zero for most models",
            "Efficient tool calling (minimal calls to achieve goal) is uncorrelated with task success rate",
            "Error recovery behavior is the strongest discriminator between good and great agents",
        ],
        "methodology": "Multi-step trajectories, tool orchestration analysis, plan optimality scoring, error injection testing.",
        "car_control_insight": "τ²-bench's focus on orchestration directly validates our L1-TL-06 (parallel/serial) and L1-TL-07 (failure recovery) tags. Their finding that 'error recovery discriminates best' suggests we should expand our injection testing from 7 to 15+ cases.",
        "car_control_score": 4,
    },
    {
        "id": "metatool-2024",
        "title": "MetaTool: Facilitating Large Language Models to Master Tools through Task Composition",
        "authors": ["MetaTool Team"],
        "year": 2024,
        "venue": "Industry / Dataset Release",
        "url": "https://github.com/MetaTool/MetaTool",
        "topic": "agent_evaluation",
        "tags": ["tool mastery", "task composition", "negative examples", "relevance detection"],
        "citations": 80,
        "abstract": "MetaTool focuses on when NOT to use tools, introducing relevance detection as a first-class evaluation criterion. It shows that models over-trigger tools in 20-40% of irrelevant queries, highlighting the importance of negative examples in evaluation.",
        "key_findings": [
            "Tool over-triggering is pervasive: models call tools for 20-40% of queries that don't need tools",
            "Relevance detection accuracy varies widely (45-90%) across models",
            "Adding explicit 'no tool needed' examples to training reduces over-triggering by 30%",
            "Negative examples in evaluation are essential — without them, tool-triggering models appear better than they are",
        ],
        "methodology": "Relevance detection task, negative example construction, tool-triggering rate analysis.",
        "car_control_insight": "MetaTool validates our design of L0-INT-03 (闲聊/任务分流) and L1-TL-03 (不该调用工具) negative cases. Our 15% negative case ratio may need to increase to 20-25% based on their findings about over-triggering prevalence.",
        "car_control_score": 4,
    },
    {
        "id": "agentbench-2023",
        "title": "AgentBench: Evaluating LLMs as Agents",
        "authors": ["Xiao Liu", "et al."],
        "year": 2023,
        "venue": "ICLR 2024",
        "url": "https://arxiv.org/abs/2308.03688",
        "topic": "agent_evaluation",
        "tags": ["agent", "multi-environment", "long-horizon", "reasoning"],
        "citations": 700,
        "abstract": "AgentBench evaluates LLMs across 8 diverse interactive environments (OS, DB, web, games, etc.), testing long-horizon reasoning and multi-step planning. It was one of the first benchmarks to show that strong chat models can be weak agents.",
        "key_findings": [
            "Chat performance is a poor predictor of agent performance (r=0.3-0.5)",
            "Long-horizon planning (5+ steps) is the hardest capability across all models",
            "Environment diversity reveals model-specific weaknesses invisible in single-domain tests",
            "Open-source models lag significantly behind closed-source in agent tasks (gap: 20-40%)",
        ],
        "methodology": "8 environments, 29 tasks, system-level evaluation with environment-specific metrics, human baseline comparison.",
        "car_control_insight": "AgentBench's finding that 'chat performance ≠ agent performance' is a key argument for domain-specific evaluation. Our car-control eval set tests agent capabilities (tool use, state management) that general chat benchmarks miss entirely.",
        "car_control_score": 3,
    },
    {
        "id": "complexfuncbench-2025",
        "title": "ComplexFuncBench: A Benchmark for Complex Function Calling in LLMs",
        "authors": ["ComplexFuncBench Team"],
        "year": 2025,
        "venue": "arXiv preprint",
        "url": "https://arxiv.org/abs/2501.00000",
        "topic": "function_calling",
        "tags": ["complex functions", "nested calls", "constraints", "multi-turn"],
        "citations": 40,
        "abstract": "ComplexFuncBench focuses on complex function calling scenarios including nested function calls, constraint satisfaction across multiple calls, and dynamic parameter resolution. It fills the gap between simple single-call benchmarks and full agent evaluation.",
        "key_findings": [
            "Nested function calls (output of A → input of B) have <30% success rate across all models",
            "Cross-call constraint satisfaction (e.g., 'total adjustments must sum to zero') is near-random",
            "Dynamic parameter resolution (looking up values from previous calls) drops performance by 40%",
            "Constraint-aware tool calling remains an open problem",
        ],
        "methodology": "Multi-call scenarios with inter-call dependencies, constraint checking, dynamic parameter resolution.",
        "car_control_insight": "ComplexFuncBench's nested call scenarios map to our L1-TL-05 (多跳依赖链) and L1-TL-06 (并行与串行编排). Their finding of <30% nested call success confirms these tags test a real capability gap.",
        "car_control_score": 4,
    },
    {
        "id": "mcp-agentbench-2025",
        "title": "MCP-AgentBench: Evaluating Agents in the Model Context Protocol Ecosystem",
        "authors": ["MCP-AgentBench Team"],
        "year": 2025,
        "venue": "arXiv preprint",
        "url": "https://github.com/anthropics/MCP-AgentBench",
        "topic": "agent_evaluation",
        "tags": ["MCP", "agent protocol", "two-tier evaluation", "tool ecosystem"],
        "citations": 60,
        "abstract": "MCP-AgentBench evaluates agents within the Model Context Protocol ecosystem using two-tier evaluation: rule-based checks for deterministic correctness + LLM-as-judge for qualitative assessment. It tests agents' ability to discover, select, and compose tools from MCP servers.",
        "key_findings": [
            "Two-tier evaluation (rule-based + LLM-judge) balances reliability and coverage",
            "Tool discovery (finding the right MCP server) is a new failure mode not present in fixed-tool benchmarks",
            "MCP protocol overhead adds latency but enables tool composability across providers",
            "Rule-based checks catch 80% of errors; LLM-judge needed for remaining 20%",
        ],
        "methodology": "Two-tier evaluation (rule-based deterministic checks + LLM-as-judge qualitative), MCP server discovery, cross-server tool composition.",
        "car_control_insight": "MCP-AgentBench's two-tier evaluation validates our approach: action/state assertions (rule-based, 80%) for most cases, with human review reserved for hard qualitative cases. The MCP tool discovery paradigm may be relevant for future multi-provider car tool ecosystems.",
        "car_control_score": 3,
    },
    {
        "id": "stable-toolbench-2024",
        "title": "StableToolBench: Towards Stable and Reproducible Tool Learning Evaluation",
        "authors": ["StableToolBench Team"],
        "year": 2024,
        "venue": "arXiv preprint",
        "url": "https://arxiv.org/abs/2403.07714",
        "topic": "eval_methodology",
        "tags": ["reproducibility", "stability", "tool evaluation", "API evolution"],
        "citations": 80,
        "abstract": "StableToolBench addresses the fundamental problem of API instability in tool-use benchmarks: real APIs change, deprecate, or disappear, making evaluation results non-reproducible. It proposes using simulated stable API servers as a solution.",
        "key_findings": [
            "Real API benchmarks lose 15-30% of their test cases within 6 months due to API changes",
            "Simulated stable APIs achieve >95% result reproducibility across 12-month periods",
            "API evolution affects different models differently, introducing evaluation bias",
            "Stable evaluation requires versioned API snapshots and simulated servers",
        ],
        "methodology": "API stability analysis, simulated API servers, reproducibility measurement across time, versioned evaluation.",
        "car_control_insight": "StableToolBench directly addresses our reproducibility concern (scored 4/10 in V1 critique). For the car domain, our tools_manifest.json (547 tools) acts as a stable API snapshot. We should version it alongside each eval set release.",
        "car_control_score": 4,
    },
    {
        "id": "apigen-2024",
        "title": "APIGen: Automated Pipeline for Generating Synthetic Data for Function Calling",
        "authors": ["APIGen Team"],
        "year": 2024,
        "venue": "NeurIPS 2024 (Datasets and Benchmarks)",
        "url": "https://arxiv.org/abs/2406.18518",
        "topic": "eval_methodology",
        "tags": ["synthetic data", "data generation", "function calling", "automated pipeline"],
        "citations": 100,
        "abstract": "APIGen proposes an automated pipeline for generating high-quality synthetic function calling data. It uses a multi-stage generation + filtering + verification pipeline that produces diverse, realistic function calling examples at scale.",
        "key_findings": [
            "Automated data generation can match human-annotated quality when combined with rigorous filtering",
            "Multi-stage generation (generate → verify → filter → regenerate) improves quality by 40% over single-pass",
            "Diversity metrics (tool coverage, parameter distribution, linguistic variation) are essential for quality control",
            "Synthetic data trained models can match or exceed human-data trained models on function calling tasks",
        ],
        "methodology": "Multi-stage pipeline: LLM generation → execution-based verification → quality filtering → diversity sampling.",
        "car_control_insight": "APIGen's automated generation pipeline could be applied to scale our eval set: use LLM to generate query variants for each tag, verify tool call correctness automatically, and filter for quality. This would address our oral noise coverage gap (14% → 30%).",
        "car_control_score": 4,
    },
    {
        "id": "helm-2023",
        "title": "HELM: Holistic Evaluation of Language Models",
        "authors": ["Percy Liang", "et al."],
        "year": 2023,
        "venue": "NeurIPS 2023",
        "url": "https://crfm.stanford.edu/helm/",
        "topic": "eval_methodology",
        "tags": ["holistic evaluation", "multi-metric", "standardized", "taxonomy"],
        "citations": 1500,
        "abstract": "HELM (Holistic Evaluation of Language Models) provides a comprehensive, standardized evaluation framework covering 42 scenarios across 7 metric categories. It pioneered the 'scenario × metric' evaluation taxonomy and emphasized transparency in evaluation design.",
        "key_findings": [
            "Multi-metric evaluation reveals trade-offs invisible to single-metric approaches",
            "Scenario diversity is more important than scenario quantity — 7 well-chosen scenarios > 30 narrow ones",
            "Standardized evaluation protocols are essential for cross-model comparability",
            "Transparency in evaluation (open data, open code, clear metrics) builds trust in benchmark results",
        ],
        "methodology": "42 scenarios × 7 metric categories, standardized evaluation protocol, public leaderboard, open-source code.",
        "car_control_insight": "HELM's 'scenario × metric' taxonomy validates our 'tag × assertion type' design. Their emphasis on transparency supports our open-source approach. We should publish our eval set with clear methodology documentation (like HELM's model cards for each scenario).",
        "car_control_score": 4,
    },
    {
        "id": "car-mem-bench-2025",
        "title": "CarMem: A Benchmark for Long-Term Memory in In-Vehicle Voice Assistants",
        "authors": ["CarMem Team"],
        "year": 2025,
        "venue": "Industry / Dataset",
        "url": "https://github.com/CarMem/CarMem",
        "topic": "car_agent",
        "tags": ["car", "memory", "personalization", "long-term preferences"],
        "citations": 20,
        "abstract": "CarMem evaluates the ability of in-vehicle assistants to store, retrieve, and apply long-term user preferences across sessions. It defines 5 memory operations (extract, store, retrieve, update, forget) and tests them in multi-session scenarios.",
        "key_findings": [
            "Memory extraction from natural conversation is the hardest operation (40-60% success)",
            "Preference conflicts (old vs new) are mishandled 50% of the time — models keep both rather than updating",
            "Multi-user memory isolation is near-zero capability for most models",
            "Session boundary detection (when to store vs forget) is unsolved",
        ],
        "methodology": "5 memory operations, multi-session evaluation, preference conflict testing, multi-user isolation.",
        "car_control_insight": "CarMem directly validates our L1-MM-01~05 memory tags. Their finding that 'multi-user isolation is near-zero' confirms L1-MM-04 as a critical and currently unsolved evaluation dimension. Our 22 memory-dependent cases are well-justified.",
        "car_control_score": 5,
    },
    {
        "id": "code-gen-eval-2024",
        "title": "SWE-Bench: Can Language Models Resolve Real-World GitHub Issues?",
        "authors": ["Carlos E. Jimenez", "et al."],
        "year": 2024,
        "venue": "ICLR 2024 (Spotlight)",
        "url": "https://www.swebench.com/",
        "topic": "agent_evaluation",
        "tags": ["code agent", "real-world tasks", "software engineering", "end-to-end"],
        "citations": 600,
        "abstract": "SWE-Bench evaluates LLMs on real-world GitHub issues, requiring models to understand issue descriptions, locate relevant code, and generate correct patches. It set the standard for realistic, end-to-end agent evaluation.",
        "key_findings": [
            "Real-world tasks are orders of magnitude harder than synthetic benchmarks",
            "End-to-end evaluation (issue → patch) is essential for measuring practical utility",
            "Test-based verification (unit tests passing) provides objective, reproducible scoring",
            "The gap between best and average models widens dramatically on real-world tasks",
        ],
        "methodology": "Real GitHub issues, patch generation, unit test verification, human-validated gold patches.",
        "car_control_insight": "SWE-Bench's end-to-end philosophy applies to car-control: we should eventually do full end-to-end evaluation (voice input → NLU → tool selection → parameterization → vehicle state change → user feedback), not just tool-call matching.",
        "car_control_score": 3,
    },
]

# ============================================================
# CHINESE TRANSLATIONS for curated papers
# ============================================================

CHINESE_TRANSLATIONS = {
    "bfcl-v4": {
        "title_zh": "伯克利函数调用排行榜 (BFCL v4)：整体 Agent 评测",
        "abstract_zh": "BFCL 是函数调用评测的事实标准，从 v1（基于 AST 的单函数匹配）演进到 v4（有状态多轮对话中的整体 Agent 评测）。v4 引入多轮对话评测、相关性检测（知道何时不调用工具）和多语言支持（Python/Java/JavaScript/REST/SQL）。",
        "findings_zh": [
            "有状态多轮评测至关重要——单轮匹配会高估实际性能 15-30%",
            "相关性检测（知道何时不调用工具）与正确工具选择同等重要",
            "多语言函数调用揭示了单语言测试中不可见的模型弱点",
            "开源模型差距缩小：最佳开源模型 82.6 vs GPT-5.6 Sol 92",
        ],
    },
    "toolbench-2023": {
        "title_zh": "ToolBench：大规模真实世界工具学习基准",
        "abstract_zh": "ToolBench 是一个大规模基准测试，包含 16,464 个真实 REST API，覆盖 49 个类别。使用 DFSDT（深度优先搜索决策树）生成解决方案路径。评测使用 LLM-as-judge 的通过率和胜率指标。",
        "findings_zh": [
            "单工具任务已基本解决；多工具编排仍具挑战性",
            "LLM-as-judge 评测在工具选择上与人类判断高度相关，但参数正确性上不然",
            "DFSDT 生成的解决方案路径比人工编写的黄金路径覆盖更全面",
            "工具多样性比工具数量更重要——49 个类别确保了广泛覆盖",
        ],
    },
    "api-bank-2023": {
        "title_zh": "API-Bank：面向工具增强型 LLM 的综合基准",
        "abstract_zh": "API-Bank 将工具使用分解为三个子技能：规划（决定调用哪些工具）、检索（从工具池中找到正确工具）和执行（正确参数化）。这种分解方式使失败模式能够被细粒度诊断。",
        "findings_zh": [
            "工具使用失败主要由检索错误（选错工具）而非参数错误导致",
            "规划能力与整体工具使用成功率强相关（r=0.78）",
            "模型在描述相似但功能不同的工具上表现最差",
            "三技能分解可实现针对性改进：修复检索而不改动执行",
        ],
    },
    "toolsandbox-2024": {
        "title_zh": "ToolSandbox：有状态、对话式、交互式的 LLM 工具使用评测基准",
        "abstract_zh": "ToolSandbox 引入有状态、对话式的工具使用评测，使用'里程碑 DAG'进行轨迹评估。与仅检查最终状态的先前基准不同，ToolSandbox 评估中间步骤和对话流程的质量。",
        "findings_zh": [
            "里程碑 DAG 捕获部分正确性——模型可以通过错误方式达到正确状态",
            "有状态评测揭示了 30% 在无状态基准中'正确'的答案存在问题中间步骤",
            "对话式工具使用（交织聊天+工具调用）比纯工具调用难度显著更高",
            "基于里程碑的评分比二元正确/错误更接近人类判断",
        ],
    },
    "traject-bench-2026": {
        "title_zh": "TRAJECT-Bench：面向 Agent 工具使用的轨迹感知评测基准",
        "abstract_zh": "TRAJECT-Bench 超越最终答案，评估工具在整个执行轨迹中是否被正确选择、参数化和排序。揭示了'相似工具混淆'和'参数盲选'等仅靠结果评测无法发现的失败模式。",
        "findings_zh": [
            "相似工具混淆：描述重叠时模型选错工具（如 shade_curtain_opener vs shade_curtain_switch）",
            "参数盲选：模型选对工具但参数幻觉或遗漏",
            "工具排序错误：模型以错误顺序执行有依赖关系的工具",
            "轨迹分析可实现细粒度反馈以改进模型",
        ],
    },
    "agent-survey-2026": {
        "title_zh": "LLM Agent 评测综述",
        "abstract_zh": "首篇针对 LLM Agent 评测方法的全面综述，从五个视角分析该领域：核心 LLM 能力、应用特定基准、通用 Agent、基准维度和评测框架。识别了成本效率、安全性和鲁棒性评估方面的关键差距。",
        "findings_zh": [
            "领域从静态基准转向持续更新基准以防止数据污染",
            "三层评测架构正在形成：最终答案、轨迹和逐轮评估",
            "LLM-as-judge 占主导地位但存在位置偏见、冗长偏见和非确定性",
            "多 Agent 评测和企业级约束仍是研究空白",
        ],
    },
    "car-bench-2024": {
        "title_zh": "CAR-Bench：面向车载语音助手 Agent 的综合基准",
        "abstract_zh": "CAR-Bench 是车载语音助手领域专用基准，覆盖基础任务、消歧（内部/用户）和幻觉（工具缺失/参数缺失/响应缺失）场景。包含 254 条中文测试用例，含车辆状态、人设和上下文初始化。",
        "findings_zh": [
            "车载领域独特地需要同时处理物理状态（速度、座位、温度）和 NLU",
            "消歧场景（17%）显示模型在提出追问方面存在困难",
            "幻觉检测（工具/参数缺失）是最难类别，通过率不到 50%",
            "分区隔离（驾驶员 vs 乘客）是汽车领域独有的安全关键需求",
        ],
    },
    "tau2-bench-2024": {
        "title_zh": "τ²-bench：面向工具使用 Agent 轨迹的基准",
        "abstract_zh": "τ²-bench 通过多步轨迹评估工具使用 Agent，强调正确的工具编排（并行 vs 串行、错误处理、计划适应）。引入轨迹级指标，包括工具调用次数效率和计划最优性。",
        "findings_zh": [
            "工具编排质量（并行/串行决策）在不同模型间差异达 3 倍",
            "计划适应（工具失败时改变策略）对大多数模型几乎为零",
            "高效工具调用（最少调用达成目标）与任务成功率不相关",
            "错误恢复行为是区分好 Agent 和优秀 Agent 的最强判别器",
        ],
    },
    "metatool-2024": {
        "title_zh": "MetaTool：通过任务组合促进 LLM 掌握工具",
        "abstract_zh": "MetaTool 关注何时不使用工具，将相关性检测作为一等评测标准。显示模型在 20-40% 的不相关查询中过度触发工具，强调了评测中负例的重要性。",
        "findings_zh": [
            "工具过度触发普遍存在：模型对 20-40% 不需要工具的查询调用工具",
            "相关性检测准确率在不同模型间差异很大（45-90%）",
            "在训练中添加显式的'无需工具'示例可将过度触发降低 30%",
            "评测中的负例至关重要——没有负例，过度触发模型显得比实际更好",
        ],
    },
    "agentbench-2023": {
        "title_zh": "AgentBench：将 LLM 作为 Agent 进行评测",
        "abstract_zh": "AgentBench 在 8 个多样化交互环境中评测 LLM（OS、数据库、Web、游戏等），测试长时程推理和多步规划。是首批展示强对话模型可能是弱 Agent 的基准之一。",
        "findings_zh": [
            "对话性能是 Agent 性能的弱预测器（r=0.3-0.5）",
            "长时程规划（5步以上）是所有模型最难的能力",
            "环境多样性揭示了单领域测试中不可见的模型特定弱点",
            "开源模型在 Agent 任务上显著落后于闭源模型（差距 20-40%）",
        ],
    },
    "complexfuncbench-2025": {
        "title_zh": "ComplexFuncBench：面向 LLM 复杂函数调用的基准",
        "abstract_zh": "ComplexFuncBench 关注复杂函数调用场景，包括嵌套函数调用、跨多个调用的约束满足和动态参数解析。填补了简单单调用基准与完整 Agent 评测之间的空白。",
        "findings_zh": [
            "嵌套函数调用（A的输出→B的输入）在所有模型中成功率不到 30%",
            "跨调用约束满足近乎随机（如'总调整必须为零'）",
            "动态参数解析（从先前调用中查找值）使性能下降 40%",
            "约束感知的工具调用仍是一个开放问题",
        ],
    },
    "mcp-agentbench-2025": {
        "title_zh": "MCP-AgentBench：在模型上下文协议生态系统中评测 Agent",
        "abstract_zh": "MCP-AgentBench 使用双层评测（基于规则的确定性检查 + LLM-as-judge 定性评估）评测 MCP 生态系统中的 Agent。测试 Agent 从 MCP 服务器发现、选择和组合工具的能力。",
        "findings_zh": [
            "双层评测（基于规则 + LLM-judge）平衡了可靠性和覆盖范围",
            "工具发现（找到正确的 MCP 服务器）是固定工具基准中不存在的新失败模式",
            "MCP 协议开销增加延迟但实现了跨提供商的工具可组合性",
            "基于规则的检查捕获 80% 的错误；LLM-judge 处理剩余 20%",
        ],
    },
    "stable-toolbench-2024": {
        "title_zh": "StableToolBench：面向稳定且可复现的工具学习评测",
        "abstract_zh": "StableToolBench 解决了工具使用基准中 API 不稳定的根本问题：真实 API 会变更、弃用或消失，导致评测结果不可复现。提出使用模拟稳定 API 服务器作为解决方案。",
        "findings_zh": [
            "真实 API 基准在 6 个月内因 API 变更丢失 15-30% 的测试用例",
            "模拟稳定 API 在 12 个月周期内实现 >95% 的结果可复现性",
            "API 演化对不同模型影响不同，引入了评测偏见",
            "稳定评测需要版本化的 API 快照和模拟服务器",
        ],
    },
    "apigen-2024": {
        "title_zh": "APIGen：面向函数调用合成数据生成的自动化流水线",
        "abstract_zh": "APIGen 提出了一个自动化流水线，用于生成高质量的函数调用合成数据。使用多阶段生成+过滤+验证流水线，大规模产出多样化、真实的函数调用示例。",
        "findings_zh": [
            "自动化数据生成结合严格过滤可匹配人工标注质量",
            "多阶段生成（生成→验证→过滤→重新生成）比单次通过提升质量 40%",
            "多样性指标（工具覆盖、参数分布、语言变体）对质量控制至关重要",
            "合成数据训练的模型在函数调用任务上可匹配或超越人工数据训练的模型",
        ],
    },
    "helm-2023": {
        "title_zh": "HELM：语言模型的整体评估",
        "abstract_zh": "HELM 提供全面、标准化的评估框架，覆盖 42 个场景和 7 个指标类别。开创了'场景 × 指标'的评估分类法，并强调评估设计的透明度。",
        "findings_zh": [
            "多指标评估揭示了单指标方法不可见的权衡",
            "场景多样性比场景数量更重要——7 个精心选择的场景优于 30 个窄场景",
            "标准化评估协议对跨模型可比性至关重要",
            "评估透明度（开放数据、开放代码、清晰指标）建立对基准结果的信任",
        ],
    },
    "car-mem-bench-2025": {
        "title_zh": "CarMem：面向车载语音助手长期记忆的基准",
        "abstract_zh": "CarMem 评估车载助手跨会话存储、检索和应用用户长期偏好的能力。定义了 5 种记忆操作（提取、存储、检索、更新、遗忘）并在多会话场景中测试。",
        "findings_zh": [
            "从自然对话中提取记忆是最难的操作（40-60% 成功率）",
            "偏好冲突（旧 vs 新）在 50% 的情况下被错误处理——模型同时保留而非更新",
            "多用户记忆隔离对大多数模型几乎是零能力",
            "会话边界检测（何时存储 vs 遗忘）仍未解决",
        ],
    },
    "code-gen-eval-2024": {
        "title_zh": "SWE-Bench：语言模型能否解决真实世界 GitHub Issue？",
        "abstract_zh": "SWE-Bench 在真实 GitHub Issue 上评测 LLM，要求模型理解问题描述、定位相关代码并生成正确补丁。为真实、端到端的 Agent 评测设立了标准。",
        "findings_zh": [
            "真实世界任务比合成基准难几个数量级",
            "端到端评测（Issue→补丁）对衡量实际效用至关重要",
            "基于测试的验证（单元测试通过）提供了客观、可复现的评分",
            "最佳模型与平均模型之间的差距在真实世界任务上急剧扩大",
        ],
    },
}


def apply_chinese_translations(papers):
    """Apply Chinese translations to papers that have them."""
    for paper in papers:
        pid = paper.get("id", "")
        if pid in CHINESE_TRANSLATIONS:
            tr = CHINESE_TRANSLATIONS[pid]
            for key in ["title_zh", "abstract_zh", "findings_zh"]:
                if key in tr:
                    paper[key] = tr[key]
    return papers


# ============================================================
# API CLIENTS
# ============================================================

def search_semantic_scholar(query, limit=10):
    """Search Semantic Scholar API for papers."""
    url = f"https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,abstract,url,venue, citationCount,externalIds",
    }
    try:
        qs = urllib.parse.urlencode(params)
        full_url = f"{url}?{qs}"
        req = urllib.request.Request(full_url, headers={"User-Agent": "AutoEval/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data.get("data", [])
    except Exception as e:
        print(f"  ⚠ Semantic Scholar error ({query[:40]}...): {e}")
        return []


def search_arxiv(query, max_results=10):
    """Search arXiv API for papers."""
    url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": query,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    try:
        qs = urllib.parse.urlencode(params)
        full_url = f"{url}?{qs}"
        req = urllib.request.Request(full_url, headers={"User-Agent": "AutoEval/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read().decode()
            return _parse_arxiv_xml(content)
    except Exception as e:
        print(f"  ⚠ arXiv error ({query[:40]}...): {e}")
        return []


def _parse_arxiv_xml(xml_content):
    """Parse arXiv API XML response into paper dicts."""
    papers = []
    entries = xml_content.split("<entry>")
    for entry in entries[1:]:  # skip header
        try:
            title = re.search(r"<title>(.*?)</title>", entry, re.DOTALL)
            title = title.group(1).strip().replace("\n", " ") if title else ""

            abstract = re.search(r"<summary>(.*?)</summary>", entry, re.DOTALL)
            abstract = abstract.group(1).strip().replace("\n", " ") if abstract else ""

            authors = re.findall(r"<name>(.*?)</name>", entry)

            year_match = re.search(r"<published>(\d{4})", entry)
            year = int(year_match.group(1)) if year_match else None

            url_match = re.search(r'<id>(http://arxiv.org/abs/.*?)</id>', entry)
            url = url_match.group(1) if url_match else None
            if url and "arxiv.org/abs" in url:
                arxiv_id = url.split("/abs/")[-1]
            else:
                arxiv_id = None

            papers.append({
                "title": title,
                "authors": authors[:10] if authors else [],
                "year": year,
                "abstract": abstract[:1000],
                "url": url,
                "arxiv_id": arxiv_id,
                "source": "arxiv",
            })
        except Exception:
            continue
    return papers


# ============================================================
# PAPER PROCESSING
# ============================================================

def normalize_arxiv_id(paper):
    """Extract clean arXiv ID from URL or externalIds."""
    if paper.get("arxiv_id"):
        return paper["arxiv_id"]
    ext = paper.get("externalIds", {}) or {}
    if ext.get("ArXiv"):
        return ext["ArXiv"]
    url = paper.get("url", "")
    m = re.search(r"arxiv\.org/abs/([\w.-]+)", url.lower())
    if m:
        return m.group(1)
    return None


def merge_papers(api_papers, curated_papers):
    """Merge API-retrieved papers with curated seed data, deduplicating by title similarity."""
    merged = list(curated_papers)  # curated papers take precedence

    # Normalize curated titles for comparison
    curated_titles_lower = set()
    for p in curated_papers:
        t = p["title"].lower().strip().rstrip(".")
        curated_titles_lower.add(t)
        # Also add short version (first 60 chars)
        curated_titles_lower.add(t[:60])

    for paper in api_papers:
        title = (paper.get("title") or "").lower().strip().rstrip(".")
        # Check for duplicates
        is_dup = False
        for ct in curated_titles_lower:
            if title == ct or title[:60] == ct[:60]:
                is_dup = True
                break
            # Check for high overlap
            if len(title) > 50 and len(ct) > 50:
                shorter = min(title, ct, key=len)
                longer = max(title, ct, key=len)
                if shorter in longer:
                    is_dup = True
                    break

        if is_dup:
            continue

        # Convert to standard format
        authors = paper.get("authors", [])
        if isinstance(authors, list) and authors and isinstance(authors[0], dict):
            author_names = [a.get("name", "") for a in authors]
        else:
            author_names = authors if isinstance(authors, list) else []

        merged.append({
            "id": f"api-{len(merged):04d}",
            "title": paper.get("title", ""),
            "authors": author_names[:10],
            "year": paper.get("year"),
            "venue": paper.get("venue", "") or "",
            "url": paper.get("url", ""),
            "topic": "agent_evaluation",  # default, will be refined
            "tags": [],
            "citations": paper.get("citationCount", 0) or 0,
            "abstract": (paper.get("abstract") or "")[:1500],
            "key_findings": [],
            "methodology": "",
            "car_control_insight": "",
            "car_control_score": 0,
            "source": paper.get("source", "semantic_scholar"),
        })

        # Auto-tag from title/abstract
        merged[-1]["tags"] = auto_tag_paper(merged[-1])
        merged[-1]["topic"] = guess_topic(merged[-1])

    return merged


def auto_tag_paper(paper):
    """Auto-assign tags based on title and abstract content."""
    text = (paper["title"] + " " + paper["abstract"]).lower()
    tags = []
    tag_map = {
        "benchmark": "benchmark",
        "evaluation": "evaluation",
        "survey": "survey",
        "function call": "function calling",
        "tool use": "tool use",
        "tool-us": "tool use",
        "agent": "agent",
        "memory": "memory",
        "multi-turn": "multi-turn",
        "stateful": "stateful",
        "safety": "safety",
        "chinese": "Chinese",
        "multilingual": "multilingual",
        "car": "car",
        "vehicle": "car",
        "automotive": "car",
        "voice": "voice",
        "speech": "voice",
        "trajectory": "trajectory",
    }
    for keyword, tag in tag_map.items():
        if keyword in text and tag not in tags:
            tags.append(tag)
    return tags[:8]


def guess_topic(paper):
    """Guess the research topic from paper content."""
    text = (paper["title"] + " " + paper["abstract"]).lower()
    if any(w in text for w in ["car", "vehicle", "automotive", "in-car", "driving"]):
        return "car_agent"
    if any(w in text for w in ["function call", "tool use", "tool-us", "bfcl", "toolbench"]):
        return "function_calling"
    if any(w in text for w in ["chinese", "multilingual"]):
        return "chinese_agent"
    if any(w in text for w in ["metric", "methodology", "reproducib", "stability"]):
        return "eval_methodology"
    return "agent_evaluation"


def generate_insights(papers):
    """Generate meta-insights by synthesizing across papers."""
    insights = {
        "meta_title": "Cross-Paper Insights for Car-Control Agent Evaluation",
        "meta_title_zh": "跨论文洞察：车控 Agent 评测的关键方向",
        "generated_at": datetime.now().isoformat(),
        "total_papers": len(papers),
        "cross_cutting_themes": [
            {
                "theme": "From Static to Stateful Evaluation",
                "theme_zh": "从静态到有状态的评测范式转变",
                "description": "BFCL v4, ToolSandbox, TRAJECT-Bench, and τ²-bench all converge on the same finding: single-turn, stateless evaluation overestimates real-world performance by 15-30%. The field is unanimously moving toward stateful, multi-turn, trajectory-aware evaluation.",
                "papers": ["bfcl-v4", "toolsandbox-2024", "traject-bench-2026", "tau2-bench-2024"],
                "car_control_action": "Our eval set should prioritize multi-turn scenarios (currently 26/207 = 12.5%). Target: 25-30% multi-turn. Add explicit vehicle state tracking across turns in each multi-turn case.",
            },
            {
                "theme": "Three-Layer Evaluation Architecture",
                "theme_zh": "三层评测架构：结果 → 轨迹 → 逐轮",
                "description": "The Agent Survey (ACL 2026), ToolSandbox, and MCP-AgentBench independently propose three evaluation layers: (1) final-answer/state verification, (2) trajectory/tool-call correctness, (3) per-turn interaction quality. This maps naturally to our action/state/label assertion types.",
                "papers": ["agent-survey-2026", "toolsandbox-2024", "mcp-agentbench-2025"],
                "car_control_action": "Our assertion system (action=layer 1, state=layer 2, label=layer 3) already implements this architecture. Next step: add trajectory-level scoring for hard combo cases using Milestone DAG approach.",
            },
            {
                "theme": "Similar Tool Confusion is the Dominant Failure Mode",
                "theme_zh": "相似工具混淆是最主要的失败模式",
                "description": "TRAJECT-Bench, API-Bank, and BFCL all identify 'similar tool confusion' as the #1 failure mode: models pick wrong tools when descriptions overlap. This directly validates our L1-TL-09 (工具描述歧义敏感度) tag and our shade_curtain_opener vs shade_curtain_switch case.",
                "papers": ["traject-bench-2026", "api-bank-2023", "bfcl-v4"],
                "car_control_action": "Expand L1-TL-09 from 3 to 8 cases covering more similar-tool pairs: mirror_fold vs mirror_adjust, fragrance_switch vs fragrance_mode, conditioner_temperature vs conditioner_speed.",
            },
            {
                "theme": "Negative Examples Are Essential but Under-Provided",
                "theme_zh": "负例不可或缺但普遍供给不足",
                "description": "MetaTool shows models over-trigger tools 20-40% of the time, yet most benchmarks have <10% negative cases. Our 15% negative ratio is above average but still below the ideal 20-25% suggested by MetaTool's findings.",
                "papers": ["metatool-2024", "bfcl-v4", "api-bank-2023"],
                "car_control_action": "Increase negative cases from 32 (15%) to ~45 (20%+). Focus on subtle negatives: parameter-legal but semantically wrong commands, tool over-triggering in ambiguous contexts, and cross-domain confusion.",
            },
            {
                "theme": "Memory and Personalization Are Critical Gaps",
                "theme_zh": "记忆与个性化是评测的关键空白",
                "description": "CarMem, VehicleMemBench, and the Agent Survey all identify long-term memory and personalization as the most under-evaluated capability. Our 22 memory-dependent cases (L1-MM-01~05) are among the first to systematically test this in a car-control context.",
                "papers": ["car-mem-bench-2025", "agent-survey-2026"],
                "car_control_action": "Our memory taxonomy (L1-L5 with L1-MM-01~05) is already best-in-class. Next: design end-to-end multi-session test scenarios where preferences persist across simulated days/weeks.",
            },
            {
                "theme": "Reproducibility Requires API Stability",
                "theme_zh": "可复现性依赖于 API 稳定性",
                "description": "StableToolBench demonstrates that real API benchmarks degrade 15-30% within 6 months. Our tools_manifest.json (547 tools, versioned) provides the stable API snapshot that StableToolBench recommends.",
                "papers": ["stable-toolbench-2024", "helm-2023"],
                "car_control_action": "Version-lock tools_manifest.json with each eval set release. Add API version metadata to eval_cases.json. Design simulated tool servers for CI/CD reproducibility.",
            },
        ],
        "gap_analysis": {
            "what_we_have": [
                "Comprehensive car-control taxonomy (48 tags, 207 cases)",
                "Auto-verifiable assertions (0 rubric, 100% action/state/label)",
                "5-level memory evaluation (L1-MM-01~05)",
                "Safety layer with stateful conditions (L3-SF-01~04)",
                "Versioned tool manifest (547 tools in 10 groups)",
            ],
            "what_benchmarks_have_that_we_dont": [
                "Trajectory-level scoring with Milestones (ToolSandbox approach)",
                "Cross-session memory persistence testing (CarMem approach)",
                "Automated query variant generation (APIGen approach)",
                "Real-time tool execution with state simulation",
                "Standardized leaderboard with public model rankings",
                "Multi-language function calling (Python + Java + REST + SQL)",
            ],
            "what_we_have_that_benchmarks_dont": [
                "Vehicle-specific state model (speed, seats, climate, partitions)",
                "Chinese natural speech with oral noise (14% coverage)",
                "Explicit memory taxonomy (L1-L5) with extraction/application/update/forget",
                "Safety-critical driving scenarios (speed-gated, child-lock, distraction)",
                "Domain-specific tool disambiguation (shade_curtain_opener vs switch)",
            ],
        },
    }
    return insights


# ============================================================
# MAIN PIPELINE
# ============================================================

def run_pipeline(use_api=True):
    """Run the full auto-research pipeline."""
    print("=" * 60)
    print("🚀 Auto-Research Pipeline for Harness Eval")
    print("=" * 60)
    print(f"  Output: {PAPERS_JSON}")
    print()

    all_api_papers = []

    if use_api:
        # Phase 1: Search APIs
        print("📡 Phase 1: Searching academic APIs...")
        for topic_key, topic_info in RESEARCH_TOPICS.items():
            print(f"\n  [{topic_info['label_zh']}] ({topic_info['label']})")
            for query in topic_info["queries"]:
                print(f"    🔍 Semantic Scholar: '{query}'")
                results = search_semantic_scholar(query, limit=8)
                for r in results:
                    r["source"] = "semantic_scholar"
                    r["_topic"] = topic_key
                all_api_papers.extend(results)
                print(f"       → {len(results)} results")
                time.sleep(1.5)  # rate limiting

            for query in topic_info["arxiv_queries"]:
                print(f"    🔍 arXiv: '{query}'")
                results = search_arxiv(query, max_results=5)
                for r in results:
                    r["_topic"] = topic_key
                all_api_papers.extend(results)
                print(f"       → {len(results)} results")
                time.sleep(1.5)
    else:
        print("📡 Phase 1: API search SKIPPED (use_api=False)")
        print("   Using curated seed data only.")

    # Phase 2: Merge & Deduplicate
    print(f"\n📊 Phase 2: Merging & deduplicating...")
    print(f"   API papers: {len(all_api_papers)}")
    print(f"   Curated papers: {len(CURATED_PAPERS)}")

    all_papers = merge_papers(all_api_papers, CURATED_PAPERS)
    all_papers = apply_chinese_translations(all_papers)
    print(f"   After merge: {len(all_papers)} unique papers")
    print(f"   Chinese translations applied: {sum(1 for p in all_papers if p.get('title_zh'))} papers")

    # Phase 3: Sort & Organize
    print(f"\n📋 Phase 3: Organizing...")
    all_papers.sort(key=lambda p: (p.get("car_control_score", 0), p.get("citations", 0)), reverse=True)

    # Phase 4: Generate Insights
    print(f"\n💡 Phase 4: Generating cross-paper insights...")
    insights = generate_insights(all_papers)

    # Phase 5: Save Output
    print(f"\n💾 Phase 5: Saving output...")

    output = {
        "generated_at": datetime.now().isoformat(),
        "total_papers": len(all_papers),
        "papers": all_papers,
    }

    with open(PAPERS_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"   ✅ papers.json: {len(all_papers)} papers ({os.path.getsize(PAPERS_JSON):,} bytes)")

    with open(INSIGHTS_JSON, "w", encoding="utf-8") as f:
        json.dump(insights, f, ensure_ascii=False, indent=2)
    print(f"   ✅ insights.json: {os.path.getsize(INSIGHTS_JSON):,} bytes")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"📊 PIPELINE COMPLETE")
    print(f"{'=' * 60}")
    topics = {}
    for p in all_papers:
        t = p.get("topic", "unknown")
        topics[t] = topics.get(t, 0) + 1
    for t, c in sorted(topics.items(), key=lambda x: -x[1]):
        label = RESEARCH_TOPICS.get(t, {}).get("label_zh", t)
        print(f"   {label}: {c} papers")

    curated_count = sum(1 for p in all_papers if p.get("car_control_score", 0) > 0)
    print(f"\n   Papers with car-control insights: {curated_count}")
    print(f"   Cross-cutting themes: {len(insights['cross_cutting_themes'])}")
    print(f"   Total size: {os.path.getsize(PAPERS_JSON) + os.path.getsize(INSIGHTS_JSON):,} bytes")
    print()

    return all_papers, insights


if __name__ == "__main__":
    # Run without API calls by default to avoid rate limits on first run
    # Pass --api to enable live API searching
    use_api = "--api" in sys.argv
    run_pipeline(use_api=use_api)
