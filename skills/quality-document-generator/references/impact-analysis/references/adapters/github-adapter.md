# GitHub 适配器 / GitHub Adapter

## 概述

GitHub 适配器负责从 GitHub 获取 PR 信息和代码变更。

## 工具发现

```yaml
discovery:
  # 优先检测 GitHub MCP
  mcp:
    - name: "github"
      description: "GitHub MCP Server"

  # 备用 GitHub CLI
  cli:
    - name: "gh"
      description: "GitHub CLI"

  # 最后使用 REST API
  api:
    - name: "github_rest"
      description: "GitHub REST API"
```

## 获取能力

| 能力 | 方式 | 说明 |
|------|------|------|
| PR 信息 | MCP/CLI/API | 获取 PR 基本信息 |
| PR 文件列表 | MCP/CLI/API | 获取变更文件 |
| PR Diff | MCP/CLI/API | 获取完整 diff |
| Commit 列表 | MCP/CLI/API | 获取提交历史 |
| PR 评论 | MCP/CLI/API | 获取评审意见 |

## API 端点

### REST API

```yaml
endpoints:
  # 获取 PR 信息
  get_pr:
    method: "GET"
    url: "/repos/{owner}/{repo}/pulls/{pr_number}"
    response: PRInfo

  # 获取 PR 文件列表
  get_pr_files:
    method: "GET"
    url: "/repos/{owner}/{repo}/pulls/{pr_number}/files"
    response: List[PRFile]

  # 获取 PR diff
  get_pr_diff:
    method: "GET"
    url: "/repos/{owner}/{repo}/pulls/{pr_number}"
    headers:
      Accept: "application/vnd.github.v3.diff"
    response: raw_diff

  # 获取 commits
  get_commits:
    method: "GET"
    url: "/repos/{owner}/{repo}/pulls/{pr_number}/commits"
    response: List[Commit]
```

### GraphQL API (可选)

```graphql
query GetPRDetails($owner: String!, $repo: String!, $prNumber: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $prNumber) {
      title
      body
      state
      changedFiles
      additions
      deletions
      files(first: 100) {
        nodes {
          path
          changeType
          additions
          deletions
        }
      }
      commits(first: 10) {
        nodes {
          commit {
            message
            author {
              name
            }
          }
        }
      }
    }
  }
}
```

## 输入格式

### PR 链接

```
https://github.com/owner/repo/pull/123
github.com/owner/repo/pull/123
owner/repo#123
```

### PR 编号

```
123
#123
PR #123
```

## 输出结构

```yaml
github_adapter_result:
  pr_info:
    number: 123
    title: "feat: add payment support"
    state: "open"
    author: "username"
    url: "https://github.com/owner/repo/pull/123"
    created_at: "2026-03-25T10:00:00Z"
    updated_at: "2026-03-25T12:00:00Z"

  files:
    - filename: "src/payment/billing.py"
      status: "modified"
      additions: 50
      deletions: 10
      patch: "@@ -1,3 +1,4 @@..."

  diff: "raw diff content..."

  commits:
    - sha: "abc123"
      message: "feat: add payment support"
      author: "username"

  stats:
    total_files: 15
    additions: 500
    deletions: 100
```

## 认证方式

### 1. GitHub MCP (推荐)

```yaml
mcp_config:
  type: "mcp"
  name: "github"
  # MCP 自动处理认证
```

### 2. GitHub CLI

```yaml
gh_config:
  type: "cli"
  auth: "gh auth login"
  # CLI 自动使用已缓存的认证
```

### 3. Personal Access Token

```yaml
api_config:
  type: "api"
  token_env: "GITHUB_TOKEN"
  # 从环境变量读取 token
```

### 4. GitHub Apps

```yaml
app_config:
  type: "github_app"
  app_id_env: "GITHUB_APP_ID"
  private_key_env: "GITHUB_APP_PRIVATE_KEY"
  installation_id: 12345
```

## 错误处理

| 错误 | 处理 |
|------|------|
| PR 不存在 | 返回错误: "PR not found" |
| 无权限访问 | 返回错误: "Access denied" |
| 网络超时 | 重试 3 次，间隔 1s |
| Rate Limit | 等待后重试，使用 exponential backoff |
| 无效 token | 提示用户配置认证 |

### Rate Limit 处理

```python
def handle_rate_limit(response):
    """
    处理 GitHub API rate limit
    """
    if response.status_code == 403:
        reset_time = response.headers.get("X-RateLimit-Reset")
        if reset_time:
            wait_seconds = int(reset_time) - time.time()
            if wait_seconds > 0:
                time.sleep(min(wait_seconds, 60))  # 最多等 60 秒
                return True
    return False
```

## 使用示例

```python
# 创建适配器
adapter = GitHubAdapter(config)

# 方式1: 通过链接
result = adapter.get_pr("https://github.com/owner/repo/pull/123")

# 方式2: 通过 owner/repo/number
result = adapter.get_pr("owner/repo/123")

# 方式3: 通过编号 (需要提供 repo 信息)
result = adapter.get_pr(123, owner="owner", repo="repo")

# 获取结果
print(result.pr_info.title)
print(result.diff)
print(result.files)
```

## 配置示例

```yaml
github:
  # 方式1: MCP (推荐)
  adapter: "mcp"
  mcp_name: "github"

  # 方式2: CLI
  # adapter: "cli"

  # 方式3: API
  # adapter: "api"
  # token: "${GITHUB_TOKEN}"

  # 通用配置
  timeout: 30
  retry_count: 3
```

## 工具发现流程

```python
def discover_and_connect():
    """
    工具发现流程
    1. 尝试 MCP
    2. 尝试 CLI
    3. 尝试 API
    """
    # Step 1: MCP
    if has_mcp_tool("github"):
        return GitHubMCPAdapter()

    # Step 2: CLI
    if has_cli_tool("gh"):
        return GitHubCLIAdapter()

    # Step 3: API
    if has_env_token("GITHUB_TOKEN"):
        return GitHubAPIAdapter()

    # 都不存在
    raise NoGitHubToolError()
```

## PR 信息增强

### PR 标题分析

```python
def enhance_pr_info(pr_info):
    """
    增强 PR 信息
    """
    # 分析标题关键词
    title_lower = pr_info.title.lower()

    pr_info.is_urgent = any(kw in title_lower
        for kw in ["urgent", "hotfix", "critical", "emergency"])

    pr_info.is_refactor = any(kw in title_lower
        for kw in ["refactor", "restructure", "cleanup"])

    pr_info.is_feature = any(kw in title_lower
        for kw in ["feat", "feature", "add", "implement"])

    pr_info.is_fix = any(kw in title_lower
        for kw in ["fix", "bug", "patch"])

    return pr_info
```

## 相关模块

| 模块 | 关系 |
|------|------|
| `main.md` | 调用 GitHub 适配器获取代码 |
| `custom-adapter.md` | 自定义适配器参考 |
| `gitlab-adapter.md` | 类似的 GitLab 适配器 |
