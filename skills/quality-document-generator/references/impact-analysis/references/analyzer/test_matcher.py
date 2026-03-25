"""
测试匹配器 / Test Matcher

根据代码变更自动匹配需要回归的测试用例。

匹配策略（按优先级）：
1. 直接匹配 - 文件路径直接对应
2. 模块匹配 - 同模块的测试
3. 依赖匹配 - 下游依赖的测试
4. 函数调用匹配 - 调用变更函数的测试

置信度等级：
- 高 (0.9-1.0): 直接匹配
- 中高 (0.7-0.9): 模块匹配
- 中 (0.5-0.7): 依赖匹配
- 低 (0.3-0.5): 语义匹配
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum
import re


class MatchType(Enum):
    """匹配类型"""
    DIRECT = "direct"           # 文件路径直接匹配
    MODULE = "module"          # 同模块匹配
    DEPENDENCY = "dependency"   # 依赖匹配
    FUNCTION_CALL = "function_call"  # 函数调用匹配
    SEMANTIC = "semantic"       # 语义匹配


class Priority(Enum):
    """测试优先级"""
    P0 = "P0"  # 必须执行
    P1 = "P1"  # 强烈建议
    P2 = "P2"  # 可选执行


@dataclass
class TestInfo:
    """测试信息"""
    test_path: str           # 测试文件路径
    test_name: str           # 测试函数名
    module: str = ""         # 所属模块
    covered_functions: List[str] = field(default_factory=list)  # 覆盖的函数
    covered_lines: List[int] = field(default_factory=list)       # 覆盖的代码行
    file_path: str = ""      # 对应的源文件路径


@dataclass
class MatchResult:
    """匹配结果"""
    test: TestInfo
    match_type: MatchType
    confidence: float
    priority: Priority
    reasons: List[str]
    evidence: Dict[str, List[str]] = field(default_factory=dict)
    matched_lines: List[int] = field(default_factory=list)


@dataclass
class MatchingInput:
    """匹配输入"""
    changed_files: List[str]           # 变更文件列表
    changed_functions: List[str] = field(default_factory=list)  # 变更的函数
    affected_modules: List[str] = field(default_factory=list)   # 受影响模块
    change_types: List[str] = field(default_factory=list)      # 变更类型


@dataclass
class MatchingOutput:
    """匹配输出"""
    matches: List[MatchResult]
    recommended_order: List[str]       # 推荐执行顺序
    missing_tests: List[Dict]          # 缺失测试建议
    confidence_summary: Dict[str, float]


# 模块名提取模式（按优先级排序）
MODULE_PATTERNS = [
    (r'Engine/Plugins/(\w+)/', 1),         # Engine/Plugins/PluginName/
    (r'Engine/Source/(\w+)/', 1),           # Engine/Source/ModuleName/
    (r'plugins/(\w+)/', 1),                  # plugins/PluginName/
    (r'source/(\w+)/', 1),                   # source/ModuleName/
    (r'/(\w+)/Classes/', 1),                 # /ModuleName/Classes/
    (r'/(\w+)/Public/', 1),                  # /ModuleName/Public/
    (r'/(\w+)/Private/', 1),                 # /ModuleName/Private/
]


def extract_module_name(file_path: str) -> str:
    """
    从文件路径提取模块名

    Args:
        file_path: 文件路径

    Returns:
        str: 模块名
    """
    file_path_lower = file_path.lower()

    # 处理测试文件 - 先还原到源文件路径
    if '/test' in file_path_lower or '/tests' in file_path_lower:
        source_path = file_path
        for pattern in ['/test/', '/tests/']:
            if pattern in file_path_lower:
                idx = file_path_lower.find(pattern)
                source_path = source_path[:idx] + source_path[idx+len(pattern):]
                break

        # 移除 test_ 前缀
        source_path = re.sub(r'^test[_\-]?', '', source_path, flags=re.IGNORECASE)
        file_path = source_path
        file_path_lower = file_path.lower()

    # 跳过 Runtime/Engine/... 这种路径
    skip_prefixes = ['runtime/', 'engine/', 'framework/', 'programs/', 'plugins/']

    for pattern, group in MODULE_PATTERNS:
        match = re.search(pattern, file_path, re.IGNORECASE)
        if match:
            module = match.group(group).lower()
            # 跳过通用目录
            if module not in skip_prefixes:
                return module

    # 如果没匹配到，返回空字符串
    return ""


def is_test_file(file_path: str) -> bool:
    """判断是否为测试文件"""
    lower = file_path.lower()
    return (
        '/test/' in lower or
        '/tests/' in lower or
        lower.endswith('_test.py') or
        lower.endswith('.test.py') or
        lower.startswith('test_')
    )


def get_source_file_from_test(test_path: str) -> Optional[str]:
    """
    从测试文件路径推导源文件路径

    Args:
        test_path: 测试文件路径

    Returns:
        str: 源文件路径
    """
    source = test_path
    source_lower = source.lower()

    # 检查是否是 C++ 测试文件
    is_cpp_test = bool(re.search(r'([/\\\\])Tests?([/\\\\])(.+?)(Test\.cpp|Test\.h)$', source, re.IGNORECASE))

    if is_cpp_test:
        # C++ 测试文件: Tests/CharacterTest.cpp -> Character.cpp
        cpp_test_match = re.search(r'([/\\\\])Tests?([/\\\\])(.+?)(Test\.cpp|Test\.h)$', source, re.IGNORECASE)
        if cpp_test_match:
            dir_path = source[:cpp_test_match.start()]
            sep = cpp_test_match.group(1)
            filename = cpp_test_match.group(3)
            ext = cpp_test_match.group(4)
            return dir_path + sep + filename + ext
    else:
        # Python/其他测试文件
        # 移除 test 目录前缀（大小写不敏感）
        for prefix in ['/test/', '/tests/', '/Test/', '/Tests/']:
            if prefix.lower() in source_lower:
                idx = source_lower.find(prefix.lower())
                source = source[:idx] + source[idx+len(prefix):]
                break

        # 移除 test_ 前缀（大小写不敏感）
        source = re.sub(r'^test[_\-]?', '', source, flags=re.IGNORECASE)

        # 替换扩展名
        source = re.sub(r'\.test\.py$', '.py', source, flags=re.IGNORECASE)
        source = re.sub(r'_test\.py$', '.py', source, flags=re.IGNORECASE)

        if source != test_path:
            return source

    return None


def extract_base_name(file_path: str) -> str:
    """
    提取文件基名（不含扩展名）

    Args:
        file_path: 文件路径

    Returns:
        str: 基名
    """
    filename = file_path.split('/')[-1]
    # 移除扩展名
    return re.sub(r'\.(cpp|h|py|go|java|ts|js)$', '', filename, flags=re.IGNORECASE)


def match_by_file_path(changed_files: List[str], test: TestInfo) -> Optional[MatchResult]:
    """
    基于文件路径匹配

    Args:
        changed_files: 变更文件列表
        test: 测试信息

    Returns:
        MatchResult: 匹配结果
    """
    test_source = test.file_path or get_source_file_from_test(test.test_path)

    for changed_file in changed_files:
        changed_lower = changed_file.lower()
        test_source_lower = test_source.lower() if test_source else ""

        # 1. 精确匹配
        if test_source_lower == changed_lower:
            return MatchResult(
                test=test,
                match_type=MatchType.DIRECT,
                confidence=0.95,
                priority=Priority.P0,
                reasons=["文件路径精确匹配"],
                evidence={"supporting": [f"test_source: {test_source} == changed: {changed_file}"]}
            )

        # 2. 类名匹配（变更 Character.h，测试 CharacterTest.cpp）
        changed_base = extract_base_name(changed_file)
        test_base = extract_base_name(test_source) if test_source else ""

        if changed_base and test_base:
            # 检查基名相似度
            if changed_base == test_base:
                return MatchResult(
                    test=test,
                    match_type=MatchType.MODULE,
                    confidence=0.90,
                    priority=Priority.P0,
                    reasons=[f"基名匹配: {changed_base}"],
                    evidence={"supporting": [f"changed_base: {changed_base}, test_base: {test_base}"]}
                )

            # 检查 test 文件是否以被测文件基名开头
            if test_base.startswith(changed_base) or changed_base.startswith(test_base):
                return MatchResult(
                    test=test,
                    match_type=MatchType.MODULE,
                    confidence=0.85,
                    priority=Priority.P1,
                    reasons=[f"基名相似: {changed_base} ~ {test_base}"],
                    evidence={"supporting": [f"changed_base: {changed_base}, test_base: {test_base}"]}
                )

        # 3. 模块匹配
        changed_module = extract_module_name(changed_file)
        test_module = extract_module_name(test_source) if test_source else ""

        if changed_module == test_module and changed_module:
            # 提取文件名（不含扩展名）进行比较
            changed_name = extract_base_name(changed_file)
            test_name = extract_base_name(test_source) if test_source else ""

            if changed_name == test_name:
                return MatchResult(
                    test=test,
                    match_type=MatchType.MODULE,
                    confidence=0.85,
                    priority=Priority.P1,
                    reasons=[f"同模块 {changed_module}，文件名匹配"],
                    evidence={"supporting": [f"changed: {changed_file}, test_source: {test_source}"]}
                )

            return MatchResult(
                test=test,
                match_type=MatchType.MODULE,
                confidence=0.70,
                priority=Priority.P1,
                reasons=[f"同属模块 {changed_module}"],
                evidence={"supporting": [f"both in {changed_module} module"]}
            )

    return None


def match_by_function_call(changed_functions: List[str], test: TestInfo) -> Optional[MatchResult]:
    """
    基于函数调用匹配

    Args:
        changed_functions: 变更的函数列表
        test: 测试信息

    Returns:
        MatchResult: 匹配结果
    """
    if not changed_functions or not test.covered_functions:
        return None

    # 标准化函数名
    normalized_changed = {f.lower().split('.')[-1] for f in changed_functions}
    normalized_covered = {f.lower().split('.')[-1] for f in test.covered_functions}

    # 检查交集
    intersection = normalized_changed & normalized_covered

    if intersection:
        confidence = min(0.3 + 0.2 * len(intersection), 0.9)
        return MatchResult(
            test=test,
            match_type=MatchType.FUNCTION_CALL,
            confidence=confidence,
            priority=Priority.P1 if confidence >= 0.7 else Priority.P2,
            reasons=[f"测试覆盖函数: {', '.join(intersection)}"],
            evidence={"supporting": [f"covered_functions: {test.covered_functions}"]}
        )

    return None


def calculate_priority(confidence: float, match_type: MatchType) -> Priority:
    """
    根据置信度和匹配类型计算优先级

    Args:
        confidence: 置信度
        match_type: 匹配类型

    Returns:
        Priority: 优先级
    """
    if confidence >= 0.9 and match_type in [MatchType.DIRECT, MatchType.MODULE]:
        return Priority.P0
    elif confidence >= 0.7:
        return Priority.P1
    else:
        return Priority.P2


def filter_test_file(test_path: str, ignore_patterns: List[str] = None) -> bool:
    """
    判断测试文件是否应该被忽略

    Args:
        test_path: 测试文件路径
        ignore_patterns: 忽略模式列表

    Returns:
        bool: True 如果应该忽略
    """
    if ignore_patterns is None:
        ignore_patterns = [
            r'/test_ui_',           # UI 测试
            r'/test_manual',        # 手动测试
            r'_manual\.py$',        # 手动测试文件
        ]

    for pattern in ignore_patterns:
        if re.search(pattern, test_path, re.IGNORECASE):
            return True

    return False


def match_tests(
    input_data: MatchingInput,
    test_inventory: List[TestInfo],
    ignore_patterns: List[str] = None
) -> MatchingOutput:
    """
    执行测试匹配

    Args:
        input_data: 匹配输入
        test_inventory: 测试清单
        ignore_patterns: 忽略模式

    Returns:
        MatchingOutput: 匹配结果
    """
    results: List[MatchResult] = []
    seen_tests: Set[str] = set()  # 去重

    for test in test_inventory:
        # 1. 过滤测试文件
        if filter_test_file(test.test_path, ignore_patterns):
            continue

        # 2. 文件路径匹配
        match = match_by_file_path(input_data.changed_files, test)
        if match:
            # 更新优先级
            match.priority = calculate_priority(match.confidence, match.match_type)
            if test.test_path not in seen_tests:
                results.append(match)
                seen_tests.add(test.test_path)
            continue

        # 3. 函数调用匹配
        match = match_by_function_call(input_data.changed_functions, test)
        if match:
            match.priority = calculate_priority(match.confidence, match.match_type)
            if test.test_path not in seen_tests:
                results.append(match)
                seen_tests.add(test.test_path)

    # 按优先级和置信度排序
    results.sort(key=lambda x: (
        -ord(x.priority.value[0]),  # P0 > P1 > P2
        -x.confidence
    ))

    # 推荐执行顺序
    recommended_order = [r.test.test_path for r in results]

    # 置信度统计
    high_count = sum(1 for r in results if r.confidence >= 0.9)
    medium_count = sum(1 for r in results if 0.7 <= r.confidence < 0.9)
    low_count = sum(1 for r in results if r.confidence < 0.7)

    confidence_summary = {
        "overall": sum(r.confidence for r in results) / len(results) if results else 0,
        "high_confidence_count": high_count,
        "medium_confidence_count": medium_count,
        "low_confidence_count": low_count
    }

    # 缺失测试分析（基于变更类型）
    missing_tests = []
    if input_data.change_types:
        if "feature" in input_data.change_types:
            missing_tests.append({
                "description": "新功能建议补充集成测试",
                "priority": "high"
            })
        if "bug_fix" in input_data.change_types:
            missing_tests.append({
                "description": "Bug 修复建议补充回归测试",
                "priority": "high"
            })

    return MatchingOutput(
        matches=results,
        recommended_order=recommended_order,
        missing_tests=missing_tests,
        confidence_summary=confidence_summary
    )


def to_dict(output: MatchingOutput) -> dict:
    """
    将匹配结果转换为字典格式

    Args:
        output: 匹配输出

    Returns:
        dict: 字典格式
    """
    return {
        "matches": [
            {
                "test_name": r.test.test_name,
                "test_path": r.test.test_path,
                "match_type": r.match_type.value,
                "priority": r.priority.value,
                "confidence": round(r.confidence, 2),
                "reasons": r.reasons,
                "evidence": r.evidence
            }
            for r in output.matches
        ],
        "recommended_order": output.recommended_order,
        "missing_tests": output.missing_tests,
        "confidence_summary": {
            k: round(v, 2) if isinstance(v, float) else v
            for k, v in output.confidence_summary.items()
        }
    }


# === 示例用法 ===

if __name__ == "__main__":
    # 示例：PR #14534 (Character.h 变更)
    input_pr_14534 = MatchingInput(
        changed_files=[
            "Engine/Source/Runtime/Engine/Classes/GameFramework/Character.h"
        ],
        changed_functions=["JumpCurrentCount"],
        affected_modules=["GameFramework"],
        change_types=["feature", "api_change"]
    )

    # 模拟测试清单
    test_inventory = [
        TestInfo(
            test_path="Engine/Source/Runtime/Engine/Tests/CharacterTest.cpp",
            test_name="TestJumpCount",
            module="GameFramework",
            covered_functions=["JumpCurrentCount", "Jump"],
            covered_lines=[100, 110, 120]
        ),
        TestInfo(
            test_path="Engine/Source/Runtime/Engine/Tests/PawnTest.cpp",
            test_name="TestPawnMovement",
            module="GameFramework",
            covered_functions=["Jump", "Move"],
            covered_lines=[50, 60]
        ),
        TestInfo(
            test_path="Engine/Source/Runtime/Input/Tests/InputTest.cpp",
            test_name="TestControllerInput",
            module="Input",
            covered_functions=["Input"],
            covered_lines=[30, 40]
        ),
    ]

    result = match_tests(input_pr_14534, test_inventory)

    print("=" * 60)
    print("PR #14534 测试匹配结果")
    print("=" * 60)
    print(f"\n找到 {len(result.matches)} 个匹配测试:\n")

    for r in result.matches:
        print(f"[{r.priority.value}] {r.test.test_name}")
        print(f"  路径: {r.test.test_path}")
        print(f"  匹配类型: {r.match_type.value}")
        print(f"  置信度: {r.confidence:.2f}")
        print(f"  原因: {', '.join(r.reasons)}")
        print()

    print(f"推荐执行顺序: {' -> '.join(result.recommended_order) or '无'}")
    print(f"\n置信度概览:")
    print(f"  整体置信度: {result.confidence_summary['overall']:.2f}")
    print(f"  高置信度: {result.confidence_summary['high_confidence_count']}")
    print(f"  中置信度: {result.confidence_summary['medium_confidence_count']}")
    print(f"  低置信度: {result.confidence_summary['low_confidence_count']}")
