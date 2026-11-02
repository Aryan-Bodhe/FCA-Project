                 YOUR ALGORITHMS
                       │
             ┌─────────┴─────────┐
             │   BaseAlgorithm   │
             │ prepare / closure │
             └─────────┬─────────┘
                       │
                algorithm runner
                       │
                 TraceEvent[]
                       │
                  FastAPI JSON
                       │
            ┌──────────┴──────────┐
            │                     │
      Hasse graph            Step timeline
            │                     │
       ELK.js layout        Next / Play / Back
            │                     │
            └──────────┬──────────┘
                       │
                 React Flow UI