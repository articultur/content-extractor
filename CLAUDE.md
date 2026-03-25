# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a **Claude Code Skill Library** containing two main skills:

1. **quality-document-generator** - Generates quality-related documents (test plans, reports, assessments) based on IEEE 829 and ISO 25010 standards
2. **impact-analysis** (sub-skill) - Analyzes code changes (PRs/diffs) and recommends test regression scope

## Repository Structure

```
skills/
└── quality-document-generator/
    ├── SKILL.md                          # Main skill entry point
    ├── references/
    │   ├── impact-analysis/              # Sub-skill: code impact analysis
    │   │   ├── SKILL.md
    │   │   └── references/
    │   │       ├── analyzer/             # Python analyzers (rule-based)
    │   │       │   ├── sensitivity_scorer.py   # Sensitivity scoring
    │   │       │   └── escape_rules_engine.py  # Escape rules
    │   │       ├── prompts/             # LLM prompt templates
    │   │       ├── workflows/           # Analysis flows
    │   │       ├── adapters/           # GitHub/GitLab adapters
    │   │       └── templates/           # Output templates
    │   ├── workflows/                   # Main workflow definitions
    │   ├── templates/                  # Document templates (IEEE 829)
    │   └── input-handlers/            # Input parsers
    └── scripts/                         # Utility scripts (empty)
```

## Key Concepts

### Rule-First + LLM Enhancement Architecture (impact-analysis)

The impact-analysis skill uses a hybrid approach:

1. **Rule-based analysis first** (Python): Fast, deterministic scoring
   - `sensitivity_scorer.py`: Calculates P0/P1/P2 sensitivity levels
   - `escape_rules_engine.py`: Checks 10 escape rules for quick decisions

2. **LLM enhancement second**: Semantic analysis when needed
   - P0 (score ≥ 5): Must call LLM for deep analysis
   - P1 (score 2-4): Recommend LLM analysis
   - P2 (score < 2): Skip LLM, rule results sufficient

### Sensitivity Scoring Formula

```
敏感度 = 规模分 + 类型分 + 位置分 + 函数分 + 核心模块分 + 合规分 - 减分

级别:
  P0: >= 5 → 全量测试 + 人工评审
  P1: 2-4  → Integration + E2E
  P2: < 2  → Unit 测试
```

## Running Analyzers

```bash
# Run sensitivity scorer
cd skills/quality-document-generator/references/impact-analysis/references/analyzer
python sensitivity_scorer.py

# Test with custom input
python -c "
from sensitivity_scorer import calculate_sensitivity, ChangeInput
change = ChangeInput(
    files_count=8,
    lines_added=327,
    lines_deleted=15,
    change_types=['feature', 'api_change'],
    new_functions=['CopilotClient', 'get_github_token'],
    files=['tradingagents/llm_clients/copilot_client.py']
)
result = calculate_sensitivity(change)
print(f'Level: {result.level}, Score: {result.score}')
"

# Test escape rules engine
python -c "
from escape_rules_engine import check_escape_rules, ChangeInput
change = ChangeInput(
    files=['pkg/github/projects.go'],
    files_count=1,
    lines_added=150,
    lines_deleted=20,
    change_types=['feature'],
    pr_title='feat: add project creation API'
)
result = check_escape_rules(change)
print(f'Action: {result.action}')
"
```

## MCP Detection

When working with GitHub/GitLab integration:
- `claude mcp list` may miss dynamically-loaded MCPs (e.g., github-mcp)
- Use `/mcp` dialog or direct tool call to verify MCP availability
- MCP detection priority: MCP > CLI (gh/glab) > API Token > manual input

## Skill Usage

### Trigger impact-analysis skill:
- "分析 PR #123"
- "这是我的 diff..."
- "需要回归哪些测试"

### Trigger quality-document-generator:
- "生成测试计划"
- "生成质量评估报告"
- "分析代码质量"

## Important Notes

- This is a **skill library**, not an application - no build/test commands needed
- Python analyzers provide deterministic rule-based analysis
- LLM prompts are in `references/impact-analysis/references/prompts/`
- Document templates follow IEEE 829 and ISO 25010 standards
