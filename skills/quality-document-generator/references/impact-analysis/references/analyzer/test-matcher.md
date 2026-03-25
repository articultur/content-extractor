# 测试匹配器 / Test Matcher

## 概述

测试匹配器负责根据代码变更推荐需要回归的测试用例，是影响分析的核心输出模块。

## 匹配策略

### 策略1: 文件路径匹配

```
变更文件: src/payment/billing.py
  ↓
匹配测试: test_payment/test_billing.py
匹配规则: 路径相似度 + 模块名匹配
```

### 策略2: 模块依赖匹配

```
变更模块: payment_module
  ↓
依赖关系: payment_module → order_module → checkout_module
  ↓
推荐测试: test_payment_*, test_order_*, test_checkout_*
```

### 策略3: 函数名签名匹配

```
变更函数: process_payment(amount, currency)
  ↓
匹配测试: test_process_payment_*
匹配规则: 函数名包含
```

### 策略4: Import 依赖匹配

```
变更: 新增 import payment_processor
  ↓
匹配测试: 导入 payment_processor 的测试
匹配规则: import 语句分析
```

## 测试类型分层

| 类型 | 搜索深度 | 说明 | 适用场景 |
|------|---------|------|---------|
| **Unit** | L2 函数层 | 单元测试只覆盖单函数逻辑 | 简单函数变更 |
| **Integration** (默认) | L1+L2 | 覆盖模块间交互 | 大多数变更 |
| **E2E** | L1+L2+L3 | 完整业务流程 | 核心流程变更 |

### 默认配置

```yaml
default_test_type: integration
```

## 测试发现

### 发现机制

```python
def discover_tests(project_root):
    """
    发现项目中的测试文件
    """
    test_patterns = [
        "**/test_*.py",
        "**/*_test.py",
        "**/tests/**/*.py",
        "**/spec_*.py",
        "**/*_spec.py",
        "**/__tests__/**/*.py",
        "**/test/**/*.py",
    ]

    tests = []
    for pattern in test_patterns:
        tests.extend(glob.glob(f"{project_root}/{pattern}"))

    return tests
```

### 测试元信息提取

```yaml
test_metadata:
  file_path: "tests/payment/test_billing.py"
  test_framework: "pytest"
  test_functions:
    - name: "test_process_payment_success"
      line: 10
      covered_functions:
        - "payment.process"
        - "payment.validate"
    - name: "test_process_payment_failure"
      line: 25
      covered_functions:
        - "payment.process"

  module_under_test: "payment.billing"
  dependencies:
    - "payment.process"
    - "payment.validate"
    - "db.insert"
```

## 匹配算法

### 多级匹配

```python
def match_tests(changed_items, test_database, config):
    """
    多级匹配算法
    """
    recommendations = []

    # Level 1: 直接文件匹配
    direct_matches = match_by_file_path(changed_items, test_database)
    recommendations.extend(direct_matches)

    # Level 2: 模块依赖匹配
    module_matches = match_by_module_deps(changed_items, test_database)
    recommendations.extend(module_matches)

    # Level 3: 函数签名匹配
    function_matches = match_by_function(changed_items, test_database)
    recommendations.extend(function_matches)

    # Level 4: 语义匹配 (LLM)
    if config.use_llm_matching:
        semantic_matches = match_by_llm(changed_items, test_database)
        recommendations.extend(semantic_matches)

    # 去重和优先级排序
    recommendations = deduplicate_and_rank(recommendations)

    return recommendations
```

### 匹配置信度

```yaml
confidence_levels:
  direct_file_match:
    level: "high"
    score: 0.95
    reason: "文件路径直接对应"

  module_match:
    level: "high"
    score: 0.90
    reason: "测试模块与变更模块相同"

  function_match:
    level: "medium"
    score: 0.75
    reason: "测试函数名包含变更函数名"

  import_match:
    level: "medium"
    score: 0.70
    reason: "测试导入变更模块"

  llm_semantic_match:
    level: "variable"
    score: "0.5-0.9"
    reason: "基于 LLM 语义分析"
```

## 过滤规则

### 逃逸规则过滤

```python
def apply_escape_rules(recommendations, pr_context):
    """
    应用逃逸规则过滤
    """
    filtered = []

    for rec in recommendations:
        skip = False

        for rule in escape_rules:
            if rule.matches(pr_context, rec):
                if rule.action == "skip":
                    skip = True
                elif rule.action == "downgrade_priority":
                    rec.priority = "P2"

        if not skip:
            filtered.append(rec)

    return filtered
```

### 用户规则过滤

```yaml
user_filter_rules:
  # 忽略某些测试
  ignore:
    - pattern: "**/test_ui_*.py"
      reason: "UI 测试跳过"

  # 强制包含某些测试
  include:
    - pattern: "**/test_payment_*.py"
      reason: "核心支付测试"

  # 否定关联
  not_related:
    - test: "test_payment_mock.py"
      module: "payment_module"
      reason: "只使用 mock，不测真实逻辑"
```

## 推荐输出

```yaml
test_recommendations:
  summary:
    total_recommended: 15
    by_priority:
      P0: 5
      P1: 7
      P2: 3

  recommended:
    - test_name: "test_payment_process_success"
      test_path: "tests/payment/test_billing.py"
      priority: "P0"
      confidence: 0.95
      reason: "直接测试变更模块"
      evidence:
        supporting:
          - "测试 payment.billing.process 函数"
          - "文件路径直接匹配"
        opposing: []

    - test_name: "test_order_checkout_with_payment"
      test_path: "tests/order/test_checkout.py"
      priority: "P1"
      confidence: 0.75
      reason: "通过 order_module 间接依赖"
      evidence:
        supporting:
          - "订单结账涉及 payment 调用"
          - "模块间有依赖关系"
        opposing:
          - "测试使用较多 mock"

  optional:
    - test_name: "test_payment_notification_email"
      test_path: "tests/notification/test_email.py"
      priority: "P2"
      confidence: 0.5
      reason: "通知模块被 payment 调用"
      suggestion: "可选执行，置信度中等"
```

## 优先级计算

```python
def calculate_test_priority(test, changed_modules):
    """
    计算测试优先级
    """
    priority = "P2"  # 默认最低

    # P0: 直接测试变更模块
    if test.module in changed_modules:
        priority = "P0"
        return priority

    # P1: 间接依赖变更模块
    if has_dependency(test.module, changed_modules):
        priority = "P1"

    return priority
```

## 对比分析 (置信度透明度)

```yaml
# 输出示例
association: test_payment.py → payment_module

supporting_evidence:
  - "✓ test_payment.py 调用了 payment_module.process()"
  - "✓ 文件名高度相似"
  - "✓ 测试函数覆盖 process 函数"

opposing_evidence:
  - "✗ test_payment.py 主要使用 mock，非真实调用"
  - "✗ 该测试被用户标记为 UI 测试"

conclusion:
  recommend: true
  priority_adjustment: "downgrade to P1"
  reason: "虽然有关联，但主要使用 mock"
```

## 测试覆盖率整合

```python
def integrate_coverage(recommendations, coverage_data):
    """
    整合测试覆盖率数据
    """
    for rec in recommendations:
        coverage = coverage_data.get(rec.test_path, {})
        rec.coverage = coverage.get("line_rate", 0)
        rec.covered_lines = coverage.get("covered_lines", [])
        rec.missed_lines = coverage.get("missed_lines", [])

        # 低覆盖率则提高优先级
        if rec.coverage < 0.5:
            rec.priority = elevate_priority(rec.priority)

    return recommendations
```

## 使用示例

```python
# 基本匹配
matcher = TestMatcher(config)
recommendations = matcher.match(
    changed_files=["src/payment/billing.py"],
    changed_modules=["payment_module"]
)

# 指定测试类型
recommendations = matcher.match(
    changed_files=["src/payment/billing.py"],
    test_type="e2e"  # 覆盖更多端到端测试
)

# 查看结果
for rec in recommendations:
    print(f"[{rec.priority}] {rec.test_name} ({rec.confidence})")
    print(f"  理由: {rec.reason}")
```

## 配置参数

```yaml
test_matcher:
  # 测试发现
  discovery:
    patterns:
      - "**/test_*.py"
      - "**/*_test.py"
      - "**/tests/**/*.py"

  # 匹配策略
  matching:
    strategies:
      - file_path
      - module_dependency
      - function_signature
      - import_analysis

    weights:
      direct_match: 0.4
      module_match: 0.3
      function_match: 0.2
      llm_match: 0.1

  # 过滤
  filtering:
    min_confidence: 0.3
    max_recommendations: 50

  # LLM
  llm:
    enabled: true
    use_comparative_analysis: true
```

## 相关模块

| 模块 | 关系 |
|------|------|
| `module-mapper.md` | 接收模块映射结果 |
| `diff-parser.md` | 接收变更文件列表 |
| `sensitivity` | 使用敏感度调整优先级 |
| `prompts/test-matching.md` | LLM 匹配提示词 |
| `templates/impact-report.md` | 输出最终报告 |
