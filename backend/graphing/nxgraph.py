import networkx as nx

class NxGraph:
    def __init__(self, nodes: list = None, edges: list = None):
        self.graph = nx.DiGraph()
        if nodes:
            self.graph.add_nodes_from(nodes)
        if edges:
            self.graph.add_edges_from(edges)

    def add_nodes(self, nodes: list):
        self.graph.add_nodes_from(nodes)

    def add_edges(self, edges: list):
        self.graph.add_nodes_from(edges)
    
