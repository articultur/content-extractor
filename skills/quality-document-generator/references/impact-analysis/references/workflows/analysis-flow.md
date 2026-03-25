# 分析流程 / Analysis Flow

## 概述

分析流程定义了从接收输入到输出报告的完整处理流程，包括各个步骤的执行顺序、数据流转、和条件分支。

## 流程图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Impact Analysis Flow                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────┐                                                         │
│  │ 1. 输入接收    │                                                         │
│  └───────┬───────┘                                                         │
│          │                                                                   │
│          ▼                                                                   │
│  ┌───────────────────────────────┐                                         │
│  │ 2. 工具发现 & 适配器选择        │                                         │
│  │   - MCP > CLI > API > 手动      │                                         │
│  └───────┬────────────────────────┘                                         │
│          │                                                                   │
│          ▼                                                                   │
│  ┌───────────────┐                                                         │
│  │ 3. 代码获取    │                                                         │
│  │   - PR / Diff │                                                         │
│  └───────┬───────┘                                                         │
│          │                                                                   │
│          ▼                                                                   │
│  ┌───────────────┐                                                         │
│  │ 4. Diff 解析  │ ◄──────────────────┐                                    │
│  └───────┬───────┘                     │                                    │
│          │                             │                                    │
│          ▼                             │                                    │
│  ┌───────────────┐                     │                                    │
│  │ 5. 逃逸规则    │ ─(命中)────────────►│ 输出: 特殊 Action                   │
│  └───────┬───────┘                     │                                    │
│          │ (未命中)                       │                                    │
│          ▼                             │                                    │
│  ┌───────────────┐                     │                                    │
│  │ 6. 敏感度分级  │                     │                                    │
│  └───────┬───────┘                     │                                    │
│          │                             │                                    │
│          ▼                             │                                    │
│  ┌───────────────────────────────┐     │                                    │
│  │ 7. 模块映射 (L1/L2)            │     │                                    │
│  └───────┬───────────────────────┘     │                                    │
│          │                               │                                    │
│          ▼                               │                                    │
│  ┌───────────────────────────────┐     │                                    │
│  │ 8. 函数识别 (L3) [可选]        │     │                                    │
│  └───────┬───────────────────────┘     │                                    │
│          │                               │                                    │
│          ▼                               │                                    │
│  ┌───────────────────────────────┐     │                                    │
│  │ 9. 依赖分析 [可选]             │     │                                    │
│  └───────┬───────────────────────┘     │                                    │
│          │                               │                                    │
│          ▼                               │                                    │
│  ┌───────────────┐                     │                                    │
│  │ 10. 测试匹配   │                     │                                    │
│  └───────┬───────┘                     │                                    │
│          │                             │                                    │
│          ▼                             │                                    │
│  ┌───────────────┐                     │                                    │
│  │ 11. 置信度评估 │                     │                                    │
│  └───────┬───────┘                     │                                    │
│          │                             │                                    │
│          ▼                             │                                    │
│  ┌───────────────┐                     │                                    │
│  │ 12. 报告生成   │                     │                                    │
│  └───────┬───────┘                     │                                    │
│          │                             │                                    │
│          ▼                             │                                    │
│  ┌───────────────┐                     │                                    │
│  │ 13. 结果输出   │                     │                                    │
│  └───────────────┘                     │                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 详细步骤

### Step 1: 输入接收

```python
def step1_receive_input(user_input):
    """
    接收用户输入
    """
    # 解析输入类型
    input_type = classify_input(user_input)

    # 提取输入数据
    input_data = {
        "type": input_type,
        "raw": user_input,
        "parsed": parse_input(user_input, input_type)
    }

    return input_data


def classify_input(user_input):
    """
    分类输入类型
    """
    # GitHub PR 链接
    if "github.com" in user_input and "/pull/" in user_input:
        return "github_pr"

    # GitLab MR 链接
    if "gitlab.com" in user_input and "/merge_requests/" in user_input:
        return "gitlab_mr"

    # PR 编号 (需要配合 repo)
    if re.match(r"^(#?\d+|PR\s+#?\d+)", user_input, re.IGNORECASE):
        return "pr_number"

    # Diff 内容
    if user_input.startswith("diff --git"):
        return "diff"

    # 文件路径
    if user_input.startswith("--- a/") or user_input.startswith("+++ b/"):
        return "diff"

    return "unknown"
```

### Step 2: 工具发现 & 适配器选择

> ⚠️ **实际经验注意**：`claude mcp list` 只做静态配置检查，存在检测遗漏问题。
> - 某些 MCP（如 github-mcp）动态加载，不在静态配置中
> - `/mcp` 对话框显示的状态更准确
> - **最佳实践**：直接尝试验证工具是否可用

```python
def step2_discover_tools():
    """
    发现可用工具
    """
    tools = []

    # 1. 检查 MCP（静态 + 动态验证）
    mcp_tools = list_mcp_tools()
    # 静态配置检查
    if any("github" in t.name.lower() for t in mcp_tools):
        tools.append(("mcp_github", priority=1))
    if any("gitlab" in t.name.lower() for t in mcp_tools):
        tools.append(("mcp_gitlab", priority=1))

    # 2. 直接验证 MCP 工具是否真正可用（实践验证）
    if is_mcp_tool_available("mcp__github__get_pull_request"):
        # 实际可用，添加到列表
        if ("mcp_github", 1) not in tools:
            tools.append(("mcp_github", priority=1))

    # 3. 检查 CLI
    if has_command("gh"):
        tools.append(("gh_cli", priority=2))
    if has_command("glab"):
        tools.append(("glab_cli", priority=2))

    # 4. 检查 API token
    if os.getenv("GITHUB_TOKEN"):
        tools.append(("github_api", priority=3))
    if os.getenv("GITLAB_TOKEN"):
        tools.append(("gitlab_api", priority=3))

    # 5. 降级: 直接粘贴
    tools.append(("manual", priority=10))

    # 按优先级排序
    tools.sort(key=lambda x: x[1])

    return tools[0][0] if tools else None


def is_mcp_tool_available(tool_name: str) -> bool:
    """
    直接验证 MCP 工具是否可用

    注意：静态检查（如 claude mcp list）可能遗漏动态加载的 MCP
    必须通过实际调用或 /mcp 对话框验证
    """
    try:
        # 方式1: 尝试调用工具元信息（轻量级）
        # 这是理论上的最佳实践，但取决于 MCP 实现
        return True  # 简化处理
    except Exception:
        return False
```

### MCP 检测经验总结

| 检测方式 | 准确性 | 说明 |
|----------|--------|------|
| `/mcp` 对话框 | ✅ 最准确 | 运行时状态 |
| 直接调用 `mcp__xxx__*` | ✅ 准确 | 功能验证 |
| `claude mcp list` | ⚠️ 有遗漏 | 静态配置检查 |

**结论**：工具选择优先级应为：
1. 直接尝试调用 MCP 工具（最可靠）
2. 使用 `/mcp` 对话框确认
3. `claude mcp list` 仅作参考

### Step 3: 代码获取

```python
def step3_fetch_code(identifier, adapter_type):
    """
    获取代码
    """
    adapter = get_adapter(adapter_type)

    try:
        # 获取 PR 信息
        pr_info = adapter.get_pr_info(identifier)

        # 获取 Diff
        diff = adapter.get_diff(identifier)

        # 获取文件列表
        files = adapter.get_files(identifier)

        return {
            "success": True,
            "pr_info": pr_info,
            "diff": diff,
            "files": files
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
```

### Step 4: Diff 解析

```python
def step4_parse_diff(diff_content):
    """
    解析 Diff
    """
    parser = DiffParser()
    result = parser.parse(diff_content)

    return {
        "files": result.files,
        "stats": {
            "total_files": result.metadata.total_files,
            "files_added": result.metadata.files_added,
            "files_modified": result.metadata.files_modified,
            "files_deleted": result.metadata.files_deleted,
            "lines_added": result.metadata.lines_added,
            "lines_removed": result.metadata.lines_removed
        },
        "is_large_pr": result.metadata.total_files > 30
    }
```

### Step 5: 逃逸规则检查

```python
def step5_escape_rules(pr_context):
    """
    检查逃逸规则
    """
    rules = load_escape_rules()

    for rule in rules:
        if rule.matches(pr_context):
            return {
                "matched": True,
                "rule": rule,
                "action": rule.action,
                "confidence": rule.confidence
            }

    return {
        "matched": False,
        "rule": None,
        "action": "integration_plus_e2e",
        "confidence": None
    }
```

### Step 6: 敏感度分级

```python
def step6_sensitivity(change_stats, modules):
    """
    计算敏感度
    """
    sensitivity = SensitivityCalculator.calculate(
        files_changed=change_stats["total_files"],
        lines_changed=change_stats["lines_added"] + change_stats["lines_removed"],
        affected_modules=modules,
        config=get_config()
    )

    return {
        "level": sensitivity.level,  # P0, P1, P2
        "score": sensitivity.score,
        "factors": sensitivity.factors
    }
```

### Step 7: 模块映射

```python
def step7_module_mapping(files, config):
    """
    文件 → 模块映射
    """
    mapper = ModuleMapper(config)
    result = mapper.map_files(files)

    return {
        "mappings": result.files,
        "modules": result.modules,
        "unmapped_files": result.unmapped
    }
```

### Step 8: 函数识别 (L3)

```python
def step8_function_recognition(modules, config):
    """
    识别函数级变更 (L3)
    """
    if not config.get("enable_l3", False):
        return {"functions": [], "skipped": True}

    # 使用代码解析
    parser = CodeParser()

    functions = []
    for module in modules:
        for file in module.files:
            parsed = parser.parse_file(file.path)
            functions.extend(parsed.functions)

    return {
        "functions": functions,
        "skipped": False
    }
```

### Step 9: 依赖分析

```python
def step9_dependency_analysis(modules, config):
    """
    分析模块依赖
    """
    if not config.get("enable_dependency", True):
        return {"dependencies": {}, "skipped": True}

    # 构建依赖图
    graph = build_dependency_graph(modules)

    # 分析影响
    impact = {}
    for module in modules:
        impact[module.name] = {
            "upstream": list(graph.get_dependencies(module.name)),
            "downstream": list(graph.get_dependents(module.name))
        }

    return {
        "dependency_graph": graph,
        "impact": impact,
        "skipped": False
    }
```

### Step 10: 测试匹配

```python
def step10_test_matching(context, config):
    """
    匹配测试用例
    """
    matcher = TestMatcher(config)

    recommendations = matcher.match(
        changed_modules=context["modules"],
        changed_files=context["files"],
        test_type=config.get("default_test_type", "integration")
    )

    return {
        "recommendations": recommendations,
        "summary": {
            "total": len(recommendations),
            "by_priority": count_by_priority(recommendations)
        }
    }
```

### Step 11: 置信度评估

```python
def step11_confidence_assessment(recommendations):
    """
    评估置信度
    """
    assessed = []

    for rec in recommendations:
        # 计算综合置信度
        confidence = calculate_confidence(rec)

        # 生成对比分析
        comparative = generate_comparative_analysis(rec)

        rec.confidence = confidence
        rec.comparative = comparative

        assessed.append(rec)

    return assessed
```

### Step 12: 报告生成

```python
def step12_generate_report(context, recommendations):
    """
    生成报告
    """
    template = load_template("impact-report.md")

    report = template.render(
        summary=context["summary"],
        sensitivity=context["sensitivity"],
        escape_result=context["escape_result"],
        modules=context["modules"],
        recommendations=recommendations,
        data_sources=context["data_sources"]
    )

    return report
```

### Step 13: 结果输出

```python
def step13_output(report, format):
    """
    输出结果
    """
    if format == "markdown":
        return output_markdown(report)
    elif format == "json":
        return output_json(report)
    elif format == "yaml":
        return output_yaml(report)
    else:
        return output_markdown(report)
```

## 条件分支

### 分支1: PR 大小

```
if total_files > 30:
    → 触发分段分析
    → 提示用户确认
elif total_files > 100:
    → 触发分批处理
    → 返回进度报告
```

### 分支2: 逃逸规则

```
if escape_rule.matched:
    → 执行 rule.action
    → 跳转到报告生成
else:
    → 继续标准流程
```

### 分支3: 置信度

```
for recommendation in recommendations:
    if recommendation.confidence >= 0.8:
        → 直接包含在报告中
    elif recommendation.confidence >= 0.5:
        → 标记为"需确认"
        → 包含在可选列表
    else:
        → 跳过或标记为低置信度
```

## 错误处理

| 错误阶段 | 错误 | 处理 |
|---------|------|------|
| Step 2 | 工具不可用 | 提示用户配置 |
| Step 3 | PR 不存在 | 返回错误信息 |
| Step 3 | 网络超时 | 重试 3 次 |
| Step 4 | Diff 解析失败 | 尝试降级解析 |
| Step 7 | 模块映射失败 | 使用 LLM 推断 |
| Step 10 | 无匹配测试 | 返回空列表 + 建议 |

## 回退策略

```
┌─────────────────────────────────┐
│          降级链路                │
├─────────────────────────────────┤
│                                 │
│  L4 (调用链) ──(失败)──► L3    │
│     │                          │
│     │ (失败)                   │
│     ▼                          │
│  L3 (函数级) ──(失败)──► L2    │
│     │                          │
│     │ (失败)                   │
│     ▼                          │
│  L2 (模块级) ──(失败)──► L1    │
│     │                          │
│     │ (失败)                   │
│     ▼                          │
│  L1 (文件级) ──(失败)──► 错误   │
│                                 │
└─────────────────────────────────┘
```

## 性能目标

| 阶段 | 目标时间 | 最大时间 |
|------|---------|---------|
| 工具发现 | < 1s | 2s |
| 代码获取 | < 3s | 10s |
| Diff 解析 | < 1s | 3s |
| 模块映射 | < 2s | 5s |
| 测试匹配 | < 5s | 15s |
| 报告生成 | < 1s | 2s |
| **总计** | < 15s | 40s |

## 相关模块

| 模块 | 关系 |
|------|------|
| `analyzer/main.md` | 使用流程 |
| `templates/impact-report.md` | 报告模板 |
