# Input Handlers / 输入处理器

## 概述

支持多种输入格式的解析和处理，将不同来源的信息转换为统一的内部数据模型。

---

## 处理器列表

| 处理器 | 支持格式 | 输出 |
|-------|---------|------|
| text-parser | 纯文本、Markdown | 文本内容 |
| code-parser | 所有编程语言 | 代码分析结果 |
| document-parser | Word (.docx)、PDF | 文档结构化内容 |
| spreadsheet-parser | Excel (.xlsx)、CSV | 表格数据 |
| image-parser | PNG、JPG、BMP | OCR文字 |
| review-parser | GitHub PR、Markdown | 评审意见列表 |
| test-result-parser | JUnit XML、pytest JSON、Jest JSON | 测试结果数据 |

---

## text-parser / 文本解析器

### 支持格式
- 纯文本 (.txt)
- Markdown (.md)
- 富文本 (.rtf)

### 处理逻辑

```python
def parse_text(content: str) -> TextData:
    """解析文本输入"""

    data = {
        'raw_text': content,
        'structured': False,
        'paragraphs': [],
        'lists': [],
        'tables': [],
        'code_blocks': [],
        'headings': []
    }

    # 识别标题
    data['headings'] = extract_markdown_headings(content)

    # 识别段落
    data['paragraphs'] = content.split('\n\n')

    # 识别代码块
    data['code_blocks'] = extract_code_blocks(content)

    # 识别列表
    data['lists'] = extract_lists(content)

    # 识别表格 (Markdown表格)
    data['tables'] = extract_markdown_tables(content)

    # 检查是否有结构化标记
    if data['headings'] or data['tables']:
        data['structured'] = True

    return data
```

### 提取规则

| 模式 | 正则表达式 |
|------|-----------|
| Markdown标题 | `^#{1,6}\s+(.+)$` |
| 代码块 | ``` ```[\s\S]*?``` ``` |
| 表格行 | `\|.+\|.+\|` |

---

## code-parser / 代码解析器

### 支持格式
- 所有主流编程语言
- JavaScript/TypeScript, Python, Java, Go, Rust, C/C++, C#, PHP, Ruby, Swift, Kotlin 等

### 处理逻辑

```python
def parse_code(code: str, language: str = None) -> CodeAnalysis:
    """解析代码输入"""

    # 1. 语言识别
    if not language:
        language = detect_language(code)

    # 2. 基础指标
    metrics = calculate_code_metrics(code)

    # 3. 结构分析
    structure = analyze_code_structure(code, language)

    # 4. 问题识别
    issues = identify_code_issues(code, language)

    # 5. 依赖分析
    dependencies = analyze_dependencies(code, language)

    return CodeAnalysis(
        language=language,
        metrics=metrics,
        structure=structure,
        issues=issues,
        dependencies=dependencies
    )
```

### 代码质量指标

| 指标 | 说明 | 计算方式 |
|------|------|---------|
| **复杂度** | 代码复杂程度 | 圈复杂度 |
| **重复率** | 重复代码比例 | 相似代码行/总行数 |
| **行数** | 代码规模 | LOC |
| **注释率** | 注释占比 | 注释行/LOC |
| **文件数** | 源文件数量 | 目录扫描 |

### 问题类型

| 类型 | 检测内容 |
|------|---------|
| **Bug风险** | 空指针、越界、逻辑错误 |
| **安全风险** | SQL注入、XSS、硬编码密码 |
| **性能问题** | N+1查询、内存泄漏 |
| **代码风格** | 命名不规范、过长函数 |

---

## document-parser / 文档解析器

### 支持格式
- Word文档 (.docx)
- PDF文档 (.pdf)

### Word文档解析

```python
def parse_docx(file_path: str) -> DocumentData:
    """解析Word文档"""

    from docx import Document

    doc = Document(file_path)

    data = {
        'title': extract_title(doc),
        'paragraphs': [],
        'tables': [],
        'headings': [],
        'styles': {}
    }

    # 提取段落
    for para in doc.paragraphs:
        data['paragraphs'].append({
            'text': para.text,
            'style': para.style.name,
            'level': get_heading_level(para)
        })

    # 提取标题
    data['headings'] = [p for p in data['paragraphs'] if 'Heading' in p['style']]

    # 提取表格
    for table in doc.tables:
        data['tables'].append(extract_table(table))

    return data
```

### PDF解析

```python
def parse_pdf(file_path: str) -> DocumentData:
    """解析PDF文档"""

    import pdfplumber

    data = {
        'pages': [],
        'tables': [],
        'text': ''
    }

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            # 提取文本
            data['pages'].append(page.extract_text())

            # 提取表格
            tables = page.extract_tables()
            data['tables'].extend(tables)

    data['text'] = '\n'.join(data['pages'])

    return data
```

### 提取内容

| 内容类型 | Word | PDF |
|---------|------|-----|
| 标题 | ✓ | ✓ |
| 段落文本 | ✓ | ✓ |
| 表格 | ✓ | ✓ |
| 图片 | ✓ | ✓ |
| 页眉页脚 | ✓ | ✗ |
| 超链接 | ✓ | ✗ |
| 样式信息 | ✓ | ✗ |

---

## spreadsheet-parser / 表格解析器

### 支持格式
- Excel (.xlsx, .xls)
- CSV (.csv)

### Excel解析

```python
def parse_excel(file_path: str) -> SpreadsheetData:
    """解析Excel文档"""

    import pandas as pd

    data = {
        'sheets': {},
        'metadata': {}
    }

    # 读取所有工作表
    excel_file = pd.ExcelFile(file_path)
    data['metadata']['sheet_names'] = excel_file.sheet_names

    for sheet_name in excel_file.sheet_names:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)

        data['sheets'][sheet_name] = {
            'columns': df.columns.tolist(),
            'rows': len(df),
            'data': df.to_dict('records'),
            'summary': {
                'numeric_columns': df.select_dtypes(include='number').columns.tolist(),
                'categorical_columns': df.select_dtypes(include='object').columns.tolist()
            }
        }

    return data
```

### CSV解析

```python
def parse_csv(file_path: str) -> SpreadsheetData:
    """解析CSV文件"""

    import pandas as pd

    df = pd.read_csv(file_path)

    return {
        'columns': df.columns.tolist(),
        'rows': len(df),
        'data': df.to_dict('records'),
        'separator': detect_separator(file_path)
    }
```

### 数据类型识别

| 原始值 | 识别类型 | 示例 |
|--------|---------|------|
| 整数 | int | 42 |
| 小数 | float | 3.14 |
| 百分比 | percent | 85% |
| 货币 | currency | $100 |
| 日期 | date | 2024-01-15 |
| 文本 | string | "文本内容" |

---

## image-parser / 图片解析器

### 支持格式
- PNG (.png)
- JPEG (.jpg, .jpeg)
- BMP (.bmp)
- GIF (.gif) - 仅支持静态

### OCR处理

```python
def parse_image(file_path: str) -> ImageData:
    """解析图片，提取文字"""

    import pytesseract
    from PIL import Image

    data = {
        'raw_text': '',
        'structured_text': [],
        'confidence': 0.0,
        'language': 'eng+chi'  # 多语言支持
    }

    # 打开图片
    img = Image.open(file_path)

    # OCR识别
    raw_text = pytesseract.image_to_string(img, lang=data['language'])
    data['raw_text'] = raw_text

    # 获取置信度
    data['confidence'] = get_ocr_confidence(img)

    # 结构化输出
    data['structured_text'] = pytesseract.image_to_data(
        img,
        lang=data['language'],
        output_type=pytesseract.Output.DICT
    )

    return data
```

### 预处理

| 处理 | 说明 | 适用场景 |
|------|------|---------|
| 灰度化 | 转为灰度图 | 文字清晰的图片 |
| 二值化 | 黑白分明 | 对比度低的图片 |
| 去噪 | 移除噪点 | 扫描文档 |
| 倾斜校正 | 校正歪斜 | 拍摄照片 |

---

## review-parser / 评审解析器

### 支持格式
- GitHub PR评论 (JSON API格式)
- GitLab MR评论
- Markdown评审记录
- 纯文本评审

### GitHub PR解析

```python
def parse_github_pr(pr_data: dict) -> ReviewData:
    """解析GitHub PR评审数据"""

    reviews = []

    for review in pr_data.get('reviews', []):
        reviews.append({
            'author': review['user']['login'],
            'state': review['state'],  # APPROVED, CHANGES_REQUESTED, COMMENTED
            'body': review['body'],
            'submitted_at': review['submitted_at'],
            'comments': parse_review_comments(review.get('comments', []))
        })

    # 分类汇总
    summary = categorize_reviews(reviews)

    return ReviewData(
        reviews=reviews,
        summary=summary
    )
```

### 评审分类

```python
def categorize_reviews(reviews: List[Review]) -> ReviewSummary:
    """评审意见分类"""

    categories = {
        'bug': [],
        'security': [],
        'performance': [],
        'code_quality': [],
        'documentation': [],
        'question': [],
        'suggestion': []
    }

    keywords = {
        'bug': ['bug', '错误', '不对', 'wrong', 'error'],
        'security': ['security', '安全', '漏洞', 'injection'],
        'performance': ['performance', '性能', 'slow', '优化'],
        'code_quality': ['quality', '风格', 'refactor', '可读性'],
        'documentation': ['docs', '文档', 'comment', '说明'],
        'question': ['question', '？', 'why', '怎么'],
        'suggestion': ['suggest', '建议', 'consider', '可以']
    }

    for review in reviews:
        for comment in review.comments:
            for category, words in keywords.items():
                if any(word in comment.body.lower() for word in words):
                    categories[category].append(comment)

    return ReviewSummary(categories=categories)
```

### 严重性推断

| 推断级别 | 依据 |
|---------|------|
| Critical | 包含 "critical", "security", "must fix", "安全", "漏洞" |
| High | 包含 "bug", "error", "wrong", "错误", "严重" |
| Medium | 包含 "consider", "should", "建议", "可以改进" |
| Low | 包含 "nit:", "minor", "optional", "可选" |
| Info | 包含 "note:", "FYI", "顺便" |

---

## test-result-parser / 测试结果解析器

### 支持格式
- JUnit XML
- pytest JSON
- Jest JSON
- TestNG XML
- NUnit XML
- TAP (Test Anything Protocol)

### 统一数据模型

```python
class UnifiedTestResult:
    """统一的测试结果数据模型"""

    # 总体统计
    total: int
    passed: int
    failed: int
    skipped: int
    errors: int

    # 时间
    duration: float  # 秒
    timestamp: str

    # 详细结果
    suites: List[TestSuite]
    failures: List[TestFailure]
    errors: List[TestError]

    # 质量指标
    pass_rate: float
    quality_score: float

class TestSuite:
    name: str
    total: int
    passed: int
    failed: int
    duration: float
    test_cases: List[TestCase]

class TestCase:
    name: str
    class_name: str
    status: str  # passed, failed, skipped, error
    duration: float
    message: Optional[str]
    stack_trace: Optional[str]
```

### 格式识别

```python
def detect_format(content: str) -> str:
    """识别测试结果格式"""

    content = content.strip()

    if content.startswith('<?xml') or content.startswith('<'):
        if 'testsuite' in content and 'failures' in content:
            return 'junit'
        elif 'testsuites' in content:
            return 'testng'

    if content.startswith('{') or content.startswith('['):
        data = json.loads(content)
        if 'summary' in data and 'results' in data:
            return 'pytest'
        if 'testResults' in data and 'numTotalTests' in data:
            return 'jest'

    if 'TAP version' in content:
        return 'tap'

    return 'unknown'
```

---

*由 quality-document-generator skill 自动生成*
