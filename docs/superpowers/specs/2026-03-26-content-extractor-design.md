# 资料阅读和收集模块 — 设计方案 v3.0

> 基于头脑风暴讨论稿

---

## 一、核心目标

解析异构资料（文档链接、文本、图片、PDF等），抽取需求要点并关联串联，为生成测试文档提供依据。

**关键设计原则：**
- **分层保存** — L1（段落索引）+ L2（结构化），不保存原始文档
- **段落为最小语义单元** — 不切碎，保持语义完整性
- **渐进式信任** — 高置信度自动使用，低置信度标记待确认
- **保留冲突** — 不强制仲裁，让下游决定

---

## 二、输入源与文档类型

### 输入方式

| 方式 | 说明 |
|------|------|
| **粘贴（对话式）** | 用户在对话中直接粘贴文本/Markdown |
| **配置文件** | 通过 `content-extractor.config.yaml` 配置输入源 |

**配置文件示例：**
```yaml
input:
  documents:
    - type: url
      path: https://confluence.example.com/REQ-001
    - type: file
      path: ./docs/requirements.md
    - type: text
      content: |
        粘贴的原始文本内容
```

### 输入源

| 类型 | 示例 |
|------|------|
| 本地文件 | PDF、Word、图片、文本 |
| 远程链接 | 网页、GitHub 文档 |
| 粘贴内容 | 文本、Markdown |

### 文档类型（混合支持）

- 需求文档 (SRS)
- UI/原型文档
- API 接口文档
- 数据库设计
- 测试策略文档
- 会议纪要/聊天记录

### 链接识别策略

粘贴多个链接时，系统自动识别类型并选择解析器：

```
粘贴的链接们
    │
    ▼
┌─────────────────────────────────────┐
│  Step 1: URL 模式识别               │
│  - 域名匹配 (confluence, github...) │
│  - 路径正则 (/blob/, /issues/...)  │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  Step 2: 内容类型探测               │
│  - HEAD 请求获取 MIME type          │
│  - 备用：文件扩展名推断             │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  Step 3: 选择解析器                 │
└─────────────────────────────────────┘
```

**URL 模式识别：**

```python
URL_PATTERNS = {
    "confluence": {
        "domains": ["confluence.atlassian.com", "*.atlassian.net"],
        "parser": "html_parser"
    },
    "github": {
        "domains": ["github.com", "gist.github.com"],
        "path_patterns": {
            r"/blob/.*\.(md|markdown)$": "markdown",
            r"/blob/.*\.(py|js|ts|go|java)$": "code",
            r"/wiki/": "wiki"
        },
        "parser": "github_parser"
    },
    "jira": {
        "domains": ["*.jira.com"],
        "parser": "jira_parser"  # 需要 API
    },
    "notion": {
        "domains": ["notion.so", "*.notion.site"],
        "parser": "html_parser"
    }
}

CONTENT_PARSERS = {
    "pdf": "pdf_extractor",
    "markdown": "markdown_extractor",
    "html": "html_extractor",
    "image": "image_extractor",  # OCR
    "code": "code_extractor"
}
```

**已知局限：**
- 私有链接需要认证 Token
- JavaScript 渲染页面需要 Playwright
- Rate limit 需要考虑限流

### 认证策略

链接访问需要认证时，通过配置文件管理 Token：

```yaml
# content-extractor.config.yaml
credentials:
  github:
    token: "${GITHUB_TOKEN}"    # 环境变量引用
  confluence:
    token: "${CONFLUENCE_TOKEN}"
    base_url: "https://company.atlassian.net"
  jira:
    token: "${JIRA_TOKEN}"
    base_url: "https://company.atlassian.net"
    email: "${JIRA_EMAIL}"
```

**Token 获取方式优先级：**
1. 环境变量（安全，不进代码库）
2. 配置文件（需加入 .gitignore）
3. 用户交互输入（一次性）

**Rate Limit 处理：**
```python
RATE_LIMITS = {
    "github": {"requests": 60, "window": 3600},  # 60次/小时
    "confluence": {"requests": 100, "window": 3600},
}

# 超出限制时自动降级：
# 1. 减少并发请求
# 2. 启用缓存复用
# 3. 提示用户等待
```

### 输出方式

以 **Markdown 文档**为主，附带 JSON 便于程序处理：

```
输出/
├── requirements-report.md      # 主报告
├── requirements-report.json   # 结构化数据
└── assets/                   # 图片等资源
```

---

## 三、信息分层保存

### 三层架构

```
L0: 原始文档 ── 不保存，只存引用路径
L1: 段落索引 ── 段落为最小语义单元，保留原始文本
L2: 结构化层 ── 机器可读，供下游使用
```

### L1：段落索引层

```json
{
  "paragraphs": [
    {
      "id": "para_001",
      "source": "需求文档.md#3.2.1",
      "section": "3.2.1",
      "section_priority": 1,
      "raw_text": "用户登录后，如果积分大于1000，自动升级为VIP会员，享受专属折扣",
      "semantic_unit": true,

      "sentences": [
        {"id": "s1", "text": "用户登录后", "role": "trigger"},
        {"id": "s2", "text": "如果积分大于1000", "role": "condition"},
        {"id": "s3", "text": "自动升级为VIP会员", "role": "action"},
        {"id": "s4", "text": "享受专属折扣", "role": "result"}
      ],
      "sentence_relations": [
        {"from": "s2", "to": "s3", "type": "if_then"}
      ]
    }
  ]
}
```

### L2：结构化层

```json
{
  "functions": [
    {
      "id": "func_001",
      "name": "用户登录",
      "name_normalized": "user_login",
      "source_paragraphs": ["para_001"],
      "confidence": 0.9,

      "extracted": {
        "trigger": "用户登录",
        "condition": "积分大于1000",
        "action": "升级VIP",
        "benefit": "专属折扣"
      },

      "attributes": {
        "auth_methods": ["密码", "验证码"],
        "priority_from_source": "必须",
        "source_authority": "甲方"
      },

      "cross_references": [
        {"to": "api_001", "type": "implements", "confidence": 0.95},
        {"to": "ui_001", "type": "rendered_as", "confidence": 0.65}
      ],

      "conflicts": [],
      "needs_review": false
    }
  ]
}
```

---

## 四、异构信息关联

### 文档内引用提取

文档中的引用是最高质量的关联线索。

```python
# 引用类型
REFERENCES_TYPES = {
    "section_ref": "章节引用，见第X章",
    "cross_doc_ref": "跨文档引用，详见X文档",
    "url_ref": "URL链接",
    "term_def_ref": "术语定义引用"
}

# 引用提取模式
patterns = {
    "cross_doc": [
        r"详见[《"]?(.+?)[文档手册]",
        r"参见[《"]?(.+?)[》\]]",
        r"[《"]?(.+?)[》\]]\s*[第见]?\s*([0-9.]+)章?"
    ],
    "section": [
        r"见第?([0-9.]+)节?",
        r"如图?([0-9]+(?:\.[0-9]+)?)",
        r"参考第?([0-9.]+)节"
    ],
    "url": r"https?://[^\s<>\"]+"
}
```

### 引用 → 关联 转换

```
"登录接口详见《API文档》第5章"
    │
    ▼ Step 1: 提取引用
    target_doc = "API文档"
    target_section = "5"
    │
    ▼ Step 2: 定位目标实体
    API文档#5 → entity_id = "api_005" (POST /auth/login)
    │
    ▼ Step 3: 建立关联
    func_001 (登录功能) ──implements──→ api_005 (登录接口)
                          source_ref: "需求文档#3.2#para_001"
```

### 循环引用检测

```python
def detect_cycles(relations):
    """检测循环引用: A→B→C→A"""
    graph = build_graph(relations)

    for cycle in find_cycles(graph):
        yield {
            "type": "cycle_detected",
            "entities": cycle,
            "message": f"循环引用: {' → '.join(cycle)}"
        }
```

### 三层关联机制

| 层次 | 方法 | 适用场景 |
|------|------|----------|
| **术语映射** | 规则驱动，同义词标准化 | 同名不同表述 |
| **跨文档引用** | 显式链接建立关系 | API-功能-页面对应 |
| **实体对齐** | 合并同名实体，处理冲突 | 多文档描述同一功能 |

### 术语标准化

```json
{
  "term_normalization": {
    "user_login": ["用户登录", "登录", "login", "sign_in", "认证", "authentication"],
    "create_order": ["创建订单", "下单", "createOrder", "new_order"]
  }
}
```

### 跨文档关联

```json
{
  "cross_doc_relations": [
    {
      "id": "rel_001",
      "from": {"entity_id": "func_001", "doc": "需求文档"},
      "to": {"entity_id": "api_001", "doc": "API文档"},
      "type": "implements",
      "confidence": 0.95,
      "status": "auto"
    },
    {
      "id": "rel_002",
      "from": {"entity_id": "func_001", "doc": "需求文档"},
      "to": {"entity_id": "ui_001", "doc": "UI文档"},
      "type": "rendered_as",
      "confidence": 0.65,
      "status": "manual_review"
    }
  ]
}
```

### 冲突处理策略

**优先级：LLM 仲裁 → 人工兜底**

```
冲突检测
    │
    ▼
┌─────────────────────────────────────┐
│ Step 1: 规则层初筛                   │
│ - 检测是否为真正冲突                 │
│ - 判断严重性 (high/medium/low)       │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ Step 2: LLM 仲裁                    │
│ - 输入冲突描述 + 各方观点            │
│ - LLM 判断是否冲突 + 推荐解决        │
│ - 置信度高 → 自动采用                │
│ - 置信度低 → 标记待确认              │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ Step 3: 人工兜底                    │
│ - LLM 无法解决的 → 标记 needs_human │
│ - 输出建议和冲突上下文              │
│ - 人工确认最终值                     │
└─────────────────────────────────────┘
```

### 自动解决策略（LLM 前置过滤）

**核心原则：谁决策，谁负责**

```
决策者文档 > 执行者文档
```

| 策略 | 说明 |
|------|------|
| **决策权威** | 谁签字/批准，谁的文档优先级高 |
| **推导关系** | 推导出的结论 < 原始决策 |
| **平等地位** | 多方平等时，以签字顺序或时间为准 |

```python
# 决策权威优先级（可配置）
DECISION_PRIORITY = {
    "甲方": 5,      # 最高
    "产品经理": 4,
    "开发": 3,
    "测试": 2,
    "LLM": 1,      # 仅作为补充
    "unknown": 0
}

# 推导层级
DERIVATION_LEVEL = {
    "原始需求": 3,   # 最高
    "派生分析": 2,
    "实现细节": 1
}
```

**优先级计算：**
```
优先级 = DECISION_PRIORITY[来源] * 0.6 + DERIVATION_LEVEL[层级] * 0.4
```

> **不定死**：用户可通过配置文件自定义权威权重，适应不同组织结构。

### 冲突严重性

| 级别 | 判断标准 | 处理方式 |
|------|----------|----------|
| **high** | 功能实现层面冲突 | LLM 优先仲裁 + 人工确认 |
| **medium** | 测试范围影响 | LLM 仲裁 + 标记 warning |
| **low** | 纯粹表述差异 | 忽略或自动合并 |

### 冲突输出格式

```json
{
  "conflicts": [
    {
      "id": "conflict_001",
      "type": "field_value",
      "severity": "high",
      "field": "password_min_length",

      "values": [
        {
          "source": "需求文档#3.2",
          "content": "密码至少8位",
          "authority": "甲方",
          "timeline": "2026-03-01"
        },
        {
          "source": "API文档#5.1",
          "content": "密码长度6-20位",
          "authority": "开发",
          "timeline": "2026-03-15"
        }
      ],

      "resolution_attempts": [
        {
          "strategy": "authority",
          "applied": true,
          "winner": "需求文档#3.2",
          "reason": "甲方权威性最高"
        },
        {
          "strategy": "llm",
          "applied": true,
          "llm_response": {
            "is_conflict": true,
            "recommendation": "以需求为准（8位），API可作为实现细节",
            "confidence": 0.75
          },
          "resolved": false,
          "reason": "LLM置信度低于阈值(0.8)"
        }
      ],

      "resolved": false,
      "final_value": null,
      "needs_human": true,
      "human_review": {
        "status": "pending",
        "suggestion": "需与甲方确认：密码长度应以哪个为准",
        "decided_value": null,
        "decided_by": null,
        "decided_at": null
      }
    }
  ]
}
```

### LLM 仲裁 Prompt

```python
CONFLICT_RESOLUTION_PROMPT = """
你是一个需求分析师，正在判断文档冲突并推荐解决方案。

## 冲突描述
{conflict_description}

## 各方观点
{values}

## 判断标准
1. 这是否真正冲突？（是/否/部分）
2. 如果冲突，哪个应该作为测试标准？
3. 你的置信度是多少？（0-1）

## 输出格式
{
    "is_conflict": true/false,
    "reason": "判断理由",
    "recommendation": "推荐解决方案",
    "confidence": 0.0-1.0
}
"""
```

```json
{
  "conflicts": [
    {
      "id": "conflict_001",
      "entity": "auth_method",
      "values": {
        "需求文档": "密码",
        "API文档": "验证码"
      },
      "resolved": false,
      "suggestion": "需与产品确认",
      "affected_functions": ["func_001"]
    }
  ]
}
```

---

## 五、信息完整性保证

### 渐进式信任

```
高置信度 (≥0.8) ──→ 自动使用
中置信度 (0.5-0.8) ──→ 标记 warning，使用时提醒
低置信度 (<0.5) ──→ 标记 needs_review，人工确认
```

### 保留的信息维度

| 信息类型 | 保留方式 |
|----------|----------|
| **语气/强调** | `priority_from_source: "必须"` 而非简单 P1 |
| **层级关系** | `parent_id`, `children_ids` |
| **依赖关系** | `dependencies: [func_xxx]` |
| **来源权威性** | `source_authority: "甲方/开发/LLM"` |
| **时间约束** | `constraints: ["上线前"]` |
| **冲突标记** | `conflicts: [...]` 不强制仲裁 |

---

## 六、输出结构

```json
{
  "metadata": {
    "module": "content-extractor",
    "version": "2.0.0",
    "sources": ["需求文档.md", "API文档.pdf", "UI文档.png"],
    "extracted_at": "2026-03-26T12:00:00Z",
    "stats": {
      "total_inputs": 5,
      "succeeded": 5,
      "partial": 0,
      "failed": 0
    }
  },

  "l1_paragraphs": { ... },

  "l2_structured": {
    "functions": [ ... ],
    "business_rules": [ ... ],
    "data_contracts": [ ... ]
  },

  "cross_doc_relations": [ ... ],

  "conflicts": [ ... ],

  "images": [
    {
      "ref": "UI文档.png#img_001",
      "type": "screenshot",
      "ocr_text": "登录页面截图...",
      "has_text": true,
      "needs_vision_model": true,
      "related_functions": ["func_001"]
    }
  ],

  "flowcharts": [ ... ],

  "tables": [ ... ],

  "functionality_graph": {
    "nodes": [
      {"id": "func_user_login", "type": "functionality", "name": "用户登录"},
      {"id": "api_login", "type": "api_endpoint", "name": "POST /auth/login", "parent": "func_user_login"},
      {"id": "ui_login_page", "type": "ui_page", "name": "登录页面", "parent": "func_user_login"}
    ],
    "edges": [
      {"from": "func_user_login", "to": "api_login", "type": "implemented_by"},
      {"from": "func_user_login", "to": "ui_login_page", "type": "rendered_as"}
    ]
  }
}
```

---

## 七、异常处理

| 情况 | 处理 |
|------|------|
| 成功解析 | 正常输出 |
| 部分解析 | 输出 + 段落标记 `status: partial` |
| 完全失败 | 警告 + 记录到 `metadata.failures` |
| 冲突无法解决 | 标记 `resolved: false` + `suggestion` |
| 敏感数据检测 | 标记 `sensitive_data_detected: true` |

### 错误码

```python
class ExtractionError(Enum):
    FILE_NOT_FOUND = "E001"
    UNSUPPORTED_FORMAT = "E002"
    PARSE_FAILED = "E003"
    PARTIAL_PARSE = "E004"
    SENSITIVE_DATA_DETECTED = "E005"
    SIZE_EXCEEDED = "E006"
    NETWORK_ERROR = "E007"
    ENTITY_CONFLICT = "E008"
```

---

## 八、图片/流程图处理

### 图片策略（分阶段）

| 阶段 | 实现 |
|------|------|
| Phase 1 | OCR 能做就做，复杂图标记 `needs_vision_model: true` |
| Phase 2 | 集成多模态 LLM 处理 `needs_vision` 的图片 |
| 后续 | 根据实际需要扩展 |

### 图片输出

```json
{
  "images": [
    {
      "ref": "文档A.md#img_001",
      "type": "screenshot|diagram|flowchart|architecture",
      "ocr_text": "提取的文字",
      "has_text": true,
      "has_visual_structure": true,
      "needs_vision_model": true,
      "visual_note": "登录表单截图"
    }
  ]
}
```

---

## 九、关联评估实现方式

### 规则/脚本 vs LLM 分工

| 评估项 | 实现方式 | 理由 |
|--------|----------|------|
| **术语匹配** | 规则/脚本 | 同义词词典查表，速度快 |
| **章节引用提取** | 规则/脚本 | 正则匹配，准确可靠 |
| **跨文档引用** | 规则/脚本 | 模式固定，如"详见X文档" |
| **语义相似度** | LLM | 需要理解上下文含义 |
| **隐式关联发现** | LLM | 需要推理能力 |
| **冲突判断** | 规则+LLM混合 | 规则初筛，LLM 仲裁 |
| **上下文理解** | LLM | 需要语义理解 |
| **实体对齐** | LLM | 需要判断语义等价 |

### 规则层职责

```python
# 1. 术语标准化
term_normalize("用户登录") → "user_login"
term_normalize("login") → "user_login"

# 2. 引用提取
re.search(r"详见(.+?)文档", text) → "API文档"

# 3. 候选生成
candidates = find_by_normalized_name("user_login")

# 4. 冲突检测
if value_a != value_b: → 标记冲突

# 5. 置信度基础分
base_score = 0.5
if exact_match: base_score += 0.4
if cross_doc_ref: base_score += 0.3
```

### LLM 层职责

```python
# 1. 语义相似度计算
llm.embedding_similarity(
    entity_a="用户登录功能，支持手机号和密码",
    entity_b="POST /auth/login, 参数: phone, code"
) → 0.92

# 2. 隐式关联发现
llm.find_hidden_relations(
    source_entity="用户登录",
    all_entities=[所有抽取的实体]
) → [
    {"target": "api_auth_login", "relation": "implements", "confidence": 0.88},
    {"target": "ui_login_page", "relation": "rendered_as", "confidence": 0.75}
]

# 3. 冲突判断
llm.check_conflict(
    desc_a="密码至少8位",
    desc_b="密码长度不限"
) → {"is_conflict": true, "severity": "high"}

# 4. 上下文补全
llm.extract_implied_info(
    text="用户登录后，如果积分大于1000，自动升级为VIP"
) → {
    "trigger": "用户登录",
    "condition": "积分 > 1000",
    "action": "升级VIP",
    "implied_benefit": "享受专属折扣"
}

# 5. 实体对齐
llm.align_entities(
    entities=[登录功能, /auth/login, 登录页面]
) → {"group_id": "user_login", "relations": {...}}
```

### 完整关联流程

```
┌─────────────────────────────────────────────────────────┐
│  输入: 多份已抽取的文档 (L1+L2)                          │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 1: 规则层预处理                                   │
│  - 引用提取 (正则)                                      │
│  - 术语标准化                                          │
│  - 候选生成                                            │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 2: LLM 核心处理                                  │
│  - 语义相似度计算                                      │
│  - 隐式关联发现                                        │
│  - 冲突判断                                            │
│  - 上下文补全                                          │
│  - 实体对齐                                            │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 3: 规则层后处理                                  │
│  - 置信度加权                                          │
│  - 循环检测                                            │
│  - 冲突聚合                                            │
│  - 输出格式化                                          │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  输出: 关联图 (functionality_graph)                       │
│  - nodes: 功能/接口/页面                                │
│  - edges: implements/rendered_as/depends_on             │
└─────────────────────────────────────────────────────────┘
```

### 置信度计算公式

```python
def calculate_confidence(entity_a, entity_b, evidence):
    score = 0.0

    # 规则得分 (可解释)
    if evidence.term_match:
        score += 0.3 * evidence.term_match_score
    if evidence.cross_doc_ref:
        score += 0.4  # 明确引用，加高权重
    if evidence.exact_match:
        score += 0.2

    # LLM 得分 (补充语义)
    if evidence.semantic_sim:
        score += 0.2 * evidence.semantic_sim

    # 上下文得分
    if evidence.context_score:
        score += 0.1 * evidence.context_score

    return min(1.0, score)
```

### LLM 调用策略

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| **实时调用** | 每次分析都用最新结果 | 追求最高质量 |
| **缓存结果** | 批量处理后缓存 | 降低成本，提高速度 |

> **注：** 不计成本时，采用实时调用，确保每次分析都用最新 LLM 能力。

---

## 十、文件结构

独立 Skill，放置于 `skills/content-extractor/`：

```
skills/
└── content-extractor/           # 独立 Skill
    ├── SKILL.md                # Skill 入口
    ├── config.py               # 配置管理
    │
    ├── handlers/               # 输入处理
    │   ├── __init__.py
    │   ├── clipboard.py        # 粘贴内容处理
    │   ├── file_handler.py     # 本地文件处理
    │   ├── url_handler.py      # 远程链接处理
    │   └── config_loader.py    # 配置文件加载
    │
    ├── extractors/             # 内容提取
    │   ├── __init__.py
    │   ├── pdf_extractor.py
    │   ├── docx_extractor.py
    │   ├── markdown_extractor.py
    │   ├── html_extractor.py
    │   ├── image_extractor.py  # OCR
    │   └── text_extractor.py
    │
    ├── associator/             # 关联串联
    │   ├── __init__.py
    │   ├── term_mapper.py      # 术语映射（规则驱动，查字典）
    │   ├── ref_linker.py       # 引用关联
    │   └── entity_aligner.py   # 实体对齐（LLM辅助）
    │
    ├── dictionaries/           # 术语字典（程序查找表，不进prompt）
    │   ├── base_terms.yaml     # 基础术语（50-80个）
    │   └── custom/             # 用户自定义
    │
    ├── merger/                 # 合并处理
    │   ├── __init__.py
    │   ├── conflict_resolver.py
    │   ├── gap_detector.py     # 缺失检测
    │   └── graph_builder.py
    │
    ├── output/                 # 输出格式
    │   ├── __init__.py
    │   ├── markdown_report.py  # Markdown 报告生成
    │   └── json_exporter.py    # JSON 结构导出
    │
    ├── templates/              # 报告模板
    │   └── requirements_report.md
    │
    ├── models/                 # 数据模型
    │   ├── __init__.py
    │   ├── paragraph.py        # L1 段落
    │   ├── structured.py      # L2 结构化
    │   └── analysis_result.py  # 分析结果
    │
    └── main.py                 # Skill 入口点
```

**术语字典设计要点：**
- **base_terms.yaml**：50-80个核心术语，覆盖通用软件概念
  ```yaml
  # base_terms.yaml (示例)
  user:
    - user
    - 用户
    - 用户管理
    - users
    - account
    - 账户
  auth:
    - login
    - sign_in
    - 登录
    - 认证
    - authenticate
    - authentication
    - 验证
  password:
    - password
    - 密码
    - pwd
    - passwd
  payment:
    - pay
    - payment
    - 支付
    - 结账
    - checkout
    - settle
    - 结算
  order:
    - order
    - 订单
    - 订购
    - purchase
  refund:
    - refund
    - 退款
    - 退费
    - 退货
  vip:
    - vip
    - 会员
    - 会员等级
    - premium
    - 高级用户
  discount:
    - discount
    - 折扣
    - 优惠
    - coupon
    - 优惠券
  points:
    - points
    - 积分
    - credit
    - score
  notification:
    - notification
    - 通知
    - 消息
    - message
    - push
    - 推送
  ```
- **用途**：关联时查表匹配，不进 LLM prompt
- **匹配流程**：`提取术语` → `查字典得同义词` → `规则匹配代码` → `LLM处理未命中`

---

## 十一、MVP 范围与迭代规划

### MVP 范围（Phase 1）

| 模块 | MVP 功能 |
|------|---------|
| **输入** | 文本粘贴、Markdown、本地文件 |
| **解析** | Markdown 解析、图片 OCR |
| **关联** | 术语映射（规则）、跨文档引用（正则） |
| **输出** | Markdown 报告 + JSON |
| **LLM** | 语义增强、冲突仲裁 |

### V1 范围（Phase 2）

| 模块 | V1 功能 |
|------|---------|
| **输入** | + PDF、Word、远程 URL |
| **关联** | + 实体对齐、增量更新 |
| **输出** | + 用户反馈循环 |

### V2 范围（Phase 3）

| 模块 | V2 功能 |
|------|---------|
| **关联** | + 向量语义搜索 |
| **图片** | + 多模态 LLM |
| **协作** | + 多用户反馈系统 |

---

## 十二、外部依赖

| 依赖 | 用途 | 必选 |
|------|------|------|
| `pdfplumber` | PDF 解析 | 是 |
| `python-docx` | Word 解析 | 是 |
| `pytesseract` | OCR | 是 |
| `markdown-it` | Markdown 解析 | 是 |
| `beautifulsoup4` | HTML 解析 | 是 |
| `playwright` / `requests` | 远程链接抓取 | 是 |
| `openai` / `anthropic` | LLM 调用 | 是 (大量调用) |
| `tiktoken` | Token 计算 | 否 |

---

## 十三、已知局限

- 纯图片流程图需人工解读
- 加密 PDF 无法解析
- 手写内容识别率低
- 架构图/时序图等复杂图需多模态 LLM
- 跨语言关联依赖术语词典覆盖

---

## 十三、用户反馈循环

### 交互流程

`needs_human: true` 的冲突通过以下流程处理：

```
分析完成 → 输出 Markdown 报告
              │
              ├→ 报告末尾列出 needs_review 项
              │
              └→ JSON 输出带 actions（供 Claude Code 直接执行）
```

### Markdown 报告中的待确认事项

```markdown
## 待确认事项 (3)

1. **[conflict_001]** 密码长度冲突
   - 需求文档#3.2：「密码至少8位」
   - API文档#5.1：「密码长度6-20位」
   - 建议：确认后更新此处

2. **[conflict_002]** VIP 门槛
   ...
```

### JSON Actions

```json
{
  "conflicts": [
    {
      "id": "conflict_001",
      "type": "field_value",
      "severity": "high",
      "needs_human": true,
      "suggestion": "需与甲方确认密码长度标准"
    }
  ],
  "actions": [
    {
      "type": "resolve_conflict",
      "conflict_id": "conflict_001",
      "decision_field": "password_length",
      "suggested_value": "8",
      "llm_suggestion": "以需求文档为准（8位）"
    }
  ]
}
```

### 用户流程

1. 查看 Markdown 报告末尾的待确认事项
2. 决定后告诉 Claude 要用什么值（如：「密码长度用8位」）
3. Claude 执行更新，标记 `resolved: true` 并记录决定

---

## 十四、增量更新策略

### 文档变更检测

```
输入文档们
    │
    ▼
┌─────────────────────────┐
│ 计算文档哈希             │
│ hash(doc) → hash_v2     │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│ 对比缓存               │
│ cache[url] = hash_v1    │
│ hash_v2 == hash_v1 ?   │
└─────────────────────────┘
    │
    ├── 相同 → 跳过，使用缓存结果
    │
    └── 不同 → 重新分析该文档
                  │
                  ▼
            ┌─────────────────┐
            │ 增量关联更新    │
            └─────────────────┘
```

### 增量关联更新规则

```python
实体变化检测:
    - 新增实体: 建立新关联
    - 删除实体: 保留旧版本标记，移除新关联
    - 修改实体:
        - 字段变化 → 检查相关关联是否仍有效
        - 严重变化（如删除整个功能）→ 标记 orphan
```

### 版本历史

```json
{
  "document_versions": {
    "https://confluence.com/REQ-001": [
      {"version": "v1", "hash": "abc123", "analyzed_at": "2026-03-01"},
      {"version": "v2", "hash": "def456", "analyzed_at": "2026-03-20"}
    ]
  },
  "association_history": {
    "func_001": {
      "v1": {"implementations": ["api_001"], "confidence": 0.95},
      "v2": {"implementations": ["api_001"], "confidence": 0.92}
    }
  }
}
```

### 缓存策略

```python
# 哈希缓存结构
cache = {
    "url": {
        "hash": "sha256_hash",
        "l1_data": {...},
        "l2_data": {...},
        "analyzed_at": "2026-03-26T12:00:00Z"
    }
}

# 缓存有效期（可配置）
CACHE_TTL = {
    "document": 7 * 24 * 3600,  # 7天
    "api_response": 24 * 3600,  # 1天（考虑API可能更新）
}
```

---

## 十五、下游接口：与 impact-analysis 集成

### 并行架构

```
Documents ──→ content-extractor ──┐
                                 ├──→ Merge & Associate ──→ Complete Requirements-Implementation-Testing Chain
Code ──────→ impact-analysis ────┘
```

### 合并输出目标

| 目标 | 说明 |
|------|------|
| **A. 完整需求图** | 需求 → 实现 → 测试用例的完整链路 |
| **B. 缺失检测** | 检测需求-实现-测试的不匹配 |
| **C. 测试推荐** | 基于分析结果推荐测试项 |

### 合并输出结构

```json
{
  "complete_analysis": {
    "requirements_map": {
      "requirements": [Requirement],
      "implementations": [Implementation],
      "test_cases": [TestCase],
      "associations": [Association]
    },
    "gaps": {
      "missing_tests": [GapItem],
      "missing_implementations": [GapItem],
      "orphan_requirements": [GapItem],
      "conflicting_specs": [ConflictItem]
    },
    "recommendations": {
      "priority_tests": [TestRecommendation],
      "regression_scope": RegressionScope,
      "coverage_gaps": [CoverageGap]
    },
    "metadata": {
      "source_documents": [str],
      "analyzed_code_paths": [str],
      "confidence": float,
      "timestamp": str
    }
  }
}
```

### 核心数据模型

```python
Requirement {
  id: str
  content: str           # L1原文
  source: str
  location: (page, line)
  priority: P0|P1|P2
  keywords: [str]      # 术语映射
  linked_implementations: [str]
  linked_tests: [str]
}

Implementation {
  id: str
  file_path: str
  function_names: [str]
  code_snippet: str      # L1原文
  sensitivity_level: P0|P1|P2
  requirements: [str]
  test_coverage: float
}

TestCase {
  id: str
  test_path: str
  test_functions: [str]
  covered_requirements: [str]
  covered_implementations: [str]
  status: covered|partial|missing
}

GapItem {
  type: str
  description: str
  related_ids: [str]
  severity: high|medium|low
  suggestion: str
}
```

---

## 十六、待确认事项

| 事项 | 状态 | 决策 |
|------|------|------|
| 置信度阈值设定 | ✅ 已确认 | ≥0.8 自动，0.5-0.8 warning，<0.5 需确认 |
| LLM 调用策略 | ✅ 已确认 | 不计成本，实时调用，大量参与 |
| 冲突处理策略 | ✅ 已确认 | LLM仲裁 → 人工兜底 |
| 术语词典用途 | ✅ 已确认 | **程序查找表，不进 prompt**，运行时加载 |
| 术语词典初始规模 | ✅ 已确认 | 50-80个核心术语，覆盖通用软件概念 |
| 文件结构 | ✅ 已确认 | 独立 skill：`skills/content-extractor/` |
| 输入方式 | ✅ 已确认 | 粘贴（对话）或配置文件 |
| 输出方式 | ✅ 已确认 | Markdown 文档为主 + JSON 结构化数据 |
| 下游接口 | ✅ 已确认 | 三个目标：完整需求图 + 缺失检测 + 测试推荐 |
| 用户反馈循环 | ✅ 已确认 | Markdown 末尾列出 + JSON actions |
| 增量更新策略 | ✅ 已确认 | 哈希对比 + 增量关联 |
| CLI 调用方式 | ❌ 待定 | - |

---

## 十七、预留扩展点

| 扩展点 | 说明 |
|--------|------|
| **向量库接口** | Phase 2 实现 |
| **多模态 LLM** | Phase 2 处理图片理解 |

---

*文档版本: v4.0*
*创建日期: 2026-03-26*
*最后更新: 2026-03-26 (用户反馈循环、增量更新策略、章节编号全部修复)*
*状态: 待评审*
