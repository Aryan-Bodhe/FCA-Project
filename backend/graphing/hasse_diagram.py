from models import FormalConcept

class HasseNode:
    def __init__(
        self, 
        concept: FormalConcept,
        parents: list["HasseNode"] = None,
        children: list["HasseNode"] = None
    ):
        self.concept = concept
        self.parents = parents or []
        self.children = children or []


class HasseDiagram:
    def __init__(self, concepts: list[FormalConcept]):
        self.graph = None
        self.concepts = concepts

    def construct(self):
        pass

