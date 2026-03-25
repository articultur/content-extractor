# 代码影响分析报告模板 / Impact Report Template

## 概述

影响分析报告的输出模板，定义了报告的结构和内容格式。

## 报告结构

```markdown
# 代码影响分析报告

## 基本信息

| 字段 | 内容 |
|------|------|
| 分析时间 | {timestamp} |
| 分析来源 | {source} |
| 变更文件数 | {file_count} |
| 变更行数 | +{additions} / -{deletions} |
| 分析耗时 | {duration}ms |

## 变更摘要

### 文件变更概览

| 状态 | 文件数 | 典型文件 |
|------|--------|---------|
| 新增 | {n} | {files} |
| 修改 | {n} | {files} |
| 删除 | {n} | {files} |

### PR 特征

| 特征 | 值 |
|------|-----|
| PR 标题 | {title} |
| 变更类型 | {change_type} |
| 是否紧急 | {is_urgent} |
| 是否重构 | {is_refactor} |

---

## 敏感度评估

### 敏感度级别

**级别: {sensitivity_level}** (评分: {sensitivity_score})

| 级别 | 说明 | 处理策略 |
|------|------|---------|
| P0 | 核心模块或重大变更 | 全量测试 + 人工确认 |
| P1 | 中等影响 | Integration + E2E |
| P2 | 轻微影响 | Unit + 快速验证 |

### 评分因素

| 因素 | 贡献 | 说明 |
|------|------|------|
| {factor_1} | {contribution_1} | {description_1} |
| {factor_2} | {contribution_2} | {description_2} |

---

## 逃逸规则

### 规则匹配

| 规则 | 条件 | 命中 |
|------|------|------|
| {rule_1} | {condition_1} | {hit_1} |
| {rule_2} | {condition_2} | {hit_2} |

### 执行 Action

**Action: {action}**

{action_description}

---

## 影响范围

### 直接影响模块

| 模块 | 置信度 | 说明 |
|------|--------|------|
| {module_1} | {confidence_1} | {reason_1} |
| {module_2} | {confidence_2} | {reason_2} |

### 间接影响模块

| 模块 | 置信度 | 依赖关系 | 说明 |
|------|--------|---------|------|
| {module_3} | {confidence_3} | {dependency_3} | {reason_3} |
| {module_4} | {confidence_4} | {dependency_4} | {reason_4} |

### 模块依赖关系

```
{dependency_diagram}
```

---

## 建议回归测试

### 测试摘要

| 优先级 | 测试数 | 说明 |
|--------|--------|------|
| P0 (必须) | {p0_count} | 直接影响模块的测试 |
| P1 (建议) | {p1_count} | 间接影响模块的测试 |
| P2 (可选) | {p2_count} | 边缘相关测试 |

### P0 必须执行

| 测试用例 | 文件路径 | 置信度 | 理由 |
|----------|---------|--------|------|
| {test_1} | {path_1} | {conf_1} | {reason_1} |
| {test_2} | {path_2} | {conf_2} | {reason_2} |

### P1 建议执行

| 测试用例 | 文件路径 | 置信度 | 理由 |
|----------|---------|--------|------|
| {test_3} | {path_3} | {conf_3} | {reason_3} |
| {test_4} | {path_4} | {conf_4} | {reason_4} |

### P2 可选执行

| 测试用例 | 文件路径 | 置信度 | 理由 |
|----------|---------|--------|------|
| {test_5} | {path_5} | {conf_5} | {reason_5} |

---

## 置信度分析

### 高置信度推荐 (≥ 0.8)

{high_confidence_tests}

### 中等置信度推荐 (0.5-0.8) - 需确认

{medium_confidence_tests}

### 低置信度推荐 (< 0.5) - 建议跳过

{low_confidence_tests}

---

## 对比分析详情

### 测试: {test_name} → {module_name}

**综合置信度: {confidence}**

#### 支持关联的证据 ✓

1. {support_1}
2. {support_2}

#### 不支持关联的证据 ✗

1. {oppose_1}
2. {oppose_2}

#### 综合建议

{recommendation}

---

## 数据来源

| 来源 | 状态 | 说明 |
|------|------|------|
| PR 信息 | {status_1} | {detail_1} |
| Diff | {status_2} | {detail_2} |
| 模块映射 | {status_3} | {detail_3} |
| 测试库 | {status_4} | {detail_4} |

---

## 警告与提醒

### ⚠️ 高风险警告

| 警告 | 说明 | 建议 |
|------|------|------|
| {warning_1} | {detail_1} | {suggestion_1} |

### ℹ️ 注意事项

| 事项 | 说明 |
|------|------|
| {note_1} | {detail_1} |

---

## 后续行动

| 行动 | 优先级 | 负责人 | 截止日期 |
|------|--------|--------|---------|
| {action_1} | {priority_1} | {owner_1} | {due_1} |
| {action_2} | {priority_2} | {owner_2} | {due_2} |

---

## 附录

### A. 变更文件清单

```
{file_list}
```

### B. 配置信息

| 配置项 | 值 |
|--------|-----|
| 测试类型 | {test_type} |
| 置信度阈值 | {confidence_threshold} |
| 核心模块 | {core_modules} |

### C. 分析元信息

| 元信息 | 值 |
|--------|-----|
| 分析器版本 | {analyzer_version} |
| 规则版本 | {rules_version} |
| 分析时间戳 | {timestamp} |

---

*报告由 Impact Analysis Skill 自动生成*
*生成时间: {generation_time}*
```

## 输出格式变体

### JSON 格式

```json
{
  "report": {
    "metadata": {
      "generated_at": "2026-03-25T12:00:00Z",
      "source": "github_pr",
      "duration_ms": 1523
    },
    "summary": {
      "file_count": 15,
      "lines_added": 500,
      "lines_removed": 100,
      "change_type": "feature"
    },
    "sensitivity": {
      "level": "P1",
      "score": 3,
      "factors": [
        {"factor": "core_module", "contribution": 2},
        {"factor": "security_sensitive", "contribution": 2}
      ]
    },
    "escape_result": {
      "matched": false,
      "action": "integration_plus_e2e"
    },
    "modules": {
      "direct": [
        {"name": "payment", "confidence": 0.95, "reason": "direct_change"}
      ],
      "indirect": [
        {"name": "order", "confidence": 0.75, "dependency": "calls_payment"}
      ]
    },
    "recommendations": {
      "p0": [
        {
          "test_name": "test_payment_process",
          "test_path": "tests/payment/test_billing.py",
          "confidence": 0.95,
          "reason": "direct_test"
        }
      ],
      "p1": [...],
      "p2": [...]
    },
    "warnings": [
      {"type": "low_coverage", "message": "test coverage below 50%"}
    ]
  }
}
```

### 精简 Markdown 格式

```markdown
# Impact Analysis Report

## Summary
- Files: {n} (+{add}/-{del})
- Sensitivity: {level}
- Recommended Tests: {count}

## Tests to Run

### P0 (Must)
- test_payment_process ✓
- test_payment_validate ✓

### P1 (Should)
- test_order_checkout ✓

### P2 (Could)
- test_payment_notification

## ⚠️ Warnings
{warnings}
```

## 置信度标记

| 标记 | 含义 |
|------|------|
| ✓ | 高置信度 (≥0.8)，直接采纳 |
| ⚠️ | 中等置信度 (0.5-0.8)，需确认 |
| ❌ | 低置信度 (<0.5)，建议跳过 |

## 报告渲染

### Markdown 渲染

```python
def render_markdown_report(data, template_path):
    """
    渲染 Markdown 报告
    """
    template = load_template(template_path)
    return template.render(**data)
```

### JSON 渲染

```python
def render_json_report(data):
    """
    渲染 JSON 报告
    """
    return json.dumps({"report": data}, indent=2, ensure_ascii=False)
```

## 相关模块

| 模块 | 关系 |
|------|------|
| `workflows/analysis-flow.md` | 使用模板生成报告 |
| `analyzer/main.md` | 协调报告生成 |
