> **Note from September 2026.** An audit of this project found that its main conclusions do not
> hold. The search started from RK4 and Dormand-Prince, and a score capped at 1 kept them, so it
> did not find them again. Nobody trained the generator, so the local-minima claim is not true.
> The harness itself works for explicit tables. See claims N1 to N11 on the
> [project site](https://jgoetzmann.github.io/numeric-integration-methods-exploration/#claims). The text below is the original from 2025.

# Novel Numerical Integration Methods

This project built an ML framework to search for new Runge–Kutta schemes by generating Butcher tables with neural nets, evolutionary search, and gradient descent. It supports 4–7 stage methods with automated constraint handling and optimizes across accuracy, efficiency, and stability. Large-scale training on 10k ODEs confirmed the framework could replicate classical integrators and assess novel ones, with full instrumentation for runtime monitoring and analysis.

Empirical benchmarks show gradient descent consistently collapsed into local minima, producing near-identical low-accuracy schemes. Evolutionary search, by contrast, independently rediscovered RK4 and Dormand–Prince with exact performance match, validating them as true mathematical optima. Attempts to force novelty generated structurally distinct methods but at catastrophic accuracy loss (orders of magnitude worse than baselines). The main conclusion: ML exploration confirms classical RK methods’ optimality, exposes gradient descent’s limitations, and underscores the difficulty of surpassing established solvers without severe trade-offs.
