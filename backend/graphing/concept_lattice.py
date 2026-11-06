import networkx as nx
from models.concept import FormalConcept

class ConceptLattice:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.node_counter = 0
        self.top = None
        self.finalized = False

    def _sort_concepts(self, concepts):
        return sorted(
            concepts,
            key=lambda c: len(c.objects),
            reverse=True
        )

    def build(self, concepts: list[FormalConcept]):
        concepts = self._sort_concepts(concepts)

        if not concepts:
            raise ValueError("Cannot build a lattice from an empty concept list")

        self.add_top(concepts[0])

        for concept in concepts[1:]:
            self.add_concept(concept)

        self.finalize_object_storage()
        self._validate(concepts)


    def _validate(self, concepts: list[FormalConcept]):
        if self.graph.number_of_nodes() != len(concepts):
            raise ValueError(
                "Graph construction failed: concept count mismatch"
            )

        for node, original in enumerate(concepts):
            reconstructed = self.get_concept(node)

            if set(original.objects) != set(reconstructed.objects):
                raise ValueError(f"Object mismatch at node {node}")

            if set(original.attributes) != set(reconstructed.attributes):
                raise ValueError(f"Attribute mismatch at node {node}")

        if not nx.is_directed_acyclic_graph(self.graph):
            raise ValueError("Generated graph contains a cycle")

    def add_top(self, concept):
        node_id = self.node_counter
        self.node_counter += 1

        self.graph.add_node(
            node_id,
            objects=set(concept.objects),  # Temporary
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

        if self.finalized:
            raise RuntimeError("Cannot add concepts after finalization")

        # Prevent duplicates
        for node in self.graph.nodes:
            if concept == self.get_concept(node):
                return node

        parents = self.find_parents(concept)

        if not parents:
            raise ValueError(f"No parents found for concept: {concept}")

        # Find existing nodes that should become children
        children = set()

        for parent in parents:
            for child in self.get_children(parent):
                child_concept = self.get_concept(child)

                if child_concept < concept:
                    children.add(child)

        # Incremental attributes
        parent_attributes = set()

        for parent in parents:
            parent_attributes.update(
                self.get_full_attributes(parent)
            )

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
            objects=set(concept.objects),
            attributes_delta=attributes_delta,
            level=level
        )

        # Add parent edges
        for parent in parents:
            self.graph.add_edge(parent, node_id)

        # Redirect child edges
        for child in children:
            for parent in self.get_parents(child):
                if parent in parents:
                    self.graph.remove_edge(parent, child)

            self.graph.add_edge(node_id, child)

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

        if self.finalized:
            return self.graph.nodes[node]["objects_delta"]

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

    def get_full_objects(self, node):

        if not self.finalized:
            return set(self.graph.nodes[node]["objects"])

        descendants = nx.descendants(self.graph, node)
        descendants.add(node)

        objects = set()

        for descendant in descendants:
            objects.update(
                self.graph.nodes[descendant]["objects_delta"]
            )

        return objects

    def get_concept(self, node):
        if self.finalized:
            objects = self.get_full_objects(node)
        else:
            objects = self.graph.nodes[node]["objects"]

        return FormalConcept(
            objects=list(objects),
            attributes=list(self.get_full_attributes(node))
        )

    def finalize_object_storage(self):

        if self.finalized:
            return

        # Calculate all object deltas before deleting complete sets
        for node in self.graph.nodes:

            node_objects = self.graph.nodes[node]["objects"]

            child_objects = set()

            for child in self.get_children(node):
                child_objects.update(
                    self.graph.nodes[child]["objects"]
                )

            self.graph.nodes[node]["objects_delta"] = (
                node_objects - child_objects
            )

        # Remove redundant complete object sets
        for node in self.graph.nodes:
            del self.graph.nodes[node]["objects"]

        self.finalized = True

    def draw(self):
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(16, 12), dpi=160)

        pos = nx.multipartite_layout(
            self.graph,
            subset_key="level",
            align="horizontal",
            scale=1.5
        )

        # Top concept at the top
        pos = {
            node: (x, -y)
            for node, (x, y) in pos.items()
        }

        labels = {}

        for node in self.graph.nodes:

            objects = self.get_node_objects(node)
            attributes = self.get_node_attributes(node)

            labels[node] = (
                f"Node {node}\n"
                f"Objects: {', '.join(map(str, sorted(objects)))}\n"
                f"Attributes: {', '.join(map(str, sorted(attributes)))}"
            )

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
            node_size=500,
            node_color="lightblue",
            edgecolors="steelblue"
        )

        nx.draw_networkx_labels(
            self.graph,
            pos,
            labels=labels,
            ax=ax,
            font_size=8,
            verticalalignment="bottom"
        )

        ax.margins(0.3)
        ax.axis("off")

        plt.tight_layout()

        plt.savefig(
            "backend/temp/hasse_diagram.png",
            dpi=300,
            bbox_inches="tight",
            pad_inches=0.5
        )

        plt.show()

    def get_objects_for_attributes(self, attributes):

        query = set(attributes)

        candidates = [
            node
            for node in self.graph.nodes
            if query.issubset(self.get_full_attributes(node))
        ]

        if not candidates:
            return None

        node = min(
            candidates,
            key=lambda n: len(self.get_full_attributes(n))
        )

        return {
            "node": node,
            "objects": self.get_full_objects(node),
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