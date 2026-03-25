# 自定义适配器模板 / Custom Adapter Template

## 概述

自定义适配器用于支持 GitHub/GitLab 以外的代码平台，或用于扩展已有平台的能力。

## 何时使用

| 场景 | 推荐适配器 |
|------|----------|
| GitHub | `github-adapter.md` |
| GitLab | `gitlab-adapter.md` |
| Bitbucket | 自定义适配器 |
| Azure DevOps | 自定义适配器 |
| 自建 Git 服务 | 自定义适配器 |
| 本地代码 | Claude Code 内置 |

## 适配器接口

```yaml
AdapterInterface:
  # 必须实现的方法
  required_methods:
    - name: "get_pr_info"
      params:
        - identifier: string  # PR 链接、编号或自定义格式
      returns: PRInfo

    - name: "get_diff"
      params:
        - identifier: string
      returns: DiffContent

    - name: "get_files"
      params:
        - identifier: string
      returns: List[ChangedFile]

  # 可选实现的方法
  optional_methods:
    - name: "get_commits"
    - name: "get_comments"
    - name: "get_reviewers"
    - name: "get_ci_status"
```

## PRInfo 结构

```yaml
PRInfo:
  number: int | string
  title: string
  description: string
  state: string  # open, closed, merged
  author: string
  url: string
  created_at: datetime
  updated_at: datetime

  # 可选字段
  source_branch: string
  target_branch: string
  reviewers: list[string]
  labels: list[string]
  base_repo: string
```

## DiffContent 结构

```yaml
DiffContent:
  raw: string  # 原始 diff 文本
  files: list[DiffFile]
  stats:
    total_files: int
    additions: int
    deletions: int

DiffFile:
  path: string
  status: string  # added, modified, deleted, renamed
  additions: int
  deletions: int
  patch: string  # 可选的 patch 内容
```

## 模板结构

```python
class CustomAdapter:
    """
    自定义代码平台适配器
    """

    def __init__(self, config):
        """
        初始化适配器
        config: 包含认证信息、API 配置等
        """
        self.config = config
        self.auth = self._setup_auth(config)

    def _setup_auth(self, config):
        """
        设置认证
        """
        # 实现认证逻辑
        pass

    def _make_request(self, method, url, **kwargs):
        """
        发送 HTTP 请求
        """
        # 实现请求逻辑
        pass

    def get_pr_info(self, identifier):
        """
        获取 PR/MR 信息
        identifier: PR 链接、编号或自定义格式
        """
        # 1. 解析 identifier
        parsed = self._parse_identifier(identifier)

        # 2. 构建 API 请求
        url = self._build_url("pr_endpoint", **parsed)

        # 3. 发送请求
        response = self._make_request("GET", url)

        # 4. 转换响应
        return self._convert_to_pr_info(response)

    def get_diff(self, identifier):
        """
        获取 Diff 内容
        """
        # 1. 解析 identifier
        parsed = self._parse_identifier(identifier)

        # 2. 获取 PR 信息
        pr_info = self.get_pr_info(identifier)

        # 3. 构建 Diff 请求
        url = self._build_url("diff_endpoint", **parsed)
        response = self._make_request("GET", url)

        # 4. 转换响应
        return self._convert_to_diff(response)

    def get_files(self, identifier):
        """
        获取变更文件列表
        """
        # 1. 解析 identifier
        parsed = self._parse_identifier(identifier)

        # 2. 构建请求
        url = self._build_url("files_endpoint", **parsed)
        response = self._make_request("GET", url)

        # 3. 转换响应
        return self._convert_to_files(response)

    def _parse_identifier(self, identifier):
        """
        解析 identifier
        支持多种格式:
        - https://platform.com/owner/repo/pull/123
        - owner/repo/123
        - 123 (需要额外配置 repo 信息)
        """
        # 实现解析逻辑
        pass

    def _convert_to_pr_info(self, response):
        """
        将 API 响应转换为标准 PRInfo 格式
        """
        return PRInfo(
            number=response["id"],
            title=response["title"],
            description=response.get("description", ""),
            state=response["state"],
            author=response["author"]["username"],
            url=response["web_url"],
            created_at=response["created_at"],
            updated_at=response["updated_at"],
        )

    def _convert_to_diff(self, response):
        """
        将 API 响应转换为标准 DiffContent 格式
        """
        files = []
        for file_data in response.get("files", []):
            files.append(DiffFile(
                path=file_data["file_path"],
                status=file_data["status"],
                additions=file_data.get("additions", 0),
                deletions=file_data.get("deletions", 0),
                patch=file_data.get("patch", ""),
            ))

        return DiffContent(
            raw=response.get("raw_diff", ""),
            files=files,
            stats=response.get("stats", {}),
        )

    def _convert_to_files(self, response):
        """
        将 API 响应转换为文件列表
        """
        files = []
        for file_data in response:
            files.append(ChangedFile(
                path=file_data["path"],
                status=file_data["status"],
                additions=file_data.get("additions", 0),
                deletions=file_data.get("deletions", 0),
            ))
        return files
```

## 配置格式

### 方式1: 通用配置

```yaml
adapters:
  custom:
    - name: "bitbucket"
      type: "rest_api"
      config:
        base_url: "https://api.bitbucket.org/2.0"
        auth:
          type: "oauth"  # 或 basic, bearer
          token_env: "BITBUCKET_TOKEN"

        # 端点配置
        endpoints:
          pr_info: "/repositories/{workspace}/{repo}/pullrequests/{id}"
          diff: "/repositories/{workspace}/{repo}/pullrequests/{id}/diff"
          files: "/repositories/{workspace}/{repo}/pullrequests/{id}/files"
```

### 方式2: OpenAPI/Swagger

```yaml
adapters:
  custom:
    - name: "custom-platform"
      type: "openapi"
      config:
        spec_url: "https://api.platform.com/openapi.json"
        auth:
          type: "api_key"
          key_env: "PLATFORM_API_KEY"

        # 可选: 指定特定端点
        overrides:
          pr_info: "/custom/pr endpoint"
```

## 认证模板

### Bearer Token

```python
def _setup_auth(self, config):
    token = os.getenv(config["token_env"])
    return {"Authorization": f"Bearer {token}"}
```

### Basic Auth

```python
def _setup_auth(self, config):
    username = os.getenv(config["username_env"])
    password = os.getenv(config["password_env"])
    import base64
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}
```

### OAuth

```python
def _setup_auth(self, config):
    token = os.getenv(config["oauth_token_env"])
    return {"Authorization": f"OAuth {token}"}
```

### API Key

```python
def _setup_auth(self, config):
    api_key = os.getenv(config["api_key_env"])
    return {"X-API-Key": api_key}
```

## 工具发现

```python
def discover():
    """
    发现可用的自定义适配器
    """
    adapters = []

    # 1. 检查环境变量
    if has_env("CUSTOM_PLATFORM_TOKEN"):
        adapters.append(CustomPlatformAdapter())

    # 2. 检查配置文件
    config = load_config("~/.impact-analysis/config.yaml")
    if config.get("adapters"):
        for adapter_config in config["adapters"]:
            adapters.append(create_adapter(adapter_config))

    return adapters
```

## 使用示例

```python
# 注册自定义适配器
registry = AdapterRegistry()
registry.register("custom-platform", CustomPlatformAdapter)

# 使用
adapter = registry.get("custom-platform")
result = adapter.get_pr_info("https://custom.platform.com/repo/pr/123")
```

## 最佳实践

| 实践 | 说明 |
|------|------|
| 错误处理 | 捕获异常，转换为本模块定义的错误类型 |
| 重试机制 | 网络错误时指数退避重试 |
| 超时处理 | 设置合理的请求超时 |
| 日志记录 | 记录关键操作，便于排查 |
| 类型转换 | API 响应转换为标准数据结构 |

## 相关模块

| 模块 | 关系 |
|------|------|
| `github-adapter.md` | 参考实现 |
| `gitlab-adapter.md` | 参考实现 |
| `main.md` | 使用适配器获取代码 |
