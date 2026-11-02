class FormalConcept:
    def __init__(self, objects: list, attributes: list):
        self.objects = objects
        self.attributes = attributes

    def __eq__(self, other: "FormalConcept"):
        return (
            set(self.objects) == set(other.objects)
            and
            set(self.attributes) == set(other.attributes)
        )

    def __le__(self, other: "FormalConcept"):
        return (
            set(self.objects) <= set(other.objects) 
            and 
            set(self.attributes) >= set(other.attributes)
        )

    def __lt__(self, other: "FormalConcept"):
        return self <= other and self != other

    def __ge__(self, other: "FormalConcept"):
        return other <= self

    def __gt__(self, other: "FormalConcept"):
        return other <= self and self != other

    def is_incomparable(self, other: "FormalConcept"):
        return not (self <= other or self >= other)