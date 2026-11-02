from algorithms.base import BaseAlgorithm, FormalConcept

class NextClosure(BaseAlgorithm):
    def _step(self, found_concept: list):
        reversed_attributes = reversed(self.context.attributes)
        for m in reversed_attributes:
            if m in found_concept:
                continue

            # Keep only attributes BEFORE m
            prefix = [i for i in found_concept if i < m]
        
            candidate = prefix + [m]
            candidate = sorted(candidate)
            candidate_closure = self.closure_of_attributes(candidate)

            # THE FIX: Check if the closure adds any new attributes BEFORE m
            new_prefix = [i for i in candidate_closure if i < m]

            if prefix == new_prefix:
                return candidate_closure

        return None

    def run(self) -> list[FormalConcept]:
        found_concepts: list[FormalConcept] = []
        found_concept = self.closure_of_attributes([])
        found_concepts.append(self.remap_concept(found_concept))

        while found_concept != self.context.attributes:
            found_concept = self._step(found_concept)
            if found_concept is None:
                break
            remapped = self.remap_concept(found_concept)
            found_concepts.append(remapped)

        return found_concepts