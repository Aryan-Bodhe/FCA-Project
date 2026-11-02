from dataclasses import dataclass, field

import numpy as np

@dataclass
class Concept:
    objects: list = field(default_factory=list)
    attributes: list = field(default_factory=list)

@dataclass
class Context:
    objects: list = field(default_factory=list)
    attributes: list = field(default_factory=list)
    relations: list = field(default_factory=list)

def intersection(a: list, b: list):
    return [x for x in a if x in b]


class NextClosure:
    def __init__(self, context: Context):
        self.concepts: list[Concept] = None
        self.context: Context = context
        self.object_map: dict = {}
        self.attribute_map: dict = {}

    def _prepare(self, context: Context):            
        att_id = 0
        for att in context.attributes:
            self.attribute_map[att_id] = att
            att_id += 1

        obj_id = 0
        for obj in context.objects:
            self.object_map[obj_id] = obj
            obj_id += 1

        attributes = list(range(att_id))
        objects = list(range(obj_id))

        new_context = Context(
            attributes=attributes,
            objects=objects,
            relations=context.relations
        )

        return new_context

    def run(self):
        self.context = self._prepare(self.context)
        found_concept = []
        found_concepts = []
        remapped = self._remap_concept(found_concept)
        found_concept.append(remapped)
        print(f"Concept {len(found_concepts) + 1}")
        print(f"Objects: {remapped[0]}")
        print(f"Attributes: {remapped[1]}")
        print("-"*50)

        while found_concept != self.context.attributes:
            found_concept = self.nextconcept(found_concept)
            if found_concept is not None:
                found_concepts.append(found_concept)

            remapped = self._remap_concept(found_concept)
            print(f"Concept {len(found_concepts) + 1}")
            print(f"Objects: {remapped[0]}")
            print(f"Attributes: {remapped[1]}")
            print("-"*50)

    def nextconcept(self, found_concept: list):
        attributes = reversed(self.context.attributes)
        for m in attributes:
            if m in found_concept:
                continue

            intx_set = list(range(m))
            prefix = intersection(found_concept, intx_set)
            candidate = prefix + [m]
            candidate_closure = self.close_attributes(candidate)
            new_prefix = [i for i in candidate_closure if i < m]

            if prefix == new_prefix:
                return candidate_closure

        return None


    def _remap_concept(self, attrs: list):
        # 1. Find the extent (G) by deriving objects from the intent (M)
        objs = self.context.objects
        for attr in attrs:
            temp = self._derive_objects(attr)
            objs = intersection(objs, temp)
            
        # 2. Map object indices back to string names
        remapped_objects = []
        for obj in objs:
            remapped_objects.append(self.object_map[obj])
            
        # 3. Map attribute indices back to string names
        remapped_attributes = []
        for attr in attrs: 
            remapped_attributes.append(self.attribute_map[attr])
            
        # Return the formal concept as a (G, M) tuple
        return (remapped_objects, remapped_attributes)


    def _derive_objects(self, m: int):
        result = []
        for g in self.context.objects:
            if self.context.relations[g][m]:
                result.append(g)
        return result


    def _derive_attributes(self, g: int):
        result = []
        for m in self.context.attributes:
            if self.context.relations[g][m]:
                result.append(m)
        return result


    def close_attributes(self, attributes: list[int]):
        objs = self.context.objects
        for attr in attributes:
            temp = self._derive_objects(attr)
            objs = intersection(objs, temp)

        attrs = self.context.attributes
        for obj in objs:
            temp = self._derive_attributes(obj)
            attrs = intersection(attrs, temp)

        return attrs

    def close_objects(self, objects: list[int]):
        attrs = self.context.attributes
        for obj in objects:
            temp = self._derive_attributes(obj)
            attrs = intersection(attrs, temp)

        objs = self.context.objects
        for attr in attrs:
            temp = self._derive_objects(attr)
            objs = intersection(objs, temp)
    
        return objs



airlines = [
    "Air Canada",
    "Air New Zealand",
    "Nippon Airways",
    "Ansett Australia",
    "Austrian Airlines"
]

attributes = [
    "Latin America",
    "Europe",
    "Canada",
    "Asia Pacific",
    "Middle East",
    "Africa",
    "Mexico",
    "Caribbean",
    "USA"
]

K = np.array([
    [1, 1, 1, 1, 1, 0, 1, 1, 1],  # Air Canada
    [0, 1, 0, 1, 0, 0, 0, 0, 1],  # Air New Zealand
    [0, 1, 0, 1, 0, 0, 0, 0, 1],  # Nippon Airways
    [0, 0, 0, 1, 0, 0, 0, 0, 0],  # Ansett Australia
    [0, 1, 1, 1, 1, 1, 0, 0, 1]   # Austrian Airlines
])

context = Context(
    objects=airlines,
    attributes=attributes,
    relations=K
)

next_closure = NextClosure(context)

next_closure.run()