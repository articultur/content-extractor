# 测试解析 / Test Parser

## 概述

测试解析模块负责从测试文件中提取结构化信息，构建测试知识库，支持测试匹配。

## 支持的测试框架

| 语言 | 框架 | 状态 |
|------|------|------|
| Python | pytest | ✅ 完全支持 |
| Python | unittest | ✅ 完全支持 |
| JavaScript | Jest | ✅ 完全支持 |
| JavaScript | Mocha | ✅ 完全支持 |
| TypeScript | Jest | ✅ 完全支持 |
| TypeScript | Vitest | ✅ 完全支持 |
| Java | JUnit | ✅ 完全支持 |
| Go | testing | ✅ 完全支持 |

## 解析信息

### 测试用例

```yaml
test_case:
  id: string              # 唯一标识
  name: string            # 测试名称
  file: string            # 文件路径
  start_line: int         # 开始行
  end_line: int           # 结束行
  framework: string       # 框架类型
  tags: list[string]      # 标签 (pytest.mark, describe, etc)
  status: active|skipped|disabled

  # 覆盖信息
  covers_functions: list[string]  # 覆盖的函数
  covers_classes: list[string]    # 覆盖的类
  covers_modules: list[string]    # 覆盖的模块

  # 实现细节
  is_unit: bool           # 是否单元测试
  is_integration: bool    # 是否集成测试
  is_e2e: bool           # 是否端到端测试
  uses_mocks: bool        # 是否使用 mock
  uses_real_db: bool      # 是否使用真实数据库

  # 代码行
  covered_lines: list[int]
  assertion_count: int
```

### 测试套件

```yaml
test_suite:
  path: string            # 测试目录/文件
  framework: string
  language: string

  test_cases: list[TestCase]
  test_count: int
  active_count: int
  skipped_count: int

  # 统计
  coverage_percentage: float
  avg_test_duration_ms: int
```

## 解析策略

### pytest 解析

```python
import ast
import re

def parse_pytest(file_content, file_path):
    """
    解析 pytest 测试文件
    """
    tests = []
    tree = ast.parse(file_content)

    for node in ast.walk(tree):
        # 函数级测试
        if isinstance(node, ast.FunctionDef):
            decorators = [d.id for d in node.decorator_list]

            # pytest 测试函数以 test_ 开头
            if node.name.startswith("test_"):
                test = extract_pytest_function(node, decorators, file_path)
                tests.append(test)

        # 类级测试
        elif isinstance(node, ast.ClassDef):
            class_name = node.name
            # pytest 测试类以 Test 开头
            if class_name.startswith("Test"):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name.startswith("test_"):
                        decorators = [d.id for d in item.decorator_list]
                        test = extract_pytest_method(item, decorators, class_name, file_path)
                        tests.append(test)

    return tests


def extract_pytest_function(node, decorators, file_path):
    """
    提取 pytest 函数信息
    """
    # 分析 pytest.mark
    markers = []
    for dec in decorators:
        if hasattr(dec, 'attr'):
            markers.append(dec.attr)
        elif isinstance(dec, ast.Name):
            markers.append(dec.id)

    # 提取调用的断言
    calls = extract_function_calls(node)

    return TestCase(
        name=node.name,
        file=file_path,
        start_line=node.lineno,
        end_line=node.end_lineno,
        framework="pytest",
        tags=markers,
        covers_functions=calls,
        is_unit="unit" in markers or "mock" in str(node.body),
    )
```

### Jest 解析

```python
def parse_jest(file_content, file_path):
    """
    解析 Jest 测试文件
    """
    tests = []

    # 匹配 describe blocks
    describe_pattern = r"describe\s*\(\s*['\"]([^'\"]+)['\"]"
    # 匹配 test/it blocks
    test_pattern = r"(?:test|it)\s*\(\s*['\"]([^'\"]+)['\"],\s*(?:async\s*)?\(\s*(?:[^)]*)\s*\)\s*=>"

    describes = re.finditer(describe_pattern, file_content)
    test_cases = re.finditer(test_pattern, file_content)

    # 构建 describe -> tests 映射
    describe_stack = []
    for match in test_cases:
        # 找到所属的 describe
        test_name = match.group(1)
        line = file_content[:match.start()].count('\n')

        # 简化: 假设所有 test 都在同一个 describe 下
        tests.append(TestCase(
            name=test_name,
            file=file_path,
            start_line=line,
            framework="jest",
            tags=extract_jest_tags(file_content, match.start(), match.end()),
        ))

    return tests
```

## 测试分类

### 按测试层次

```yaml
test_hierarchy:
  unit:
    description: "单元测试，测试单个函数/类"
    patterns:
      - name: "test_*_unit"
      - name: "Test*Class"
        when: "类内方法测试"
    indicators:
      - uses_mocks: true
      - no_real_db: true
      - small_scope: true

  integration:
    description: "集成测试，测试模块间交互"
    patterns:
      - name: "test_*_integration"
      - name: "test_*_combined"
    indicators:
      - multiple_modules: true
      - real_db_or_service: true

  e2e:
    description: "端到端测试，测试完整流程"
    patterns:
      - name: "test_*_e2e"
      - name: "test_*_flow"
      - name: "test_*_smoke"
    indicators:
      - full_system: true
      - user_like: true
      - no_mocks: true
```

### 按业务领域

```python
def classify_by_domain(test_case, module_mapping):
    """
    根据模块映射分类测试的业务领域
    """
    for module in test_case.covers_modules:
        if module in module_mapping:
            return module_mapping[module]

    # 尝试从测试名称推断
    test_name_lower = test_case.name.lower()

    if "payment" in test_name_lower or "billing" in test_name_lower:
        return "payment"
    elif "auth" in test_name_lower or "login" in test_name_lower:
        return "auth"
    elif "order" in test_name_lower or "checkout" in test_name_lower:
        return "order"

    return "unknown"
```

## 测试元信息提取

### 测试依赖分析

```yaml
dependency_analysis:
  # 测试调用了哪些函数/模块
  called_functions:
    test_payment_process:
      - "payment.process"
      - "payment.validate"

  # 测试使用了哪些外部服务
  external_services:
    test_payment_process:
      - "db"
      - "payment_gateway"

  # 测试是否依赖其他测试
  test_dependencies:
    test_payment_integration:
      - "test_payment_unit"
```

### Mock 使用分析

```python
def analyze_mock_usage(test_code):
    """
    分析测试中的 mock 使用
    """
    patterns = {
        "python": {
            "mock_call": r"(?:mock|patch|@pytest\.fixture).*?",
            "mock_library": r"from (?:unittest\.mock|mock) import",
        },
        "javascript": {
            "mock_call": r"(?:jest\.mock|vi\.mock|sinon\.stub)",
            "mock_library": r"from ['\"]@?[a-z]+(?:-\w+)*['\"]",
        }
    }

    # 计算 mock 覆盖率
    mock_lines = count_pattern_matches(test_code, patterns)
    total_lines = count_lines(test_code)

    return {
        "mock_percentage": mock_lines / total_lines,
        "uses_mocks": mock_lines > 0,
        "mock_intensity": "high" if mock_lines > 10 else "medium" if mock_lines > 5 else "low"
    }
```

## 测试索引

### 构建测试索引

```yaml
test_index:
  # 按模块索引
  by_module:
    payment_module:
      - test_payment.py::test_process
      - test_payment.py::test_validate
      - test_billing.py::test_invoice

  # 按函数索引
  by_function:
    "payment.process":
      - test_payment.py::test_process_success
      - test_payment.py::test_process_failure

  # 按标签索引
  by_tag:
    "smoke":
      - test_checkout.py::test_smoke
      - test_payment.py::test_smoke

  # 按状态索引
  by_status:
    "skipped":
      - test_payment.py::test_skipped_test
```

## 测试覆盖分析

### 覆盖报告

```yaml
coverage_analysis:
  file: "src/payment/billing.py"
  total_lines: 100
  covered_lines: 75
  coverage_percentage: 75%

  line_details:
    - line: 10
      covered: true
      tests: ["test_process", "test_validate"]
    - line: 20
      covered: false
      reason: "error handling branch"

  uncovered_branches:
    - lines: [20, 25]
      reason: "error handling"
```

## 解析输出

### 单文件解析结果

```yaml
test_parse_result:
  file_path: "tests/payment/test_billing.py"
  language: "python"
  framework: "pytest"

  test_cases:
    - id: "test_billing.py::test_process_success"
      name: "test_process_success"
      start_line: 10
      end_line: 30
      covers_functions: ["payment.billing.process"]
      covers_modules: ["payment"]
      is_unit: true
      uses_mocks: true

    - id: "test_billing.py::test_integration"
      name: "test_integration"
      start_line: 35
      end_line: 60
      covers_functions: ["payment.billing", "db.insert"]
      covers_modules: ["payment", "db"]
      is_integration: true
      uses_real_db: true
```

### 项目测试解析结果

```yaml
project_test_result:
  project_path: "."
  total_test_files: 50
  total_test_cases: 500
  active_cases: 450
  skipped_cases: 50

  by_module:
    payment_module:
      file_count: 5
      test_cases: 50
    order_module:
      file_count: 3
      test_cases: 30

  by_framework:
    pytest: 400
    unittest: 100

  by_level:
    unit: 300
    integration: 150
    e2e: 50
```

## 使用示例

```python
# 解析单个测试文件
parser = TestParser(language="python", framework="pytest")
result = parser.parse_file("tests/payment/test_billing.py")

print(f"测试用例数: {len(result.test_cases)}")
for test in result.test_cases:
    print(f"  - {test.name}")
    print(f"    覆盖: {test.covers_functions}")
    print(f"    类型: {'单元' if test.is_unit else '集成'}")

# 解析项目测试
project_result = parser.parse_project("tests/")

# 查找覆盖特定函数的测试
tests = project_result.get_tests_for_function("payment.process")
print(f"覆盖 payment.process 的测试: {tests}")

# 查找特定模块的测试
tests = project_result.get_tests_for_module("payment")
print(f"payment 模块的测试: {tests}")
```

## 过滤规则

```yaml
parse_filters:
  # 忽略的文件
  exclude:
    - "**/__init__.py"
    - "**/conftest.py"      # pytest fixtures
    - "**/test_utils.py"    # 工具类
    - "**/mocks/**"         # mock 文件

  # 只解析的测试
  include_patterns:
    - "**/test_*.py"
    - "**/*_test.py"
    - "**/tests/**/*.py"

  # 跳过被跳过的测试
  skip_skipped: true
```

## 相关模块

| 模块 | 关系 |
|------|------|
| `code-parser.md` | 解析被测代码 |
| `module-mapper.md` | 使用模块映射 |
| `test-matcher.md` | 使用测试解析结果 |
