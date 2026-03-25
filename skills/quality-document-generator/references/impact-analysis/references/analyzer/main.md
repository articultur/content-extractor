# 主分析器逻辑 / Main Analyzer

## 概述

主分析器是 Impact Analysis 的核心引擎，协调各个子模块完成从代码变更到测试建议的完整分析流程。

## 核心职责

| 职责 | 说明 |
|------|------|
| 流程编排 | 协调各子模块的执行顺序 |
| 数据传递 | 管理模块间的数据流转 |
| 结果整合 | 汇总各模块结果生成最终报告 |
| 异常处理 | 处理分析过程中的错误 |

## 分析流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                         主分析器流程                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  输入: PR编号/链接 或 Diff内容                                       │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────┐                                               │
│  │ Step 0: 工具发现 │ ← 检查可用的 MCP/API/Skill                   │
│  └────────┬────────┘                                               │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────────┐                                               │
│  │ Step 1: 代码获取 │ ← 通过适配器获取 PR/diff                      │
│  └────────┬────────┘                                               │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────────┐                                               │
│  │ Step 2: Diff解析 │ ← L1 文件级分析                              │
│  │  diff-parser    │                                               │
│  └────────┬────────┘                                               │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────────┐                                               │
│  │ Step 3: 模块映射 │ ← L2 模块级分析                              │
│  │  module-mapper  │                                               │
│  └────────┬────────┘                                               │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────────┐                                               │
│  │ Step 4: 函数识别 │ ← L3 函数级分析 (可选)                       │
│  └────────┬────────┘                                               │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────────┐                                               │
│  │ Step 5: 逃逸规则 │ ← 检查是否命中逃逸条件                        │
│  └────────┬────────┘                                               │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────────┐                                               │
│  │ Step 6: 敏感度分级 │ ← 计算变更敏感度                           │
│  └────────┬────────┘                                               │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────────┐                                               │
│  │ Step 7: 测试匹配 │ ← 推荐测试用例                               │
│  │  test-matcher   │                                               │
│  └────────┬────────┘                                               │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────────┐                                               │
│  │ Step 8: 置信度   │ ← 评估结果置信度                            │
│  └────────┬────────┘                                               │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────────┐                                               │
│  │ Step 9: 报告生成 │ ← 输出最终报告                               │
│  └────────┬────────┘                                               │
│           │                                                         │
│           ▼                                                         │
│  输出: Impact Report                                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 输入类型

### 类型1: PR 链接/编号

```
输入: "分析 PR #123"
输入: "https://github.com/owner/repo/pull/123"
```

处理流程:
1. 解析 PR 标识
2. 调用适配器获取 PR 信息
3. 获取变更文件列表
4. 获取 diff 内容

### 类型2: 直接粘贴 Diff

```
输入: 用户粘贴完整的 diff 内容
```

处理流程:
1. 解析 diff 内容
2. 提取变更文件
3. 提取变更统计

### 类型3: 混合模式

```
输入: "分析 PR #123，主要关注 payment 模块"
```

处理流程:
1. 正常获取 PR 信息
2. 用户指定关注模块
3. 优先分析指定模块

## 输出结构

```yaml
analysis_result:
  summary:
    changed_files: int
    changed_functions: int
    affected_modules: int
    confidence_score: float
    sensitivity_level: P0 | P1 | P2

  escape_result:
    matched: bool
    rule: string | null
    action: string | null
    confidence: float | null

  modules:
    - name: string
      confidence: float
      evidence: list[string]
      files: list[string]

  tests:
    priority: P0 | P1 | P2
    recommended:
      - test_name: string
        confidence: float
        reason: string
        evidence:
          supporting: list[string]
          opposing: list[string]
    optional:
      - test_name: string
        confidence: float

  data_sources:
    - source: string
      status: success | failed
      details: string

  warnings:
    - message: string
      severity: low | medium | high
```

## 异常处理

| 异常 | 处理方式 |
|------|---------|
| PR 不存在 | 返回错误，提示用户检查 PR 编号 |
| 网络超时 | 重试 3 次，失败则提示用户 |
| Diff 过大 | 触发分批处理逻辑 |
| 无匹配测试 | 返回空列表，提示用户 |
| 工具不可用 | 降级到其他方式或提示配置 |

## 缓存策略

```
┌─────────────────────────────────────────────┐
│              缓存层级                         │
├─────────────────────────────────────────────┤
│                                             │
│  Hot Cache (access_count > 10)              │
│  - 最近频繁访问的分析结果                     │
│  - 保留在内存中                              │
│                                             │
│  Warm Cache (access_count 3-10)            │
│  - 偶尔访问的分析结果                         │
│  - 保留在磁盘                               │
│                                             │
│  Cold Cache (access_count < 3)              │
│  - 很少访问的分析结果                         │
│  - 按需重建                                  │
│                                             │
└─────────────────────────────────────────────┘
```

## 配置参数

```yaml
analyzer:
  # 工具发现
  tool_discovery:
    enabled: true
    priority:
      - mcp
      - skill
      - api

  # Diff 解析
  diff_parser:
    max_file_size_mb: 1
    max_files: 1000

  # 模块映射
  module_mapper:
    use_cache: true
    cache_ttl_hours: 24

  # 测试匹配
  test_matcher:
    default_test_type: integration
    max_recommendations: 50

  # 敏感度分级
  sensitivity:
    core_modules: []      # 用户配置的核心模块
    security_sensitive: [] # 安全敏感模块
```

## 使用示例

### 基本使用

```python
# 伪代码示例
analyzer = ImpactAnalyzer(config)

# 分析 PR
result = analyzer.analyze(pr_url="https://github.com/owner/repo/pull/123")

# 分析 Diff
result = analyzer.analyze(diff_content=pasted_diff)

# 查看结果
print(result.summary)
print(result.recommended_tests)
```

### 高级使用

```python
# 指定配置
config = AnalysisConfig(
    test_type="e2e",
    focus_modules=["payment", "auth"],
    skip_modules=["docs"],
    sensitivity_overrides={"payment": "P0"}
)

result = analyzer.analyze(pr_url="...", config=config)
```

## 相关模块

| 模块 | 文件 | 职责 |
|------|------|------|
| Diff 解析器 | `diff-parser.md` | 解析 diff 内容 |
| 模块映射器 | `module-mapper.md` | 文件 → 模块映射 |
| 测试匹配器 | `test-matcher.md` | 测试用例推荐 |
| 适配器 | `adapters/*.md` | 代码获取 |
| 提示词 | `prompts/*.md` | LLM 分析 |
