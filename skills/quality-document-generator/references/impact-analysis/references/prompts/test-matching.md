# 测试匹配提示词 / Test Matching Prompt

## 概述

测试匹配提示词用于指导 LLM 根据代码变更推荐具体的测试用例，并提供匹配置信度。

## 使用场景

| 场景 | 说明 |
|------|------|
| 候选测试筛选 | 从测试库中筛选相关测试 |
| 测试优先级排序 | 对候选测试排序 |
| 匹配置信度评估 | 评估每个匹配的质量 |
| 缺失测试识别 | 识别可能缺失的测试 |

## 提示词模板

### 基础测试匹配模板

```markdown
## 任务

你是一位测试策略专家，负责根据代码变更推荐需要执行的测试用例。

## 输入信息

### 变更摘要

| 指标 | 值 |
|------|-----|
| 变更文件 | {changed_files} |
| 涉及模块 | {affected_modules} |
| 变更类型 | {change_type} |
| 代码分析 | {code_analysis_summary} |

### 可用测试库

{test_inventory}

### 模块映射

{module_mappings}

### 历史测试执行记录

{historical_execution}

## 匹配策略

### 1. 直接匹配

基于文件路径和模块名匹配:

```yaml
direct_matches:
  - test: "test_payment.py"
    matched_on: "file_path_similarity"
    confidence: 0.95
    reason: "文件名与模块名完全匹配"

  - test: "test_billing.py"
    matched_on: "same_module"
    confidence: 0.90
    reason: "billing.py 和 test_billing.py 同属 payment 模块"
```

### 2. 依赖匹配

基于模块间依赖关系匹配:

```yaml
dependency_matches:
  - test: "test_order_checkout.py"
    matched_on: "downstream_dependency"
    module: "order_module"
    depends_on: "payment_module"
    confidence: 0.75
    reason: "order.checkout 调用 payment.process"
```

### 3. 语义匹配

基于业务逻辑语义匹配:

```yaml
semantic_matches:
  - test: "test_payment_notification.py"
    matched_on: "business_logic"
    confidence: 0.60
    reason: "支付成功会触发通知，业务逻辑相关"
```

## 匹配置信度

### 置信度等级

| 等级 | 分值 | 说明 |
|------|------|------|
| 高 | 0.9-1.0 | 直接匹配，证据充分 |
| 中高 | 0.7-0.9 | 相关性强，有一定证据 |
| 中 | 0.5-0.7 | 可能相关，需要确认 |
| 低 | 0.3-0.5 | 弱相关，可选执行 |
| 极低 | < 0.3 | 几乎不相关，建议跳过 |

### 置信度因素

```yaml
confidence_factors:
  # 增加置信度
  increases:
    - factor: "文件路径直接匹配"
      bonus: +0.2
    - factor: "测试函数调用变更函数"
      bonus: +0.3
    - factor: "历史执行中发现过类似关联"
      bonus: +0.15
    - factor: "测试覆盖变更的代码行"
      bonus: +0.2

  # 降低置信度
  decreases:
    - factor: "测试大量使用 mock"
      penalty: -0.2
    - factor: "测试标记为 'ui_only'"
      penalty: -0.3
    - factor: "测试不执行断言"
      penalty: -0.4
    - factor: "测试文件很久未更新 (>1年)"
      penalty: -0.15
```

## 输出格式

```json
{
  "matching_results": [
    {
      "test_name": "test_payment_process_success",
      "test_path": "tests/payment/test_billing.py::test_payment_process_success",
      "matched_on": "file_path + function_call",
      "priority": "P0",
      "confidence": 0.95,
      "module": "payment_module",
      "reasons": [
        "文件路径与变更文件同模块",
        "测试函数直接调用变更的 process() 函数"
      ],
      "evidence": {
        "supporting": [
          "test_payment_process() 调用 payment.process()",
          "测试覆盖变更的核心逻辑"
        ],
        "opposing": [
          "测试使用 mock 未覆盖真实 DB"
        ]
      },
      "covered_lines": [10, 15, 20, 25],
      "missed_lines": [30, 35]
    }
  ],
  "recommended_order": [
    "test_payment_process_success",
    "test_payment_process_failure",
    "test_order_checkout_with_payment",
    "test_payment_notification_email"
  ],
  "missing_tests": [
    {
      "description": "缺少对新增错误处理的测试",
      "suggested_test_name": "test_payment_invalid_amount_error",
      "priority": "high"
    }
  ],
  "confidence_summary": {
    "overall": 0.82,
    "high_confidence_count": 5,
    "medium_confidence_count": 3,
    "low_confidence_count": 2
  }
}
```

## 对比分析 (置信度透明度)

```markdown
## 详细对比分析

### 测试: test_payment.py → payment_module

#### 支持关联的证据 ✓

1. **文件路径匹配** (+0.15)
   - test_payment.py 与 payment/billing.py 路径相似
   - 两者都在 payment/ 目录下

2. **函数调用关系** (+0.30)
   - test_payment_process() 调用 billing.process()
   - test_payment_validate() 调用 billing.validate()

3. **历史执行模式** (+0.10)
   - 过去 5 次 payment_module 变更都执行了该测试
   - 该测试曾发现过 2 个 bug

#### 反对关联的证据 ✗

1. **Mock 使用过多** (-0.20)
   - 测试使用 mock_billing, mock_db
   - 非真实调用，验证有限

2. **覆盖不完整** (-0.15)
   - 未覆盖新增的错误处理分支
   - 第 30-35 行的新逻辑未被测试

3. **测试分类** (-0.10)
   - 该测试被标记为 'integration_smoke'
   - 不适合作为深度回归测试

#### 综合评分

| 因素 | 贡献 |
|------|------|
| 基础分 | 0.50 |
| 支持证据 | +0.55 |
| 反对证据 | -0.45 |
| **最终分** | **0.60** |

#### 建议

- 建议关联，但优先级调整为 **P1** (非 P0)
- 补充建议: 执行 test_payment_full_integration.py
```

## 上下文变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `{changed_files}` | 变更文件列表 | ["src/payment/billing.py"] |
| `{affected_modules}` | 受影响模块 | ["payment_module"] |
| `{change_type}` | 变更类型 | feature, bug_fix |
| `{code_analysis_summary}` | 代码分析摘要 | 函数、业务逻辑 |
| `{test_inventory}` | 测试清单 | 测试文件、函数、覆盖范围 |
| `{module_mappings}` | 模块映射 | 文件→模块 |
| `{historical_execution}` | 历史执行 | 成功/失败模式 |

## 测试清单格式

```yaml
test_inventory:
  - path: "tests/payment/test_billing.py"
    functions:
      - name: "test_payment_process_success"
        covered_functions: ["payment.process", "payment.validate"]
        lines: [10, 25]
      - name: "test_payment_process_failure"
        covered_functions: ["payment.process"]
        lines: [30, 40]
    module: "payment_module"

  - path: "tests/order/test_checkout.py"
    functions:
      - name: "test_order_checkout_with_payment"
        covered_functions: ["order.checkout", "payment.process"]
        lines: [5, 15]
    module: "order_module"
```

## 过滤规则

```markdown
## 过滤后的候选测试

### 已排除

| 测试 | 排除原因 |
|------|---------|
| test_ui_payment.py | 命中 test_ui_* 忽略规则 |
| test_payment_manual.py | 标记为 manual，不自动执行 |
| test_payment_skipped.py | 已被 skip 装饰器禁用 |

### 保留

| 测试 | 保留原因 |
|------|---------|
| test_payment_process_success | 直接匹配 |
| test_order_checkout.py | 依赖匹配 |
```

## 测试优先级计算

```python
def calculate_priority(test, change_context):
    priority = "P2"  # 默认

    # P0: 直接匹配且高置信度
    if test.matched_on in ["file_path", "module"]:
        if test.confidence >= 0.9:
            priority = "P0"

    # P1: 依赖匹配或中高置信度
    elif test.matched_on in ["dependency", "function_call"]:
        if test.confidence >= 0.7:
            priority = "P1"

    # P2: 语义匹配或中低置信度
    elif test.matched_on == "semantic":
        priority = "P2"

    return priority
```

## 缺失测试识别

```yaml
missing_tests:
  - scenario: "新增的错误处理逻辑"
    affected_code: "billing.py lines 30-35"
    suggested:
      - name: "test_payment_invalid_amount_error"
        priority: "high"
        reason: "覆盖新增的错误处理"

  - scenario: "新增的验证规则"
    affected_code: "billing.py lines 15-20"
    suggested:
      - name: "test_payment_validation_rules"
        priority: "medium"
```

## 使用示例

```python
prompt = TestMatchingPrompt(
    changed_files=["src/payment/billing.py"],
    affected_modules=["payment_module"],
    change_type="feature",
    code_analysis_summary={
        "functions": ["process", "validate"],
        "new_logic": "错误处理分支"
    },
    test_inventory=[
        {
            "path": "tests/payment/test_billing.py",
            "functions": ["test_payment_process_success"]
        }
    ],
    module_mappings={
        "billing.py": "payment_module"
    }
)

result = llm.analyze(prompt.render())

# 输出匹配结果
for test in result.matching_results:
    print(f"[{test.priority}] {test.test_name} ({test.confidence})")
    print(f"  理由: {test.reasons}")
```

## 配置参数

```yaml
test_matching:
  # 匹配策略权重
  weights:
    direct_match: 0.4      # 文件路径直接匹配
    module_match: 0.3       # 模块匹配
    dependency_match: 0.2   # 依赖匹配
    semantic_match: 0.1     # 语义匹配

  # 置信度阈值
  thresholds:
    direct_execute: 0.8     # >= 0.8 直接执行
    confirm_first: 0.5      # 0.5-0.8 需确认
    skip: 0.5              # < 0.5 跳过

  # 过滤规则
  filters:
    ignore_patterns:
      - "**/test_ui_*.py"
      - "**/test_manual_*.py"
```

## 相关模块

| 模块 | 关系 |
|------|------|
| `main.md` | 使用测试匹配结果 |
| `impact-analysis.md` | 提供影响分析上下文 |
| `code-analysis.md` | 提供代码分析上下文 |
| `module-mapper.md` | 提供模块映射信息 |
