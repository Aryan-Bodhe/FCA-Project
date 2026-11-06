import time
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import pandas as pd
from algorithms import *
from backend.graphing.concept_lattice import ConceptLattice
from models import FormalContext, FormalConcept

data = pd.read_csv("data/fca_airlines.csv", index_col=0)
# data = pd.read_csv("data/fca_benchmark_20x12.csv", index_col=0)

context = FormalContext.from_pandas(data)
TIME_DELAY = 0.001

def canonicalize(concepts: list[FormalConcept]):
    return {
        (frozenset(c.objects), frozenset(c.attributes))
        for c in concepts
    }

print("Algorithm: NextClosure")
algo = InClose(context)

concepts: list[FormalConcept] = []
for c in algo.run():
    concepts.append(c)
    time.sleep(TIME_DELAY)
    print(f"\rFound: {len(concepts)}", end="", flush=True)
print()



# Build and display lattice
lattice = ConceptLattice(concepts)

print("Nodes:", lattice.graph.number_of_nodes())
print("Edges:", lattice.graph.number_of_edges())

lattice.draw()