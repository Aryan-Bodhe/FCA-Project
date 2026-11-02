from pathlib import Path
import pandas as pd

class FormalContext:
    def __init__(self, objects: list, attributes: list, relations: list[list]):
        self.objects: list = objects
        self.attributes: list = attributes
        self.relations: list[list] = relations
        self.shape: tuple[int, int] = None

        self.object_map: dict = {}
        self.attribute_map: dict = {}

        self._preprocess()

    @staticmethod
    def from_csv(path: Path):
        data = pd.read_csv(str(path), index_col=0)
        objs = data.index
        attrs = data.columns
        rels = data.to_numpy().tolist()
        return FormalContext(objs, attrs, rels)

    @staticmethod
    def from_pandas(df: pd.DataFrame):
        objs = df.index
        attrs = df.columns
        rels = df.to_numpy().tolist()
        return FormalContext(objs, attrs, rels)

    def save(self):
        pass

    def _preprocess(self):
        n = len(self.objects)
        m = len(self.attributes)

        self.shape = (n,m)

        self.object_map = {i: o for i, o in enumerate(self.objects)}
        self.attribute_map = {i: a for i, a in enumerate(self.attributes)}

        self.objects = list(range(len(self.objects)))
        self.attributes = list(range(len(self.attributes)))

    def remap_objects(self, objects: list[int]):
        return [self.object_map[o] for o in objects]

    def remap_attributes(self, attributes: list[int]):
        return [self.attribute_map[a] for a in attributes]
