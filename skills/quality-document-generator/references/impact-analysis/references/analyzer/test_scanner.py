"""
测试文件扫描器 / Test Scanner

扫描代码库中的测试文件，生成测试清单（List[TestInfo]）。

支持的测试文件约定：
- Python: test_*.py, *_test.py, *_tests.py
- Go: *_test.go
- C++: *Test.cpp, *Test.h, Tests/*.cpp
- Java: *Test.java, *Tests.java
- JavaScript/TypeScript: *.test.ts, *.spec.ts, *.test.js

扫描策略：
1. 基于命名约定识别测试文件
2. 基于路径结构建立测试→源文件映射
3. 提取测试函数名
"""

import os
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, TYPE_CHECKING
from pathlib import Path
from enum import Enum

# 类型检查时导入，避免循环依赖
if TYPE_CHECKING:
    from test_matcher import TestInfo


# 测试文件模式定义
class Language(Enum):
    PYTHON = "python"
    GO = "go"
    CPP = "cpp"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    UNKNOWN = "unknown"


# 语言对应的测试文件模式
TEST_FILE_PATTERNS: Dict[Language, List[re.Pattern]] = {
    Language.PYTHON: [
        re.compile(r'^test_.*\.py$', re.IGNORECASE),
        re.compile(r'.*_test\.py$', re.IGNORECASE),
        re.compile(r'.*_tests\.py$', re.IGNORECASE),
    ],
    Language.GO: [
        re.compile(r'.*_test\.go$'),
    ],
    Language.CPP: [
        re.compile(r'.*Test\.cpp$', re.IGNORECASE),
        re.compile(r'.*Test\.h$', re.IGNORECASE),
        re.compile(r'Tests?/.*\.cpp$', re.IGNORECASE),
    ],
    Language.JAVA: [
        re.compile(r'.*Test\.java$', re.IGNORECASE),
        re.compile(r'.*Tests\.java$', re.IGNORECASE),
    ],
    Language.JAVASCRIPT: [
        re.compile(r'.*\.test\.js$', re.IGNORECASE),
        re.compile(r'.*\.spec\.js$', re.IGNORECASE),
    ],
    Language.TYPESCRIPT: [
        re.compile(r'.*\.test\.ts$', re.IGNORECASE),
        re.compile(r'.*\.spec\.ts$', re.IGNORECASE),
        re.compile(r'.*\.test\.tsx$', re.IGNORECASE),
        re.compile(r'.*\.spec\.tsx$', re.IGNORECASE),
    ],
}


def detect_language(file_path: str) -> Language:
    """根据文件扩展名检测语言"""
    ext = os.path.splitext(file_path)[1].lower()
    mapping = {
        '.py': Language.PYTHON,
        '.go': Language.GO,
        '.cpp': Language.CPP,
        '.h': Language.CPP,
        '.cc': Language.CPP,
        '.java': Language.JAVA,
        '.js': Language.JAVASCRIPT,
        '.ts': Language.TYPESCRIPT,
        '.tsx': Language.TYPESCRIPT,
    }
    return mapping.get(ext, Language.UNKNOWN)


def is_test_file(file_path: str) -> bool:
    """
    判断文件是否为测试文件

    Args:
        file_path: 文件路径

    Returns:
        bool: True 如果是测试文件
    """
    basename = os.path.basename(file_path)
    lang = detect_language(file_path)

    patterns = TEST_FILE_PATTERNS.get(lang, [])
    for pattern in patterns:
        if pattern.match(basename):
            return True

    # 额外检查：Tests/ 目录下的 C++ 文件
    if '/Tests/' in file_path or '/tests/' in file_path.lower():
        return True

    return False


def extract_test_functions_python(content: str) -> List[str]:
    """从 Python 测试文件提取测试函数名"""
    # pytest 约定: test_ 开头的函数
    # unittest 约定: test_ 开头的方法
    pattern = re.compile(r'^def\s+(test_\w+)\s*\(', re.MULTILINE | re.IGNORECASE)
    return pattern.findall(content)


def extract_test_functions_go(content: str) -> List[str]:
    """从 Go 测试文件提取测试函数名"""
    # Go 约定: Test 开头的函数
    pattern = re.compile(r'^func\s+(Test\w+)\s*\(', re.MULTILINE)
    return pattern.findall(content)


def extract_test_functions_cpp(content: str) -> List[str]:
    """从 C++ 测试文件提取测试函数/类名"""
    results = []
    # 类名模式: class FooTest { ... };
    class_pattern = re.compile(r'class\s+(\w+Test)\s*[:{]', re.MULTILINE)
    results.extend(class_pattern.findall(content))
    # TEST_F 宏: TEST_F(FooTest, Bar) { ... }
    test_f_pattern = re.compile(r'TEST_F\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)', re.MULTILINE)
    for match in test_f_pattern.finditer(content):
        results.append(f"{match.group(1)}.{match.group(2)}")
    return results


def extract_test_functions_java(content: str) -> List[str]:
    """从 Java 测试文件提取测试方法名"""
    # JUnit 约定: @Test 注解的方法，或 test 开头的方法
    pattern = re.compile(r'@(?:Test|Before|After)\s+(?:public\s+)?(?:void|static)?\s*(\w+)\s*\(')
    method_pattern = re.compile(r'public\s+(?:void|static\s+void)\s+(test\w+)\s*\(')
    results = pattern.findall(content)
    results.extend(method_pattern.findall(content))
    return results


def extract_test_functions_js(content: str) -> List[str]:
    """从 JS/TS 测试文件提取测试函数名"""
    # describe/it 或 test/expect 模式
    patterns = [
        re.compile(r'(?:describe|test|it)\s*\(\s*[\'"`]([^\'"`]+)[\'"`]', re.MULTILINE),
        re.compile(r'function\s+(test\w+)\s*\(', re.MULTILINE | re.IGNORECASE),
    ]
    results = []
    for pattern in patterns:
        results.extend(pattern.findall(content))
    return results


def extract_test_functions(content: str, language: Language) -> List[str]:
    """根据语言提取测试函数名"""
    extractors = {
        Language.PYTHON: extract_test_functions_python,
        Language.GO: extract_test_functions_go,
        Language.CPP: extract_test_functions_cpp,
        Language.JAVA: extract_test_functions_java,
        Language.JAVASCRIPT: extract_test_functions_js,
        Language.TYPESCRIPT: extract_test_functions_js,
    }
    extractor = extractors.get(language, lambda x: [])
    return extractor(content)


def get_source_file_from_test_cpp(test_path: str) -> Optional[str]:
    """
    C++ 测试文件到源文件的映射

    Rules:
    - Tests/CharacterTest.cpp -> Classes/GameFramework/Character.cpp 或 .h
    - Source/Module/Tests/TestFile.cpp -> Source/Module/... (移除 Tests 目录)
    """
    # 模式1: Tests/CharacterTest.cpp -> 查找同级的 Character.cpp/.h
    tests_match = re.search(r'([/\\])Tests?([/\\])(.+?)(Test\.cpp|Test\.h)$', test_path, re.IGNORECASE)
    if tests_match:
        dir_path = test_path[:tests_match.start()]
        filename = tests_match.group(3)
        ext = tests_match.group(4)
        return dir_path + tests_match.group(1) + filename + ext

    return None


def get_source_file_from_test_generic(test_path: str, language: Language) -> Optional[str]:
    """
    通用测试文件到源文件的映射

    Python:
    - tests/test_billing.py -> billing.py 或 src/billing.py
    - test_payment.py -> payment.py

    Go:
    - pkg/billing/billing_test.go -> pkg/billing/billing.go

    Java:
    - src/test/java/com/foo/BillingTest.java -> src/main/java/com/foo/Billing.java
    """
    if language == Language.PYTHON:
        # 移除 test_ 前缀或 _test 后缀
        basename = os.path.basename(test_path)
        source_name = re.sub(r'^test_', '', basename, flags=re.IGNORECASE)
        source_name = re.sub(r'_test(s)?\.py$', r'\1.py', source_name, flags=re.IGNORECASE)
        source_name = re.sub(r'\.test\.py$', '.py', source_name, flags=re.IGNORECASE)

        # 尝试从路径推断源文件位置
        test_dir = os.path.dirname(test_path)

        # tests/test_billing.py -> 可能在同目录或兄弟目录
        if '/tests/' in test_path.lower() or '/test/' in test_path.lower():
            # 移除 tests 部分
            parts = test_path.lower().split('/')
            for i, part in enumerate(parts):
                if part in ['tests', 'test']:
                    # 构建源文件路径
                    src_parts = parts[:i] + parts[i+1:]
                    src_path = '/'.join(src_parts)
                    return src_path

        return source_name

    elif language == Language.GO:
        # 移除 _test.go 后缀
        source = re.sub(r'_test\.go$', '.go', test_path)
        return source

    elif language == Language.JAVA:
        # src/test/java/... -> src/main/java/...
        source = re.sub(r'/test/java/', '/main/java/', test_path)
        source = re.sub(r'Test\.java$', '.java', source, flags=re.IGNORECASE)
        return source

    return None


def get_source_file(test_path: str) -> Optional[str]:
    """获取测试文件对应的源文件路径"""
    lang = detect_language(test_path)

    if lang == Language.CPP:
        return get_source_file_from_test_cpp(test_path)
    else:
        return get_source_file_from_test_generic(test_path, lang)


def extract_module_from_path(file_path: str) -> str:
    """从路径提取模块名"""
    parts = file_path.strip('/').split('/')

    # Engine/Source/ModuleName/... (Unreal Engine 模式)
    for i, part in enumerate(parts):
        if part == 'Engine' and i + 2 < len(parts):
            if parts[i + 1].lower() == 'source':
                return parts[i + 2]

    # Source/ModuleName/... (通用模式)
    for i, part in enumerate(parts):
        if part.lower() in ['source', 'src']:
            if i + 1 < len(parts):
                module = parts[i + 1]
                # 跳过常见目录
                if module.lower() not in ['runtime', 'engine', 'framework', 'programs']:
                    return module

    # plugins/PluginName/...
    for i, part in enumerate(parts):
        if part.lower() == 'plugins' and i + 1 < len(parts):
            return parts[i + 1]

    # pkg/ModuleName/... (Go 模式)
    for i, part in enumerate(parts):
        if part == 'pkg' and i + 1 < len(parts):
            return parts[i + 1]

    # 最后一级的上一级作为模块（对于 tests/xxx/Test.cpp 模式）
    for i, part in enumerate(parts):
        if part.lower() in ['tests', 'test'] and i > 0:
            return parts[i - 1]

    return ""


@dataclass
class ScannedTest:
    """扫描到的测试信息"""
    test_path: str
    test_functions: List[str]
    language: Language
    module: str
    source_file: Optional[str] = None


def scan_file(file_path: str) -> Optional[ScannedTest]:
    """
    扫描单个测试文件

    Args:
        file_path: 测试文件路径

    Returns:
        ScannedTest 或 None
    """
    if not os.path.isfile(file_path):
        return None

    if not is_test_file(file_path):
        return None

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(10000)  # 只读前10KB用于提取函数名
    except Exception:
        return None

    lang = detect_language(file_path)
    test_functions = extract_test_functions(content, lang)
    module = extract_module_from_path(file_path)
    source_file = get_source_file(file_path)

    return ScannedTest(
        test_path=file_path,
        test_functions=test_functions,
        language=lang,
        module=module,
        source_file=source_file
    )


def scan_directory(
    root_path: str,
    extensions: List[str] = None,
    max_depth: int = 10,
    ignore_dirs: List[str] = None
) -> List[ScannedTest]:
    """
    扫描目录下所有测试文件

    Args:
        root_path: 根目录路径
        extensions: 只扫描指定扩展名（如 ['.py', '.cpp']）
        max_depth: 最大递归深度
        ignore_dirs: 忽略的目录名

    Returns:
        List[ScannedTest]: 扫描到的测试文件列表
    """
    if ignore_dirs is None:
        ignore_dirs = [
            'node_modules', '.git', '.svn', '__pycache__',
            '.venv', 'venv', '.env', 'build', 'dist',
            '.idea', '.vscode', '.pytest_cache'
        ]

    results: List[ScannedTest] = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        # 计算当前深度
        depth = dirpath[len(root_path):].count(os.sep)
        if depth > max_depth:
            dirnames.clear()
            continue

        # 过滤忽略的目录
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]

        for filename in filenames:
            file_path = os.path.join(dirpath, filename)

            # 检查扩展名过滤
            if extensions:
                _, ext = os.path.splitext(filename)
                if ext.lower() not in [e.lower() for e in extensions]:
                    continue

            scanned = scan_file(file_path)
            if scanned:
                results.append(scanned)

    return results


def scanned_to_test_info(scanned: ScannedTest) -> "TestInfo":
    """
    将 ScannedTest 转换为 TestInfo

    Args:
        scanned: 扫描结果

    Returns:
        TestInfo: 兼容 test_matcher 的数据结构
    """
    # 运行时导入避免循环依赖
    from test_matcher import TestInfo

    # 将模块名首字母大写作为默认 module
    module = scanned.module.capitalize() if scanned.module else "Unknown"

    return TestInfo(
        test_path=scanned.test_path,
        test_name=', '.join(scanned.test_functions[:5]),  # 最多5个函数名
        module=module,
        covered_functions=scanned.test_functions,
        file_path=scanned.source_file or ""
    )


def scan_and_collect(
    root_path: str,
    extensions: List[str] = None
) -> List["TestInfo"]:
    """
    扫描目录并返回 TestInfo 列表

    Args:
        root_path: 根目录路径
        extensions: 只扫描指定扩展名

    Returns:
        List[TestInfo]: 兼容 test_matcher 的测试清单
    """
    scanned_tests = scan_directory(root_path, extensions)
    return [scanned_to_test_info(s) for s in scanned_tests]


# === 示例用法 ===

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        root = sys.argv[1]
    else:
        # 默认扫描当前目录
        root = "."

    print(f"扫描目录: {root}")
    print("-" * 60)

    tests = scan_and_collect(root)

    print(f"找到 {len(tests)} 个测试文件:\n")

    # 按模块分组
    by_module: Dict[str, List["TestInfo"]] = {}
    for test in tests:
        module = test.module
        if module not in by_module:
            by_module[module] = []
        by_module[module].append(test)

    for module, module_tests in sorted(by_module.items()):
        print(f"[{module}] ({len(module_tests)} 个测试)")
        for test in module_tests[:5]:  # 每模块最多显示5个
            funcs = test.covered_functions[:3]
            print(f"  - {os.path.basename(test.test_path)}: {', '.join(funcs) or 'N/A'}")
        if len(module_tests) > 5:
            print(f"  ... 还有 {len(module_tests) - 5} 个")
        print()
