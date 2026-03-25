# 用户配置 / User Configuration

## 概述

用户配置模块负责管理和持久化用户的配置，包括核心模块定义、规则覆盖、敏感度设置等。

## 配置存储

### 存储位置

```
~/.impact-analysis/
├── config.yaml           # 全局配置
├── rules/                # 规则目录
│   └── {project_id}/
│       └── user_rules.yaml
├── cache/                # 缓存目录
└── logs/                 # 日志目录
```

### 配置文件格式

```yaml
# ~/.impact-analysis/config.yaml
impact_analysis:
  version: "1.0"

  # 默认测试类型
  default_test_type: integration  # unit | integration | e2e

  # PR 处理
  pr:
    max_size_mb: 5
    auto_split: true
    split_threshold: 30  # 文件数超过此值分批

  # 置信度阈值
  confidence:
    direct: 0.8      # >= 0.8 直接执行
    confirm: 0.5     # 0.5-0.8 需确认
    skip: 0.5        # < 0.5 跳过

  # 工具配置
  tools:
    code_platform: github  # github | gitlab | custom
    use_mcp: true
    use_cache: true

  # 输出配置
  output:
    format: markdown  # markdown | json | yaml
    show_evidence: true
    show_comparative: true
```

### 项目规则文件

```yaml
# ~/.impact-analysis/rules/{project_id}/user_rules.yaml
project:
  id: "my-project"
  name: "My Project"
  created_at: "2026-03-25"
  updated_at: "2026-03-25"

# 核心模块定义
core_modules:
  - "payment"
  - "auth"
  - "order"

# 安全敏感模块
security_sensitive:
  - "auth"
  - "permission"
  - "payment"

# 监管域模块
compliance_domains:
  - "finance"
  - "medical"

# 用户定义的模块映射
module_mappings:
  - file_pattern: "src/payment/*.py"
    module: "payment"
  - file_pattern: "src/legacy_payment/*.py"
    module: "legacy_payment"

# 测试关联规则
test_associations:
  # 否定关联
  - test: "test_payment_ui.py"
    not_related_to: ["payment_module"]
    reason: "只测 UI，使用 mock"

  # 肯定关联
  - test: "test_payment_integration.py"
    related_to: ["payment_module", "db"]
    reason: "真实集成测试"

# 敏感度覆盖
sensitivity_overrides:
  - module: "legacy_payment"
    level: "P0"
    reason: "核心遗留模块"

# 忽略模式
ignore_patterns:
  - pattern: "**/test_ui_*.py"
    reason: "UI 测试跳过"
  - pattern: "**/test_manual_*.py"
    reason: "手动测试跳过"
```

## 配置加载

### 加载流程

```python
class ConfigLoader:
    def __init__(self, config_dir="~/.impact-analysis"):
        self.config_dir = Path(config_dir).expanduser()
        self.global_config = None
        self.project_rules = {}

    def load(self, project_id=None):
        """
        加载配置
        """
        # 1. 加载全局配置
        self.global_config = self._load_global_config()

        # 2. 加载项目规则 (如果指定了项目)
        if project_id:
            self.project_rules = self._load_project_rules(project_id)

        # 3. 合并配置
        return self._merge_configs()

    def _load_global_config(self):
        """
        加载全局配置
        """
        config_path = self.config_dir / "config.yaml"
        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f)
        return self._default_config()

    def _load_project_rules(self, project_id):
        """
        加载项目规则
        """
        rules_path = self.config_dir / "rules" / project_id / "user_rules.yaml"
        if rules_path.exists():
            with open(rules_path) as f:
                return yaml.safe_load(f)
        return {}
```

### 配置优先级

```
用户项目规则 > 全局项目规则 > 默认配置
```

| 优先级 | 来源 | 说明 |
|--------|------|------|
| 最高 | 命令行参数 | 运行时指定 |
| 高 | 用户项目规则 | `~/.impact-analysis/rules/{project}/` |
| 中 | 全局项目规则 | `~/.impact-analysis/config.yaml` |
| 低 | 默认配置 | 代码中的默认值 |

## 配置项说明

### 核心模块配置

```yaml
core_modules:
  - "payment"        # 支付模块
  - "auth"           # 认证模块
  - "order"          # 订单模块

# 模块优先级 (可选)
module_priority:
  payment: 1
  auth: 2
  order: 3
```

### 安全敏感模块

```yaml
security_sensitive:
  - "auth"
  - "permission"
  - "crypto"
  - "payment"
  - "user_data"
```

### 测试类型默认

```yaml
default_test_type: integration
# 可选值:
#   - unit: 单元测试
#   - integration: 集成测试 (默认)
#   - e2e: 端到端测试
```

### 逃逸规则配置

```yaml
escape_rules:
  # 是否启用
  enabled: true

  # 规则文件位置
  rules_file: null  # null 表示使用内置规则

  # 自定义规则
  custom_rules:
    - condition: "files match '^(docs/|README)'"
      action: "skip_analysis"
```

## 配置更新

### 更新流程

```python
def update_config(project_id, updates):
    """
    更新配置
    """
    config = load_config(project_id)

    # 合并更新
    for key, value in updates.items():
        config[key] = value

    # 保存
    save_config(project_id, config)

    return config


def add_user_rule(project_id, rule):
    """
    添加用户规则
    """
    rules = load_rules(project_id)

    if 'test_associations' not in rules:
        rules['test_associations'] = []

    rules['test_associations'].append(rule)
    rules['updated_at'] = datetime.now().isoformat()

    save_rules(project_id, rules)
```

### 对话式配置更新

```python
def handle_config_update(statement, current_config):
    """
    处理用户配置更新请求
    """
    # 检测配置类型
    if "核心模块" in statement or "core module" in statement.lower():
        modules = extract_modules(statement)
        return {"core_modules": modules}

    elif "安全" in statement or "security" in statement.lower():
        modules = extract_modules(statement)
        return {"security_sensitive": modules}

    elif "忽略" in statement or "ignore" in statement.lower():
        patterns = extract_patterns(statement)
        return {"ignore_patterns": patterns}

    elif "测试类型" in statement or "test type" in statement.lower():
        test_type = extract_test_type(statement)
        return {"default_test_type": test_type}

    return None
```

## 配置验证

### 验证规则

```python
def validate_config(config):
    """
    验证配置有效性
    """
    errors = []
    warnings = []

    # 验证测试类型
    if config.get('default_test_type') not in ['unit', 'integration', 'e2e']:
        errors.append("default_test_type must be unit, integration, or e2e")

    # 验证置信度阈值
    confidence = config.get('confidence', {})
    if confidence.get('direct', 0) < confidence.get('confirm', 0):
        warnings.append("direct threshold should be >= confirm threshold")

    # 验证模块名
    for module in config.get('core_modules', []):
        if not module.replace('_', '').isalnum():
            errors.append(f"Invalid module name: {module}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }
```

## 持久化

### 保存配置

```python
def save_config(project_id, config):
    """
    保存配置到文件
    """
    config_dir = Path("~/.impact-analysis").expanduser()

    if project_id:
        config_dir = config_dir / "rules" / project_id
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "user_rules.yaml"
    else:
        config_file = config_dir / "config.yaml"

    config_dir.mkdir(parents=True, exist_ok=True)

    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
```

### 导入/导出

```python
def export_config(project_id, output_path):
    """
    导出配置
    """
    config = load_config(project_id)

    with open(output_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)


def import_config(input_path, project_id):
    """
    导入配置
    """
    with open(input_path) as f:
        config = yaml.safe_load(f)

    save_config(project_id, config)
```

## 使用示例

```python
# 加载配置
loader = ConfigLoader()
config = loader.load(project_id="my-project")

print(f"默认测试类型: {config.default_test_type}")
print(f"核心模块: {config.core_modules}")
print(f"安全敏感模块: {config.security_sensitive}")

# 更新配置
update_config("my-project", {
    "core_modules": ["payment", "auth", "order", "inventory"]
})

# 添加用户规则
add_user_rule("my-project", {
    "test": "test_payment_ui.py",
    "not_related_to": ["payment_module"],
    "reason": "只测 UI mock"
})

# 对话式更新
new_config = handle_config_update(
    "把 payment 模块设为核心模块",
    current_config
)
if new_config:
    update_config("my-project", new_config)
```

## 相关模块

| 模块 | 关系 |
|------|------|
| `main.md` | 使用配置 |
| `test-matcher.md` | 使用规则过滤 |
| `module-mapper.md` | 使用模块映射 |
| `sensitivity` | 使用敏感度配置 |
