"""Build functionality graph from extracted data."""

from typing import List, Dict
from dataclasses import dataclass, field


@dataclass
class GraphNode:
    id: str
    type: str  # functionality, api_endpoint, ui_page
    name: str
    parent: str = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class GraphEdge:
    from_id: str
    to_id: str
    type: str  # implements, rendered_as, depends_on
    confidence: float = 1.0


class GraphBuilder:
    """Builds functionality graph from extracted functions."""

    def __init__(self):
        self.nodes: List[GraphNode] = []
        self.edges: List[GraphEdge] = []

    def add_function(self, func_id: str, name: str, func_type: str = "functionality", metadata: Dict = None):
        """Add a node to the graph."""
        node = GraphNode(
            id=func_id,
            type=func_type,
            name=name,
            metadata=metadata or {}
        )
        self.nodes.append(node)
        return node

    def add_edge(self, from_id: str, to_id: str, edge_type: str, confidence: float = 1.0):
        """Add an edge to the graph."""
        edge = GraphEdge(
            from_id=from_id,
            to_id=to_id,
            type=edge_type,
            confidence=confidence
        )
        self.edges.append(edge)
        return edge

    def link_function_to_api(self, func_id: str, api_id: str, api_name: str, confidence: float = 0.9):
        """Link a function to its API implementation."""
        # Add API node if not exists
        if not self._node_exists(api_id):
            self.add_function(api_id, api_name, "api_endpoint")

        self.add_edge(func_id, api_id, "implemented_by", confidence)

    def link_function_to_ui(self, func_id: str, ui_id: str, ui_name: str, confidence: float = 0.7):
        """Link a function to its UI representation."""
        if not self._node_exists(ui_id):
            self.add_function(ui_id, ui_name, "ui_page")

        self.add_edge(func_id, ui_id, "rendered_as", confidence)

    def _normalize_domain_name(self, domain_name: str) -> str:
        """Normalize domain name to a safe ID string (pinyin for Chinese)."""
        # Chinese to pinyin mapping for common domains
        chinese_to_pinyin = {
            "认证模块": "auth_module",
            "账户模块": "account_module",
            "首页模块": "home_module",
            "订单模块": "order_module",
            "支付模块": "payment_module",
            "通知模块": "notification_module",
            "报表模块": "report_module",
            "搜索模块": "search_module",
            "安全模块": "security_module",
            "配置模块": "config_module",
            "通用": "common",
        }
        if domain_name in chinese_to_pinyin:
            return chinese_to_pinyin[domain_name]
        # Fallback: lowercase and replace spaces
        return domain_name.replace(' ', '_').lower()

    def add_domain_node(self, domain_name: str, metadata: Dict = None):
        """Add a domain node to the graph."""
        normalized = self._normalize_domain_name(domain_name)
        domain_id = f"domain_{normalized}"
        node = GraphNode(id=domain_id, type="domain", name=domain_name, metadata=metadata or {})
        self.nodes.append(node)
        return node

    def link_function_to_domain(self, func_id: str, domain_name: str, confidence: float = 1.0):
        """Link a function to a domain."""
        normalized = self._normalize_domain_name(domain_name)
        domain_id = f"domain_{normalized}"
        if not self._node_exists(domain_id):
            self.add_domain_node(domain_name)
        self.add_edge(func_id, domain_id, "belongs_to", confidence)

    def _node_exists(self, node_id: str) -> bool:
        """Check if node exists."""
        return any(n.id == node_id for n in self.nodes)

    def to_dict(self) -> Dict:
        """Export graph as dictionary."""
        return {
            "nodes": [
                {
                    "id": n.id,
                    "type": n.type,
                    "name": n.name,
                    "parent": n.parent,
                    **n.metadata
                }
                for n in self.nodes
            ],
            "edges": [
                {"from": e.from_id, "to": e.to_id, "type": e.type, "confidence": e.confidence}
                for e in self.edges
            ]
        }

    def detect_cycles(self) -> List[List[str]]:
        """Detect cycles in the graph."""
        # Simple DFS cycle detection
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(node_id: str, path: List[str]):
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            for edge in self.edges:
                if edge.from_id == node_id:
                    neighbor = edge.to_id
                    if neighbor not in visited:
                        dfs(neighbor, path[:])
                    elif neighbor in rec_stack:
                        # Found cycle
                        cycle_start = path.index(neighbor)
                        cycles.append(path[cycle_start:])

            rec_stack.remove(node_id)

        for node in self.nodes:
            if node.id not in visited:
                dfs(node.id, [])

        return cycles
