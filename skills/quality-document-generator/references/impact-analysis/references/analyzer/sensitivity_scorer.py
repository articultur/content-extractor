"""
敏感度评分器 / Sensitivity Scorer

根据代码变更计算敏感度评分，决定测试深度。

评分公式：
    敏感度 = 规模分 + 类型分 + 位置分 + 函数分

级别：
    P0: >= 5 (核心模块 或 高影响) → 全量测试 + 人工确认
    P1: 2-4 (非核心但有多个关联) → Integration + E2E
    P2: < 2 (微小变更 或 低影响) → Unit + 快速验证
"""

from dataclasses import dataclass, field
from typing import List, Optional


# 敏感路径关键词（安全相关模块）
SENSITIVE_PATHS = ["auth", "security", "permission", "crypto", "payment", "credential", "token"]

# API 变更关键词
API_CHANGE_PATTERNS = ["api", "endpoint", "route", "handler", "client", "create_", "update_", "delete_"]

# 合规/监管关键词
COMPLIANCE_KEYWORDS = ["PII", "GDPR", "HIPAA", "SOC2", "PCI", "KYC", "AML", "privacy", "personal_data"]

# 核心模块关键词（项目特定，可配置）
CORE_MODULE_PATTERNS = ["core", "domain", "business", "service"]


def is_core_module(file_path: str, core_patterns: list = None) -> bool:
    """
    判断文件是否属于核心模块

    Args:
        file_path: 文件路径
        core_patterns: 核心模块匹配模式，默认使用 CORE_MODULE_PATTERNS

    Returns:
        bool: 是否为核心模块
    """
    patterns = core_patterns or CORE_MODULE_PATTERNS
    file_lower = file_path.lower()
    return any(pattern in file_lower for pattern in patterns)


def is_compliance_related(files: list) -> bool:
    """
    判断变更是否涉及合规/监管领域

    Args:
        files: 文件路径列表

    Returns:
        bool: 是否涉及合规
    """
    for f in files:
        f_lower = f.lower()
        if any(keyword.lower() in f_lower for keyword in COMPLIANCE_KEYWORDS):
            return True
    return False


@dataclass
class ChangeInput:
    """代码变更输入"""
    files_count: int
    lines_added: int
    lines_deleted: int
    change_types: List[str] = field(default_factory=list)
    new_functions: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    pr_title: str = ""


@dataclass
class SensitivityScore:
    """敏感度评分结果"""
    level: str  # P0, P1, P2
    score: int
    breakdown: dict
    recommendation: dict


def calculate_sensitivity(change: ChangeInput) -> SensitivityScore:
    """
    计算敏感度评分

    Args:
        change: 代码变更输入

    Returns:
        SensitivityScore: 包含级别、分数、分解和建议
    """
    score = 0
    breakdown = {
        "scale": 0,
        "change_type": 0,
        "location": 0,
        "functions": 0,
        "core_module": 0,
        "compliance": 0,
        "deductions": 0
    }

    # === 1. 规模评分 ===
    files = change.files_count
    lines = change.lines_added + change.lines_deleted

    if files > 30 or lines > 1000:
        score += 2
        breakdown["scale"] = 2
    elif files > 10 or lines > 500:
        score += 1
        breakdown["scale"] = 1
    elif files < 3 and lines < 100:
        score -= 2
        breakdown["scale"] = -2

    # === 2. 变更类型评分 ===
    type_score = 0
    if "api_change" in change.change_types:
        type_score += 2
    if "feature" in change.change_types:
        type_score += 2
    # bug_fix 细分：安全相关 bug 加分更高
    if "bug_fix" in change.change_types:
        # 检查是否涉及安全敏感路径
        is_security_bug = any(
            sensitive_path in f.lower()
            for f in change.files
            for sensitive_path in SENSITIVE_PATHS
        )
        type_score += 2 if is_security_bug else 1
    if "security" in change.change_types:
        type_score += 2
    # refactor 调整：有删除行的重构风险较高不减分，无删除才是"纯重构"减分
    if "refactor" in change.change_types:
        has_deletion = change.lines_deleted > 0
        type_score -= 1 if not has_deletion else 0

    score += type_score
    breakdown["change_type"] = type_score

    # === 3. 文件位置评分 ===
    location_score = 0
    # 如果 change_type 已是 security，不重复加分
    has_security_type = "security" in change.change_types
    if not has_security_type:
        for sensitive_path in SENSITIVE_PATHS:
            if any(sensitive_path in f.lower() for f in change.files):
                location_score = 2
                break

    score += location_score
    breakdown["location"] = location_score

    # === 4. 核心模块评分 ===
    core_module_score = 0
    for f in change.files:
        if is_core_module(f):
            core_module_score = 2
            break

    score += core_module_score
    breakdown["core_module"] = core_module_score

    # === 5. 合规域评分 ===
    compliance_score = 0
    if is_compliance_related(change.files):
        compliance_score = 2

    score += compliance_score
    breakdown["compliance"] = compliance_score

    # === 6. 新增函数评分 ===
    func_score = 0
    if change.new_functions and len(change.new_functions) > 0:
        # 检查是否新增了 API 相关的函数/类
        has_api_function = any(
            any(pattern in fn.lower() for pattern in API_CHANGE_PATTERNS)
            for fn in change.new_functions
        )
        if has_api_function:
            func_score = 2
        else:
            func_score = 1

    score += func_score
    breakdown["functions"] = func_score

    # === 7. 减分项 ===
    deductions = 0
    # 测试文件变更本身风险低（仅测试变更文件时减分，不叠加）
    if "test" in change.change_types and files < 5:
        test_file_ratio = sum(1 for f in change.files if "test" in f.lower()) / max(files, 1)
        if test_file_ratio > 0.8:
            deductions -= 1

    breakdown["deductions"] = deductions

    # === 评分下限保护 ===
    MIN_SCORE = -3
    score = max(score, MIN_SCORE)

    # === 级别分类 ===
    level = classify(score)

    # === 建议 ===
    recommendation = get_recommendation(level, change)

    return SensitivityScore(
        level=level,
        score=score,
        breakdown=breakdown,
        recommendation=recommendation
    )


def classify(score: int) -> str:
    """
    根据分数分类敏感度级别

    Args:
        score: 评分

    Returns:
        str: P0, P1, 或 P2
    """
    if score >= 5:
        return "P0"
    elif score >= 2:
        return "P1"
    else:
        return "P2"


def get_recommendation(level: str, change: ChangeInput) -> dict:
    """
    根据级别获取测试建议

    Args:
        level: 敏感度级别
        change: 代码变更输入

    Returns:
        dict: 包含测试策略和人工评审建议
    """
    if level == "P0":
        return {
            "test_strategy": "full",
            "human_review": True,
            "expand_scope": True,
            "description": "全量测试 + 必须人工评审"
        }
    elif level == "P1":
        return {
            "test_strategy": "integration_plus_e2e",
            "human_review": False,
            "expand_scope": True,
            "description": "Integration + E2E 测试"
        }
    else:
        return {
            "test_strategy": "unit_only",
            "human_review": False,
            "expand_scope": False,
            "description": "Unit 测试 + 快速验证"
        }


def sensitivity_to_dict(score: SensitivityScore) -> dict:
    """
    将 SensitivityScore 转换为字典格式

    Args:
        score: 敏感度评分结果

    Returns:
        dict: JSON 友好的字典
    """
    return {
        "level": score.level,
        "score": score.score,
        "breakdown": score.breakdown,
        "recommendation": score.recommendation
    }


# === 示例用法 ===

if __name__ == "__main__":
    # PR #442 示例
    pr_442 = ChangeInput(
        files_count=8,
        lines_added=327,
        lines_deleted=15,
        change_types=["feature", "api_change"],
        new_functions=[
            "CopilotClient", "NormalizedChatOpenAI",
            "get_github_token", "list_copilot_models",
            "check_copilot_auth", "perform_copilot_oauth"
        ],
        files=[
            "tradingagents/llm_clients/copilot_client.py",
            "cli/utils.py",
            "cli/main.py",
            "tradingagents/llm_clients/factory.py"
        ]
    )

    result = calculate_sensitivity(pr_442)
    print(f"PR #442 敏感度评分: {result.level} (score: {result.score})")
    print(f" Breakdown: {result.breakdown}")
    print(f" Recommendation: {result.recommendation}")

    # 微小变更示例
    tiny = ChangeInput(
        files_count=1,
        lines_added=20,
        lines_deleted=5,
        change_types=["refactor"],
        new_functions=[],
        files=["pkg/utils/helper.py"]
    )

    result_tiny = calculate_sensitivity(tiny)
    print(f"\n微小变更: {result_tiny.level} (score: {result_tiny.score})")
