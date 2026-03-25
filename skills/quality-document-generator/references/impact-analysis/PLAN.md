# 代码影响分析 (Impact Analysis) - 实施计划
**版本: v1.0**

> 本文档为讨论稿，待确认后实施

---

## 一、功能定位

| 项目 | 内容 |
|------|------|
| **名称** | `impact-analysis` (影响分析) |
| **定位** | 测试策略建议工具 |
| **核心价值** | 输入代码变更 → 输出建议回归范围 |
| **不做的** | 完整AST解析、100%准确判断 |

---

## 二、代码获取方式

### 优先级矩阵

| 优先级 | 方式 | 获取难度 | 代码保密性 | 自动化 | 实时性 |
|--------|------|---------|-----------|--------|--------|
| **P0** | MCP | ⭐ | 内存/临时 | 支持 | 实时 |
| **P1** | GitHub/GitLab API | ⭐⭐ | 可控 | 支持 | 实时 |
| **P2** | 直接粘贴 | ⭐ | ⭐⭐⭐ | 不支持 | 手动 |
| **P3** | Clone到本地 | ⭐ | ⭐⭐⭐ | 支持 | 需clone |
| **P4** | CI/CD Artifacts | ⭐⭐ | ⭐⭐ | 支持 | 延迟 |
| **P5** | Raw URL | ⭐ | 公开友好 | 支持 | 实时 |
| **P6** | Webhook | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | 实时 |
| **P7** | IDE插件 | ⭐⭐⭐ | ⭐⭐⭐ | 可选 | 开发时 |

### 详细说明

#### P0: MCP (推荐)
```
配置一次，永久使用
像读本地文件一样读取远程代码

使用方式:
- "分析PR #123"
- "获取这个文件的diff"
```

#### P1: GitHub/GitLab API
```
需要手动处理，获取diff

API端点:
- GET /repos/{owner}/{repo}/pulls/{pr_number}
- GET /repos/{owner}/{repo}/pulls/{pr_number}/files
```

#### P2: 直接粘贴
```
最简单，用户复制diff/代码内容

适用场景:
- 临时分析
- 隐私敏感场景
- 小量diff
```

#### P3: Clone到本地
```
万不得已的选择

适用场景:
- 需要完整AST分析
- 无网络环境
- 特殊项目不支持API/MCP

注意: 使用临时目录，分析后立即清理
```

#### P4: CI/CD Artifacts
```
从Jenkins/GitHub Actions获取已有构建产物

适用场景:
- 已有完整构建产物
- 需要分析测试结果
- 历史版本对比
```

#### P5: Raw URL
```
公开仓库可直接获取

URL格式:
https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}
```

#### P6: Webhook (自动化)
```
代码变更时自动触发分析

流程:
代码变更 → Webhook → 分析服务 → 生成报告 → 评论到PR/通知Slack
```

#### P7: IDE插件
```
编辑器内实时分析

适用场景:
- VSCode / Cursor / JetBrains插件
- 本地开发时实时分析
```

### 使用模式

#### 模式1: MCP/API模式 (默认)
- 输入: GitHub PR链接 / PR编号
- 处理: MCP或API获取diff，本地分析
- 适用: 云端代码评审

#### 模式2: 直接粘贴模式
- 输入: 用户粘贴diff/代码内容
- 处理: 直接分析粘贴内容
- 适用: 临时分析、隐私场景

#### 模式3: 混合模式
- 基础分析: 本地立即执行
- 深度分析: 可选，用户触发
- 适用: 大型PR分批处理

#### 模式4: 自动化模式
- 触发: Webhook自动推送
- 处理: CI/CD中运行分析
- 适用: 自动化质量门禁

---

## 三、分析层级

| 层级 | 说明 | 准确率 | 速度 |
|------|------|--------|------|
| L1 | 文件级（变更了哪些文件） | >95% | 秒级 |
| L2 | 模块级（文件→模块映射） | >90% | 秒级 |
| L3 | 函数级（识别的函数名） | 70-90% | 秒级 |
| L4 | 调用链（简单import追踪） | 60-80% | 分钟级 |

---

## 四、数据来源优先级

### P0 (必须有)
- [x] 代码diff/变更 - 核心输入
- [x] 测试代码 - 映射到回归用例

### P1 (推荐)
- [ ] 依赖声明 (requirements.txt, package.json)
- [ ] README.md
- [ ] 测试用例列表/路径

### P2 (可选)
- [ ] CODEOWNERS - 知道谁负责
- [ ] OpenAPI/Swagger - API调用方
- [ ] 架构文档

### P3 (锦上添花)
- [ ] Wiki文档
- [ ] 设计决策记录

---

## 五、大PR处理策略

| PR规模 | 处理策略 |
|--------|---------|
| < 1MB | 全量分析，立即返回 |
| 1-5MB | 增量分析，优先核心模块 |
| > 5MB | 分批处理 + 用户确认 |

### 优先级策略

| 优先级 | 文件类型 | 处理方式 |
|--------|---------|---------|
| P0 | 新增文件 | 必须分析 |
| P0 | 修改的核心模块 | 必须分析 |
| P1 | 修改的工具类 | 快速扫描 |
| P2 | 测试文件 | 可选分析 |
| P3 | 文档/配置文件 | 跳过 |

---

## 六、输出格式

```markdown
# 代码影响分析报告

### 变更摘要
- 变更文件: {n}个
- 变更函数: {n}个
- 影响模块: {n}个
- 分析置信度: {score}%

### 影响范围

| 模块 | 置信度 | 说明 |
|------|--------|------|
| user_service | 高(95%) | 直接变更的文件 |
| auth_module | 中(75%) | 共享auth函数 |
| payment | 低(40%) | 不确定是否相关 |

### 建议回归

| 优先级 | 测试用例 | 置信度 |
|--------|---------|--------|
| P0 | test_login_* | 高 |
| P0 | test_auth_token_* | 中 |
| P1 | test_user_profile_* | 低 |

### 数据来源

- 变更代码: GitHub PR #123
- 测试用例: 50个 (已覆盖30个相关)
- 依赖声明: package.json ✓

### 建议

⚠️ auth_module的关联基于函数名推断，请确认是否影响payment模块
```

---

## 七、代码存储策略

### 推荐方案：临时 + 按需

```
分析时: 临时目录 → 分析完成 → 自动清理
         /tmp/.../pr-123/ → 报告输出 → 7天后自动删除
```

| 阶段 | 存储 | 说明 |
|------|------|------|
| 获取diff | 内存/临时文件 | 不持久化 |
| 分析过程 | 临时目录 | 只保留必要文件 |
| 分析完成 | 仅报告 | 代码不存储 |
| 缓存（如需要） | `~/.impact-analysis/cache/` | 可选，节省重复获取 |

### 存储结构（如果选择缓存）

```bash
~/.impact-analysis/
├── config.yaml              # 用户配置
├── cache/                   # 可选的缓存
│   └── {project-name}/
│       ├── pr-123/         # PR #123
│       │   ├── diff        # diff文件
│       │   ├── files/     # 变更文件
│       │   └── analysis/  # 分析结果
│       └── pr-124/
│           └── ...
└── logs/                    # 分析日志
```

### 存储方案对比

| 方案 | 存储位置 | 优点 | 缺点 |
|------|---------|------|------|
| **不存储** | 纯内存/临时 | 隐私最好，无存储成本 | 每次重新获取 |
| **临时目录** | `/tmp/impact-analysis/` | 简单，系统自动清理 | 重启丢失 |
| **项目目录** | `{project}/.impact-analysis/` | 持久化，可重复分析 | 污染项目目录 |
| **统一存储** | `~/.impact-analysis/` | 统一管理，与项目隔离 | 占用用户空间 |

### 安全考虑

| 场景 | 处理方式 |
|------|---------|
| 敏感项目 | 不缓存，直接分析后删除 |
| 私有仓库 | 内存处理，不落盘 |
| 企业内网 | 可配置本地部署 |
| 分析日志 | 不记录敏感内容（仅记录文件名，非内容） |

### 决策点

| 问题 | 选项 |
|------|------|
| 代码是否存储？ | A) 不存储(默认) B) 可选缓存 |
| 缓存位置？ | A) 临时目录 B) 用户目录 C) 项目目录 |
| 缓存清理？ | A) 自动清理(7天) B) 手动清理 C) 永不清理 |

**推荐**: 不存储 + 临时目录 + 自动清理

---

## 八、技术实现方案

### 混合架构

```
┌─────────────────────────────────────────────────────────────┐
│                     混合架构                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  简单操作 (获取PR列表、获取diff) → MCP/API代码封装         │
│                    │                                        │
│                    ▼                                        │
│  复杂分析 (理解代码、推断影响) → LLM + 提示词              │
│                    │                                        │
│                    ▼                                        │
│  输出报告 → 模板填充                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

| 操作类型 | 方式 | 原因 |
|---------|------|------|
| 获取代码/diff | MCP/API代码 | 确定性操作，需要稳定 |
| 理解业务逻辑 | LLM + 提示词 | 需要推理能力 |
| 分析影响范围 | LLM + 提示词 | 需要判断 |
| 生成报告 | 模板 | 结构化输出 |

### 决策：代码写死 vs 动态生成

| 方案 | 说明 | 适用场景 |
|------|------|---------|
| **写死代码** | 预先写好GitHub/GitLab适配器 | 确定只用这几个平台 |
| **动态生成** | 根据用户提供的工具/文档生成 | 多平台、需要扩展 |

#### 动态生成方案（推荐）

```
用户: "配置我的代码平台"
输入: GitHub MCP配置 / GitLab API Token / 自定义API文档

处理:
1. 读取用户提供的配置/文档
2. 生成适配该平台的代码
3. 保存生成的代码到配置目录
4. 使用生成的代码执行操作

优点:
- 一次配置，持续使用
- 支持任何提供API的平台
- 不需要预置所有平台代码

缺点:
- 首次配置需要用户提供正确的配置/文档
- 生成质量依赖用户提供的文档质量
```

### 实现流程

```
Step 0: 工具发现 (优先)
         │
         ▼
Step 1: 检查当前环境中的可用工具
         │
         ▼
Step 2: 有可用工具 → 直接使用
         │
         ▼
Step 3: 没有可用工具 → 询问用户配置
         │
         ▼
Step 4: 生成/更新适配器
         │
         ▼
Step 5: 使用适配器执行操作
```

### 工具发现机制

```
┌─────────────────────────────────────────────────────────────┐
│  Step 0: 自动发现 (优先执行)                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  AI主动检测当前环境已有能力:                                │
│  ├── MCP工具列表 → 发现GitHub/GitLab MCP                 │
│  ├── Skill列表 → 发现可用的Skill                          │
│  ├── 环境变量 → 发现API Token                             │
│  ├── 当前目录 → 发现Git仓库                               │
│  └── Claude Code内置能力 → 发现基础代码读取               │
│                                                             │
│  发现可用工具 → 直接进入Step 2                             │
│  没有发现工具 → 进入Step 3询问用户                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 可发现的工具类型

| 工具类型 | 发现方式 | 可获取能力 |
|---------|---------|-----------|
| MCP | list_mcp_tools() | PR/diff/文件/评审 |
| Skill | list_active_skills() | 任意定义的能力 |
| API Token | 环境变量 | GitHub/GitLab等API |
| Git仓库 | 当前目录/.git | 本地代码 |
| Claude内置 | 原生支持 | 基础代码读取 |

### 用户体验对比

**没有工具发现:**
```
用户: "分析PR #123"
AI: "请告诉我你用什么工具访问GitHub？"
用户: "GitHub MCP"
AI: "好的，让我配置..."
... (多次交互)
```

**有工具发现:**
```
用户: "分析PR #123"
AI: "发现GitHub MCP已配置，直接获取PR #123..."
AI: "分析完成，建议回归以下测试..."
```

### 工具配置示例

#### 方式1: 直接告诉AI (兜底)

```
用户: "我用GitHub Enterprise，地址是 https://ghe.company.com"
AI: 理解 → 生成适配器 → 使用
```

#### 方式2: 提供MCP配置

```json
{
  "type": "mcp",
  "name": "github-enterprise",
  "config": {
    "url": "https://mcp.company.com/github",
    "auth": "oauth"
  }
}
```

#### 方式3: 提供Skill

```
用户: "我有一个读取代码的skill，叫 code-reader"
AI: 调用skill → 获取代码 → 分析
```

#### 方式4: 混合配置

```json
{
  "code": {
    "type": "mcp",
    "provider": "github-enterprise"
  },
  "ci": {
    "type": "skill",
    "name": "jenkins-api"
  },
  "project": {
    "type": "api",
    "openapi": "https://api.company.com/openapi.json"
  }
}
```

### 支持的平台配置方式

| 平台 | 配置方式 |
|------|---------|
| GitHub | MCP配置 / Personal Access Token |
| GitLab | API Token / OAuth |
| 自定义REST API | OpenAPI/Swagger文档 / 手写API文档 |
| 其他 | 通用HTTP配置 + 认证信息 |

### 目录结构更新

```bash
impact-analysis/
├── SKILL.md                    # 技能定义
│
└── references/
    ├── analyzer/
    │   ├── main.md           # 主分析器逻辑
    │   ├── diff-parser.md    # Diff解析
    │   ├── module-mapper.md  # 文件→模块映射
    │   └── test-matcher.md   # 测试用例匹配
    │
    ├── adapters/              # 适配器 (动态生成)
    │   ├── github-adapter.md  # GitHub适配器模板
    │   ├── gitlab-adapter.md # GitLab适配器模板
    │   └── custom-adapter.md # 自定义适配器模板
    │
    ├── prompts/               # 提示词 (LLM驱动)
    │   ├── code-analysis.md   # 代码分析提示词
    │   ├── impact-analysis.md # 影响分析提示词
    │   └── test-matching.md   # 测试匹配提示词
    │
    ├── data-sources/
    │   ├── code-parser.md    # 代码解析
    │   ├── test-parser.md     # 测试代码解析
    │   ├── dependency.md       # 依赖声明解析
    │   └── config.md          # 用户配置
    │
    ├── workflows/
    │   └── analysis-flow.md   # 分析流程
    │
    └── templates/
        └── impact-report.md   # 报告模板
```

---

## 九、目录结构

```
impact-analysis/
├── SKILL.md                    # 技能定义 (可选，集成到主skill)
│
└── references/
    ├── analyzer/
    │   ├── main.md           # 主分析器逻辑
    │   ├── diff-parser.md    # Diff解析
    │   ├── module-mapper.md  # 文件→模块映射
    │   └── test-matcher.md   # 测试用例匹配
    │
    ├── data-sources/
    │   ├── code-parser.md    # 代码解析
    │   ├── test-parser.md    # 测试代码解析
    │   ├── dependency.md      # 依赖声明解析
    │   └── config.md         # 用户配置
    │
    ├── workflows/
    │   └── analysis-flow.md  # 分析流程
    │
    └── templates/
        └── impact-report.md  # 报告模板
```

---

## 十、实施计划

### Phase 1: MVP (核心功能)

| 任务 | 时间 | 状态 |
|------|------|------|
| Diff解析器 | 2天 | 待开发 |
| 文件→模块映射 | 1天 | 待开发 |
| 函数名匹配 | 2天 | 待开发 |
| 测试用例映射 | 2天 | 待开发 |
| 报告生成 | 1天 | 待开发 |
| GitHub API集成 | 2天 | 待开发 |

### Phase 2: 增强功能

| 任务 | 时间 | 状态 |
|------|------|------|
| Import分析 | 3天 | 待开发 |
| 大PR分批处理 | 2天 | 待开发 |
| 置信度优化 | 2天 | 待开发 |
| 多种语言支持 | 3天 | 待开发 |

---

## 十一、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 准确率不足 | 用户过度依赖 | 明确标注置信度 |
| 动态调用检测不到 | 漏报 | 不做L4作为主要依据 |
| 大PR超时 | 分析失败 | 分批处理 + 阈值控制 |
| 配置复杂 | 用户不愿使用 | MVP只做文件名匹配 |

---

## 十二、与主Skill的集成

```
quality-document-generator (主技能)
    │
    ├── 原有功能
    │   ├── 测试报告
    │   ├── 质量评估
    │   └── 评审摘要
    │
    └── 新增功能: impact-analysis
            │
            ├── "分析这个PR"
            ├── "需要回归哪些测试"
            ├── "影响哪些模块"
            └── "补充分析..."
```
## 十三、测试类型与搜索深度

### 测试类型分层

| 测试类型 | 搜索深度 | 说明 | 适用场景 |
|---------|---------|------|---------|
| **Unit** | L2 函数层 | 单元测试只覆盖单函数逻辑 | 简单函数变更 |
| **Integration** (默认) | L1 模块层 + L2 函数层 | 覆盖模块间交互 | 大多数变更 |
| **E2E** | L1 + L2 + L3 全量 | 完整业务流程 | 核心流程变更 |

### 默认配置

```yaml
default_test_type: integration
```

用户不指定时，默认使用 Integration 级别进行分析。

---

## 十四、逃逸规则

### 设计原则

```
PR 输入 → 规则匹配 → 命中逃逸条件 → 执行特殊 Action
                        ↓
                  未命中 → 默认逻辑 (integration_plus_e2e)
```

逃逸规则 = 偏离默认的 case，其他默认。规则少容易维护，新增 case 只需加逃逸规则。

### 逃逸规则定义

```yaml
escape_rules:

  # 1. 测试文件本身变更 → 只跑相关测试
  - condition: files match "^(test/|spec/|__tests__/)"
    action: run_related_tests_only

  # 2. 文档变更 → 跳过分析
  - condition: files match "^(docs/|\.md$|README)"
    action: skip_analysis

  # 3. 配置变更 → 冒烟测试
  - condition: files match "(\.env$|config/|\.yaml$|\.json$)" AND files_changed < 5
    action: minimal_smoke

  # 4. 微小变更 → 单元测试即可
  - condition: files_changed < 3 AND lines_changed < 100
    action: unit_only

  # 5. 大型PR → 分段分析
  - condition: files_changed > 30
    action: segment_analysis

  # 6. 安全相关模块 → 安全测试 + E2E
  - condition: modules match "^(security|auth|permission|crypto)/"
    action: security_focus

  # 7. 数据库迁移 → DB测试优先
  - condition: files match "(migration|schema|\.sql$|alembic)"
    action: db_integration_focus

  # 8. 紧急修复 → 扩大范围
  - condition: title matches "(urgent|hotfix|critical|emergency)"
    action: expand_full_coverage

  # 9. 纯重构 → 回归测试优先
  - condition: lines_removed > lines_added * 0.3 AND files_deleted > 0
    action: regression_focus

  # 10. API接口签名变更 → 调用方验证
  - condition: signature_changed IN diff
    action: api_contract_verification
```

### 代码变更结构逃逸（补充）

```yaml
code_change_patterns:

  # 函数签名变更
  - condition: diff contains "def " AND signature_changed
    action: api_contract_test_plus_smoke

  # 新增/删除 import
  - condition: diff contains "import " AND (added OR removed)
    action: check_dependency_tests

  # 数据库迁移
  - condition: files match "(migration|schema|\.sql$|alembic|prisma)"
    action: db_integration_focus

  # 新增文件为主（可能是新功能）
  - condition: files_added > files_modified * 2
    action: new_feature_scope

  # 重构模式（大量删除+同量新增）
  - condition: files_deleted > 0 AND lines_removed > lines_added * 0.5
    action: refactor_regression_focus

  # API/接口文件变更
  - condition: files match "(api|route|endpoint|handler)"
    action: api_integration_plus_smoke

  # 配置文件变更
  - condition: files match "(\.env|\.config\.|settings\.py|config\.js)"
    action: env_config_test

  # 循环依赖引入
  - condition: circular_dependency_detected
    action: circular_dependency_warning

  # 新增第三方依赖
  - condition: diff contains "package.json" OR "requirements.txt" OR "go.mod"
    action: check_dependency_tests
```

### 判断逻辑

```python
def evaluate(pr_input):
    # 按优先级检查逃逸条件
    for rule in escape_rules:
        if rule.matches(pr_input):
            return rule.action

    # 未命中任何逃逸条件 → 默认
    return "integration_plus_e2e"
```

### Action 类型说明

| Action | 说明 |
|--------|------|
| `skip_analysis` | 跳过分析 |
| `syntax_check_only` | 只做语法检查 |
| `minimal_smoke` | 冒烟测试 |
| `unit_only` | 只测单元 |
| `run_related_tests_only` | 只跑相关测试 |
| `segment_analysis` | 分段分析 |
| `integration_plus_e2e` | 集成测试 + E2E（默认） |
| `security_focus` | 安全测试优先 |
| `db_integration_focus` | 数据库测试优先 |
| `expand_full_coverage` | 扩大测试范围 |
| `regression_focus` | 回归测试优先 |
| `api_contract_verification` | API契约验证 |

---

## 十五、用户申诉/反馈机制

### 设计原则

```
用户: "xxx 不应该关联"
    ↓
系统识别为纠正 → 提取实体 → 询问确认 → 写入规则
    ↓
规则持久化 → 后续分析自动应用
```

### 纠正类型

| 类型 | 示例 | 生成规则 |
|------|------|---------|
| **测试关联** | "test_payment.py 不应该关联到 payment_module" | `test: test_payment.py, not_related_to: [payment_module]` |
| **肯定添加** | "test_user.py 应该关联到 user_module" | `test: test_user.py, related_to: [user_module]` |
| **模块映射** | "user.py 属于 user_service" | `file: user.py, belongs_to: user_service` |
| **敏感度调整** | "payment_module 应该是 P0" | `module: payment_module, sensitivity: P0` |
| **忽略模式** | "忽略 test_ui.py" | `pattern: test_ui.py, ignore: true` |

### 触发模式定义

```yaml
trigger_patterns:

  # 类型1: 否定/排除
  negation:
    keywords: ["不关联", "不应该", "忽略", "不用测", "不是", "不要关联", "排除了", "不用", "排除"]
    patterns:
      - "测试 {test} 不关联 {module}"
      - "{test} 不应该关联"
      - "忽略 {test}"
      - "{test} 不是测 {module}"

  # 类型2: 肯定/添加
  addition:
    keywords: ["应该关联", "要测", "加上", "包括", "还有", "要加上", "关联到", "应该测"]
    patterns:
      - "测试 {test} 应该关联 {module}"
      - "{test} 要测"
      - "加上 {test}"

  # 类型3: 映射修正
  mapping:
    keywords: ["属于", "归类", "是"]
    patterns:
      - "{file} 属于 {module}"
      - "{file} 归类到 {module}"

  # 类型4: 敏感度调整
  sensitivity:
    keywords: ["敏感度", "级别", "P0", "P1", "P2", "重大", "轻微"]
    patterns:
      - "{module} 应该是 P0"
      - "{module} 敏感度太低"

  # 类型5: 忽略模式
  ignore:
    keywords: ["忽略", "跳过", "不用分析"]
    patterns:
      - "忽略 {pattern}"
      - "{pattern} 跳过"
```

### 识别逻辑

```python
def is_correction(statement, analysis_context):
    """判断用户输入是否为纠正"""

    # 检测否定模式
    negation_keywords = ["不关联", "不应该", "忽略", "不用测", "不是"]
    for kw in negation_keywords:
        if kw in statement:
            return ("negation", extract_entities(statement, kw, analysis_context))

    # 检测肯定模式
    addition_keywords = ["应该关联", "要测", "加上", "包括"]
    for kw in addition_keywords:
        if kw in statement:
            return ("addition", extract_entities(statement, kw, analysis_context))

    # 检测敏感度模式
    sensitivity_keywords = ["敏感度", "级别", "P0", "P1", "P2"]
    for kw in sensitivity_keywords:
        if kw in statement:
            return ("sensitivity", extract_entities(statement, kw, analysis_context))

    return None
```

### 规则持久化

```yaml
# 用户规则存储位置
# ~/.impact-analysis/rules/{project_id}/user_rules.yaml

user_rules:
  version: 1
  project_id: my-app
  created_at: 2026-03-25

  test_associations:
    - test: test_payment_ui.py
      not_related_to: [payment_module, checkout_flow]
      reason: "只测 UI mock，无真实调用"
      created_by: user
      created_at: 2026-03-25

  module_mappings:
    - file: user.py
      belongs_to: user_service

  sensitivity_overrides:
    - module: legacy_payment
      level: P0
      reason: "核心支付流程"

  ignore_patterns:
    - pattern: "**/test_ui_*.py"
      reason: "UI 测试跳过"
```

### 规则优先级

```
用户规则 > 项目规则 > 默认规则
```

### 上下文推断

当用户输入不完整时，系统从分析上下文中推断缺失实体：

```
用户: "test_payment.py 不应该关联"
    ↓
系统: 从最近分析结果推断涉及模块
    ↓
系统询问: "是不关联 payment_module 吗？"
```

### 对话流程

```
用户: "test_payment.py 不应该关联"
    ↓
系统检测: 否定模式 → test_payment.py
    ↓
系统推断: 可能涉及 payment_module (从分析上下文)
    ↓
系统询问: "是否保存规则：test_payment.py 不关联 payment_module？"
    ↓
用户确认
    ↓
规则写入 user_rules.yaml
    ↓
系统: "已保存，后续分析将忽略该关联"
```

---



### 待实现功能

| 功能 | 说明 |
|------|------|
| 触发方式 | PR 创建/更新时自动触发分析 |
| 门禁条件 | 满足条件才能合并（覆盖率、敏感度） |
| 结果反馈 | 评论到 PR / 返回 JSON 给 pipeline |
| 失败处理 | strict / warn / disabled 模式 |

### 预期设计（暂定）

```yaml
# GitHub Actions 集成
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  impact-analysis:
    steps:
      - name: Run Impact Analysis
        uses: impact-analysis-action@v1
        with:
          pr-number: ${{ github.event.pull_request.number }}
          gate-mode: warn  # strict | warn | disabled
```

### 门禁模式

| 模式 | 行为 |
|------|------|
| `strict` | 不满足条件 → block merge |
| `warn` | 不满足条件 → warn 但不 block |
| `disabled` | 只生成报告，不做门禁检查 |

---




### 评估维度

| 维度 | 说明 | 权重 |
|------|------|------|
| **变更行数** | lines_changed | 高 |
| **关联模块数** | modules_affected_count | 高 |
| **是否核心模块** | is_core_module | 高 |
| **依赖数量** | downstream_dependencies | 中 |
| **公开接口** | exposes_public_api | 中 |
| **测试覆盖率** | test_coverage_rate | 中 |
| **安全敏感** | is_security_sensitive | 高 |
| **监管域** | is_compliance_domain | 高 |
| **变更频率** | recent_change_frequency | 低 |

### 评分公式

```
敏感度 = f(基础维度) + Σ加分项 - Σ减分项

基础维度:
  - 核心模块: +2
  - 高依赖 (5+ 模块依赖): +2
  - 安全敏感: +2
  - 监管域: +2
  - 大型变更 (>30 文件 OR >1000 行): +1

加分项:
  + 暴露公开接口: +1
  + 低测试覆盖率 (<50%): +1

减分项:
  - 高测试覆盖率 (>80%): -1
  - 低变更频率 (季度首改): -1
  - 微小变更 (<3 文件 AND <100 行): -2
```

### 敏感度级别

| 级别 | 评分范围 | 说明 | 处理策略 |
|------|---------|------|---------|
| **P0 重大** | ≥5 | 核心模块 OR 高影响 | 全量测试 + 人工确认 |
| **P1 中等** | 2-4 | 非核心但有多个关联 | integration + E2E |
| **P2 轻微** | <2 | 微小变更 OR 低影响 | unit + 快速验证 |

### 配置化核心模块

```yaml
# 用户可配置
core_modules:
  - payment/
  - auth/
  - user_management/
  - core_api/

security_sensitive:
  - auth/
  - permission/
  - crypto/
  - payment/

compliance_domains:
  - finance/
  - medical/
  - legal/
```

### 检测逻辑

```python
def calculate_sensitivity(pr_input, module_graph):
    score = 0

    # 基础维度
    if is_core_module(pr_input.modules):
        score += 2
    if downstream_dependencies(pr_input.modules) >= 5:
        score += 2
    if is_security_sensitive(pr_input.modules):
        score += 2
    if is_compliance_domain(pr_input.modules):
        score += 2
    if pr_input.files_changed > 30 or pr_input.lines_changed > 1000:
        score += 1

    # 加分项
    if exposes_public_api(pr_input):
        score += 1
    if test_coverage_rate(pr_input) < 50:
        score += 1

    # 减分项
    if test_coverage_rate(pr_input) > 80:
        score -= 1
    if recent_change_frequency(pr_input) == 'low':
        score -= 1
    if pr_input.files_changed < 3 and pr_input.lines_changed < 100:
        score -= 2

    return classify(score)
```

---




> 后续增强内容



## 十六、敏感度分级

### 评估维度

| 维度 | 说明 | 权重 |
|------|------|------|
| **变更行数** | lines_changed | 高 |
| **关联模块数** | modules_affected_count | 高 |
| **是否核心模块** | is_core_module | 高 |
| **依赖数量** | downstream_dependencies | 中 |
| **公开接口** | exposes_public_api | 中 |
| **测试覆盖率** | test_coverage_rate | 中 |
| **安全敏感** | is_security_sensitive | 高 |
| **监管域** | is_compliance_domain | 高 |
| **变更频率** | recent_change_frequency | 低 |

### 评分公式

```
敏感度 = f(基础维度) + Σ加分项 - Σ减分项

基础维度:
  - 核心模块: +2
  - 高依赖 (5+ 模块依赖): +2
  - 安全敏感: +2
  - 监管域: +2
  - 大型变更 (>30 文件 OR >1000 行): +1

加分项:
  + 暴露公开接口: +1
  + 低测试覆盖率 (<50%): +1

减分项:
  - 高测试覆盖率 (>80%): -1
  - 低变更频率 (季度首改): -1
  - 微小变更 (<3 文件 AND <100 行): -2
```

### 敏感度级别

| 级别 | 评分范围 | 说明 | 处理策略 |
|------|---------|------|---------|
| **P0 重大** | ≥5 | 核心模块 OR 高影响 | 全量测试 + 人工确认 |
| **P1 中等** | 2-4 | 非核心但有多个关联 | integration + E2E |
| **P2 轻微** | <2 | 微小变更 OR 低影响 | unit + 快速验证 |

### 配置化核心模块

```yaml
# 用户可配置
core_modules:
  - payment/
  - auth/
  - user_management/
  - core_api/

security_sensitive:
  - auth/
  - permission/
  - crypto/
  - payment/

compliance_domains:
  - finance/
  - medical/
  - legal/
```

### 检测逻辑

```python
def calculate_sensitivity(pr_input, module_graph):
    score = 0

    # 基础维度
    if is_core_module(pr_input.modules):
        score += 2
    if downstream_dependencies(pr_input.modules) >= 5:
        score += 2
    if is_security_sensitive(pr_input.modules):
        score += 2
    if is_compliance_domain(pr_input.modules):
        score += 2
    if pr_input.files_changed > 30 or pr_input.lines_changed > 1000:
        score += 1

    # 加分项
    if exposes_public_api(pr_input):
        score += 1
    if test_coverage_rate(pr_input) < 50:
        score += 1

    # 减分项
    if test_coverage_rate(pr_input) > 80:
        score -= 1
    if recent_change_frequency(pr_input) == 'low':
        score -= 1
    if pr_input.files_changed < 3 and pr_input.lines_changed < 100:
        score -= 2

    return classify(score)
```



## 十七、增强优化项

### 高优先级优化

#### 1. 规则冲突检测 + 置信度分级

**问题：**多条用户规则可能互相冲突，漏报后用户才知道。

**解决方案：**

```yaml
# 规则增加置信度
escape_rules:
  - condition: files match "^(test/|spec/)"
    action: run_related_tests_only
    confidence: 0.95  # 高置信度，很少误报

  - condition: files_changed < 3
    action: unit_only
    confidence: 0.6  # 中等置信度，需要确认
```

**处理流程：**
```
规则匹配时：
  ├── 置信度 ≥ 0.8 → 直接执行
  ├── 置信度 0.5-0.8 → 提示用户确认
  └── 置信度 < 0.5 → 不执行，建议用户判断
```

**模糊匹配：** 类似规则自动建议，而不是漏报。

#### 2. 置信度透明度 + 对比分析

**问题：**置信度数字不直观，用户不知道怎么用。

**解决方案：** 对比分析，提供正反证据。

```yaml
# 输出示例
关联: test_payment.py → payment_module

支持关联的证据:
  ✓ test_payment.py 调用了 payment_module.process()
  ✓ 文件名相似度高

不支持关联的证据:
  ✗ test_payment.py 主要使用 mock，非真实调用
  ✗ 该测试已被用户标记为"UI测试"

建议: 建议关联，但优先级下调（基于证据2）
```

**设计原则：** 不给用户一个数字让他猜，而是提供正反证据让他判断。

#### 3. 知识图谱优化：按需触发 + 分层缓存

**问题：** 首次构建慢，增量触发条件不明确。

**解决方案：**

```yaml
build_strategy:
  trigger: code_change  # 只有代码变更才触发

  incremental:
    enabled: true
    scope: changed_modules + direct_neighbors
    cache_policy:
      hot: access_count > 10  # 最近常用，保留
      warm: access_count 3-10  # 偶尔用，可回收
      cold: access_count < 3   # 很少用，按需重建

  background:
    enabled: true
    delay_minutes: 5  # 5分钟内的变更合并处理
```

**触发流程：**
```
代码变更 webhook 触发
    ↓
增量构建变更模块 + 直接依赖
    ↓
更新缓存策略（hot/warm/cold）
    ↓
不访问的模块降级，需要时重建
```

**关键点：** 避免全量重建，只做必要的增量。

### 中优先级优化

#### 4. 跨仓库依赖分析

MCP 跨仓库能力 + 降级配置。

#### 5. 前端组件关联

组件名匹配 + UI 测试兜底。

#### 6. 历史风险累计评估

变更频率因子 + 报告增强。

### 低优先级优化

#### 7. 配置漂移检测

作为逃逸规则处理。





## 十八、CI/CD 门禁集成（后续增强）

> **状态**: 后续增强，MVP 暂不包含

### 待实现功能

| 功能 | 说明 |
|------|------|
| 触发方式 | PR 创建/更新时自动触发分析 |
| 门禁条件 | 满足条件才能合并（覆盖率、敏感度） |
| 结果反馈 | 评论到 PR / 返回 JSON 给 pipeline |
| 失败处理 | strict / warn / disabled 模式 |

### 预期设计（暂定）

```yaml
# GitHub Actions 集成
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  impact-analysis:
    steps:
      - name: Run Impact Analysis
        uses: impact-analysis-action@v1
        with:
          pr-number: ${{ github.event.pull_request.number }}
          gate-mode: warn  # strict | warn | disabled
```

### 门禁模式

| 模式 | 行为 |
|------|------|
| `strict` | 不满足条件 → block merge |
| `warn` | 不满足条件 → warn 但不 block |
| `disabled` | 只生成报告，不做门禁检查 |

---


## 待讨论问题

- [x] 能力分层是否合理？ ✓
- [x] 必须能力清单是否完整？ ✓
- [x] 测试类型区分 ✓
- [x] 回退链路 ✓
- [x] 逃逸规则 ✓
- [x] 变更敏感度分级 ✓
- [x] 用户申诉/反馈机制 ✓
- [x] CI/CD门禁集成 → 后续增强
- [x] PR语义利用 → 可跳过

---

## 十九、版本记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v0.1 | 2026-03-25 | 初始版本 |
| v0.4 | 2026-03-25 | 增加必选能力定义 |
| v0.5 | 2026-03-25 | 增加测试类型分层 |
| v0.6 | 2026-03-25 | 增加逃逸规则 |
| v0.7 | 2026-03-25 | 增加敏感度分级 |
| v0.8 | 2026-03-25 | 增加用户申诉/反馈机制 |
| v0.9 | 2026-03-25 | 增加增强优化项 |
| v1.0 | 2026-03-25 | 细化三个风险优化方案 |

---

*文档版本: v1.0*
*创建日期: 2026-03-25*
*状态: 讨论中*
