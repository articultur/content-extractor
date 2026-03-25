# 代码解析 / Code Parser

## 概述

代码解析模块负责从代码文件中提取结构化信息，用于支持影响分析和测试匹配。

## 支持的语言

| 语言 | 状态 | 解析能力 |
|------|------|---------|
| Python | ✅ 完全支持 | AST, 函数, 类, import |
| JavaScript | ✅ 完全支持 | AST, 函数, 类, import |
| TypeScript | ✅ 完全支持 | AST, 函数, 类, import, 接口 |
| Java | ✅ 完全支持 | AST, 函数, 类, import |
| Go | ✅ 完全支持 | AST, 函数, 包, import |
| C/C++ | ⚠️ 基础支持 | 函数, 简单 import |
| Ruby | ⚠️ 基础支持 | 函数, 类, require |
| 其他 | ❌ 不支持 | - |

## 解析信息

### 函数/方法

```yaml
function_info:
  name: string           # 函数名
  file: string          # 文件路径
  start_line: int        # 开始行
  end_line: int          # 结束行
  visibility: public|private|protected
  parameters: list[Parameter]
  return_type: string|null
  decorators: list[string]
  is_async: bool
  calls: list[string]    # 调用的函数

parameter:
  name: string
  type: string|null
  default: string|null
```

### 类/结构体

```yaml
class_info:
  name: string
  file: string
  start_line: int
  end_line: int
  methods: list[Method]
  properties: list[Property]
  inheritance: list[string]
  imports: list[string]
```

### Import/Require

```yaml
import_info:
  type: import|require|include
  source: string         # 来源模块/包
  imported_items: list[string]
  is_relative: bool
  line: int
```

### 模块/包

```yaml
module_info:
  name: string
  path: string
  exports: list[string]
  submodules: list[string]
```

## 解析策略

### 策略1: AST 解析 (推荐)

```python
import ast

def parse_python_ast(file_content):
    """
    使用 Python AST 解析代码
    """
    tree = ast.parse(file_content)

    functions = []
    classes = []
    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append(extract_function(node))
        elif isinstance(node, ast.ClassDef):
            classes.append(extract_class(node))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(extract_import(node))

    return {
        "functions": functions,
        "classes": classes,
        "imports": imports
    }
```

### 策略2: 简单正则解析 (备用)

```python
import re

def parse_with_regex(file_content, language):
    """
    使用正则表达式解析代码 (不推荐，精度较低)
    仅用于 AST 不可用时
    """
    patterns = {
        "python": {
            "function": r"def (\w+)\([^)]*\):",
            "class": r"class (\w+)(?:[^:]+)?:",
            "import": r"(?:from (\S+) import|import (\S+))",
        },
        "javascript": {
            "function": r"(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\()",
            "class": r"class\s+(\w+)",
            "import": r"(?:import|from)\s+['\"]([^'\"]+)['\"]",
        }
    }

    # 应用对应语言的正则
    # ...
```

## 解析输出

### 文件解析结果

```yaml
file_parse_result:
  file_path: string
  language: string
  size_bytes: int
  parse_success: bool
  error: string|null

  functions: list[FunctionInfo]
  classes: list[ClassInfo]
  imports: list[ImportInfo]

  # 统计
  stats:
    total_functions: int
    public_functions: int
    total_classes: int
    total_imports: int
```

### 项目解析结果

```yaml
project_parse_result:
  project_path: string
  language: string
  project_type: web_api|cli_tool|library|monolith

  files: list[FileParseResult]

  # 索引
  function_index:
    # function_name -> list[FilePath]
    "process_payment": ["src/payment/billing.py", "src/payment/processor.py"]

  class_index:
    # class_name -> FilePath
    "PaymentProcessor": "src/payment/processor.py"

  module_index:
    # module_name -> list[FilePath]
    "payment": ["src/payment/__init__.py", "src/payment/billing.py"]

  import_graph:
    # FilePath -> set[ImportPath]
    "src/payment/billing.py": {"payment", "db", "logging"}
```

## LLM 增强解析

### 语义分析

```markdown
## LLM 语义分析提示词

对于无法通过 AST 解析的复杂代码，使用 LLM 进行语义分析:

```yaml
semantic_analysis:
  prompt: |
    分析以下代码的功能:

    ```{language}
    {code_snippet}
    ```

    请提供:
    1. 函数/类的功能描述
    2. 输入输出
    3. 依赖的外部模块/服务
    4. 可能的副作用

  output_format:
    - purpose: string
      inputs: list[string]
      outputs: list[string]
      dependencies: list[string]
      side_effects: list[string]
```
```

## 依赖分析

### 构建依赖图

```python
def build_dependency_graph(project_parse_result):
    """
    从解析结果构建依赖图
    """
    graph = DependencyGraph()

    for file_result in project_parse_result.files:
        file = file_result.file_path

        for imp in file_result.imports:
            # 解析导入来源
            source_module = resolve_import(imp.source, file)

            # 添加依赖边
            graph.add_edge(file, source_module)

    return graph


def resolve_import(import_source, from_file):
    """
    解析 import 来源，转换为模块名
    """
    # 相对导入
    if import_source.startswith('.'):
        return resolve_relative_import(import_source, from_file)

    # 绝对导入
    return import_source.split('.')[0]
```

### 依赖类型

| 类型 | 说明 | 示例 |
|------|------|------|
| 内部模块 | 同项目模块 | `from payment import` |
| 外部库 | 第三方包 | `import requests` |
| 系统库 | 语言内置 | `import os` |

## 过滤规则

```yaml
parse_filters:
  # 忽略的文件
  exclude:
    - "**/__pycache__/**"
    - "**/node_modules/**"
    - "**/venv/**"
    - "**/.venv/**"
    - "**/build/**"
    - "**/dist/**"
    - "**/*.min.js"
    - "**/*.bundle.js"

  # 只解析的文件类型
  include_extensions:
    - ".py"
    - ".js"
    - ".ts"
    - ".jsx"
    - ".tsx"
    - ".java"
    - ".go"

  # 忽略的空文件
  skip_empty: true
  min_lines: 3
```

## 性能优化

### 增量解析

```python
def incremental_parse(project, changed_files):
    """
    只解析变更的文件
    """
    # 使用缓存
    cached = load_cache(project)

    results = {}
    for file_path in changed_files:
        if file_path in cached:
            # 验证缓存有效性
            if is_cache_valid(file_path, cached[file_path]):
                results[file_path] = cached[file_path]
                continue

        # 重新解析
        results[file_path] = parse_file(file_path)

    # 更新缓存
    save_cache(project, results)

    return results
```

### 并行解析

```python
from concurrent.futures import ThreadPoolExecutor

def parse_files_parallel(file_paths, max_workers=4):
    """
    并行解析多个文件
    """
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(parse_file, file_paths))

    return results
```

## 错误处理

| 错误 | 处理 |
|------|------|
| 语法错误 | 记录警告，返回部分解析结果 |
| 编码错误 | 尝试其他编码，失败则跳过 |
| 文件不存在 | 记录错误，继续处理其他文件 |
| 依赖解析失败 | 记录警告，使用保守估计 |

## 使用示例

```python
# 解析单个文件
parser = CodeParser(language="python")
result = parser.parse_file("src/payment/billing.py")

print(f"函数数: {len(result.functions)}")
for func in result.functions:
    print(f"  - {func.name}({', '.join(func.parameters)})")

# 解析项目
project_result = parser.parse_project("src/")

# 查找函数定义
files = project_result.function_index.get("process_payment", [])
print(f"process_payment 定义在: {files}")

# 构建依赖图
dep_graph = build_dependency_graph(project_result)
```

## 相关模块

| 模块 | 关系 |
|------|------|
| `test-parser.md` | 使用代码解析理解测试覆盖 |
| `dependency.md` | 依赖解析的基础 |
| `module-mapper.md` | 使用解析结果进行模块映射 |
