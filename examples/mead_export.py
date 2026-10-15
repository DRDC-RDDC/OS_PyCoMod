"""Example: export a MEAD workforce pipeline model to an HTML tool."""

import os
import pycomod as pcm

_HERE = os.path.dirname(os.path.abspath(__file__))


class MEAD(pcm.Model):
    """MEAD workforce pipeline model."""

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
        F_IE = self.flow(lambda: min(I * rI, E * rI) / R, src=I, dest=E)
        F_EN = self.flow(lambda: a * N, src=E, dest=N)

        F_EA = self.flow(lambda: a * E, src=E, stochastic=True)
        F_NA = self.flow(lambda: a * N, src=N)

        self.set_available(locals(), output=(I, E, N))


help_text = """
# MEAD Workforce Pipeline Model

This model simulates workforce progression through experience levels
with stochastic intake and attrition.

## Pools

- **I (Inexperienced)**: New workforce members
- **E (Experienced)**: Members who have gained experience
- **N (Non-operational)**: Members no longer in active operation

## Parameters

- **g (Intake)**: Rate of new members entering the pipeline
- **R**: Capacity scaling factor (default: 100)
- **rI**: Inexperienced transition rate (default: 5)
- **rE**: Experienced transition rate (default: 7)
- **a (Attrition)**: Attrition rate (default: 0.005)

## Flows

- **F_I**: Intake flow into I (stochastic)
- **F_IE**: Promotion from I to E, rate = min(I*rI, E*rI)/R
- **F_EN**: Transition from E to N, rate = a*N
- **F_EA**: Attrition from E (stochastic), rate = a*E
- **F_NA**: Attrition from N, rate = a*N

## How to Use

1. Adjust initial pool values and parameters in the Inputs tab
2. Click **Run Model** to execute the simulation
3. Switch to **Monte Carlo** mode to see stochastic variation in intake
   and attrition
"""

if __name__ == "__main__":
    model = MEAD(intake=0.4, inexp=40, exp=15, nop=50)
    output = pcm.export_to_html(
        model=model,
        filename="mead_model.html",
        path=_HERE,
        title="MEAD Workforce Pipeline Model",
        help_text=help_text,
    )
    print(f"HTML tool generated: {output}")
