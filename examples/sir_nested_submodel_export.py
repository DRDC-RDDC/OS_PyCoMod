"""Example: export a model with nested sub-models to an interactive HTML tool.

Demonstrates a parent model containing two identical SIR sub-models
(e.g. two population groups) with cross-infection flows between them,
similar to a simplified Monte-Carlo mixing model but using deterministic
flows.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import pycomod as pcm

_HERE = os.path.dirname(os.path.abspath(__file__))


class SIR(pcm.Model):
    """Basic SIR compartment model."""
    def build(self, s0=95, i0=5, r0=0):
        S = self.pool(s0)
        I = self.pool(i0)
        R = self.pool(r0)

        N = self.equation(lambda: S + I + R)

        b = self.parameter(0.2)
        g = self.parameter(0.1)

        Fsi = self.flow(lambda: b * S * I / N, src=S, dest=I, stochastic=True)
        Fir = self.flow(lambda: g * I, src=I, dest=R, stochastic=True)

        self.set_available(locals(), output=(S, I, R))


class MixSIR(pcm.Model):
    """Two SIR groups with cross-infection between them."""
    def build(self):
        GrpA = self.submodel(SIR(95, 5, 0))
        GrpB = self.submodel(SIR(90, 10, 0))

        b_mix = self.parameter(0.05)

        S = self.equation(lambda: GrpA.S + GrpB.S)
        I = self.equation(lambda: GrpA.I + GrpB.I)
        R = self.equation(lambda: GrpA.R + GrpB.R)

        Fsi_AB = self.flow(
            lambda: b_mix * GrpA.S * GrpB.I / GrpB.N,
            src=GrpA.S, dest=GrpA.I)
        Fsi_BA = self.flow(
            lambda: b_mix * GrpB.S * GrpA.I / GrpA.N,
            src=GrpB.S, dest=GrpB.I)

        self.set_available(locals(), output=(GrpA, GrpB, S, I, R))


help_text = """
# Two-Group Mixing SIR Model

This model contains **two SIR sub-models** representing separate population
groups (Group A and Group B), connected by cross-infection flows.

## Sub-models

- **GrpA**: Group A SIR model (S=95, I=5, R=0)
- **GrpB**: Group B SIR model (S=90, I=10, R=0)

Each group has its own transmission rate **b** and recovery rate **g**.

## Cross-infection

- **b_mix**: Rate of cross-group transmission (default: 0.05)
- **Fsi_AB**: Infection of Group A susceptibles by Group B infecteds
- **Fsi_BA**: Infection of Group B susceptibles by Group A infecteds

## How to Use

1. Adjust initial values for each group and the mixing rate in the Inputs tab
2. Click **Run Model** to execute the simulation
3. Outputs are labelled with sub-model prefixes (e.g. GrpA.S, GrpB.I)
"""

if __name__ == "__main__":
    model = MixSIR()
    output = pcm.export_to_html(
        model=model,
        filename="mix_sir.html",
        path=_HERE,
        title="Two-Group Mixing SIR Model",
        help_text=help_text,
    )
    print(f"HTML tool generated: {output}")
