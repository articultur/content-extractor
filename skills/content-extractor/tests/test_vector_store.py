"""Tests for VectorStore implementations."""


def test_inmemory_vector_store_search():
    from storage.vector_store import create_vector_store
    store = create_vector_store("inmemory")
    store.add("func_001", "用户登录系统")
    store.add("func_002", "用户登出系统")
    store.add("func_003", "管理员查看报表")
    results = store.search("登录", top_k=2)
    assert len(results) >= 1
    assert results[0].id == "func_001"


def test_inmemory_search_order():
    from storage.vector_store import create_vector_store
    store = create_vector_store("inmemory")
    store.add("func_001", "登录验证")
    store.add("func_002", "身份认证")
    results = store.search("身份认证", top_k=2)
    assert results[0].id == "func_002"
    assert results[0].score > results[1].score