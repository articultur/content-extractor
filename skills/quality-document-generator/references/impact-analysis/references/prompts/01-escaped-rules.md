# 逃逸规则检查 / Escape Rules Check

## 概述

逃逸规则用于快速判断代码变更是否属于特殊场景，从而决定分析策略。

## 实现参考

> **Python 实现**：`../analyzer/escape_rules_engine.py`
>
> 已实现 `check_escape_rules(change: ChangeInput) -> EscapeRulesResult` 函数，可直接调用：
> ```python
> from analyzer.escape_rules_engine import check_escape_rules, ChangeInput
>
> change = ChangeInput(
>     files=["pkg/github/projects.go", "pkg/github/projects_test.go"],
>     files_count=2,
>     lines_added=150,
>     lines_deleted=20,
>     new_functions=["createProject"],
>     change_types=["feature", "api_change"],
>     pr_title="feat: add project creation API"
> )
> result = check_escape_rules(change)
> # result.action: "api_contract_verification"
> # result.should_expand_scope: True
> ```

## 规则列表

### 规则 1: 测试文件变更

```yaml
rule: test_file_change
condition: files match "^(test/|spec/|__tests__/)"
action: run_related_tests_only
confidence: 0.95
description: "测试文件本身变更，只分析相关测试"
```

### 规则 2: 文档变更

```yaml
rule: documentation_change
condition: files match "^(docs/|\.md$|README)"
action: skip_analysis
confidence: 0.9
description: "纯文档变更，跳过影响分析"
```

### 规则 3: 配置变更（小规模）

```yaml
rule: small_config_change
condition: files match "(\.env$|config/|\.yaml$|\.json$)" AND files_count < 5
action: minimal_smoke
confidence: 0.7
description: "小规模配置变更，建议冒烟测试"
```

### 规则 4: 微小变更

```yaml
rule: tiny_change
condition: files_count < 3 AND lines_changed < 100
action: unit_only
confidence: 0.6
description: "微小变更，只执行单元测试"
```

### 规则 5: 大型 PR

```yaml
rule: large_pr
condition: files_count > 30
action: segment_analysis
confidence: 0.85
description: "大型 PR，建议分批分析"
```

### 规则 6: 安全相关模块

```yaml
rule: security_sensitive
condition: modules match "^(auth|security|permission|crypto|payment)/"
action: security_focus
confidence: 0.85
description: "安全敏感模块，扩大测试范围"
```

### 规则 7: 数据库迁移

```yaml
rule: database_migration
condition: files match "(migration|schema|\.sql$|alembic|prisma)"
action: db_integration_focus
confidence: 0.9
description: "数据库迁移相关，DB 集成测试优先"
```

### 规则 8: 紧急修复

```yaml
rule: urgent_fix
condition: pr_title matches "(urgent|hotfix|critical|emergency|fix)"
action: expand_full_coverage
confidence: 0.7
description: "紧急修复，扩大测试范围"
```

### 规则 9: API 接口变更

```yaml
rule: api_interface_change
condition: |
  - diff contains function signature changes (def, func, interface)
  - OR new API endpoints added
  - OR API parameters changed
action: api_contract_verification
confidence: 0.9
description: "API 接口变更，验证调用方兼容性"
```

### 规则 10: 纯重构

```yaml
rule: pure_refactor
condition: lines_removed > lines_added * 0.3 AND files_deleted > 0
action: regression_focus
confidence: 0.75
description: "纯重构，以回归测试为主"
```

## 检查流程

```
Step 1: 检查规则 1-3（跳过型）
         │
         ├── 命中 → 输出 action，立即返回
         │
         └── 未命中 → 继续 Step 2
                          │
                          ▼
Step 2: 检查规则 4-7（策略型）
         │
         ├── 命中 → 输出 action 和额外建议
         │
         └── 未命中 → 继续 Step 3
                          │
                          ▼
Step 3: 检查规则 8-10（扩大型）
         │
         ├── 命中 → 输出 action，标记需要扩大范围
         │
         └── 未命中 → 执行标准分析
```

## 输出格式

```json
{
  "escape_rules_check": {
    "checked_rules": [
      {"rule": "test_file_change", "matched": false},
      {"rule": "documentation_change", "matched": false},
      {"rule": "small_config_change", "matched": false},
      {"rule": "tiny_change", "matched": false},
      {"rule": "large_pr", "matched": false},
      {"rule": "security_sensitive", "matched": false},
      {"rule": "database_migration", "matched": false},
      {"rule": "urgent_fix", "matched": false},
      {"rule": "api_interface_change", "matched": true},
      {"rule": "pure_refactor", "matched": false}
    ],
    "matched_rules": [
      {
        "rule": "api_interface_change",
        "action": "api_contract_verification",
        "confidence": 0.9,
        "evidence": "新增 create_project 和 create_iteration_field 方法"
      }
    ],
    "action": "api_contract_verification",
    "should_expand_scope": true,
    "analysis_strategy": "full"
  }
}
```

## 快速检查清单

对于简单场景，只需检查以下关键规则：

| 规则 | 适用场景 | 检查要点 |
|------|---------|---------|
| `tiny_change` | < 3 文件，< 100 行 | 是 → unit_only |
| `security_sensitive` | 文件路径含安全关键词 | 是 → security_focus |
| `api_interface_change` | 有新增函数/方法 | 是 → api_contract_verification |

## 使用示例

### 示例 1: 微小变更

**输入**：
- files_count: 2
- lines_changed: 50
- files: ["src/utils/helper.go"]

**检查结果**：
```json
{
  "matched_rules": [
    {
      "rule": "tiny_change",
      "action": "unit_only",
      "confidence": 0.6
    }
  ],
  "action": "unit_only",
  "analysis_strategy": "minimal"
}
```

### 示例 2: 安全相关

**输入**：
- files: ["src/auth/token.go", "src/auth/jwt.go"]
- pr_title: "fix: token validation security issue"

**检查结果**：
```json
{
  "matched_rules": [
    {
      "rule": "security_sensitive",
      "action": "security_focus",
      "confidence": 0.85,
      "evidence": "文件位于 auth/ 目录"
    },
    {
      "rule": "urgent_fix",
      "action": "expand_full_coverage",
      "confidence": 0.7,
      "evidence": "PR title 包含 fix 和 security"
    }
  ],
  "action": "security_focus",
  "should_expand_scope": true,
  "analysis_strategy": "full"
}
```

### 示例 3: API 变更

**输入**：
- files: ["pkg/api/handler.go"]
- new_functions: ["createProject", "createIterationField"]
- change_types: ["feature", "api_change"]

**检查结果**：
```json
{
  "matched_rules": [
    {
      "rule": "api_interface_change",
      "action": "api_contract_verification",
      "confidence": 0.9,
      "evidence": "新增 create_project 和 create_iteration_field 公开方法"
    }
  ],
  "action": "api_contract_verification",
  "should_expand_scope": true,
  "analysis_strategy": "full"
}
```
