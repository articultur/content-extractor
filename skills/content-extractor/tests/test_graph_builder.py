"""Tests for GraphBuilder domain node support."""


def test_graph_builder_add_domain_node():
    from merger.graph_builder import GraphBuilder
    gb = GraphBuilder()
    gb.add_function("func_001", "登录", "functionality")
    gb.add_domain_node("认证模块", {"function_count": 5})
    assert any(n.id == "domain_auth_module" for n in gb.nodes)
    assert any(n.type == "domain" for n in gb.nodes)


def test_graph_builder_link_function_to_domain():
    from merger.graph_builder import GraphBuilder
    gb = GraphBuilder()
    gb.add_function("func_001", "登录", "functionality")
    gb.add_domain_node("认证模块", {"function_count": 1})
    gb.link_function_to_domain("func_001", "认证模块")
    edges = gb.to_dict()["edges"]
    assert any(e["from"] == "func_001" and e["to"] == "domain_auth_module" and e["type"] == "belongs_to" for e in edges)