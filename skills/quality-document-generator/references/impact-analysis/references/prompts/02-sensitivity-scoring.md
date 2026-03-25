# 敏感度评分 / Sensitivity Scoring

## 概述

敏感度评分用于量化代码变更的重要程度，决定需要多深入的测试覆盖。

## 实现参考

> **Python 实现**：`../analyzer/sensitivity_scorer.py`
>
> 已实现 `calculate_sensitivity(change: ChangeInput) -> SensitivityScore` 函数，可直接调用：
> ```python
> from analyzer.sensitivity_scorer import calculate_sensitivity, ChangeInput
>
> change = ChangeInput(
>     files_count=8,
>     lines_added=327,
>     lines_deleted=15,
>     change_types=["feature", "api_change"],
>     new_functions=["CopilotClient", "get_github_token"],
>     files=["tradingagents/llm_clients/copilot_client.py"]
> )
> result = calculate_sensitivity(change)
> # result.level: "P1", result.score: 4, result.breakdown: {...}
> ```

## 评分公式

```
敏感度评分 = Σ加分维度 - Σ减分维度
```

### 加分维度

| 维度 | 条件 | 分值 | 说明 |
|------|------|------|------|
| `core_module` | 变更涉及核心模块 | +2 | 核心模块需要更高覆盖 |
| `high_dependency` | 影响 5+ 依赖模块 | +2 | 高依赖意味大影响 |
| `security_sensitive` | 涉及安全敏感模块 | +2 | 安全问题放大风险 |
| `compliance_domain` | 涉及监管域 | +2 | 金融、医疗、法律等 |
| `large_scale` | > 30 文件 或 > 1000 行 | +1 | 大规模变更风险高 |
| `api_change` | 有 API 接口变更 | +2 | API 变更影响调用方 |
| `new_methods` | 有新增公开方法 | +1 | 新接口需要测试 |

### 减分维度

| 维度 | 条件 | 分值 | 说明 |
|------|------|------|------|
| `tiny_change` | < 3 文件 且 < 100 行 | -2 | 微小变更风险低 |
| `high_coverage` | 测试覆盖率 > 80% | -1 | 高覆盖降低风险 |
| `low_frequency` | 季度内首次变更 | -1 | 低频变更可能遗漏 |
| `test_only` | 仅测试文件变更 | -1 | 测试变更风险低 |

## 敏感度级别

| 级别 | 分值范围 | 说明 | 测试策略 |
|------|---------|------|---------|
| **P0** | ≥ 5 | 核心模块 或 高影响 | 全量测试 + 人工确认 |
| **P1** | 2-4 | 非核心但有多个关联 | Integration + E2E |
| **P2** | < 2 | 微小变更 或 低影响 | Unit + 快速验证 |

## 简化评分（无依赖数据时）

当没有模块依赖数据时，使用简化评分：

```python
def calculate_sensitivity_simple(change):
    score = 0

    # 1. 规模评分
    files = change.files_count
    lines = change.lines_added + change.lines_deleted

    if files > 30 or lines > 1000:
        score += 2
    elif files > 10 or lines > 500:
        score += 1
    elif files < 3 and lines < 100:
        score -= 2

    # 2. 变更类型评分
    if "api_change" in change.change_types:
        score += 2
    if "feature" in change.change_types:
        score += 2
    # bug_fix 细分：安全路径 bug +2，普通 bug +1
    if "bug_fix" in change.change_types:
        is_security_bug = any(
            p in f.lower()
            for f in change.files
            for p in ["auth", "security", "permission", "crypto", "payment", "credential", "token"]
        )
        score += 2 if is_security_bug else 1
    if "security" in change.change_types:
        score += 2
    # refactor: 无删除才减分
    if "refactor" in change.change_types:
        score -= 1 if change.lines_deleted == 0 else 0

    # 3. 文件位置评分（security 类型不重复加分）
    if "security" not in change.change_types:
        sensitive_paths = ["auth", "security", "permission", "crypto", "payment", "credential", "token"]
        for path in sensitive_paths:
            if any(path in f.lower() for f in change.files):
                score += 2
                break

    # 4. 核心模块评分
    core_patterns = ["core", "domain", "business", "service"]
    if any(p in f.lower() for f in change.files for p in core_patterns):
        score += 2

    # 5. 合规域评分
    compliance_keywords = ["PII", "GDPR", "HIPAA", "SOC2", "PCI", "KYC", "AML", "privacy", "personal_data"]
    if any(k.lower() in f.lower() for f in change.files for k in compliance_keywords):
        score += 2

    # 6. 新增函数评分
    if change.new_functions and len(change.new_functions) > 0:
        score += 1

    # 7. 评分下限保护
    score = max(score, -3)

    return classify(score)


def classify(score):
    if score >= 5:
        return "P0"
    elif score >= 2:
        return "P1"
    else:
        return "P2"
```

## 评分示例

### 示例 1: PR #2232 评分

**输入**：
```json
{
  "files_count": 5,
  "lines_added": 695,
  "lines_deleted": 22,
  "change_types": ["feature", "api_change"],
  "new_functions": ["createProject", "createIterationField", "getOwnerNodeID", "getProjectNodeID"],
  "files": [
    "pkg/github/projects.go",
    "pkg/github/projects_test.go",
    "pkg/github/__toolsnaps__/projects_write.snap",
    "README.md",
    "pkg/github/projects_v2_test.go"
  ]
}
```

**评分计算**：
```json
{
  "score": 6,
  "breakdown": {
    "scale": 1,
    "change_type": 4,
    "location": 0,
    "functions": 1,
    "core_module": 0,
    "compliance": 0,
    "deductions": 0
  },
  "level": "P0"
}
```

**说明**：
- +1: 695 行变更，规模较大（> 500 行）
- +4: change_type = feature(+2) + api_change(+2)
- +1: 新增 4 个方法（有 API 相关函数 +2，但 scale 已部分覆盖）
- 注：非安全敏感路径，location=0

**结论**: P0，建议全量测试 + 人工确认

### 示例 2: 安全相关变更

**输入**：
```json
{
  "files_count": 2,
  "lines_added": 50,
  "lines_deleted": 10,
  "change_types": ["bug_fix", "security"],
  "files": ["pkg/auth/token.go", "pkg/auth/jwt.go"]
}
```

**评分计算**：
```json
{
  "score": 5,
  "breakdown": {
    "scale": 0,
    "change_type": 4,
    "location": 0,
    "functions": 0,
    "core_module": 0,
    "compliance": 0,
    "deductions": 0
  },
  "level": "P0"
}
```

**说明**：
- change_type = 4: bug_fix(安全路径 +2) + security(+2)
- location = 0: security 类型不重复加敏感路径分

**结论**: P0，建议全量测试 + 人工确认

### 示例 3: 微小变更

**输入**：
```json
{
  "files_count": 1,
  "lines_added": 20,
  "lines_deleted": 5,
  "change_types": ["refactor"],
  "files": ["pkg/utils/helper.go"]
}
```

**评分计算**：
```json
{
  "score": -2,
  "breakdown": {
    "scale": -2,
    "change_type": 0,
    "location": 0,
    "functions": 0,
    "core_module": 0,
    "compliance": 0,
    "deductions": 0
  },
  "level": "P2"
}
```

**说明**：
- scale = -2: < 3 文件 且 < 100 行
- change_type = 0: refactor 无删除不减分
- 总分 = -2，P2

**结论**: P2，建议 Unit 测试即可

## 输出格式

```json
{
  "sensitivity": {
    "level": "P1",
    "score": 3,
    "breakdown": {
      "scale": 1,
      "change_type": 2,
      "location": 0,
      "functions": 0,
      "core_module": 0,
      "compliance": 0,
      "deductions": 0
    },
    "recommendation": {
      "test_strategy": "integration_plus_e2e",
      "human_review": false,
      "expand_scope": true
    }
  }
}
```

## 测试策略映射

| 敏感度 | 测试策略 | 说明 |
|--------|---------|------|
| P0 | full + human_review | 全量测试 + 必须人工评审 |
| P1 | integration_plus_e2e | 集成测试 + E2E |
| P2 | unit_only | 单元测试 + 快速验证 |

## 置信度说明

简化评分依赖文件名匹配和变更类型判断，准确率约 70%。

**提升准确率的方法**：
1. 接入模块依赖数据 → +15%
2. 接入历史变更数据 → +10%
3. 人工确认关键判断 → +5%
