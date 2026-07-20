// ============================================================================
// Element Classes
// ============================================================================

// --- Stochastic sampling utilities ---

function _normal_random() {
    let u, v;
    do { u = Math.random(); } while (u === 0);
    do { v = Math.random(); } while (v === 0);
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

function _gamma_random(alpha, beta) {
    // Marsaglia-Tsang method
    if (alpha < 1) {
        return _gamma_random(1 + alpha, beta) * Math.pow(Math.random(), 1 / alpha);
    }
    const d = alpha - 1 / 3;
    const c = 1 / Math.sqrt(9 * d);
    while (true) {
        let x, v;
        do {
            x = _normal_random();
            v = 1 + c * x;
        } while (v <= 0);
        v = v * v * v;
        const u = Math.random();
        if (u < 1 - 0.0331 * x * x * x * x) return d * v * beta;
        if (Math.log(u) < 0.5 * x * x + d * (1 - v + Math.log(v))) return d * v * beta;
    }
}

class Element {
    constructor(name, init_value) {
        this.name = name;
        this.init_value = init_value;
        this.value = init_value;
        this.value_hist = [init_value];
    }

    reset() {
        this.value = this.init_value;
        this.value_hist = [this.init_value];
    }

    save_hist() {
        this.value_hist.push(this.value);
    }

    get_history() {
        return this.value_hist.slice();
    }
}

class Pool extends Element {
    constructor(name, init_value, allow_negative = false) {
        super(name, init_value);
        this.allow_negative = allow_negative;
        this.inflows = [];
        this.outflows = [];
    }

    update(dt) {
        let delta = 0;
        for (const flow of this.inflows) {
            delta += flow.value;
        }
        for (const flow of this.outflows) {
            delta -= flow.value;
        }
        this.value += delta * dt;
        if (!this.allow_negative && this.value < 0) {
            this.value = 0;
        }
    }
}

class Parameter extends Element {
    constructor(name, init_value) {
        super(name, init_value);
    }

    update(_dt) {}
}

class Equation extends Element {
    constructor(name, init_value, eq_func) {
        super(name, init_value);
        this.eq_func = eq_func;
    }

    update(_dt, _sim_time) {
        this.value = this.eq_func();
    }
}

class Step extends Equation {
    constructor(name, values, times, default_value) {
        super(name, default_value, () => 0);
        const len = Math.min(values.length, times.length);
        this.values = values.slice(0, len);
        this.times = times.slice(0, len);
        this.default_value = default_value;
    }

    update(_dt, sim_time) {
        let idx = -1;
        for (let i = 0; i < this.times.length; i++) {
            if (this.times[i] <= sim_time) idx = i;
        }
        this.value = idx < 0 ? this.default_value : this.values[idx];
    }
}

class Impulse extends Equation {
    constructor(name, values, times) {
        super(name, 0, () => 0);
        const len = Math.min(values.length, times.length);
        this.values = values.slice(0, len);
        this.times = times.slice(0, len);
    }

    update(dt, sim_time) {
        let total = 0;
        for (let i = 0; i < this.times.length; i++) {
            if (this.times[i] > sim_time - dt && this.times[i] <= sim_time) {
                total += this.values[i];
            }
        }
        this.value = total > 0 ? total / dt : 0;
    }
}

function _parse_csv(str, fallback) {
    if (str === undefined || str === null) return fallback;
    const trimmed = String(str).trim();
    if (trimmed === '') return [];
    const parts = trimmed.split(',').map(s => parseFloat(s.trim())).filter(n => !isNaN(n));
    return parts.length > 0 ? parts : fallback;
}

class Flow extends Element {
    constructor(name, rate_func, src = null, dest = null, discrete = false, stochastic = false, variance = null) {
        super(name, 0);
        this.rate_func = rate_func;
        this.src = src;
        this.dest = dest;
        this.discrete = discrete;
        this.stochastic = stochastic;
        this.variance = variance;  // volume variance (per step); null → Poisson (volume var = mean·dt)
        this.rem = 0;              // fractional remainder carried forward for discrete flows

        if (src) src.outflows.push(this);
        if (dest) dest.inflows.push(this);
    }

    reset() {
        super.reset();
        this.rem = 0;
    }

    update(dt, stochastic_enabled) {
        let rate = this.rate_func();
        if (this.stochastic && stochastic_enabled && rate > 0) {
            const variance = (this.variance !== null ? this.variance : rate) / dt;
            if (variance > 0) {
                const alpha = rate * rate / variance;
                const beta = variance / rate;
                rate = _gamma_random(alpha, beta);
            }
        }
        if (this.discrete) {
            // Convert to volume, round to integer (banking the remainder for the
            // next step so fractional parts accumulate rather than disappear)
            let volume = Math.max(0, rate * dt + this.rem);
            const rounded = Math.round(volume);
            this.rem = volume - rounded;
            rate = rounded / dt;
        }
        this.value = rate;
    }
}

// ============================================================================
// Process / Event System
// ============================================================================

// --- Min-heap (JS has no built-in heapq) ---

class MinHeap {
    constructor() {
        this._data = [];
    }

    get length() {
        return this._data.length;
    }

    peek() {
        return this._data[0];
    }

    push(item) {
        this._data.push(item);
        this._bubbleUp(this._data.length - 1);
    }

    pop() {
        const top = this._data[0];
        const last = this._data.pop();
        if (this._data.length > 0) {
            this._data[0] = last;
            this._sinkDown(0);
        }
        return top;
    }

    _bubbleUp(i) {
        while (i > 0) {
            const parent = (i - 1) >> 1;
            if (this._cmp(this._data[i], this._data[parent]) < 0) {
                [this._data[i], this._data[parent]] = [this._data[parent], this._data[i]];
                i = parent;
            } else {
                break;
            }
        }
    }

    _sinkDown(i) {
        const n = this._data.length;
        while (true) {
            let smallest = i;
            const left = 2 * i + 1;
            const right = 2 * i + 2;
            if (left < n && this._cmp(this._data[left], this._data[smallest]) < 0) smallest = left;
            if (right < n && this._cmp(this._data[right], this._data[smallest]) < 0) smallest = right;
            if (smallest !== i) {
                [this._data[i], this._data[smallest]] = [this._data[smallest], this._data[i]];
                i = smallest;
            } else {
                break;
            }
        }
    }

    _cmp(a, b) {
        if (a.time !== b.time) return a.time - b.time;
        return b.priority - a.priority;
    }
}

// --- Delay / Time marker objects (what yield returns) ---

class Delay {
    constructor(delay) {
        this.delay = delay;
    }
}

class Time {
    constructor(time) {
        this.time = time;
    }
}

// --- Event: wraps a generator and manages its lifecycle on the heap ---

class SimEvent {
    constructor(routine, { time = null, args = [], priority = 0, origin = null, parent = null } = {}) {
        this.routine = routine;
        this.time = time;
        this.args = args;
        this.priority = priority;
        this.origin = origin;
        this.parent = parent;
        this.finished = false;
        this._generator = null;
    }

    _yieldReturn(y) {
        if (y instanceof Delay) {
            this.time = this.parent.sim_time + y.delay;
            this.parent.event_queue.push(this);
        } else if (y instanceof Time) {
            this.time = y.time;
            this.parent.event_queue.push(this);
        } else if (y instanceof SimEvent) {
            y.time = this.parent.sim_time;
            y.origin = this;
            y.run();
        }
    }

    resume(value) {
        if (this.finished) return;
        try {
            const { value: y, done } = this._generator.next(value);
            if (done) {
                this.finished = true;
                if (this.origin) this.origin.resume(y);
            } else {
                this._yieldReturn(y);
            }
        } catch (e) {
            this.finished = true;
            console.error('Process error:', e);
        }
    }

    run() {
        if (this.finished) return;

        if (this._generator) {
            this.resume(undefined);
            return;
        }

        const result = this.routine(...this.args);

        if (result && typeof result.next === 'function') {
            this._generator = result;
            try {
                const { value: y, done } = this._generator.next();
                if (done) {
                    this.finished = true;
                    if (this.origin) this.origin.resume(y);
                } else {
                    this._yieldReturn(y);
                }
            } catch (e) {
                this.finished = true;
                console.error('Process error:', e);
            }
        } else {
            this.finished = true;
            if (this.origin) this.origin.resume(result);
        }
    }

    start(startMarker) {
        if (startMarker) {
            if (startMarker instanceof Delay) {
                this.time = this.parent.sim_time + startMarker.delay;
                this.parent.event_queue.push(this);
            } else if (startMarker instanceof Time) {
                this.time = startMarker.time;
                this.parent.event_queue.push(this);
            }
        } else {
            this.run();
        }
    }
}

// --- Process: template for creating events (mirrors Python Process) ---

class Process {
    constructor(routine, { start = null, priority = 0, parent = null } = {}) {
        this.routine = routine;
        this._start = start;
        this.priority = priority;
        this.parent = parent;
    }

    reset() {
        if (this._start) {
            const ev = new SimEvent(this.routine, {
                time: 0,
                priority: this.priority,
                parent: this.parent,
            });
            if (this._start instanceof Delay) {
                ev.time = this.parent.sim_time + this._start.delay;
            } else if (this._start instanceof Time) {
                ev.time = this._start.time;
            }
            this.parent.event_queue.push(ev);
        }
    }

    call(...args) {
        return new SimEvent(this.routine, {
            time: this.parent.sim_time,
            args: args,
            priority: this.priority,
            parent: this.parent,
        });
    }
}

// --- Helper: wait_delay / wait_time (used inside generator processes) ---

function wait_delay(d) {
    return new Delay(d);
}

function wait_time(t) {
    return new Time(t);
}
