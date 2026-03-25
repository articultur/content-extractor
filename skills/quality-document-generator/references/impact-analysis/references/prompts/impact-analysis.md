# 影响分析提示词 / Impact Analysis Prompt

## 概述

本提示词用于指导 LLM 在**规则分析之后**进行深度语义分析，弥补规则匹配的不足。

## 输入数据

### 1. PR 基本信息

```json
{
  "title": "{pr_title}",
  "files_count": {files_count},
  "lines_added": {lines_added},
  "lines_deleted": {lines_deleted},
  "changed_files": [
    {{file_path}}: +{additions}/-{deletions}
  ]
}
```

### 2. 逃逸规则检查结果

```json
{{escape_rules_check}}
```

### 3. 敏感度评分结果

```json
{{sensitivity_score}}
```

### 4. Diff 内容

```diff
{diff_content}
```

## LLM 分析职责

规则已覆盖以下分析，**LLM 无需重复**：
- 文件路径匹配
- 规模计算
- 变更类型分类
- 安全敏感路径检测

**LLM 应专注于**：

### 1. 语义理解

分析代码变更的实际含义，不只是模式匹配：

```
- 这个函数改变什么行为？
- 新增的逻辑有什么边界条件？
- 修改的算法有什么假设前提？
```

### 2. 业务影响推断

基于代码理解推断对业务的影响：

```
- 什么用户场景会受影响？
- 什么业务流程可能被破坏？
- 什么边缘情况需要测试？
```

### 3. 隐性依赖发现

发现规则无法捕捉的依赖关系：

```
- 通过业务逻辑推断的依赖
- 通过数据流的隐式依赖
- 通过配置变化的间接影响
```

### 4. 边缘案例建议

基于代码理解推荐边缘测试：

```
- 什么输入会触发新代码的错误路径？
- 什么并发/竞态条件需要测试？
- 什么错误恢复场景需要覆盖？
```

## 输出格式

```json
{
  "semantic_analysis": {
    "summary": "代码变更的业务含义（1-2句话）",
    "key_changes": [
      {
        "file": "文件路径",
        "change_description": "变更的实际含义",
        "risk_level": "high|medium|low"
      }
    ],
    "edge_cases": [
      {
        "scenario": "边缘场景描述",
        "test_suggestion": "测试建议",
        "priority": "P0|P1|P2"
      }
    ]
  },
  "business_impact": {
    "affected_user_flows": ["受影响的用户流程"],
    "affected_stakeholders": ["可能受影响的人员"],
    "risk_description": "业务风险描述"
  },
  "hidden_dependencies": [
    {
      "module": "依赖模块",
      "dependency_type": "business|data|config|implicit",
      "confidence": 0.0-1.0,
      "reason": "为什么存在依赖"
    }
  ],
  "test_recommendations": [
    {
      "test_type": "unit|integration|e2e|security|performance",
      "scenario": "测试场景描述",
      "priority": "P0|P1|P2",
      "reason": "为什么需要这个测试"
    }
  ],
  "confidence": {
    "overall": 0.0-1.0,
    "semantic_understanding": 0.0-1.0,
    "business_impact_assessment": 0.0-1.0
  }
}
```

## 分析示例

### 输入

```json
{
  "title": "Add Polaris as news/sentiment/price data vendor",
  "files_count": 4,
  "lines_added": 820,
  "escape_rules": {
    "action": "standard",
    "matched_rules": []
  },
  "sensitivity": {
    "level": "P1",
    "score": 4
  }
}
```

### LLM 分析要点

1. **语义理解**：
   - 这是新增数据源（Polaris），不是修改现有数据源
   - 13 个新函数，3 个是 Polaris 独有的情感分析功能
   - 对现有 vendor（Alpha Vantage, YFinance）无破坏性变更

2. **业务影响**：
   - 交易 agent 获取情感分析能力
   - 可能影响交易策略的执行
   - 需要验证新数据源的准确性

3. **边缘案例**：
   - Polaris API 不可用时的降级处理
   - API 限流的处理
   - 情感分数异常值的处理

4. **测试建议**：
   - Polaris vendor 单元测试（高优先级）
   - 多 vendor 切换测试
   - API 降级场景测试

## 使用约束

1. **只分析规则无法判断的内容**
2. **基于代码语义推断，不猜测**
3. **置信度低于 0.6 的结论应标注"不确定"**
4. **优先关注 P0/P1 级别的建议**

## 快速分析模式

对于 P2 变更（敏感度 < 2），只需简短分析：

```json
{
  "semantic_analysis": {
    "summary": "一句话描述变更",
    "risk_level": "low"
  },
  "test_recommendations": [
    {"test_type": "unit", "scenario": "基本验证"}
  ],
  "confidence": {"overall": 0.8}
}
```
