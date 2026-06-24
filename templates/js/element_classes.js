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
