"""
逃逸规则引擎 / Escape Rules Engine

快速判断代码变更是否属于特殊场景，从而决定分析策略。

规则分类：
- 跳过型 (Step 1): test_file_change, documentation_change, small_config_change
- 策略型 (Step 2): tiny_change, large_pr, security_sensitive, database_migration
- 扩大型 (Step 3): urgent_fix, api_interface_change, pure_refactor
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# 规则定义
ESCAPE_RULES = [
    {
        "name": "test_file_change",
        "description": "测试文件本身变更，只分析相关测试",
        "action": "run_related_tests_only",
        "default_confidence": 0.95,
    },
    {
        "name": "documentation_change",
        "description": "纯文档变更，跳过影响分析",
        "action": "skip_analysis",
        "default_confidence": 0.9,
    },
    {
        "name": "small_config_change",
        "description": "小规模配置变更，建议冒烟测试",
        "action": "minimal_smoke",
        "default_confidence": 0.7,
    },
    {
        "name": "tiny_change",
        "description": "微小变更，只执行单元测试",
        "action": "unit_only",
        "default_confidence": 0.6,
    },
    {
        "name": "large_pr",
        "description": "大型 PR，建议分批分析",
        "action": "segment_analysis",
        "default_confidence": 0.85,
    },
    {
        "name": "security_sensitive",
        "description": "安全敏感模块，扩大测试范围",
        "action": "security_focus",
        "default_confidence": 0.85,
    },
    {
        "name": "database_migration",
        "description": "数据库迁移相关，DB 集成测试优先",
        "action": "db_integration_focus",
        "default_confidence": 0.9,
    },
    {
        "name": "urgent_fix",
        "description": "紧急修复，扩大测试范围",
        "action": "expand_full_coverage",
        "default_confidence": 0.7,
    },
    {
        "name": "api_interface_change",
        "description": "API 接口变更，验证调用方兼容性",
        "action": "api_contract_verification",
        "default_confidence": 0.9,
    },
    {
        "name": "pure_refactor",
        "description": "纯重构，以回归测试为主",
        "action": "regression_focus",
        "default_confidence": 0.75,
    },
]

# 跳过型规则（命中后立即返回）
SKIP_RULES = {"test_file_change", "documentation_change"}

# 扩大型规则（标记 should_expand_scope）
EXPAND_SCOPE_RULES = {
    "security_sensitive",
    "database_migration",
    "urgent_fix",
    "api_interface_change",
}


@dataclass
class ChangeInput:
    """代码变更输入"""
    files: List[str] = field(default_factory=list)
    files_count: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    lines_changed: int = 0  # total lines changed
    new_functions: List[str] = field(default_factory=list)
    change_types: List[str] = field(default_factory=list)
    pr_title: str = ""


@dataclass
class MatchedRule:
    """匹配的规则"""
    rule: str
    action: str
    confidence: float
    evidence: str


@dataclass
class EscapeRulesResult:
    """逃逸规则检查结果"""
    checked_rules: List[str]
    matched_rules: List[MatchedRule]
    action: str
    should_expand_scope: bool
    analysis_strategy: str  # "minimal", "standard", "full"
    skip_analysis: bool  # True if should skip entirely


def check_pattern(file_pattern: str, text: str) -> bool:
    """检查文本是否匹配文件模式"""
    # 转换为正则表达式
    pattern = file_pattern.replace("/", r"\/").replace(".", r"\.").replace("*", ".*")
    return bool(re.search(pattern, text, re.IGNORECASE))


def check_file_pattern(file_pattern: str, files: List[str]) -> Tuple[bool, str]:
    """
    检查文件列表是否匹配模式
    Returns: (matched, evidence)
    """
    matched_files = []
    for f in files:
        if check_pattern(file_pattern, f):
            matched_files.append(f)

    if matched_files:
        evidence = f"匹配文件: {', '.join(matched_files[:3])}"
        if len(matched_files) > 3:
            evidence += f" 等共 {len(matched_files)} 个文件"
        return True, evidence
    return False, ""


def check_test_file_change(change: ChangeInput) -> Tuple[bool, float, str]:
    """规则 1: 测试文件变更"""
    pattern = r"^(test/|spec/|__tests__/|_test\.|\.test\.|_spec\.|\.spec\.)"
    matched, evidence = check_file_pattern(pattern, change.files)
    return matched, 0.95, evidence


def check_documentation_change(change: ChangeInput) -> Tuple[bool, float, str]:
    """规则 2: 文档变更"""
    pattern = r"^(docs/|\.md$|README|LICENSE|CHANGELOG)"
    matched, evidence = check_file_pattern(pattern, change.files)
    return matched, 0.9, evidence


def check_small_config_change(change: ChangeInput) -> Tuple[bool, float, str]:
    """规则 3: 配置变更（小规模）"""
    config_pattern = r"(\.env$|config/|\.yaml$|\.yml$|\.json$|\.toml$|\.ini$)"
    has_config = False
    config_files = []
    for f in change.files:
        if check_pattern(config_pattern, f):
            has_config = True
            config_files.append(f)

    if has_config and change.files_count < 5:
        evidence = f"配置变更文件: {', '.join(config_files[:3])}"
        return True, 0.7, evidence
    return False, 0.0, ""


def check_tiny_change(change: ChangeInput) -> Tuple[bool, float, str]:
    """规则 4: 微小变更"""
    lines = change.lines_added + change.lines_deleted
    if change.files_count < 3 and lines < 100:
        evidence = f"文件数: {change.files_count}, 变更行数: {lines}"
        return True, 0.6, evidence
    return False, 0.0, ""


def check_large_pr(change: ChangeInput) -> Tuple[bool, float, str]:
    """规则 5: 大型 PR"""
    if change.files_count > 30:
        evidence = f"变更文件数: {change.files_count} > 30"
        return True, 0.85, evidence
    return False, 0.0, ""


def check_security_sensitive(change: ChangeInput) -> Tuple[bool, float, str]:
    """规则 6: 安全相关模块"""
    security_patterns = ["auth", "security", "permission", "crypto", "payment", "credential", "token"]
    matched, evidence = check_file_pattern("|".join(security_patterns), change.files)
    return matched, 0.85, evidence


def check_database_migration(change: ChangeInput) -> Tuple[bool, float, str]:
    """规则 7: 数据库迁移"""
    db_patterns = [r"migration", r"schema", r"\.sql$", r"alembic", r"prisma", r"migrate"]
    matched, evidence = check_file_pattern("|".join(db_patterns), change.files)
    return matched, 0.9, evidence


def check_urgent_fix(change: ChangeInput) -> Tuple[bool, float, str]:
    """规则 8: 紧急修复"""
    urgent_patterns = ["urgent", "hotfix", "critical", "emergency", "fix", "patch"]
    title_lower = change.pr_title.lower()
    matched_terms = [t for t in urgent_patterns if t in title_lower]
    if matched_terms:
        evidence = f"PR title 包含关键词: {', '.join(matched_terms)}"
        return True, 0.7, evidence
    return False, 0.0, ""


def check_api_interface_change(change: ChangeInput) -> Tuple[bool, float, str]:
    """规则 9: API 接口变更"""
    # 检查新增函数/方法
    api_patterns = ["create_", "update_", "delete_", "api", "endpoint", "handler", "client"]
    new_api_functions = []

    for fn in change.new_functions:
        fn_lower = fn.lower()
        if any(pattern in fn_lower for pattern in api_patterns):
            new_api_functions.append(fn)

    # 检查 API 相关的变更类型
    has_api_change = "api_change" in change.change_types

    if new_api_functions:
        evidence = f"新增 API 相关函数: {', '.join(new_api_functions[:5])}"
        return True, 0.9, evidence
    elif has_api_change:
        return True, 0.85, "变更类型包含 api_change"
    return False, 0.0, ""


def check_pure_refactor(change: ChangeInput) -> Tuple[bool, float, str]:
    """规则 10: 纯重构"""
    lines_added = change.lines_added
    lines_deleted = change.lines_deleted

    # 删除 > 新增 * 0.3 且有删除文件
    if lines_deleted > lines_added * 0.3:
        # 检查是否有删除的文件
        # 简化：只用行数判断
        evidence = f"删除行数: {lines_deleted}, 新增行数: {lines_added}, 比例: {lines_deleted/lines_added:.2f}"
        return True, 0.75, evidence
    return False, 0.0, ""


# 规则检查函数映射
RULE_CHECKERS = {
    "test_file_change": check_test_file_change,
    "documentation_change": check_documentation_change,
    "small_config_change": check_small_config_change,
    "tiny_change": check_tiny_change,
    "large_pr": check_large_pr,
    "security_sensitive": check_security_sensitive,
    "database_migration": check_database_migration,
    "urgent_fix": check_urgent_fix,
    "api_interface_change": check_api_interface_change,
    "pure_refactor": check_pure_refactor,
}


def check_escape_rules(change: ChangeInput) -> EscapeRulesResult:
    """
    检查所有逃逸规则

    Args:
        change: 代码变更输入

    Returns:
        EscapeRulesResult: 包含检查结果的元组
    """
    checked_rules = []
    matched_rules = []
    should_expand_scope = False
    skip_analysis = False
    primary_action = "standard"

    # 获取规则定义
    rule_defs = {r["name"]: r for r in ESCAPE_RULES}

    # 按顺序检查所有规则
    for rule_name, checker in RULE_CHECKERS.items():
        checked_rules.append(rule_name)
        matched, confidence, evidence = checker(change)

        if matched:
            rule_def = rule_defs[rule_name]
            action = rule_def["action"]

            matched_rules.append(MatchedRule(
                rule=rule_name,
                action=action,
                confidence=confidence,
                evidence=evidence
            ))

            # 跳过型规则：立即返回
            if rule_name in SKIP_RULES:
                skip_analysis = True
                primary_action = action
                break

            # 扩大型规则：标记 should_expand_scope
            if rule_name in EXPAND_SCOPE_RULES:
                should_expand_scope = True

    # 确定主要 action
    if matched_rules:
        # 优先使用最后一个匹配的扩大型规则，或第一个匹配的规则
        for mr in reversed(matched_rules):
            if mr.action != "skip_analysis":
                primary_action = mr.action
                break

    # 确定分析策略
    if skip_analysis:
        analysis_strategy = "skip"
    elif should_expand_scope:
        analysis_strategy = "full"
    elif primary_action in ["minimal_smoke", "unit_only"]:
        analysis_strategy = "minimal"
    else:
        analysis_strategy = "standard"

    return EscapeRulesResult(
        checked_rules=checked_rules,
        matched_rules=matched_rules,
        action=primary_action,
        should_expand_scope=should_expand_scope,
        analysis_strategy=analysis_strategy,
        skip_analysis=skip_analysis
    )


def escape_rules_to_dict(result: EscapeRulesResult) -> dict:
    """将结果转换为字典格式"""
    return {
        "escape_rules_check": {
            "checked_rules": [{"rule": r, "matched": False} for r in result.checked_rules],
            "matched_rules": [
                {
                    "rule": mr.rule,
                    "action": mr.action,
                    "confidence": mr.confidence,
                    "evidence": mr.evidence
                }
                for mr in result.matched_rules
            ],
            "action": result.action,
            "should_expand_scope": result.should_expand_scope,
            "analysis_strategy": result.analysis_strategy
        }
    }


# === 示例用法 ===

if __name__ == "__main__":
    # 示例 1: API 变更
    print("=== 示例 1: API 变更 ===")
    api_change = ChangeInput(
        files=[
            "pkg/github/projects.go",
            "pkg/github/projects_test.go",
        ],
        files_count=2,
        lines_added=150,
        lines_deleted=20,
        new_functions=["createProject", "createIterationField"],
        change_types=["feature", "api_change"],
        pr_title="feat: add project creation API"
    )
    result1 = check_escape_rules(api_change)
    print(f"Action: {result1.action}")
    print(f"Should expand scope: {result1.should_expand_scope}")
    print(f"Matched rules: {[mr.rule for mr in result1.matched_rules]}")
    print()

    # 示例 2: 微小变更
    print("=== 示例 2: 微小变更 ===")
    tiny_change = ChangeInput(
        files=["src/utils/helper.py"],
        files_count=1,
        lines_added=20,
        lines_deleted=5,
        new_functions=[],
        change_types=["refactor"],
        pr_title="refactor: rename helper function"
    )
    result2 = check_escape_rules(tiny_change)
    print(f"Action: {result2.action}")
    print(f"Analysis strategy: {result2.analysis_strategy}")
    print(f"Matched rules: {[mr.rule for mr in result2.matched_rules]}")
    print()

    # 示例 3: 安全相关
    print("=== 示例 3: 安全相关 ===")
    security_change = ChangeInput(
        files=["src/auth/token.go", "src/auth/jwt.go"],
        files_count=2,
        lines_added=50,
        lines_deleted=10,
        new_functions=["validateToken"],
        change_types=["bug_fix", "security"],
        pr_title="fix: token validation security issue"
    )
    result3 = check_escape_rules(security_change)
    print(f"Action: {result3.action}")
    print(f"Should expand scope: {result3.should_expand_scope}")
    print(f"Matched rules: {[(mr.rule, mr.evidence) for mr in result3.matched_rules]}")
    print()

    # 示例 4: 文档变更（跳过）
    print("=== 示例 4: 文档变更 ===")
    docs_change = ChangeInput(
        files=["README.md", "docs/guide.md"],
        files_count=2,
        lines_added=100,
        lines_deleted=10,
        new_functions=[],
        change_types=["docs"],
        pr_title="docs: update README"
    )
    result4 = check_escape_rules(docs_change)
    print(f"Action: {result4.action}")
    print(f"Skip analysis: {result4.skip_analysis}")
    print(f"Matched rules: {[mr.rule for mr in result4.matched_rules]}")
