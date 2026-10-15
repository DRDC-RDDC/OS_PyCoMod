"""Example: SIR model with step and impulse inputs exported to HTML."""

import os
import pycomod as pcm

_HERE = os.path.dirname(os.path.abspath(__file__))


class SIRWithInterventions(pcm.Model):
    """SIR model with a step intervention and an impulse."""

    def build(self):
        # Pools
        """Define the model elements."""
        S = self.pool(950)
        I = self.pool(50)
        R = self.pool(0)

        # Equations
        N = self.equation(lambda: S + I + R)

        # Parameters
        g = self.parameter(0.1)

        # Step function for contact rate: changes over time (e.g., lockdown)
        b = self.step(
            values=[0.3, 0.05, 0.2],
            times=[0, 30, 60],
            default=0.3,
        )

        # Impulse for vaccination: one-time bursts move people from S to R
        vax = self.impulse(
            values=[50, 100],
            times=[20, 45],
        )

        # Flows
        Fsi = self.flow(lambda: b * S * I / N, src=S, dest=I, stochastic=True)
        Fir = self.flow(lambda: g * I, src=I, dest=R, stochastic=True)
        Fvax = self.flow(lambda: vax, src=S, dest=R)

        self.set_available(locals(), output=(S, I, R, N))


help_text = """
# SIR Model with Interventions

This model adds **step** and **impulse** inputs to the classic SIR model
to simulate public-health interventions.

## Step: Contact Rate (b)

The contact rate changes at specified times — for example, a lockdown that
reduces transmission, followed by a partial reopening.

## Impulse: Vaccination (vax)

Vaccination campaigns deliver one-time bursts that move people from
Susceptible to Recovered at specific times.

## How to Use

1. Edit the step values/times and impulse values/times in the Inputs tab
2. Click **Run Model** to see the effect of interventions
3. Switch to **Monte Carlo** mode to see stochastic variability
"""

if __name__ == "__main__":
    model = SIRWithInterventions()
    output = pcm.export_to_html(
        model=model,
        filename="sir_interventions.html",
        path=_HERE,
        title="SIR with Step & Impulse Interventions",
        help_text=help_text,
    )
    print(f"HTML tool generated: {output}")
