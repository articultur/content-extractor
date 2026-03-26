"""Tests for GraphBuilder confidence propagation."""


def test_get_path_confidence_single_hop():
    """Test path confidence with single direct edge."""
    from merger.graph_builder import GraphBuilder

    gb = GraphBuilder()
    gb.add_function("func_001", "登录", "functionality")
    gb.add_function("func_002", "验证", "functionality")
    gb.add_edge("func_001", "func_002", "depends_on", 0.9)

    # Single hop: 0.9
    assert gb.get_path_confidence("func_001", "func_002") == 0.9


def test_get_path_confidence_multi_hop():
    """Test path confidence with multiple hops."""
    from merger.graph_builder import GraphBuilder

    gb = GraphBuilder()
    gb.add_function("func_001", "A", "functionality")
    gb.add_function("func_002", "B", "functionality")
    gb.add_function("func_003", "C", "functionality")

    # A -> B (0.9), B -> C (0.7)
    gb.add_edge("func_001", "func_002", "depends_on", 0.9)
    gb.add_edge("func_002", "func_003", "depends_on", 0.7)

    # Two hop path: 0.9 * 0.7 = 0.63
    assert gb.get_path_confidence("func_001", "func_003") == 0.63


def test_get_path_confidence_no_path():
    """Test that no path returns 0."""
    from merger.graph_builder import GraphBuilder

    gb = GraphBuilder()
    gb.add_function("func_001", "A", "functionality")
    gb.add_function("func_002", "B", "functionality")

    # No edge between them
    assert gb.get_path_confidence("func_001", "func_002") == 0.0


def test_get_path_confidence_max_hops():
    """Test max_hops boundary."""
    from merger.graph_builder import GraphBuilder

    gb = GraphBuilder()
    gb.add_function("func_001", "A", "functionality")
    gb.add_function("func_002", "B", "functionality")
    gb.add_function("func_003", "C", "functionality")
    gb.add_function("func_004", "D", "functionality")

    # A -> B -> C -> D (3 hops)
    gb.add_edge("func_001", "func_002", "depends_on", 0.9)
    gb.add_edge("func_002", "func_003", "depends_on", 0.9)
    gb.add_edge("func_003", "func_004", "depends_on", 0.9)

    # Within max_hops=3
    assert gb.get_path_confidence("func_001", "func_004", max_hops=3) == 0.9 ** 3

    # Exceeds max_hops=2
    assert gb.get_path_confidence("func_001", "func_004", max_hops=2) == 0.0


def test_get_path_confidence_self():
    """Test path to self returns 1.0."""
    from merger.graph_builder import GraphBuilder

    gb = GraphBuilder()
    gb.add_function("func_001", "登录", "functionality")

    assert gb.get_path_confidence("func_001", "func_001") == 1.0


def test_get_all_path_confidences():
    """Test computing all path confidences."""
    from merger.graph_builder import GraphBuilder

    gb = GraphBuilder()
    gb.add_function("func_001", "A", "functionality")
    gb.add_function("func_002", "B", "functionality")
    gb.add_function("func_003", "C", "functionality")

    gb.add_edge("func_001", "func_002", "depends_on", 0.9)
    gb.add_edge("func_002", "func_003", "depends_on", 0.7)

    all_conf = gb.get_all_path_confidences()

    assert all_conf[("func_001", "func_002")] == 0.9
    assert all_conf[("func_002", "func_003")] == 0.7
    assert all_conf[("func_001", "func_003")] == 0.63


def test_find_strong_associations():
    """Test finding strong associations above threshold."""
    from merger.graph_builder import GraphBuilder

    gb = GraphBuilder()
    gb.add_function("func_001", "A", "functionality")
    gb.add_function("func_002", "B", "functionality")
    gb.add_function("func_003", "C", "functionality")
    gb.add_function("api_001", "API", "api_endpoint")  # Not functionality

    gb.add_edge("func_001", "func_002", "depends_on", 0.9)
    gb.add_edge("func_002", "func_003", "depends_on", 0.7)
    gb.add_edge("func_001", "api_001", "implemented_by", 0.8)

    # Threshold 0.5 should include func_001->func_002 (0.9) and func_001->func_003 (0.63)
    # But not api_001 since it's not functionality
    associations = gb.find_strong_associations(threshold=0.5)

    assert ("func_001", "func_002", 0.9) in associations
    assert ("func_001", "func_003", 0.63) in associations
    # Should not include api_001 as source or target since it's not functionality
    for from_id, to_id, _ in associations:
        assert from_id.startswith("func_")
        assert to_id.startswith("func_")


def test_find_strong_associations_threshold():
    """Test threshold filtering."""
    from merger.graph_builder import GraphBuilder

    gb = GraphBuilder()
    gb.add_function("func_001", "A", "functionality")
    gb.add_function("func_002", "B", "functionality")

    gb.add_edge("func_001", "func_002", "depends_on", 0.3)

    # Below threshold 0.5
    associations = gb.find_strong_associations(threshold=0.5)
    assert len(associations) == 0

    # Below threshold 0.2
    associations = gb.find_strong_associations(threshold=0.2)
    assert ("func_001", "func_002", 0.3) in associations


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