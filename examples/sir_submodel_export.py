"""Example: export a model with sub-models to an interactive HTML tool.

Demonstrates a parent model containing two SIR sub-models (e.g. two
regions) connected by a migration flow.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import pycomod as pcm

_HERE = os.path.dirname(os.path.abspath(__file__))


class SIR(pcm.Model):
    """Basic SIR compartment model."""
    def build(self, s0=950, i0=50, r0=0):
        S = self.pool(s0)
        I = self.pool(i0)
        R = self.pool(r0)

        N = self.equation(lambda: S + I + R)

        b = self.parameter(0.3)
        g = self.parameter(0.1)

        Fsi = self.flow(lambda: b * S * I / N, src=S, dest=I, stochastic=True)
        Fir = self.flow(lambda: g * I, src=I, dest=R, stochastic=True)

        self.set_available(locals(), output=(S, I, R))


class TwoRegionModel(pcm.Model):
    """Two SIR regions with inter-region migration."""
    def build(self):
        r1 = self.submodel(SIR(950, 50, 0))
        r2 = self.submodel(SIR(950, 50, 0))

        migration_rate = self.parameter(0.01)

        F_r1_to_r2 = self.flow(lambda: migration_rate * r1.I, src=r1.I, dest=r2.I)

        self.set_available(locals(), output=(r1, r2))


help_text = """
# Two-Region SIR Model

This model contains **two SIR sub-models** representing separate regions,
connected by a migration flow that moves infected individuals from
Region 1 to Region 2.

## Sub-models

- **r1**: Region 1 SIR model
- **r2**: Region 2 SIR model

## Parameters

- **migration_rate**: Rate at which infected individuals move from r1 to r2

## How to Use

1. Adjust initial values for each region in the Inputs tab
2. Click **Run Model** to execute the simulation
3. Outputs are labelled with sub-model prefixes (e.g. r1.S, r2.I)
"""

if __name__ == "__main__":
    model = TwoRegionModel()
    output = pcm.export_to_html(
        model=model,
        filename="two_region_sir.html",
        path=_HERE,
        title="Two-Region SIR Model with Sub-Models",
        help_text=help_text,
    )
    print(f"HTML tool generated: {output}")
