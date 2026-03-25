# GitLab 适配器 / GitLab Adapter

## 概述

GitLab 适配器负责从 GitLab 获取 MR (Merge Request) 信息和代码变更。

## 工具发现

```yaml
discovery:
  # 优先检测 GitLab MCP
  mcp:
    - name: "gitlab"
      description: "GitLab MCP Server"

  # 备用 GitLab CLI
  cli:
    - name: "glab"
      description: "GitLab CLI"

  # 最后使用 REST API
  api:
    - name: "gitlab_rest"
      description: "GitLab REST API"
```

## 获取能力

| 能力 | 方式 | 说明 |
|------|------|------|
| MR 信息 | MCP/CLI/API | 获取 MR 基本信息 |
| MR 文件列表 | MCP/CLI/API | 获取变更文件 |
| MR Diff | MCP/CLI/API | 获取完整 diff |
| Commit 列表 | MCP/CLI/API | 获取提交历史 |
| MR 评论 | MCP/CLI/API | 获取评审意见 |

## API 端点

### REST API

```yaml
endpoints:
  # 获取 MR 信息
  get_mr:
    method: "GET"
    url: "/projects/{project_id}/merge_requests/{mr_iid}"
    response: MRInfo

  # 获取 MR 变更文件
  get_mr_changes:
    method: "GET"
    url: "/projects/{project_id}/merge_requests/{mr_iid}/changes"
    response: MRChanges

  # 获取 MR diff
  get_mr_diff:
    method: "GET"
    url: "/projects/{project_id}/merge_requests/{mr_iid}"
    query:
      diff: "true"
    response: MRDiff

  # 获取 commits
  get_commits:
    method: "GET"
    url: "/projects/{project_id}/merge_requests/{mr_iid}/commits"
    response: List[Commit]
```

## 输入格式

### MR 链接

```
https://gitlab.com/owner/repo/-/merge_requests/123
gitlab.com/owner/repo/-/merge_requests/123
owner/repo!123
```

### MR 编号

```
!123
MR !123
Merge Request !123
```

### Project ID

```
project_id 可以是:
- 数字 ID: 12345
- URL 编码路径: owner%2Frepo
```

## 输出结构

```yaml
gitlab_adapter_result:
  mr_info:
    iid: 123
    title: "feat: add payment support"
    state: "opened"
    author: "username"
    web_url: "https://gitlab.com/owner/repo/-/merge_requests/123"
    created_at: "2026-03-25T10:00:00Z"
    updated_at: "2026-03-25T12:00:00Z"
    source_branch: "feature/payment"
    target_branch: "main"

  changes:
    - old_path: "src/payment/billing.py"
      new_path: "src/payment/billing.py"
      new_file: false
      renamed_file: false
      deleted_file: false
      diff: "@@ -1,3 +1,4 @@..."

  diff: "raw diff content..."

  commits:
    - id: "abc123"
      message: "feat: add payment support"
      author:
        name: "username"
        email: "user@example.com"

  stats:
    total_files: 15
    additions: 500
    deletions: 100
```

## 认证方式

### 1. GitLab MCP (推荐)

```yaml
mcp_config:
  type: "mcp"
  name: "gitlab"
```

### 2. GitLab CLI

```yaml
glab_config:
  type: "cli"
  auth: "glab auth login"
```

### 3. Personal Access Token

```yaml
api_config:
  type: "api"
  token_env: "GITLAB_TOKEN"
  base_url: "https://gitlab.com"  # 或私有 GitLab 实例
```

### 4. OAuth Token

```yaml
oauth_config:
  type: "oauth"
  token_env: "GITLAB_OAUTH_TOKEN"
```

## 与 GitHub 的差异

| 特性 | GitHub | GitLab |
|------|--------|--------|
| PR 名称 | Pull Request | Merge Request |
| 标识符 | PR #123 | MR !123 |
| 项目 ID | owner/repo | project_id 或路径 |
| diff 端点 | /pulls/{n}/files | /merge_requests/{iid}/changes |

### 代码转换

```python
def convert_github_to_gitlab(github_input):
    """
    将 GitHub 风格的输入转换为 GitLab 格式
    """
    # GitHub: owner/repo#123
    # GitLab: owner/repo!123

    if "#" in github_input:
        owner, repo, number = github_input.split("/")
        return f"{owner}/{repo}!{number}"

    return github_input
```

## 错误处理

| 错误 | 处理 |
|------|------|
| MR 不存在 | 返回错误: "Merge request not found" |
| 无权限访问 | 返回错误: "Access denied" |
| 网络超时 | 重试 3 次，间隔 1s |
| Rate Limit | 等待后重试 |
| 无效 token | 提示用户配置认证 |

## 使用示例

```python
# 创建适配器
adapter = GitLabAdapter(config)

# 方式1: 通过链接
result = adapter.get_mr("https://gitlab.com/owner/repo/-/merge_requests/123")

# 方式2: 通过 owner/repo!number
result = adapter.get_mr("owner/repo!123")

# 方式3: 通过 project_id 和 iid
result = adapter.get_mr(mr_iid=123, project_id="owner/repo")

# 获取结果
print(result.mr_info.title)
print(result.diff)
print(result.changes)
```

## 配置示例

```yaml
gitlab:
  # 方式1: MCP (推荐)
  adapter: "mcp"
  mcp_name: "gitlab"

  # 方式2: CLI
  # adapter: "cli"

  # 方式3: API
  # adapter: "api"
  # base_url: "https://gitlab.com"  # 或私有实例
  # token: "${GITLAB_TOKEN}"

  # 私有 GitLab 实例
  # base_url: "https://gitlab.company.com"
  # token: "${GITLAB_TOKEN}"
```

## 特殊场景

### Self-Managed GitLab

```yaml
gitlab_self_managed:
  base_url: "https://gitlab.company.com"
  api_version: "v4"
  token_env: "GITLAB_TOKEN"
```

### GitLab Groups

```yaml
gitlab_group:
  # Group 下的项目
  group: "team-name"
  project: "project-name"
  mr_iid: 123
```

## 相关模块

| 模块 | 关系 |
|------|------|
| `main.md` | 调用 GitLab 适配器获取代码 |
| `github-adapter.md` | GitHub 适配器参考 |
| `custom-adapter.md` | 自定义适配器模板 |
