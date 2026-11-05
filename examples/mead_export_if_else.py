"""Example: MEAD model with if/else guards in flow lambdas, exported to HTML.

Same as mead_export.py, but every flow that drains a pool uses
``rate if pool > 0 else 0.0`` so the pool cannot be pushed below zero.
"""

import os
import pycomod as pcm

_HERE = os.path.dirname(os.path.abspath(__file__))


class MEADIfElse(pcm.Model):
    """MEAD workforce pipeline model with non-negative pool guards."""

    def build(self, intake, inexp, exp, nop):
        """Define the model elements."""
        I = self.pool(inexp, pool_type='int')
        E = self.pool(exp, pool_type='int')
        N = self.pool(nop, pool_type='int')

        g = self.parameter(intake)
        R = self.parameter(100)
        rI = self.parameter(5)
        rE = self.parameter(7)
        a = self.parameter(0.005)

        F_I = self.flow(lambda: g, dest=I, stochastic=True)
        F_IE = self.flow(lambda: min(I * rI, E * rI) / R if I > 0 else 0.0,
                         src=I, dest=E)
        F_EN = self.flow(lambda: a * N if E > 0 else 0.0, src=E, dest=N)

        F_EA = self.flow(lambda: a * E if E > 0 else 0.0, src=E,
                         stochastic=True)
        F_NA = self.flow(lambda: a * N if N > 0 else 0.0, src=N)

        self.set_available(locals(), output=(I, E, N))


help_text = """
# MEAD Workforce Pipeline Model (if/else guards)

This version of the MEAD model guards each outgoing flow with an
if/else expression, e.g. `a * N if E > 0 else 0.0`, so a flow stops
when its source pool is empty and no pool drops below zero.

## How to Use

1. Adjust initial pool values and parameters in the Inputs tab
2. Click **Run Model** to execute the simulation
3. Switch to **Monte Carlo** mode to see stochastic variation in intake
   and attrition
"""

if __name__ == "__main__":
    model = MEADIfElse(intake=0.4, inexp=40, exp=15, nop=50)
    output = pcm.export_to_html(
        model=model,
        filename="mead_model_if_else.html",
        path=_HERE,
        title="MEAD Workforce Pipeline Model (if/else guards)",
        help_text=help_text,
    )
    print(f"HTML tool generated: {output}")
