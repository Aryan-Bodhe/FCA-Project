import networkx as nx
from backend.models.concept import FormalConcept

class ConceptLattice:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.node_counter = 0
        self.top = None

    def add_top(self, concept):
        node_id = self.node_counter
        self.node_counter += 1
        self.graph.add_node(
            node_id,
            objects=concept.objects,
            attributes_delta=set(concept.attributes),
            level=0
        )
        self.top = node_id
        return node_id

    def find_parents(self, concept):
        parents = set()
        stack = [self.top]

        while stack:
            node = stack.pop()
            current = self.get_concept(node)

            if not concept < current:
                continue

            eligible_children = []
            for child in self.graph.successors(node):
                child_concept = self.get_concept(child)

                if concept < child_concept:
                    eligible_children.append(child)

            if eligible_children:
                stack.extend(eligible_children)
            else:
                parents.add(node)

        return parents

    def add_concept(self, concept):
        parents = self.find_parents(concept)

        # Union of complete attributes of all parents
        parent_attributes = set()

        for parent in parents:
            parent_attributes.update(
                self.get_full_attributes(parent)
            )

        # Only newly introduced attributes
        attributes_delta = (
            set(concept.attributes) - parent_attributes
        )

        node_id = self.node_counter
        self.node_counter += 1

        level = max(
            self.graph.nodes[p]["level"]
            for p in parents
        ) + 1

        self.graph.add_node(
            node_id,
            objects=concept.objects,
            attributes_delta=attributes_delta,
            level=level
        )

        for parent in parents:
            self.graph.add_edge(parent, node_id)

        return node_id

    def get_parents(self, node):
        return list(self.graph.predecessors(node))


    def get_children(self, node):
        return list(self.graph.successors(node))


    def get_siblings(self, node):
        siblings = set()

        for parent in self.get_parents(node):
            siblings.update(self.get_children(parent))

        siblings.discard(node)

        return list(siblings)

    def get_node_attributes(self, node):
        return self.graph.nodes[node]["attributes_delta"]


    def get_node_objects(self, node):
        return self.graph.nodes[node]["objects"]


    def get_node_label(self, node):
        return (
            f"Node {node}\n"
            f"Objects: {list(self.get_node_objects(node))}\n"
            f"New Attributes: {list(self.get_node_attributes(node))}"
        )

    def get_full_attributes(self, node):
        ancestors = nx.ancestors(self.graph, node)
        ancestors.add(node)

        attributes = set()

        for ancestor in ancestors:
            attributes.update(
                self.graph.nodes[ancestor]["attributes_delta"]
            )

        return attributes

    def get_concept(self, node):
        return FormalConcept(
            objects=self.graph.nodes[node]["objects"],
            attributes=list(self.get_full_attributes(node))
        )

    def draw(self):
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(14, 10), dpi=160)

        pos = nx.multipartite_layout(
            self.graph,
            subset_key="level",
            align="horizontal",
            scale=1.5
        )

        # Flip vertically so top concept is at the top
        pos = {
            node: (x, -y)
            for node, (x, y) in pos.items()
        }

        labels = {
            node: (
                f"Node {node}\n"
                f"Attributes: "
                f"{', '.join(sorted(self.get_node_attributes(node)))}"
            )
            for node in self.graph.nodes
        }

        nx.draw_networkx_edges(
            self.graph,
            pos,
            ax=ax,
            arrows=False,
            width=1.5,
            edge_color="steelblue"
        )

        nx.draw_networkx_nodes(
            self.graph,
            pos,
            ax=ax,
            node_size=400,
            node_color="lightblue",
            edgecolors="steelblue"
        )

        nx.draw_networkx_labels(
            self.graph,
            pos,
            labels=labels,
            ax=ax,
            font_size=9,
            verticalalignment="bottom"
        )

        ax.margins(0.25)
        ax.axis("off")

        plt.tight_layout()

        plt.savefig(
            "temp/hasse_diagram.png",
            dpi=300,
            bbox_inches="tight",
            pad_inches=0.5
        )

        plt.show()

    def get_objects_for_attributes(self, attributes):

        query = set(attributes)

        candidates = []

        for node in self.graph.nodes:

            full_attributes = self.get_full_attributes(node)

            if query.issubset(full_attributes):
                candidates.append(node)

        if not candidates:
            return None

        # Find the smallest closed intent containing the query
        node = min(
            candidates,
            key=lambda n: len(self.get_full_attributes(n))
        )

        return {
            "node": node,
            "objects": self.graph.nodes[node]["objects"],
            "closure": self.get_full_attributes(node)
        }

    def print_graph(self):
        for node in self.graph.nodes:
            print(f"\n[{node}]")
            print(f"  Objects:          {self.get_node_objects(node)}")
            print(f"  New Attributes:   {self.get_node_attributes(node)}")
            print(f"  Full Attributes:  {self.get_full_attributes(node)}")
            print(f"  Parents:          {self.get_parents(node)}")
            print(f"  Children:         {self.get_children(node)}")