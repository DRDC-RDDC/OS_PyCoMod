"""Wait types validation models for HTML export verification.

Replicas of the models in test.ipynb.

Each model is exported to a separate HTML file.  Run each in the browser
and compare the output graph against the corresponding test.ipynb plot.

Models:
  1. Cond   -- wait_condition (start marker + body)
  2. Msg    -- wait_message / send_message
  3. Ranks  -- wait_sequence / wait_all
  4. Procs  -- wait_date / wait_delay / wait_time / sub-process
  5. Extra  -- wait_step / wait_any (no test.ipynb example)
"""

import os
import pycomod as pcm

_HERE = os.path.dirname(os.path.abspath(__file__))


# =====================================================================
# 1. Cond -- from test.ipynb cell "8ea5fd61"
#    wait_condition as start marker AND in process body
# =====================================================================
class Cond(pcm.Model):
    """Process started by wait_condition."""

    def build(self):
        """Define the model elements."""
        P = self.pool(10)
        F = self.flow(lambda: P * 0.05, src=P, discrete=True)

        @self.process(start=self.wait_condition(lambda: P <= 5))
        def top_up():
            while True:
                P.add(5)
                yield self.wait_condition(lambda: P <= 5)

        self.set_available(locals(), output=(P,))


cond_help = """
# Cond -- wait_condition validation

Replica of the **Cond** model from `test.ipynb`.

## Expected behaviour (dt=1, duration=100)

- **P** starts at 10 and decays via a discrete flow at rate `P*0.05`.
- When P drops to 5 or below, `top_up` fires and adds 5.
- P then decays again until the condition triggers once more.
- Result: **saw-tooth** pattern oscillating roughly between 5 and 10.
"""


# =====================================================================
# 2. Msg -- from test.ipynb cell "af6bbf46"
#    wait_message / send_message
# =====================================================================
class Msg(pcm.Model):
    """Processes communicating with wait_message/send_message."""

    def build(self):
        """Define the model elements."""
        P = self.pool(10)

        @self.process(start=self.wait_time(10))
        def start():
            P.add(5)
            x = yield self.wait_message("wake up!")
            P.remove(x)
            yield self.wait_time(60)
            P.add(15)

        @self.process(start=self.wait_time(0))
        def msg():
            yield self.wait_time(50)
            self.send_message("wake up!", 4)

        self.set_available(locals(), output=(P,))


msg_help = """
# Msg -- wait_message / send_message validation

Replica of the **Msg** model from `test.ipynb`.

## Expected behaviour (dt=1, duration=100)

| Time | Event | P |
|------|-------|---|
| 0 | start | 10 |
| 10 | `start` adds 5 | **15** |
| 10-49 | waiting for message | 15 |
| 50 | `msg` sends "wake up!" (value 4); `start` removes 4 | **11** |
| 60 | `start` adds 15 | **26** |
| 60-100 | no change | 26 |

Graph: step function with jumps at t=10, 50, 60.
"""


# =====================================================================
# 3. Ranks -- from test.ipynb cell "3d8b1f62"
#    wait_sequence / wait_all / sub-process return values
# =====================================================================
class Ranks(pcm.Model):
    """Processes using wait_sequence and wait_all."""

    def build(self):
        """Define the model elements."""
        P1 = self.pool(0, allow_neg=True)
        P2 = self.pool(0, allow_neg=True)
        A = self.pool(0, allow_neg=True)

        @self.process
        def promote():
            yield self.wait_delay(15)

        @self.process
        def attrit():
            yield self.wait_delay(30)

        @self.process(start=self.wait_time(0))
        def enterP1():
            P1.add(1)
            x = yield self.wait_sequence(
                self.wait_delay(5),
                self.wait_all(promote(), attrit()),
                self.wait_delay(10),
            )
            P1.remove(1)

        self.set_available(locals(), output=(P1, P2, A))


ranks_help = """
# Ranks -- wait_sequence / wait_all validation

Replica of the **Ranks** model from `test.ipynb`.

## Expected behaviour (dt=1, duration=100)

The `enterP1` process runs this chain:
1. `wait_delay(5)` -- completes at **t=5**
2. `wait_all(promote(), attrit())` -- promote finishes at t=5+15=20,
   attrit finishes at t=5+30=**35**; wait_all completes when BOTH done = t=35
3. `wait_delay(10)` -- completes at t=35+10=**45**
4. P1.remove(1) at t=45

| Time | P1 |
|------|----|
| 0 | **1** (enterP1 adds 1) |
| 0-44 | 1 |
| 45 | **0** (sequence completes, removes 1) |
| 45-100 | 0 |
"""


# =====================================================================
# 4. Procs -- from test.ipynb cell "793e86c0"
#    wait_date / wait_delay / wait_time / sub-process calls
#    Adjusted: start_date=2025-07-01, duration=120 so wait_date fires
# =====================================================================
class Procs(pcm.Model):
    """Processes using wait_date, wait_delay, wait_time and sub-processes."""

    def build(self):
        """Define the model elements."""
        P = self.pool(100)

        @self.process
        def temp(n, d, s):
            P.remove(n)
            yield self.wait_delay(d)
            P.add(n)
            return int(n * (1 - s))

        @self.process(start=self.wait_time(20))
        def rem():
            P.remove(10)
            yield self.wait_time(30)
            P.remove(3)
            yield self.wait_delay(5)
            P.remove(7)
            yield self.wait_date("2025-10-01")
            P.remove(5)
            yield self.wait_delay(10)
            x = yield temp(22, 5, 0.8)
            P.remove(x)
            yield self.wait_delay(5)
            temp(15, 10, 0.5).start()
            temp(25, 10, 0.7).start(self.wait_delay(5))

        self.set_available(locals(), output=(P,))


procs_help = """
# Procs -- wait_date / sub-process validation

Replica of the **Procs** model from `test.ipynb`, adjusted so `wait_date`
fires within the simulation window.

**Settings**: Start Date = **2025-07-01**, Duration = **120**, dt = 1.

## Expected behaviour (verified in Python)

2025-10-01 is 92 days from 2025-07-01, so `wait_date("2025-10-01")`
fires at **t=92**.

| Time | Event | P |
|------|-------|---|
| 0 | start | 100 |
| 20 | remove 10 | **90** |
| 30 | remove 3 | **87** |
| 35 | remove 7 | **80** |
| 92 | wait_date fires, remove 5 | **75** |
| 102 | `temp(22,5,0.8)` starts: remove 22 | **53** |
| 107 | temp adds 22 back; rem resumes, remove x=4 | **71** |
| 112 | `temp(15,10,0.5).start()`: remove 15 | **56** |
| 117 | `temp(25,10,0.7).start(delay 5)`: remove 25 | **31** |
| 120 | **end of sim** — P = **31** |

(The two temp processes would add back 15 at t=122 and 25 at t=127, but
the sim ends at t=120.)
"""


# =====================================================================
# 5. Extra -- wait_step / wait_sim_start / wait_any
#    No test.ipynb example for these -- new model
# =====================================================================
class Extra(pcm.Model):
    """Processes using wait_step and wait_any."""

    def build(self):
        """Define the model elements."""
        A = self.pool(0)
        B = self.pool(0)

        @self.process(start=self.wait_time(0))
        def p_step():
            yield self.wait_step(10)
            A.add(10)

        @self.process(start=self.wait_time(0))
        def p_any():
            yield self.wait_any(self.wait_delay(30), self.wait_delay(50))
            B.add(15)

        self.set_available(locals(), output=(A, B))


extra_help = """
# Extra -- wait_step / wait_any validation

These wait types have no example in `test.ipynb`.

(`wait_sim_start` is equivalent to `wait_time(t_start)` and only differs
when `t_start != 0`, which is uncommon.  It is translated but not tested here.)

## Expected behaviour (dt=1, duration=100)

| Pool | Wait Type | Fires at | Final |
|------|-----------|----------|-------|
| **A** | `wait_step(10)` = 10 steps × dt=1 = 10 time units | **t=10** | 10 |
| **B** | `wait_any(delay(30), delay(50))` = first to finish | **t=30** | 15 |
"""


# =====================================================================
# Export all models
# =====================================================================
if __name__ == "__main__":
    models = [
        ("Cond", Cond, cond_help, {"date": "2025-01-01", "end": 100}),
        ("Msg", Msg, msg_help, {"date": "2025-01-01", "end": 100}),
        ("Ranks", Ranks, ranks_help, {"date": "2025-01-01", "end": 100}),
        ("Procs", Procs, procs_help, {"date": "2025-07-01", "end": 120}),
        ("Extra", Extra, extra_help, {"date": "2025-01-01", "end": 100}),
    ]

    for name, ModelClass, help_text, params in models:
        model = ModelClass()
        init = model.get_init()
        init['run']['date'] = [params['date']]
        init['run']['end'] = [params['end']]
        model.set_init(init)

        filename = "wait_%s.html" % name.lower()
        try:
            output = pcm.export_to_html(
                model=model,
                filename=filename,
                path=_HERE,
                title="Wait Types -- %s" % name,
                help_text=help_text,
            )
            print("  %s -> %s" % (name, output))
        except Exception as e:
            print("  %s FAILED: %s" % (name, e))

    print("\nDone. Open each HTML in a browser to verify.")
