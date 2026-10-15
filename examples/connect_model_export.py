"""Example: export a model with sub-model connections (connect) to HTML."""

import os
import pycomod as pcm

_HERE = os.path.dirname(os.path.abspath(__file__))


class simple(pcm.Model):
    """Sub-model with one pool draining into two external pools."""

    def build(self, n):
        """Define the model elements."""
        P = self.pool(n, pool_type='int')

        A = self.pool(external=True)
        B = self.pool(external=True)

        Fa = self.flow(lambda: P * 0.01, src=P, dest=A)
        Fb = self.flow(lambda: P * 0.02, src=P, dest=B)

        return locals()


class simple2(pcm.Model):
    """Three connected copies of the simple sub-model."""

    def build(self):
        """Define the model elements."""
        M1 = self.submodel(simple(10))
        M2 = self.submodel(simple(0))
        M3 = self.submodel(simple(0))

        M1.A.connect(M2.P)
        M1.B.connect(M3.P)

        return locals()


help_text = """
# Connected Sub-Models Example

This model demonstrates **sub-model connections** using external pools
and the `connect()` mechanism.

## Structure

Three instances of the `simple` sub-model are connected together:

- **M1** starts with population 10
- **M2** starts with population 0, receives flow from M1 via connection A
- **M3** starts with population 0, receives flow from M1 via connection B

## Sub-model: simple

Each `simple` sub-model contains:

- **P**: Main population pool (integer)
- **A**: External pool (connection point) - receives 1% of P per time unit
- **B**: External pool (connection point) - receives 2% of P per time unit

## Connections

- `M1.A.connect(M2.P)` - M1's A output feeds into M2's population
- `M1.B.connect(M3.P)` - M1's B output feeds into M3's population

This causes M1's population to drain into M2 and M3 over time.
"""


if __name__ == "__main__":
    model = simple2()
    output = pcm.export_to_html(
        model=model,
        filename="connect_model.html",
        path=_HERE,
        title="Connected Sub-Models Example",
        help_text=help_text,
    )
    print(f"HTML tool generated: {output}")
