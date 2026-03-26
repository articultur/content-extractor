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