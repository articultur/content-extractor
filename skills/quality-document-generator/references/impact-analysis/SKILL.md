---
name: impact-analysis
description: |
  代码影响分析 (Impact Analysis) skill
  用于分析代码变更(PR/diff)并推荐需要回归的测试范围

  **触发场景**:
  - 用户提到分析 PR、代码变更、diff
  - 用户问"需要回归哪些测试"、"影响哪些模块"
  - 用户提供 PR 链接或编号
  - 用户粘贴 diff 内容

  **不触发场景**:
  - 纯文档生成请求(用主 skill)
  - 测试报告生成(用主 skill)
  - 代码评审请求(用 review skill)
---

# Impact Analysis Skill

代码影响分析工具，用于分析代码变更并推荐测试回归范围。

## 核心能力

| 能力 | 说明 |
|------|------|
| PR 分析 | 输入 PR 链接/编号，分析变更影响 |
| Diff 分析 | 输入 diff 内容，分析影响范围 |
| 模块映射 | 识别变更文件归属的模块 |
| 测试匹配 | 推荐需要回归的测试用例 |
| 敏感度分级 | 评估变更的重要程度 |

## 使用方式

### 方式1: 分析 PR

```
用户: "分析 PR #123"
AI: 发现 GitHub MCP 已配置，直接获取 PR #123...
AI: 分析完成，建议回归以下测试...
```

### 方式2: 粘贴 Diff

```
用户: "这是我的 diff：
...
AI: 收到 diff，开始分析...
AI: 分析完成，建议回归以下测试...
```

### 方式3: 混合模式

```
用户: "分析 PR #456，主要关注 payment 模块"
AI: 重点分析 payment 模块及其关联...
```

## 分析流程

```
Step 0: 工具发现
         │
         ▼
Step 1: 获取代码/diff
         │
         ▼
Step 2: Diff 解析 (L1 文件级)
         │
         ▼
Step 3: 模块映射 (L2 模块级)
         │
         ▼
Step 4: 函数识别 (L3 函数级)
         │
         ▼
Step 5: 逃逸规则检查
         │
         ▼
Step 6: 敏感度分级
         │
         ▼
Step 7: 测试匹配
         │
         ▼
Step 8: 置信度评估
         │
         ▼
Step 9: 生成报告
```

## 配置

### 默认配置

```yaml
impact_analysis:
  default_test_type: integration  # unit | integration | e2e
  max_pr_size_mb: 5              # 超过此大小触发分批处理
  confidence_threshold:
    direct: 0.8                  # >= 0.8 直接执行
    confirm: 0.5                 # 0.5-0.8 需确认
    skip: 0.5                    # < 0.5 跳过
  core_modules: []                # 核心模块列表
  security_sensitive: []          # 安全敏感模块
```

### 工具发现优先级

> ⚠️ **MCP 检测经验**：`claude mcp list` 有检测遗漏问题。某些 MCP（如 github-mcp）可能动态加载，不在静态配置中。

| 优先级 | 工具 | 检测方式 |
|--------|------|----------|
| 1 | MCP (github/gitlab) | 直接尝试验证 `mcp__xxx__*` |
| 2 | CLI (gh/glab) | `has_command()` |
| 3 | API Token | 环境变量检查 |
| 4 | 手动输入 | 用户粘贴 |

**实践建议**：
- 不要只依赖 `claude mcp list` 的结果
- 使用 `/mcp` 对话框查看 MCP 状态
- 直接尝试调用 MCP 工具验证可用性

### 用户配置

用户可通过对话配置:

```
用户: "payment 模块是核心模块"
AI: 已将 payment 加入核心模块配置

用户: "跳过 test_ui_ 开头的测试"
AI: 已添加忽略规则: test_ui_*
```

## 输出格式

详见 `references/templates/impact-report.md`

## 提示词模板结构

```
prompts/
├── 00-context.md              # 角色定义、核心原则
├── 01-escaped-rules.md        # 逃逸规则检查（10 条规则）
├── 02-sensitivity-scoring.md   # 敏感度评分公式
├── 03-output-schema.md        # JSON 输出格式 Schema
├── 10-analysis-full.md        # 完整分析入口（大型 PR）
├── 11-analysis-quick.md        # 快速分析入口（轻量级）
├── code-analysis.md           # 代码分析提示词（详细版）
├── impact-analysis.md         # 影响分析提示词（详细版）
└── test-matching.md          # 测试匹配提示词（详细版）
```

### 使用指南

| 场景 | 使用模板 | 说明 |
|------|---------|------|
| < 10 文件，< 1000 行 | `11-analysis-quick.md` | 快速返回，简化分析 |
| > 10 文件，复杂变更 | `10-analysis-full.md` | 深度分析，详细输出 |
| 逃逸规则检查 | `01-escaped-rules.md` | 10 条规则逐一检查 |
| 敏感度评分 | `02-sensitivity-scoring.md` | 简化评分公式 |
| 输出格式定义 | `03-output-schema.md` | JSON Schema |

### 快速分析流程

```
1. 读取 11-analysis-quick.md 或 10-analysis-full.md
2. 填充输入变量
3. LLM 分析后按 03-output-schema.md 验证输出
4. 如需深度分析，按 01-escaped-rules.md 检查逃逸规则
5. 按 02-sensitivity-scoring.md 计算敏感度
```

## 分析器实现

| 文件 | 用途 |
|------|------|
| `analyzer/sensitivity_scorer.py` | **敏感度评分器** - P1 已实现 |
| `analyzer/escape_rules_engine.py` | **逃逸规则引擎** - P2 已实现 |
| `analyzer/test_matcher.py` | **测试匹配器** - P3 已实现 |
| `analyzer/test_scanner.py` | **测试扫描器** - P3 已实现 |

### 敏感度评分器 (P1 已实现)

```python
from analyzer.sensitivity_scorer import calculate_sensitivity, ChangeInput

# 使用示例
change = ChangeInput(
    files_count=8,
    lines_added=327,
    lines_deleted=15,
    change_types=["feature", "api_change"],
    new_functions=["CopilotClient", "get_github_token"],
    files=["tradingagents/llm_clients/copilot_client.py"]
)

result = calculate_sensitivity(change)
# result.level: "P1"
# result.score: 4
# result.breakdown: {"scale": 0, "change_type": 2, ...}
```

### 逃逸规则引擎 (P2 已实现)

```python
from analyzer.escape_rules_engine import check_escape_rules, ChangeInput

# 使用示例
change = ChangeInput(
    files=["pkg/github/projects.go", "pkg/github/projects_test.go"],
    files_count=2,
    lines_added=150,
    lines_deleted=20,
    new_functions=["createProject", "createIterationField"],
    change_types=["feature", "api_change"],
    pr_title="feat: add project creation API"
)

result = check_escape_rules(change)
# result.action: "api_contract_verification"
# result.should_expand_scope: True
# result.analysis_strategy: "full"
```

### 测试匹配器 (P3 已实现)

```python
from analyzer.test_matcher import match_tests, MatchingInput, TestInfo, to_dict

# 定义输入
input_data = MatchingInput(
    changed_files=["Engine/Source/Runtime/Engine/Classes/GameFramework/Character.h"],
    changed_functions=["JumpCurrentCount"],
    affected_modules=["GameFramework"],
    change_types=["feature", "api_change"]
)

# 定义测试清单
test_inventory = [
    TestInfo(
        test_path="Engine/Source/Runtime/Engine/Tests/CharacterTest.cpp",
        test_name="TestJumpCount",
        module="GameFramework",
        covered_functions=["JumpCurrentCount", "Jump"],
        covered_lines=[100, 110, 120]
    ),
]

# 执行匹配
result = match_tests(input_data, test_inventory)

# 转换为 JSON 格式
output = to_dict(result)
# output["matches"]: 匹配结果列表
# output["recommended_order"]: 推荐执行顺序
# output["confidence_summary"]: 置信度统计
```

### 测试扫描器 (P3 已实现)

```python
from analyzer.test_scanner import scan_and_collect, is_test_file, detect_language

# 扫描目录获取测试清单
test_inventory = scan_and_collect("/path/to/project", extensions=['.py', '.cpp'])

# 扫描结果直接传给 test_matcher
result = match_tests(input_data, test_inventory)

# 或者只扫描特定扩展名
test_inventory = scan_and_collect("/path/to/project", extensions=['.cpp'])

# 判断单个文件是否为测试文件
is_test = is_test_file("tests/test_billing.py")  # True
is_test = is_test_file("src/billing.py")  # False
```

### 评分公式

```
敏感度 = 规模分 + 类型分 + 位置分 + 函数分

规模分:
  - > 30 文件 或 > 1000 行: +2
  - > 10 文件 或 > 500 行: +1
  - < 3 文件 且 < 100 行: -2

类型分:
  - API 变更/新功能: +2
  - Bug 修复: +1
  - 安全变更: +2
  - 重构: -1

位置分:
  - 安全敏感目录: +2

函数分:
  - 新增 API 函数/类: +2
  - 其他新增函数: +1

级别:
  - >= 5: P0 (全量测试 + 人工评审)
  - 2-4: P1 (Integration + E2E)
  - < 2: P2 (Unit 测试)
```

## 参考文档

| 文档 | 用途 |
|------|------|
| `analyzer/main.md` | 主分析器逻辑 |
| `analyzer/diff-parser.md` | Diff 解析器 |
| `analyzer/module-mapper.md` | 模块映射器 |
| `analyzer/test-matcher.md` | 测试匹配器 |
| `analyzer/sensitivity_scorer.py` | **敏感度评分器** (P1 已实现) |
| `prompts/00-context.md` | 角色定义、核心原则 |
| `prompts/01-escaped-rules.md` | 逃逸规则检查 |
| `prompts/02-sensitivity-scoring.md` | 敏感度评分公式 |
| `prompts/03-output-schema.md` | 输出格式 Schema |
| `prompts/10-analysis-full.md` | 完整分析入口 |
| `prompts/11-analysis-quick.md` | 快速分析入口 |
| `prompts/code-analysis.md` | 代码分析提示词（详细版） |
| `prompts/impact-analysis.md` | 影响分析提示词（详细版） |
| `prompts/test-matching.md` | 测试匹配提示词（详细版） |
| `data-sources/code-parser.md` | 代码解析 |
| `data-sources/test-parser.md` | 测试解析 |
| `data-sources/dependency.md` | 依赖解析 |
| `data-sources/config.md` | 用户配置 |
| `workflows/analysis-flow.md` | 分析流程 |
| `adapters/github-adapter.md` | GitHub 适配器 |
| `adapters/gitlab-adapter.md` | GitLab 适配器 |

## 集成方式

本 skill 可独立使用，也可集成到主 `quality-document-generator` skill 中。

独立使用: 直接调用 impact-analysis skill
集成使用: 作为主 skill 的子功能调用
