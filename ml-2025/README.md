# Novel Numerical Integration Methods

A machine learning system for discovering new Runge-Kutta integration schemes (Butcher tables) that can outperform classical methods in terms of accuracy, efficiency, and stability.

## Project Overview

This project explores the fascinating intersection of machine learning and numerical analysis by automatically discovering new Runge-Kutta integration methods. Instead of manually designing these methods (which has been done for over a century), I built a system that uses neural networks and evolutionary algorithms to generate novel "Butcher tables" - the mathematical structures that define how numerical integrators work.

The system trains on a diverse dataset of 10,000 ordinary differential equations (ODEs), ranging from simple linear systems to complex stiff problems like Van der Pol oscillators. Through iterative training, the neural networks learn to generate integration schemes that balance three key objectives: accuracy (how close the solution is to the true answer), efficiency (how fast it runs), and stability (how well it handles difficult problems). The most promising methods are then rigorously tested against classical baselines like RK4 and RK45.

What makes this project particularly interesting is that it's not just optimizing existing methods - it's discovering entirely new mathematical structures. Some of the generated methods achieve comparable accuracy to classical approaches while being significantly more efficient, or they handle stiff problems that would cause traditional methods to fail. The system includes comprehensive evaluation metrics, database storage for tracking experiments, and rich visualizations to understand what makes these new methods work.

The key insight is that machine learning can help us explore the vast space of possible integration schemes that human mathematicians might never have considered. By framing numerical integration as an optimization problem with multiple objectives, we can discover methods tailored to specific types of problems or performance requirements. This opens up exciting possibilities for developing specialized integrators for different scientific computing applications.

## Training Variables

The neural networks in this system learn to optimize several key variables that define how numerical integration methods work:

**Butcher Table Coefficients (A, b, c matrices)**: These are the core mathematical parameters that define a Runge-Kutta method. The A matrix contains the intermediate step coefficients, the b vector contains the final weights for combining intermediate steps, and the c vector contains the time nodes. For a 4-stage method, this gives us 24 total parameters (4×4 + 4 + 4) that the neural network learns to optimize.

**Performance Metrics**: The system evaluates each generated method on three key dimensions:
- **Accuracy**: Measured by maximum error, L2 error, and mean error across test problems
- **Efficiency**: Based on runtime, number of integration steps, and steps per second
- **Stability**: How well the method handles stiff problems and maintains convergence

**Composite Scoring**: The final score combines these metrics with configurable weights (default: 40% accuracy, 40% efficiency, 20% stability). Different training configurations emphasize different objectives - for example, accuracy-focused training uses 70% accuracy weight.

**Neural Network Architecture**: The generator network takes random noise (128 dimensions) and outputs Butcher table coefficients (24 dimensions for 4-stage methods). The surrogate evaluator takes these coefficients and predicts performance metrics, allowing for fast screening of candidate methods without expensive numerical evaluation.
