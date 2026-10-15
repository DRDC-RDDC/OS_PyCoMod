"""Shared test fixtures: lightweight pycomod models for the export tests."""

import pytest
import pycomod as pcm


class SimpleSIR(pcm.Model):
    """Minimal SIR model with equations, parameters, flows."""

    def build(self):
        """Define the model elements."""
        S = self.pool(950)
        I = self.pool(50)
        R = self.pool(0)

        N = self.equation(lambda: S + I + R)

        b = self.parameter(0.3)
        g = self.parameter(0.1)

        Fsi = self.flow(lambda: b * S * I / N, src=S, dest=I, stochastic=True)
        Fir = self.flow(lambda: g * I, src=I, dest=R, stochastic=True)

        self.set_available(locals(), output=(S, I, R, N))


class SIRWithStepImpulse(pcm.Model):
    """SIR model with step and impulse equations."""

    def build(self):
        """Define the model elements."""
        S = self.pool(950)
        I = self.pool(50)
        R = self.pool(0)

        N = self.equation(lambda: S + I + R)
        g = self.parameter(0.1)

        b = self.step(values=[0.3, 0.05, 0.2], times=[0, 30, 60], default=0.3)
        vax = self.impulse(values=[50, 100], times=[20, 45])

        Fsi = self.flow(lambda: b * S * I / N, src=S, dest=I)
        Fir = self.flow(lambda: g * I, src=I, dest=R)
        Fvax = self.flow(lambda: vax, src=S, dest=R)

        self.set_available(locals(), output=(S, I, R, N))


class InnerSIR(pcm.Model):
    """SIR sub-model with configurable initial values."""

    def build(self, s0=950, i0=50, r0=0):
        """Define the model elements."""
        S = self.pool(s0)
        I = self.pool(i0)
        R = self.pool(0)
        N = self.equation(lambda: S + I + R)
        b = self.parameter(0.3)
        g = self.parameter(0.1)
        Fsi = self.flow(lambda: b * S * I / N, src=S, dest=I)
        Fir = self.flow(lambda: g * I, src=I, dest=R)
        self.set_available(locals(), output=(S, I, R))


class TwoRegionSIR(pcm.Model):
    """Model with two sub-models."""

    def build(self):
        """Define the model elements."""
        r1 = self.submodel(InnerSIR(950, 50, 0))
        r2 = self.submodel(InnerSIR(950, 50, 0))
        migration_rate = self.parameter(0.01)
        F_r1_to_r2 = self.flow(
            lambda: migration_rate * r1.I, src=r1.I, dest=r2.I
        )
        self.set_available(locals(), output=(r1, r2))


class ProcessModel(pcm.Model):
    """Model with process (discrete event) definitions."""

    def build(self):
        """Define the model elements."""
        W = self.pool(100)
        C = self.pool(0)
        P = self.pool(0)
        F = self.pool(0)

        duration = self.parameter(5)
        passRate = self.parameter(0.8)
        maxLoad = self.parameter(30)
        minLoad = self.parameter(10)
        startInt = self.parameter(10)

        @self.process
        def attend(n):
            W.remove(n)
            C.add(n)
            yield self.wait_delay(duration)
            C.remove(n)
            np_val = round(n * passRate)
            P.add(np_val)
            F.add(n - np_val)

        @self.process(start=self.wait_time(2))
        def scheduler():
            while True:
                if W >= minLoad:
                    n = min(int(W), maxLoad)
                    attend(n).start()
                yield self.wait_delay(startInt)

        self.set_available(locals(), output=(W, C, P, F))


class MinimalModel(pcm.Model):
    """Single pool + parameter, simplest possible model."""

    def build(self):
        """Define the model elements."""
        X = self.pool(10)
        r = self.parameter(0.5)
        Fx = self.flow(lambda: r * X, src=X)
        self.set_available(locals(), output=(X,))


class WaitTypesModel(pcm.Model):
    """Model exercising the wait types.

    Covers date start, condition start, wait_step,
    wait_message/send_message, wait_any, wait_all and wait_sequence.
    """

    def build(self):
        """Define the model elements."""
        A = self.pool(100)
        B = self.pool(0)

        f_drain = self.flow(lambda: 1, src=A)

        @self.process(start=self.wait_date("2025-03-01"))
        def p_date():
            B.add(10)

        @self.process(start=self.wait_condition(lambda: A <= 50))
        def p_cond():
            B.add(20)

        @self.process(start=self.wait_time(0))
        def p_waits():
            yield self.wait_step(5)
            yield self.wait_delay(10)
            self.send_message("go", 42)

        @self.process(start=self.wait_time(0))
        def p_recv():
            val = yield self.wait_message("go")
            B.add(val)

        @self.process(start=self.wait_time(0))
        def p_composite():
            yield self.wait_any(self.wait_delay(10), self.wait_delay(20))
            yield self.wait_all(self.wait_delay(5), self.wait_delay(8))
            yield self.wait_sequence(self.wait_delay(3), self.wait_delay(4))

        self.set_available(locals(), output=(A, B))


@pytest.fixture
def wait_types_model():
    """Return a built WaitTypesModel."""
    m = WaitTypesModel()
    init = m.get_init()
    init['run']['date'] = ['2025-01-01']
    init['run']['end'] = [100]
    m.set_init(init)
    return m


@pytest.fixture
def simple_sir():
    """Return a built SimpleSIR model."""
    return SimpleSIR()


@pytest.fixture
def sir_step_impulse():
    """Return a built SIRWithStepImpulse model."""
    return SIRWithStepImpulse()


@pytest.fixture
def two_region_sir():
    """Return a built TwoRegionSIR model."""
    return TwoRegionSIR()


@pytest.fixture
def process_model():
    """Return a built ProcessModel."""
    return ProcessModel()


@pytest.fixture
def minimal_model():
    """Return a built MinimalModel."""
    return MinimalModel()
