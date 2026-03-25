# Diff 解析器 / Diff Parser

## 概述

Diff 解析器负责将原始 diff 内容解析为结构化的变更数据，是 L1 文件级分析的核心。

## 支持格式

| 格式 | 说明 | 支持状态 |
|------|------|---------|
| Unified Diff | 标准 unified diff 格式 | ✅ 完全支持 |
| Context Diff | 带上下文的 diff | ✅ 完全支持 |
| Git Diff | Git 扩展格式 | ✅ 完全支持 |
| GitHub/GitLab PR Diff | PR 特有的 diff | ✅ 完全支持 |
| Patch 文件 | .patch 文件格式 | ✅ 完全支持 |

## 输入示例

### Unified Diff

```diff
diff --git a/src/payment.py b/src/payment.py
index 1234567..89abcdef 100644
--- a/src/payment.py
+++ b/src/payment.py
@@ -10,7 +10,9 @@ def process_payment(amount):
     """Process a payment."""
     result = validate(amount)
-    return result
+    if not result:
+        raise PaymentError("Invalid amount")
+    return confirm(result)
```

### GitHub PR Diff Header

```diff
diff --git a/src/payment.py b/src/payment.py
index 1234567..89abcdef 100644
--- a/src/payment.py
+++ b/src/payment.py
@@ -1,3 +1,4 @@
+import new_dependency
```

## 输出结构

```yaml
diff_result:
  metadata:
    total_files: int
    files_added: int
    files_modified: int
    files_deleted: int
    lines_added: int
    lines_removed: int
    timestamp: datetime

  files:
    - path: string
      status: added | modified | deleted | renamed
      additions: int
      deletions: int
      hunks: list[Hunk]

    hunk:
      header: string          # @@ -1,3 +1,4 @@
      old_start: int
      old_lines: int
      new_start: int
      new_lines: int
      content: string
      changes: list[Change]

    change:
      type: add | delete | context
      line_number_old: int | null
      line_number_new: int | null
      content: string
```

## 解析规则

### 文件路径提取

```
正则: ^diff --git a/(.*) b/(.*)$
提取: 文件路径 (取 b/ 路径)
```

### 变更状态识别

| Diff 标记 | 状态 |
|-----------|------|
| `new file` | added |
| `deleted file` | deleted |
| `rename from/to` | renamed |
| 无特殊标记 | modified |

### Hunk 解析

```
正则: ^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@
提取: old_start, old_lines, new_start, new_lines
```

### 行级变更解析

```
+ 添加行 (type: add)
- 删除行 (type: delete)
  上下文行 (type: context)
```

## 统计计算

### 文件统计

```python
def calculate_file_stats(files):
    stats = {
        "total_files": len(files),
        "files_added": sum(1 for f in files if f.status == "added"),
        "files_modified": sum(1 for f in files if f.status == "modified"),
        "files_deleted": sum(1 for f in files if f.status == "deleted"),
    }
    return stats
```

### 行数统计

```python
def calculate_line_stats(files):
    total_added = sum(f.additions for f in files)
    total_removed = sum(f.deletions for f in files)
    return {
        "lines_added": total_added,
        "lines_removed": total_removed,
        "net_changes": total_added - total_removed
    }
```

## 过滤规则

### 按文件类型过滤

```yaml
file_type_filters:
  include:
    - "*.py"
    - "*.js"
    - "*.ts"
    - "*.go"
    - "*.java"

  exclude:
    - "*.md"
    - "*.txt"
    - "*.lock"
    - "docs/**"
    - "test/**"
```

### 按目录过滤

```yaml
directory_filters:
  exclude:
    - "^docs/"
    - "^test/"
    - "^vendor/"
    - "\.git/"
```

### 按变更大小过滤

```yaml
size_filters:
  min_file_size: 0        # bytes
  max_file_size: 1048576  # 1MB
```

## 特殊模式检测

### 1. 函数签名变更

```yaml
pattern: "^[-+].*def \w+\([^)]*\):"
action: flag_api_change
```

### 2. Import 变更

```yaml
pattern: "^[-+].*import "
action: flag_dependency_change
```

### 3. 配置文件变更

```yaml
pattern: "(\.env$|\.yaml$|\.json$|config\.)"
action: flag_config_change
```

### 4. 测试文件变更

```yaml
pattern: "(test_|spec_|__tests__/)"
action: flag_test_change
```

## 大文件处理

```python
def process_large_diff(diff_content, max_file_size_mb=1):
    files = parse_diff(diff_content)

    for file in files:
        if file.size > max_file_size_mb * 1024 * 1024:
            # 截取前 N 行
            file.hunks = truncate_hunks(file.hunks, max_lines=500)
            file.truncated = True

    return files
```

## PR 特征提取

### 标题分析

```python
def extract_pr_features(pr_title):
    features = {
        "is_urgent": any(kw in pr_title.lower()
            for kw in ["urgent", "hotfix", "critical", "emergency"]),
        "is_refactor": any(kw in pr_title.lower()
            for kw in ["refactor", "restructure", "cleanup"]),
        "is_feature": any(kw in pr_title.lower()
            for kw in ["feat", "feature", "add", "implement"]),
        "is_fix": any(kw in pr_title.lower()
            for kw in ["fix", "bug", "patch"]),
    }
    return features
```

### Commit Message 分析

```python
def analyze_commit_messages(commits):
    patterns = {
        "breaking": sum(1 for c in commits if "BREAKING" in c.message),
        "api_change": sum(1 for c in commits
            if any(kw in c.message.lower() for kw in ["api", "signature", "interface"])),
        "security": sum(1 for c in commits
            if any(kw in c.message.lower() for kw in ["security", "auth", "permission"])),
    }
    return patterns
```

## 错误处理

| 错误 | 处理 |
|------|------|
| 空 diff | 返回空结果 |
| 格式错误 | 尽可能解析，标记警告 |
| 编码问题 | 尝试 UTF-8，失败则标记错误 |
| 文件过大 | 截断处理，标记警告 |

## 使用示例

```python
# 基本解析
parser = DiffParser()
result = parser.parse(diff_content)

# 过滤解析
result = parser.parse(diff_content,
    exclude_patterns=["*.md", "docs/**"],
    max_file_size_mb=1
)

# 带统计的解析
result = parser.parse(diff_content)
print(f"变更文件数: {result.metadata.total_files}")
print(f"新增行数: {result.metadata.lines_added}")
```

## 相关模块

| 模块 | 关系 |
|------|------|
| `main.md` | 调用 Diff Parser 获取变更数据 |
| `module-mapper.md` | 接收文件列表进行模块映射 |
| `test-matcher.md` | 接收变更文件进行测试匹配 |
