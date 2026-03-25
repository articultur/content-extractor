# 快速分析入口 / Quick Analysis Entry

## 适用场景

- PR 变更文件 < 10 个
- 变更行数 < 1000 行
- 需要快速返回结果

## 输入格式

```markdown
## 任务

你是一个代码影响分析助手。请分析以下代码变更，输出 JSON 格式结果。

## 输入信息

### 变更摘要
- 变更文件: {files_count} 个
- 变更行数: +{additions} / -{deletions}
- 涉及文件: {files_list}

### 变更类型
{change_types}

### 新增函数 (如有)
{new_functions}

### 变更文件详情
{file_details}

## 分析要求

1. **逃逸规则检查** - 检查是否命中特殊场景
2. **影响模块识别** - 识别直接和间接影响的模块
3. **测试推荐** - 推荐需要回归的测试用例
4. **敏感度评分** - 计算敏感度级别

## 输出要求

请直接输出 JSON，不要有其他内容：

```json
{
  "change_summary": {
    "files_count": number,
    "lines_added": number,
    "lines_deleted": number,
    "new_functions": ["string"],
    "change_types": ["string"]
  },
  "escape_rules_check": {
    "matched_rules": [
      {"rule": "string", "matched": boolean, "action": "string"}
    ],
    "action": "string"
  },
  "impact_modules": [
    {
      "module": "string",
      "type": "direct|indirect|potential",
      "confidence": number,
      "reason": "string"
    }
  ],
  "test_recommendations": [
    {
      "test_name": "string",
      "test_path": "string",
      "priority": "P0|P1|P2",
      "confidence": number,
      "reason": "string"
    }
  ],
  "sensitivity": {
    "level": "P0|P1|P2",
    "score": number,
    "breakdown": {}
  },
  "confidence": {
    "overall": number
  }
}
```

## 简化规则

### 逃逸规则（按顺序检查）

| 规则 | 条件 | Action |
|------|------|--------|
| 文档变更 | 文件含 .md, README, docs/ | skip_analysis |
| 测试文件变更 | 文件含 test/, spec/, __tests__/ | run_related_tests_only |
| 微小变更 | < 3 文件 且 < 100 行 | unit_only |
| 大型 PR | > 30 文件 | segment_analysis |
| 安全敏感 | 文件含 auth, security, permission, crypto | security_focus |
| API 变更 | 有新增方法/函数签名变化 | api_contract_verification |

### 敏感度评分

```
评分 = 规模分 + 类型分 + 位置分 + 函数分

规模分:
  - > 30 文件 或 > 1000 行: +2
  - > 10 文件 或 > 500 行: +1
  - < 3 文件 且 < 100 行: -2

类型分:
  - API 变更: +2
  - 新功能/重构: +1
  - Bug 修复: +1
  - 纯重构: -1

位置分:
  - 安全敏感目录: +2

级别:
  - >= 5: P0
  - 2-4: P1
  - < 2: P2
```

### 测试匹配策略

| 匹配类型 | 置信度 | 说明 |
|---------|--------|------|
| 文件名匹配 | 0.9 | test_xxx.py 对应 xxx.py |
| 同模块匹配 | 0.8 | 同一目录下的测试 |
| 函数名匹配 | 0.85 | 测试函数调用变更函数 |
| 依赖推断 | 0.6 | 业务上可能相关 |

## 示例

### 示例输入

```
变更文件: 3 个
变更行数: +150 / -20
涉及文件:
  - pkg/github/projects.go
  - pkg/github/projects_test.go
  - pkg/github/projects_v2_test.go

变更类型: feature, api_change
新增函数: createProject, createIterationField
```

### 示例输出

```json
{
  "change_summary": {
    "files_count": 3,
    "lines_added": 150,
    "lines_deleted": 20,
    "new_functions": ["createProject", "createIterationField"],
    "change_types": ["feature", "api_change"]
  },
  "escape_rules_check": {
    "matched_rules": [
      {"rule": "api_interface_change", "matched": true, "action": "api_contract_verification"}
    ],
    "action": "api_contract_verification"
  },
  "impact_modules": [
    {
      "module": "projects",
      "type": "direct",
      "confidence": 0.95,
      "reason": "变更文件直接归属 projects 模块"
    }
  ],
  "test_recommendations": [
    {
      "test_name": "Test_ProjectsWrite_CreateProject",
      "test_path": "pkg/github/projects_v2_test.go",
      "priority": "P0",
      "confidence": 0.9,
      "reason": "新增 createProject 方法的测试"
    },
    {
      "test_name": "Test_ProjectsWrite_CreateIterationField",
      "test_path": "pkg/github/projects_v2_test.go",
      "priority": "P0",
      "confidence": 0.9,
      "reason": "新增 createIterationField 方法的测试"
    },
    {
      "test_name": "Test_ProjectsWrite",
      "test_path": "pkg/github/projects_test.go",
      "priority": "P1",
      "confidence": 0.85,
      "reason": "projects 模块现有测试，确保未破坏"
    }
  ],
  "sensitivity": {
    "level": "P1",
    "score": 4,
    "breakdown": {
      "api_change": 2,
      "new_methods": 1,
      "scale": 1
    }
  },
  "confidence": {
    "overall": 0.85
  }
}
```

## 约束

1. 只输出 JSON，不要有其他文字
2. 置信度只保留 2 位小数
3. 如果不确定，优先扩大影响范围
4. 始终包含 test_recommendations（即使为空数组）
