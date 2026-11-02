from algorithms.nextclosure import NextClosure, Context

import numpy as np

objects = [
    "T1", "T2", "T3", "T4", "T5",
    "T6", "T7", "T8", "T9", "T10"
]

attributes = [
    "A1", "A2", "A3", "A4", "A5",
    "A6", "A7", "A8", "A9", "A10",
    "A11", "A12", "A13", "A14", "A15",
    "A16", "A17", "A18", "A19", "A20"
]

K = np.array([
    # A1 A2 A3 A4 A5 A6 A7 A8 A9 A10 A11 A12 A13 A14 A15 A16 A17 A18 A19 A20
    [ 1,  1,  1,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],  # T1
    [ 0,  0,  0,  0,  1,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],  # T2
    [ 0,  1,  0,  0,  0,  1,  1,  0,  0,  0,  0,  0,  0,  1,  0,  1,  0,  1,  0,  0],  # T3
    [ 0,  1,  1,  0,  0,  1,  1,  0,  0,  1,  1,  1,  0,  0,  0,  1,  1,  1,  1,  0],  # T4
    [ 0,  1,  0,  1,  0,  0,  1,  1,  1,  0,  0,  0,  1,  0,  0,  0,  0,  1,  1,  0],  # T5
    [0, 1, 0, 0, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0],  # T6
[0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0],  # T7
[0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0],  # T8
[0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0],  # T9
    [ 0,  0,  0,  1,  0,  0,  1,  0,  0,  0,  0,  0,  0,  0,  1,  0,  0,  0,  0,  1]   # T10
])

context = Context(
    objects=objects,
    attributes=attributes,
    relations=K
)

algorithm = NextClosure(context)
output = algorithm.run()

i = 0
for concept in output:
    print(f"Concept {i}: {concept}")
    i += 1