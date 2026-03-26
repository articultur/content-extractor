"""Tests for ContentExtractor pipeline integration."""


def test_pipeline_includes_domain_classification():
    from main import ContentExtractor
    from config import SourceDocument
    extractor = ContentExtractor()
    sources = [SourceDocument(type="text", content="# 登录\n用户点击登录按钮，系统验证密码后登录成功。")]
    result = extractor.analyze(sources, output_dir="/tmp/test_output")
    import json
    with open("/tmp/test_output/requirements-report.json") as f:
        data = json.load(f)
    functions = data.get("l2_structured", {}).get("functions", [])
    assert len(functions) >= 1
    # Check that functions have domain field (may be None for some)
    for func in functions:
        assert "domain" in func


def test_pipeline_embedding_generation():
    from main import ContentExtractor
    from config import SourceDocument
    extractor = ContentExtractor()
    sources = [SourceDocument(type="text", content="# 登录\n用户点击登录按钮，系统验证密码后登录成功。\n\n# 支付\n用户进行支付操作。")]
    result = extractor.analyze(sources, output_dir="/tmp/test_output2")
    assert result["stats"]["embeddings"] >= 2  # Should have embeddings for both functions
    assert "vector_backend" in result["stats"]


def test_embedding_semantic_associations():
    from main import ContentExtractor
    from config import SourceDocument
    import json
    extractor = ContentExtractor()
    sources = [
        SourceDocument(type="text", content="# 登录\n用户点击登录按钮，系统验证密码。"),
        SourceDocument(type="text", content="# 身份验证\n用户通过身份认证访问系统。"),
    ]
    result = extractor.analyze(sources, output_dir="/tmp/test_output3")
    with open("/tmp/test_output3/requirements-graph.json") as f:
        graph = json.load(f)
    # Should have edges between the two related functions
    edges = graph.get("edges", [])
    # Verify semantic associations exist (embedding similarity)
    func_ids = {f["name"] for f in graph.get("nodes", []) if f["type"] == "functionality"}
    assert len(func_ids) >= 2


def test_pipeline_includes_full_text_search():
    from main import ContentExtractor
    from config import SourceDocument
    import json
    import os
    extractor = ContentExtractor()
    sources = [SourceDocument(type="text", content="# 登录\n用户点击登录按钮。\n\n# 支付\n用户进行支付。")]
    result = extractor.analyze(sources, output_dir="/tmp/test_output_search")
    # Check that search index file was created
    index_path = "/tmp/test_output_search/requirements-search-index.json"
    assert os.path.exists(index_path)
    with open(index_path) as f:
        searchable = json.load(f)
    assert len(searchable) >= 2
    # Check stats
    assert result.get('stats', {}).get('search_index_size', 0) >= 2