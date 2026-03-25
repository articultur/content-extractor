# 代码分析提示词 / Code Analysis Prompt

## 概述

代码分析提示词用于指导 LLM 对变更代码进行深入分析，理解业务逻辑和影响范围。

## 使用场景

| 场景 | 说明 |
|------|------|
| L3 函数级分析 | 识别变更中的函数及其作用 |
| 业务逻辑推断 | 理解代码变更的业务含义 |
| 关联模块推断 | 推断可能受影响的模块 |
| 变更模式识别 | 识别代码变更的模式 |

## 提示词模板

### 基础分析模板

```markdown
## 任务

你是一位资深的代码审查专家，负责分析代码变更的业务影响。

## 输入信息

### 变更文件

{changed_files_list}

### Diff 内容

{diff_content}

### 项目上下文

{project_context}

## 分析要求

### 1. 函数识别

识别变更中涉及的主要函数，分析其功能:

```yaml
functions:
  - name: "函数名"
    file: "文件路径"
    lines: "行号范围"
    purpose: "功能描述"
    is_public_api: true/false
```

### 2. 业务逻辑分析

分析代码变更的业务含义:

```yaml
business_logic:
  - aspect: "业务角度"
    before: "变更前"
    after: "变更后"
    impact: "影响说明"
```

### 3. 变更模式识别

识别代码变更的模式:

```yaml
change_patterns:
  - type: "pattern 类型"
    evidence: "证据"
    implications: "潜在影响"
```

## 输出格式

请按以下 JSON 格式输出分析结果:

```json
{
  "functions": [
    {
      "name": "函数名",
      "file": "文件路径",
      "start_line": 10,
      "end_line": 25,
      "purpose": "功能描述",
      "is_public_api": false,
      "parameters": ["参数列表"],
      "calls": ["调用的函数"]
    }
  ],
  "business_logic": [
    {
      "aspect": "业务角度",
      "before": "变更前行为",
      "after": "变更后行为",
      "impact": "业务影响"
    }
  ],
  "change_patterns": [
    {
      "type": "bug_fix|feature|refactor|security|config",
      "evidence": "具体证据",
      "confidence": 0.95
    }
  ],
  "risk_assessment": {
    "level": "high|medium|low",
    "reasons": ["风险原因"]
  }
}
```

## 分析原则

### 准确性优先

- 只输出有明确证据支持的结论
- 不确定时使用 "unknown" 而非猜测
- 标注置信度

### 上下文感知

- 考虑项目类型 (Web/API/CLI/库)
- 考虑使用的框架和语言
- 考虑已有的业务领域知识

### 保守估计

- 宁可多报，不可漏报
- 存疑时扩大影响范围
- 明确标注不确定性

## 上下文变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `{changed_files_list}` | 变更文件列表 | ["src/payment.py", "src/billing.py"] |
| `{diff_content}` | 完整 diff 内容 | unified diff 格式 |
| `{project_context}` | 项目上下文 | 语言、框架、架构描述 |
| `{language}` | 编程语言 | Python, JavaScript, Go |
| `{project_type}` | 项目类型 | web_api, cli_tool, library |
| `{focus_modules}` | 关注的模块 | ["payment", "billing"] |

## 场景变体

### 场景1: 简单函数变更

```markdown
## 上下文
- 变更文件: 1-2 个
- 变更行数: < 100 行
- 变更类型: 函数内部逻辑修改

## 侧重点
- 函数功能是否改变
- 是否影响接口签名
```

### 场景2: 模块重构

```markdown
## 上下文
- 变更文件: 多个相关文件
- 变更行数: > 500 行
- 变更类型: 重构、移动、拆分

## 侧重点
- 重构是否改变行为
- 模块间依赖是否正确
- 是否有循环依赖
```

### 场景3: 安全变更

```markdown
## 上下文
- 变更涉及: 认证、授权、加密、数据处理
- 关键词: auth, password, token, encrypt, sanitize

## 侧重点
- 是否有安全漏洞
- 是否正确使用加密
- 是否有注入风险
```

## 错误处理

### 上下文不足

```markdown
如果提供的信息不足以进行准确分析:

```json
{
  "error": "insufficient_context",
  "missing": ["项目类型", "框架信息"],
  "assumptions": ["假设项目是 Web API"]
}
```

### Diff 格式错误

```json
{
  "error": "invalid_diff_format",
  "issue": "无法解析 diff",
  "suggestion": "请提供标准 unified diff 格式"
}
```

## 使用示例

### Python 代码分析

```python
prompt = CodeAnalysisPrompt(
    changed_files=["src/payment/billing.py"],
    diff_content=diff_of_billing_py,
    language="python",
    project_type="web_api",
    project_context="使用 Django 框架的支付服务"
)

analysis = llm.analyze(prompt.render())
```

### JavaScript 代码分析

```python
prompt = CodeAnalysisPrompt(
    changed_files=["src/auth/login.ts"],
    diff_content=diff_of_login_ts,
    language="typescript",
    project_type="spa",
    project_context="使用 React + Node.js 的单页应用"
)

analysis = llm.analyze(prompt.render())
```

## 相关模块

| 模块 | 关系 |
|------|------|
| `main.md` | 传入变更数据 |
| `impact-analysis.md` | 提供更广的影响分析上下文 |
| `test-matching.md` | 使用分析结果进行测试匹配 |
