# 模块映射器 / Module Mapper

## 概述

模块映射器负责将变更文件映射到对应的业务模块，是 L2 模块级分析的核心。

## 映射层级

```
┌─────────────────────────────────────────────────────────────┐
│                     映射层级示意                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  文件路径                                                    │
│    │                                                        │
│    ▼                                                        │
│  ┌──────────────────┐                                      │
│  │   src/payment/   │ ← 目录名直接映射                       │
│  │     billing.py   │                                      │
│  └────────┬─────────┘                                      │
│           │                                                 │
│           ▼                                                 │
│  ┌──────────────────┐                                      │
│  │ payment_module   │ ← 业务模块                            │
│  │ (payment/billing)│                                     │
│  └────────┬─────────┘                                      │
│           │                                                 │
│           ▼                                                 │
│  ┌──────────────────┐                                      │
│  │   payment_service │ ← 服务聚合                           │
│  └──────────────────┘                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 映射策略

### 策略1: 目录名映射 (最优先)

```yaml
mapping_rules:
  - path_pattern: "^src/(payment|billing)/"
    module: "payment_module"

  - path_pattern: "^src/(auth|login|oauth)/"
    module: "auth_module"

  - path_pattern: "^src/(user|customer)/"
    module: "user_module"
```

### 策略2: 文件名模式映射

```yaml
mapping_rules:
  - file_pattern: "payment*.py"
    module: "payment_module"

  - file_pattern: "*_payment_*.py"
    module: "payment_module"
```

### 策略3: 模块声明映射

```python
# 检测文件开头的模块声明
# __module__ = "payment.billing"

mapping_rules:
  - declaration: "__module__"
    module: "payment_module"
```

### 策略4: LLM 推断映射

```yaml
llm_fallback:
  enabled: true
  confidence_threshold: 0.7

  prompt: |
    根据文件路径和内容，推断该文件属于哪个业务模块。

    文件路径: {file_path}
    文件内容摘要: {content_summary}

    返回格式:
    - 模块名: xxx
    - 置信度: 0.xx
    - 理由: xxx
```

## 映射规则定义

### 默认规则 (通用)

```yaml
default_mappings:
  # 支付相关
  payment: payment_module
  billing: payment_module
  invoice: payment_module
  transaction: payment_module

  # 认证相关
  auth: auth_module
  login: auth_module
  oauth: auth_module
  permission: auth_module
  role: auth_module

  # 用户相关
  user: user_module
  profile: user_module
  account: user_module

  # 订单相关
  order: order_module
  cart: order_module
  checkout: order_module

  # 通知相关
  notification: notification_module
  email: notification_module
  sms: notification_module
```

### 用户自定义规则

```yaml
# 用户可通过配置添加自定义映射
custom_mappings:
  # 文件 → 模块
  "src/legacy_payment/*.py": legacy_payment_module
  "features/payment/*.py": new_payment_module

  # 模块 → 聚合服务
  "payment_module, notification_module": payment_service
```

## 依赖关系分析

### 依赖类型

| 类型 | 说明 | 示例 |
|------|------|------|
| 导入依赖 | import/require | `from payment import Process` |
| 调用依赖 | 函数调用 | `payment.process()` |
| 继承依赖 | 类继承 | `class X extends Payment` |
| 配置依赖 | 配置引用 | `payment.enabled: true` |

### 依赖方向

```
正向依赖: A → B (A 依赖 B)
反向依赖: A ← B (B 依赖 A)

影响分析:
  变更 A → 影响 A 的下游 (依赖 A 的模块)
  变更 A → 影响 A 的上游 (A 依赖的模块)
```

### 下游依赖追踪

```python
def get_downstream_modules(module, dependency_graph):
    """
    获取指定模块的下游依赖模块
    下游 = 依赖该模块的模块
    """
    downstream = set()

    for other_module, dependencies in dependency_graph.items():
        if module in dependencies:
            downstream.add(other_module)

    return downstream
```

## 聚合服务识别

```yaml
# 服务聚合规则
service_aggregation:
  payment_service:
    modules:
      - payment_module
      - billing_module
      - invoice_module
    related_tests:
      - test_payment_*.py
      - test_billing_*.py

  order_service:
    modules:
      - order_module
      - cart_module
      - checkout_module
```

## 模块重要性评估

```python
def assess_module_importance(module_name):
    """
    评估模块重要性
    """
    importance = {
        "is_core": False,
        "is_shared": False,
        "downstream_count": 0,
        "is_public_api": False
    }

    # 核心模块
    if module_name in CORE_MODULES:
        importance["is_core"] = True

    # 被多个模块依赖
    if downstream_count > 3:
        importance["is_shared"] = True

    # 公开 API
    if module_name.endswith("_api") or module_name.endswith("_service"):
        importance["is_public_api"] = True

    return importance
```

## 模块变更影响

```yaml
impact_assessment:
  # 直接影响
  direct_impact:
    - 变更文件所属模块

  # 间接影响
  indirect_impact:
    - 直接依赖的模块
    - 间接依赖的模块 (可选, L4)

  # 传播影响
  propagation_impact:
    - 下游依赖模块
    - 聚合服务包含的其他模块
```

## 映射结果

```yaml
module_mapping_result:
  files:
    - file_path: "src/payment/billing.py"
      mapped_module: "payment_module"
      confidence: 0.95
      mapping_strategy: "directory_name"

  modules:
    - name: "payment_module"
      importance:
        is_core: true
        downstream_count: 5
      confidence: 0.9
      related_files:
        - "src/payment/billing.py"
        - "src/payment/invoice.py"
      upstream_dependencies:
        - "auth_module"
        - "notification_module"
      downstream_dependents:
        - "order_module"
        - "checkout_module"
```

## 置信度计算

```python
def calculate_mapping_confidence(file_path, mapped_module, context):
    confidence = 0.5  # 基础置信度

    # 目录名精确匹配
    if matches_directory_name(file_path, mapped_module):
        confidence += 0.3

    # 文件名模式匹配
    if matches_file_pattern(file_path, mapped_module):
        confidence += 0.15

    # LLM 确认
    if context.get("llm_confirmed"):
        confidence += 0.1

    # 依赖关系确认
    if context.get("dependency_confirmed"):
        confidence += 0.1

    return min(confidence, 1.0)
```

## 冲突解决

当一个文件可能属于多个模块时:

```python
def resolve_mapping_conflict(file_path, candidate_modules):
    """
    冲突解决策略:
    1. 目录路径最长匹配优先
    2. 用户显式配置优先
    3. LLM 判断参考
    """
    if len(candidate_modules) == 1:
        return candidate_modules[0]

    # 选择路径匹配最长的
    best_match = max(candidate_modules,
        key=lambda m: len(get_common_path(file_path, m)))

    return best_match
```

## 使用示例

```python
# 基本映射
mapper = ModuleMapper(config)
result = mapper.map_files(changed_files)

# 查看映射结果
for file_result in result.files:
    print(f"{file_result.file_path} → {file_result.mapped_module}")

# 查看模块依赖
for module_result in result.modules:
    print(f"模块: {module_result.name}")
    print(f"  上游: {module_result.upstream_dependencies}")
    print(f"  下游: {module_result.downstream_dependents}")
```

## 配置参数

```yaml
module_mapper:
  # 映射策略优先级
  strategy_priority:
    - directory_name
    - file_pattern
    - module_declaration
    - llm_inference

  # 依赖分析深度
  dependency_depth:
    direct: true
    indirect: true
    transitive: false  # 可选

  # LLM 配置
  llm:
    enabled: true
    confidence_threshold: 0.7
    fallback_to_directory: true
```

## 相关模块

| 模块 | 关系 |
|------|------|
| `diff-parser.md` | 提供变更文件列表 |
| `test-matcher.md` | 接收模块映射结果 |
| `sensitivity` | 使用模块重要性评估敏感度 |
| `prompts/impact-analysis.md` | LLM 分析提示词 |
