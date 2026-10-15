"""Comprehensive validation model exercising all exportable features.

Run:  python comprehensive_validation_export.py
Settings:  Start Date = 2025-01-01, Duration = 120, dt = 1

Features covered (32):
  1.  Nested submodel (2 levels: mid > inner)
  2.  Pool (float)
  3.  Pool (integer, pool_type='int')
  4.  Pool (allow_neg=True)
  5.  External pool + connect
  6.  Parameter
  7.  Step function
  8.  Impulse
  9.  Equation
  10. Deterministic flow
  11. Discrete flow
  12. Step-driven flow
  13. Impulse-driven flow (inflow)
  14. Cross-submodel flow (2 levels deep)
  15. Stochastic flow
  16. Stochastic flow with custom variance
  17. Flow with when guard
  18. Flow with limit (cumulative cap)
  19. Process: wait_delay + pool.add / pool.remove
  20. Process: wait_time
  21. Process: wait_step
  22. Process: wait_date
  23. Process: wait_condition (as start marker)
  24. Process: wait_condition (in body)
  25. Process: wait_message / send_message
  26. Process: wait_any
  27. Process: wait_all
  28. Process: wait_sequence
  29. Sub-process (yield sub_process)
  30. Sub-process .start()
  31. Sub-process .start(wait)
  32. Monte Carlo mode (via stochastic flows on D)

VALUE TABLE FOR MANUAL VERIFICATION
Running this script prints the reference value table from the Python
engine (single run, dt=1, Duration=120, Start Date=2025-01-01). D is
stochastic and varies between runs.

Key process events (verify these timestamps in HTML):
  t=10:  proc_basic fires B.add(10)
  t=20:  proc_wstep fires C.add(15)
  t=25:  proc_all fires B.add(30) (wait_all: helper_a@15 + helper_b@25)
  t=30:  proc_basic fires B.remove(5)
  t=35:  proc_any fires C.add(20) (wait_any: first delay 35)
  t=45:  proc_seq fires C.add(25) (wait_sequence: 10+15+20)
  t=50:  proc_sub starts sub_task(10) -> E.add(10)
  t=55:  sub_task(10) completes -> E.add(10), proc_sub E.add(10),
         sub_task(8).start -> E.add(8)
  t=53:  sub_task(6).start(delay 3) fires -> E.add(6)
  t=58:  sub_task(6) completes -> E.add(6)
  t=60:  sub_task(8) completes -> E.add(8), proc_sender sends msg,
         proc_receiver B.add(7)
  t=80:  impulse +60 at t=75 reflected in A
  t=90:  proc_date fires A.remove(50)
"""

import os
import pycomod as pcm

_HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# Inner submodel (level 2) -- external pool + connect
# ---------------------------------------------------------------------------
class Inner(pcm.Model):
    """Level-2 sub-model with an external pool."""

    def build(self):
        """Define the model elements."""
        P = self.pool(100, pool_type='int')
        Ext = self.pool(external=True)
        Fa = self.flow(lambda: 1, src=P, dest=Ext)
        return locals()


# ---------------------------------------------------------------------------
# Middle submodel (level 1) -- connect wiring + 2-level nesting
# ---------------------------------------------------------------------------
class Middle(pcm.Model):
    """Level-1 sub-model that connects the inner external pool."""

    def build(self):
        """Define the model elements."""
        inner = self.submodel(Inner())
        R = self.pool(0)
        inner.Ext.connect(R)
        self.set_available(locals(), output=(inner, R))


# ---------------------------------------------------------------------------
# Top-level model -- all exportable features
# ---------------------------------------------------------------------------
class Everything(pcm.Model):
    """Top-level model using every exportable feature."""

    def build(self):

        # === NESTED SUBMODEL (2 levels: mid > inner) ===
        """Define the model elements."""
        mid = self.submodel(Middle())

        # === POOLS ===
        A = self.pool(1000)                        # float
        B = self.pool(0, pool_type='int')           # integer
        C = self.pool(0, allow_neg=True)            # allow negative
        D = self.pool(200)                           # stochastic source
        E = self.pool(0)                             # sub-process target

        # === PARAMETER ===
        rate = self.parameter(5)

        # === STEP FUNCTION: 2 -> 8 -> 2 ===
        stp = self.step(values=[2, 8, 2], times=[0, 40, 80], default=2)

        # === IMPULSE: +30 at t=25, +60 at t=75 ===
        imp = self.impulse(values=[30, 60], times=[25, 75])

        # === EQUATION ===
        total = self.equation(lambda: A + B + C)

        # === FLOWS ===
        f_det = self.flow(lambda: rate, src=A, dest=B)
        f_disc = self.flow(lambda: 1, src=A, discrete=True)
        f_step = self.flow(lambda: stp, src=B, dest=C)
        f_imp = self.flow(lambda: imp, dest=A)
        f_cross = self.flow(lambda: 0.5, src=A, dest=mid.inner.P)
        f_stoch = self.flow(lambda: 2, src=D, stochastic=True)
        f_stoch_var = self.flow(
            lambda: 1, src=D, stochastic=True,
            variance=lambda: 0.5,
        )
        f_when = self.flow(lambda: 1, src=A, when=lambda: self.t() <= 50)
        f_limit = self.flow(lambda: 1, src=A, limit=30)

        # === PROCESSES ===

        # wait_delay + wait_time + pool.add / pool.remove
        @self.process(start=self.wait_time(0))
        def proc_basic():
            yield self.wait_delay(10)
            B.add(10)
            yield self.wait_time(30)
            B.remove(5)

        # wait_step (20 steps * dt=1 = t=20)
        @self.process(start=self.wait_time(0))
        def proc_wstep():
            yield self.wait_step(20)
            C.add(15)

        # wait_date (2025-04-01 = t=90 from 2025-01-01)
        @self.process(start=self.wait_time(0))
        def proc_date():
            yield self.wait_date("2025-04-01")
            A.remove(50)

        # wait_condition as start + in body
        @self.process(start=self.wait_condition(lambda: B >= 20))
        def proc_cond():
            C.add(10)
            yield self.wait_condition(lambda: C >= 50)
            C.remove(5)

        # wait_message / send_message
        @self.process(start=self.wait_time(0))
        def proc_sender():
            yield self.wait_time(60)
            self.send_message("sig", 7)

        @self.process(start=self.wait_time(0))
        def proc_receiver():
            val = yield self.wait_message("sig")
            B.add(val)

        # wait_any (fires at first: delay 35)
        @self.process(start=self.wait_time(0))
        def proc_any():
            yield self.wait_any(self.wait_delay(35), self.wait_delay(70))
            C.add(20)

        # wait_all (fires when both done: delay 25)
        @self.process
        def helper_a():
            yield self.wait_delay(15)

        @self.process
        def helper_b():
            yield self.wait_delay(25)

        @self.process(start=self.wait_time(0))
        def proc_all():
            yield self.wait_all(helper_a(), helper_b())
            B.add(30)

        # wait_sequence (10 + 15 + 20 = t=45)
        @self.process(start=self.wait_time(0))
        def proc_seq():
            yield self.wait_sequence(
                self.wait_delay(10),
                self.wait_delay(15),
                self.wait_delay(20),
            )
            C.add(25)

        # Sub-process: yield + .start() + .start(wait)
        @self.process
        def sub_task(n):
            E.add(n)
            yield self.wait_delay(5)
            E.add(n)
            return n

        @self.process(start=self.wait_time(50))
        def proc_sub():
            result = yield sub_task(10)
            E.add(result)
            sub_task(8).start()
            sub_task(6).start(self.wait_delay(3))

        self.set_available(
            locals(),
            output=(A, B, C, total, D, E, mid),
        )


help_text = """
# Comprehensive Validation Model

This model exercises **every feature** supported by the HTML export
pipeline in a single model.

## Verification

Run in **Single** mode with Duration=**120**, Time Step=**1**,
Start Date=**2025-01-01**.

Compare output values against the value table in the Python source
file comments (top of comprehensive_validation_export.py).
"""


if __name__ == "__main__":
    model = Everything()

    init = model.get_init()
    init['run']['date'] = ['2025-01-01']
    init['run']['end'] = [120]
    model.set_init(init)

    # --- Run in Python and print value table ---
    mgr = pcm.RunManager()
    mgr.run(model, duration=120, label='validation')

    out = mgr['validation']['output']
    times = [0, 10, 20, 25, 30, 35, 40, 45, 50, 55, 60, 75, 80, 90, 100, 120]

    print("\nVALUE TABLE (Single Run, dt=1, Duration=120)")
    print("=" * 100)

    pool_names = ['A', 'B', 'C', 'total', 'D', 'E',
                  'mid.inner.P', 'mid.R']
    pool_data = {}
    for name in pool_names:
        parts = name.split('.')
        d = out
        for p in parts:
            d = d[p]
        pool_data[name] = d

    header = "t".rjust(6)
    for name in pool_names:
        header += name.rjust(14)
    print(header)
    print("-" * len(header))

    def find_value_at_time(data, t_target):
        """Return the last value recorded at or before *t_target*."""
        ts = data['times']
        vs = data['values']
        idx = None
        for i, t_val in enumerate(ts):
            if abs(t_val - t_target) < 0.001:
                idx = i
        if idx is None:
            for i, t_val in enumerate(ts):
                if t_val <= t_target + 0.001:
                    idx = i
        if idx is not None and idx < len(vs):
            return vs[idx]
        return None

    for t_target in times:
        row = str(t_target).rjust(6)
        for name in pool_names:
            v = find_value_at_time(pool_data[name], t_target)
            if v is None:
                row += "           N/A"
            elif isinstance(v, float):
                row += "{:14.2f}".format(v)
            else:
                row += "{:>14}".format(v)
        print(row)

    print("=" * 100)
    print(
        "\nNote: D values include stochastic noise -- they vary between runs."
    )
    print(
        "All other values are deterministic and should match HTML exactly.\n"
    )

    # --- Export to HTML ---
    output = pcm.export_to_html(
        model=model,
        filename="comprehensive_validation.html",
        path=_HERE,
        title="Comprehensive Validation",
        help_text=help_text,
    )
    print("HTML tool generated: " + str(output))
