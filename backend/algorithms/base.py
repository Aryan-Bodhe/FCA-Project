from models import FormalContext, FormalConcept

def intersection(a: list, b: list):
    return [x for x in a if x in set(b)]

def is_subset(a: list, b: list):
    return set(a) <= set(b)

class BaseAlgorithm:
    def __init__(self, context: FormalContext):
        self.concepts: list[FormalConcept] = []
        self.context: FormalContext = context


    def _step(self):
        pass


    def run(self):
        pass


    def derive_objects(self, m: int) -> list[int]:
        if self.context is None:
            raise ValueError("Context not initialised. Call prepare() before any other function.")
        
        result = []
        for g in self.context.objects:
            if self.context.relations[g][m]:
                result.append(g)
        return result
    
    
    def derive_attributes(self, g: int) -> list[int]:
        if self.context is None:
            raise ValueError("Context not initialised. Call prepare() before any other function.")
        
        result = []
        for m in self.context.attributes:
            if self.context.relations[g][m]:
                result.append(m)
        return result


    def closure_of_attributes(self, attributes: list[int]) -> list[int]:
        """
            Computes and returns closure of attribute list.
        """
        if self.context is None:
            raise ValueError("Context not initialised. Call prepare() before any other function.")
        
        objs = self.context.objects
        for attr in attributes:
            temp = self.derive_objects(attr)
            objs = intersection(objs, temp)

        attrs = self.context.attributes
        for obj in objs:
            temp = self.derive_attributes(obj)
            attrs = intersection(attrs, temp)

        return attrs

    def compute_extent(self, attrs: list[int]):
        """
        Computes the extent set for the given attribute set.
        """
        objs = self.context.objects
        for attr in attrs:
            temp = self.derive_objects(attr)
            objs = intersection(objs, temp)
        return objs

    def compute_intent(self, objs: list[int]):
        """
        Computes the intent set for the given object set.
        """
        attrs = self.context.attributes
        for obj in objs:
            temp = self.derive_attributes(obj)
            attrs = intersection(attrs, temp)
        return attrs


    def remap_concept(self, attrs: list) -> FormalConcept:
        """
            Returns list of (object, attribute) concept pairs from given attribute list.
        """
        if self.context is None:
            raise ValueError("Context not initialised. Call prepare() before any other function.")

        # 1. Find the extent (G) by deriving objects from the intent (M)
        objs = self.compute_extent(attrs)
        
        # 2. Map object indices back to string names
        remapped_objects = self.context.remap_objects(objs)
        
        # 3. Map attribute indices back to string names
        remapped_attributes = self.context.remap_attributes(attrs)
            
        # Return the formal concept as a (G, M) tuple
        return FormalConcept(remapped_objects, remapped_attributes) 