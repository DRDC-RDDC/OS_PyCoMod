// ============================================================================
// Element Classes
// ============================================================================

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

    update(dt) {}
}

class Equation extends Element {
    constructor(name, init_value, eq_func) {
        super(name, init_value);
        this.eq_func = eq_func;
    }

    update(dt) {
        this.value = this.eq_func();
    }
}

class Flow extends Element {
    constructor(name, rate_func, src = null, dest = null, discrete = false) {
        super(name, 0);
        this.rate_func = rate_func;
        this.src = src;
        this.dest = dest;
        this.discrete = discrete;

        if (src) src.outflows.push(this);
        if (dest) dest.inflows.push(this);
    }

    update(dt) {
        let rate = this.rate_func();
        if (this.discrete) {
            rate = Math.max(0, rate);
        }
        this.value = rate;
    }
}
