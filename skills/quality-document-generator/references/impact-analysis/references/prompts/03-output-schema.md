# 输出格式 Schema / Output Schema

## 分析结果输出格式

所有分析结果必须按以下 JSON Schema 输出：

```json
{
  "$schema": "impact-analysis-output",
  "version": "1.0",

  "change_summary": {
    "files_count": 5,
    "files": ["pkg/github/projects.go", "pkg/github/projects_test.go"],
    "lines_added": 695,
    "lines_deleted": 22,
    "new_functions": ["createProject", "createIterationField", "getOwnerNodeID", "getProjectNodeID"],
    "change_types": ["feature", "api_change"]
  },

  "impact_modules": [
    {
      "module": "projects",
      "type": "direct",
      "confidence": 0.95,
      "reason": "变更文件直接归属",
      "files": ["pkg/github/projects.go"]
    }
  ],

  "test_recommendations": [
    {
      "test_name": "Test_ProjectsWrite_CreateProject",
      "test_path": "pkg/github/projects_v2_test.go",
      "priority": "P0",
      "confidence": 0.9,
      "reason": "新增功能，需要完整覆盖",
      "covered_functions": ["createProject"]
    }
  ],

  "sensitivity": {
    "level": "P1",
    "score": 3,
    "breakdown": {
      "core_module": 2,
      "api_change": 1,
      "scale": 0
    }
  },

  "escape_rules": [
    {
      "rule": "api_interface_change",
      "matched": true,
      "action": "api_contract_verification"
    }
  ],

  "confidence": {
    "overall": 0.85,
    "data_sources": {
      "diff_analysis": 0.95,
      "function_detection": 0.90,
      "module_mapping": 0.85
    }
  },

  "warnings": [
    {
      "type": "incomplete_coverage",
      "message": "仅基于文件名推断，未分析 import 依赖"
    }
  ]
}
```

## 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `change_summary` | object | ✅ | 变更摘要 |
| `change_summary.files_count` | number | ✅ | 变更文件数 |
| `change_summary.lines_added` | number | ✅ | 新增行数 |
| `change_summary.lines_deleted` | number | ✅ | 删除行数 |
| `change_summary.new_functions` | string[] | ✅ | 新增函数名 |
| `change_summary.change_types` | string[] | ✅ | 变更类型 |
| `impact_modules` | array | ✅ | 影响模块列表 |
| `impact_modules[].module` | string | ✅ | 模块名 |
| `impact_modules[].type` | string | ✅ | `direct`/`indirect`/`potential` |
| `impact_modules[].confidence` | number | ✅ | 置信度 0-1 |
| `impact_modules[].reason` | string | ✅ | 影响原因 |
| `test_recommendations` | array | ✅ | 测试建议 |
| `test_recommendations[].test_name` | string | ✅ | 测试名 |
| `test_recommendations[].test_path` | string | ✅ | 测试文件路径 |
| `test_recommendations[].priority` | string | ✅ | `P0`/`P1`/`P2` |
| `test_recommendations[].confidence` | number | ✅ | 置信度 0-1 |
| `test_recommendations[].reason` | string | ✅ | 推荐理由 |
| `test_recommendations[].covered_functions` | string[] | ❌ | 覆盖的函数 |
| `sensitivity` | object | ✅ | 敏感度评级 |
| `sensitivity.level` | string | ✅ | `P0`/`P1`/`P2` |
| `sensitivity.score` | number | ✅ | 计算得分 |
| `sensitivity.breakdown` | object | ✅ | 得分明细 |
| `escape_rules` | array | ✅ | 逃逸规则匹配结果 |
| `escape_rules[].rule` | string | ✅ | 规则名 |
| `escape_rules[].matched` | boolean | ✅ | 是否命中 |
| `escape_rules[].action` | string | ❌ | 触发的 action |
| `confidence` | object | ✅ | 置信度评估 |
| `confidence.overall` | number | ✅ | 总体置信度 |
| `warnings` | array | ❌ | 警告信息 |

## 变更类型枚举

| 值 | 说明 |
|-----|------|
| `feature` | 新功能 |
| `bug_fix` | Bug 修复 |
| `refactor` | 重构 |
| `security` | 安全相关 |
| `config` | 配置变更 |
| `api_change` | API 变更 |
| `docs` | 文档变更 |
| `test` | 测试变更 |

## 优先级定义

| 优先级 | 适用场景 | 执行建议 |
|--------|---------|---------|
| `P0` | 直接影响的测试 | 必须执行 |
| `P1` | 间接影响、关联模块 | 强烈建议 |
| `P2` | 可选、边缘相关 | 建议执行 |

## 置信度等级

| 等级 | 分值 | 说明 |
|------|------|------|
| 高 | 0.8-1.0 | 有明确证据，直接执行 |
| 中 | 0.5-0.8 | 有一定证据，建议确认 |
| 低 | < 0.5 | 证据不足，可选执行 |

## 错误格式

当分析失败时：

```json
{
  "error": {
    "code": "insufficient_context",
    "message": "缺少必要的上下文信息",
    "missing": ["test_inventory", "module_mappings"],
    "suggestions": ["请提供测试文件列表", "请提供模块映射配置"]
  }
}
```
