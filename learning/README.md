# Discrete energy-allocation exercise

Status: implemented educational exercise; not the production DP controller and not a learned policy.

Three segments have base costs of 10 time units each. Spending one energy token on a segment saves 1, 4 or 2 units respectively. Two tokens are available; at most one can be spent per segment. The quantities are deliberately invented, dimensionless teaching values. They are unrelated to the vehicle parameters or synthetic analytic straight.

The Bellman recursion is `V(i,E) = min_a [10 - savings[i]*a + V(i+1,E-a)]`, where `a` is 0 or 1 and `a <= E`; `V(3,E)=0`. Exhaustive search independently enumerates all eight binary action sequences and rejects those using more than two tokens. The optimum is `(0,1,1)`, costing `10+6+8=24`. Both methods must produce this result. This proves agreement on this finite toy problem only.

Run `python learning/energy_allocation.py` from the project root after choosing a working Python interpreter. No model training occurs. Answer these questions in your own learning log before using the explanation academically:

1. Calculate `V(2,0)`, `V(2,1)` and `V(1,1)` by hand.
2. Why is spending energy at the earliest opportunity suboptimal here?
3. Why does this tiny result not prove that a grid-based physical DP is globally optimal?
4. What state variables would a real lap simulator need in addition to the energy budget?

The remaining guide exercises, including Q-learning and neural-network training, have not been implemented or run.
