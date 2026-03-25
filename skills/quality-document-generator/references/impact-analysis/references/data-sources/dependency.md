# 依赖解析 / Dependency Parser

## 概述

依赖解析模块负责分析项目中的依赖声明和模块间依赖关系，构建依赖图谱。

## 依赖类型

| 类型 | 说明 | 示例 |
|------|------|------|
| 外部依赖 | 第三方包 | requests, lodash, com.google |
| 内部依赖 | 项目内模块 | payment, auth, user |
| 系统依赖 | 语言/平台内置 | os, sys, console |
| 可选依赖 | 条件引入 | pytest-xdist (可选) |
| 开发依赖 | 仅开发使用 | pytest, eslint |

## 支持的依赖声明文件

| 语言 | 文件 | 格式 |
|------|------|------|
| Python | requirements.txt | pip |
| Python | pyproject.toml | poetry/pip |
| Python | setup.py | setuptools |
| Python | setup.cfg | setuptools |
| JavaScript | package.json | npm |
| JavaScript | package-lock.json | npm (锁) |
| TypeScript | package.json | npm |
| Java | pom.xml | Maven |
| Java | build.gradle | Gradle |
| Go | go.mod | Go modules |
| Ruby | Gemfile | RubyGems |
| Rust | Cargo.toml | Cargo |
| .NET | *.csproj | NuGet |

## 解析输出

### 外部依赖

```yaml
external_dependencies:
  - name: "requests"
    version: "^2.28.0"
    type: "runtime"         # runtime | dev
    source_file: "requirements.txt"

  - name: "pytest"
    version: "^7.0.0"
    type: "dev"
    source_file: "requirements-dev.txt"
```

### 内部依赖

```yaml
internal_dependencies:
  # 模块依赖
  modules:
    payment:
      depends_on:
        - auth
        - notification
      used_by:
        - order
        - checkout

  # 文件依赖
  files:
    "src/payment/billing.py":
      imports:
        - "payment.process"
        - "auth.validate"
        - "db"
      imported_by:
        - "src/order/checkout.py"
        - "src/api/payment.py"
```

## 解析策略

### 1. 依赖声明文件解析

```python
def parse_requirements_file(content):
    """
    解析 requirements.txt
    """
    dependencies = []

    for line in content.split('\n'):
        line = line.strip()

        # 跳过空行和注释
        if not line or line.startswith('#'):
            continue

        # 跳过 -r (include) 和 -e (editable)
        if line.startswith(('-r', '-e', '--', '-i', '-f')):
            continue

        # 解析依赖
        dep = parse_requirement_line(line)
        if dep:
            dependencies.append(dep)

    return dependencies


def parse_requirement_line(line):
    """
    解析单行依赖
    支持格式:
    - requests==2.28.0
    - requests>=2.28.0
    - requests[security]>=2.28.0
    """
    import re

    # 匹配包名和版本
    pattern = r'^([a-zA-Z0-9][-a-zA-Z0-9._]*)((?:[><=!]+.*)?)$'
    match = re.match(pattern, line)

    if match:
        name = match.group(1)
        version = match.group(2) or ""

        # 处理 extras (如 requests[security])
        extras = re.findall(r'\[([^\]]+)\]', version)
        version = re.sub(r'\[.*\]', '', version)

        return Dependency(
            name=name,
            version=version,
            extras=extras
        )

    return None
```

### 2. package.json 解析

```python
import json

def parse_package_json(content):
    """
    解析 package.json
    """
    data = json.loads(content)

    dependencies = []

    # dependencies
    for name, version in data.get('dependencies', {}).items():
        dependencies.append(Dependency(
            name=name,
            version=version,
            type='runtime'
        ))

    # devDependencies
    for name, version in data.get('devDependencies', {}).items():
        dependencies.append(Dependency(
            name=name,
            version=version,
            type='dev'
        ))

    return dependencies
```

### 3. go.mod 解析

```python
def parse_go_mod(content):
    """
    解析 go.mod
    """
    dependencies = []
    module_name = None

    for line in content.split('\n'):
        line = line.strip()

        if line.startswith('module '):
            module_name = line.split()[1]
        elif line.startswith('require ('):
            # 多行 require
            in_require_block = True
        elif line.startswith(')'):
            in_require_block = False
        elif line.startswith('//'):
            # 注释
            continue
        elif line and not line.startswith('go '):
            if in_require_block or line.startswith('"'):
                # 单行 require 或间接依赖
                dep = parse_go_require_line(line)
                if dep:
                    dependencies.append(dep)

    return DependencyInfo(
        module=module_name,
        requirements=dependencies
    )


def parse_go_require_line(line):
    """
    解析 go require 行
    """
    import re

    # 移除括号和引号
    line = line.strip('() "')

    parts = line.split()
    if len(parts) >= 1:
        name = parts[0]
        version = parts[1] if len(parts) > 1 else ""

        return Dependency(
            name=name,
            version=version,
            type='runtime'
        )

    return None
```

## 依赖图构建

### 模块依赖图

```python
class DependencyGraph:
    def __init__(self):
        self.nodes = set()
        self.edges = {}  # node -> set of dependencies

    def add_module(self, module):
        self.nodes.add(module)

    def add_dependency(self, from_module, to_module):
        if from_module not in self.edges:
            self.edges[from_module] = set()
        self.edges[from_module].add(to_module)

    def get_dependencies(self, module):
        """获取模块的直接依赖"""
        return self.edges.get(module, set())

    def get_dependents(self, module):
        """获取依赖该模块的模块"""
        dependents = set()
        for m, deps in self.edges.items():
            if module in deps:
                dependents.add(m)
        return dependents

    def get_all_dependencies(self, module, visited=None):
        """获取模块的所有依赖 (递归)"""
        if visited is None:
            visited = set()

        if module in visited:
            return set()

        visited.add(module)
        all_deps = set()

        for dep in self.get_dependencies(module):
            all_deps.add(dep)
            all_deps.update(self.get_all_dependencies(dep, visited))

        return all_deps

    def get_all_dependents(self, module, visited=None):
        """获取所有依赖该模块的模块 (递归)"""
        if visited is None:
            visited = set()

        if module in visited:
            return set()

        visited.add(module)
        all_deps = set()

        for dep in self.get_dependents(module):
            all_deps.add(dep)
            all_deps.update(self.get_all_dependents(dep, visited))

        return all_deps
```

### 依赖图示例

```
payment_module
├── auth_module (直接依赖)
│   └── [auth_module 依赖其他]
├── notification_module (直接依赖)
│   └── [notification_module 依赖其他]
└── db (直接依赖)

order_module
├── payment_module (直接依赖)
└── inventory_module

checkout_module
├── order_module (直接依赖)
└── payment_module (直接依赖)
```

## 传递依赖

```python
def get_transitive_dependencies(module, dependency_graph):
    """
    获取传递依赖
    例如: A -> B -> C, 则 A 的传递依赖包括 B 和 C
    """
    return dependency_graph.get_all_dependencies(module)


def get_impact_scope(module, dependency_graph):
    """
    获取影响范围
    例如: A -> B -> C, 则 A 变更会影响 B 和 C
    """
    return dependency_graph.get_all_dependents(module)
```

## 依赖与测试关联

```python
def build_test_dependency_mapping(dependency_graph, test_index):
    """
    构建测试与依赖的映射
    """
    mapping = {}

    for test_case in test_index.all_tests():
        # 分析测试覆盖的模块
        covered_modules = test_case.covers_modules

        # 获取这些模块的传递依赖
        all_deps = set()
        for module in covered_modules:
            all_deps.update(get_transitive_dependencies(module, dependency_graph))

        # 测试与所有受影响的模块关联
        mapping[test_case] = {
            "direct_modules": covered_modules,
            "all_affected_modules": all_deps
        }

    return mapping
```

## 循环依赖检测

```python
def detect_circular_dependencies(dependency_graph):
    """
    检测循环依赖
    """
    circular = []
    visited = set()
    path = set()

    def dfs(module):
        if module in path:
            # 发现循环
            cycle = list(path)[path.index(module):] + [module]
            circular.append(cycle)
            return

        if module in visited:
            return

        visited.add(module)
        path.add(module)

        for dep in dependency_graph.get_dependencies(module):
            dfs(dep)

        path.remove(module)

    for module in dependency_graph.nodes:
        if module not in visited:
            dfs(module)

    return circular
```

## 解析配置

```yaml
dependency_parsing:
  # 解析的依赖文件
  manifest_files:
    python:
      - "requirements.txt"
      - "pyproject.toml"
      - "setup.py"
      - "Pipfile"
    javascript:
      - "package.json"
      - "package-lock.json"
    go:
      - "go.mod"
      - "go.sum"

  # 过滤的系统依赖
  skip_system:
    - "os"
    - "sys"
    - "time"
    - "json"
    - "console"

  # 过滤的开发依赖 (可选)
  skip_dev: false

  # 解析深度
  depth:
    direct: true
    transitive: true      # 传递依赖
    max_depth: 10
```

## 输出格式

```yaml
dependency_analysis_result:
  project_path: "/path/to/project"

  manifest:
    file: "requirements.txt"
    format: "pip"
    dependencies:
      - name: "requests"
        version: "^2.28.0"
        type: "runtime"

  internal_graph:
    nodes:
      - "payment"
      - "auth"
      - "order"

    edges:
      - from: "payment"
        to: "auth"
      - from: "order"
        to: "payment"

  external_count: 50
  internal_count: 10

  warnings:
    - type: "circular_dependency"
      modules: ["a", "b", "c"]
    - type: "unused_dependency"
      module: "payment"
      dependency: "old_module"
```

## 使用示例

```python
# 解析项目依赖
parser = DependencyParser(project_path=".")
result = parser.parse()

print(f"外部依赖: {len(result.external_dependencies)}")
print(f"内部模块: {len(result.internal_graph.nodes)}")

# 构建依赖图
graph = result.internal_graph

# 获取 payment 的所有依赖
deps = graph.get_all_dependencies("payment")
print(f"payment 及其依赖: {deps}")

# 获取受 payment 影响的模块
impacted = graph.get_all_dependents("payment")
print(f"受 payment 影响的模块: {impacted}")

# 检测循环依赖
circular = detect_circular_dependencies(graph)
if circular:
    print(f"发现循环依赖: {circular}")
```

## 相关模块

| 模块 | 关系 |
|------|------|
| `code-parser.md` | 提供 import 解析 |
| `test-parser.md` | 依赖用于测试匹配 |
| `module-mapper.md` | 模块映射基础 |
| `test-matcher.md` | 使用依赖图匹配 |
