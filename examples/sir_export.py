"""Example: export a simple SIR model to an interactive HTML tool."""

import os
import pycomod as pcm

# Directory where this script lives
_HERE = os.path.dirname(os.path.abspath(__file__))


class SimpleSIR(pcm.Model):
    def build(self):
        # Pools
        S = self.pool(95)
        I = self.pool(5)
        R = self.pool(0)

        # Equations
        N = self.equation(lambda: S + I + R)

        # Parameters
        b = self.parameter(0.2)
        g = self.parameter(0.1)

        # Flows
        Fsi = self.flow(lambda: b * S * I / N, src=S, dest=I, stochastic=True)
        Fir = self.flow(lambda: g * I, src=I, dest=R, stochastic=True)

        return locals()


help_text = """
# SIR Disease Model

This model simulates the spread of an infectious disease in a population.

## Compartments

- **S (Susceptible)**: Individuals who can contract the disease
- **I (Infected)**: Individuals currently infected and infectious
- **R (Recovered)**: Individuals who have recovered and are immune

## Parameters

- **b (Contact Rate)**: Rate of transmission per contact (default: 0.2)
- **g (Recovery Rate)**: Rate of recovery (default: 0.1)

## How to Use

1. Adjust initial values and parameters in the Inputs tab
2. Click **Run Model** to execute the simulation
3. Use **Save Inputs** / **Load Inputs** to persist your configuration
"""

if __name__ == "__main__":
    model = SimpleSIR()
    output = pcm.export_to_html(
        model=model,
        filename="sir_model.html",
        path=_HERE,
        title="SIR Disease Model - Interactive Tool",
        help_text=help_text,
    )
    print(f"HTML tool generated: {output}")
