from algorithms.base import BaseAlgorithm, FormalConcept, intersection, is_subset

class InClose(BaseAlgorithm):
    def _step(self, objects: list, attributes: list, index: int):
        n = len(self.context.attributes)

        for i in range(index, n):
            if i in attributes:
                continue

            objects_having_attribute_i = self.derive_objects(i)
            new_objects = intersection(objects, objects_having_attribute_i)

            if new_objects == objects:
                attributes.append(i)

            else:
                is_canonical = True

                for j in range(i):
                    if j not in attributes and is_subset(
                        new_objects, self.derive_objects(j)
                    ):
                        is_canonical = False
                        break

                if is_canonical:
                    new_attributes = attributes + [i]

                    if new_objects == []:
                        yield list(self.context.attributes)

                    else:
                        yield from self._step(
                            new_objects, new_attributes, i + 1
                        )

                        yield new_attributes



    def run(self):
        found_concept = self.closure_of_attributes([])
        yield self.remap_concept(found_concept)
        
        seed_objects = self.context.objects

        for c in found_concept:
            temp = self.derive_objects(c)
            seed_objects = intersection(seed_objects, temp)

        for concept in self._step(seed_objects, found_concept, 0):
            yield self.remap_concept(concept)