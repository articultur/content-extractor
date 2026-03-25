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
