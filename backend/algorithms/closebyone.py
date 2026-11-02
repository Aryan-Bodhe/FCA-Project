from algorithms.base import BaseAlgorithm, intersection, FormalConcept

class CloseByOne(BaseAlgorithm):
    def _step(self, A: list, y: int):
        for i in range(y, len(self.context.attributes)):
            if i not in A:
                B = A + [i]
                C = self.closure_of_attributes(B)
                indx_set = list(range(i))
                if intersection(A, indx_set) == intersection(C, indx_set):
                    yield C
                    yield from self._step(C, i+1)

    def run(self) -> list[FormalConcept]:
        found_concepts: list[FormalConcept] = []
        found_concept = self.closure_of_attributes([])
        found_concepts.append(self.complete_concept(found_concept))
        
        for concept in self._step(found_concept, 0):
            remapped = self.complete_concept(concept)
            found_concepts.append(remapped)

        return found_concepts
