"""Example: export a model with a conditional (when) flow to HTML."""

import os
import pycomod as pcm

_HERE = os.path.dirname(os.path.abspath(__file__))


class FlowTracker(pcm.Model):
    """Pool drained by a flow with a when guard."""

    def build(self):
        """Define the model elements."""
        P = self.pool(20, pool_type='int')

        Fout = self.flow(
            lambda: P.init_value * 0.02, src=P, when=lambda: self.t() <= 40
        )

        return locals()


help_text = """
# Flow with When Guard Example

This model demonstrates the **when** parameter on flows, which acts as
a conditional guard that enables or disables the flow based on a runtime
condition.

## Elements

- **P**: Population pool (integer, starts at 20)
- **Fout**: Outflow from P at a constant rate of `P.init_value * 0.02`

## When Guard

The flow `Fout` has `when=lambda: self.t()<=40`, which means:

- **Before time 40**: The flow is active, draining P at the specified rate
- **After time 40**: The flow is disabled (returns 0), and P stops decreasing

This is useful for modeling time-limited processes, seasonal effects,
or policy changes that turn flows on or off at specific times.
"""


if __name__ == "__main__":
    model = FlowTracker()
    output = pcm.export_to_html(
        model=model,
        filename="when_model.html",
        path=_HERE,
        title="Flow with When Guard Example",
        help_text=help_text,
    )
    print(f"HTML tool generated: {output}")
