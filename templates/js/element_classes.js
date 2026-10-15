/**
 * @file Model element classes, event queue and process wait helpers.
 */

/**
 * Standard normal random number (Box-Muller).
 * @returns {number}
 */
function _normal_random () {
  let u, v
  do { u = Math.random() } while (u === 0)
  do { v = Math.random() } while (v === 0)
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v)
}

/**
 * Gamma random number (Marsaglia-Tsang).
 * @param {number} alpha - Shape.
 * @param {number} beta - Scale.
 * @returns {number}
 */
function _gamma_random (alpha, beta) {
  if (alpha < 1) {
    return _gamma_random(1 + alpha, beta) * Math.pow(Math.random(), 1 / alpha)
  }
  const d = alpha - 1 / 3
  const c = 1 / Math.sqrt(9 * d)
  while (true) {
    let x, v
    do {
      x = _normal_random()
      v = 1 + c * x
    } while (v <= 0)
    v = v * v * v
    const u = Math.random()
    if (u < 1 - 0.0331 * x * x * x * x) return d * v * beta
    if (Math.log(u) < 0.5 * x * x + d * (1 - v + Math.log(v))) return d * v * beta
  }
}

/**
 * Round like Python round(): ties go to the nearest even integer.
 * @param {number} x
 * @returns {number}
 */
function _py_round (x) {
  const r = Math.round(x)
  return (Math.abs(x % 1) === 0.5) ? 2 * Math.round(x / 2) : r
}

/**
 * Base class for model elements; keeps a value history.
 * @param {string} name
 * @param {number} init_value
 */
class Element {
  constructor (name, init_value) {
    this.name = name
    this.init_value = init_value
    this.value = init_value
    this.value_hist = [init_value]
  }

  /** Restore the initial value and clear history. */
  reset () {
    this.value = this.init_value
    this.value_hist = [this.init_value]
  }

  /** Append the current value to the history. */
  save_hist () {
    this.value_hist.push(this.value)
  }

  /**
   * @returns {number[]} Copy of the value history.
   */
  get_history () {
    return this.value_hist.slice()
  }
}

/**
 * Stock that changes by its inflows and outflows.
 * @param {string} name
 * @param {number} init_value
 * @param {boolean} [allow_negative=false]
 */
class Pool extends Element {
  constructor (name, init_value, allow_negative = false) {
    super(name, init_value)
    this.allow_negative = allow_negative
    this.inflows = []
    this.outflows = []
  }

  /**
   * Apply this step's net flow.
   * @param {number} dt
   */
  update (dt) {
    let delta = 0
    for (const flow of this.inflows) {
      delta += flow.value
    }
    for (const flow of this.outflows) {
      delta -= flow.value
    }
    this.value += delta * dt
    if (!this.allow_negative && this.value < 0) {
      this.value = 0
    }
  }
}

/** Constant model input. */
class Parameter extends Element {
  /** Parameters do not change during a run. */
  update (_dt) {}
}

/**
 * Value computed from other elements each step.
 * @param {string} name
 * @param {number} init_value
 * @param {Function} eq_func - Returns the value.
 */
class Equation extends Element {
  constructor (name, init_value, eq_func) {
    super(name, init_value)
    this.eq_func = eq_func
  }

  /** Evaluate at reset, like Python Equation.reset(). */
  reset () {
    this.init_value = this.eq_func()
    super.reset()
  }

  /** Re-evaluate the equation. */
  update (_dt, _sim_time) {
    this.value = this.eq_func()
  }
}

/**
 * Piecewise-constant value that changes at given times.
 * @param {string} name
 * @param {number[]} values
 * @param {number[]} times
 * @param {number} default_value - Value before the first time.
 */
class Step extends Equation {
  constructor (name, values, times, default_value) {
    super(name, default_value, () => 0)
    const len = Math.min(values.length, times.length)
    this.values = values.slice(0, len)
    this.times = times.slice(0, len)
    this.default_value = default_value
  }

  /** Restore the default value. */
  reset () {
    Element.prototype.reset.call(this)
  }

  /**
   * Use the value of the latest time reached.
   * @param {number} _dt
   * @param {number} sim_time
   */
  update (_dt, sim_time) {
    let idx = -1
    for (let i = 0; i < this.times.length; i++) {
      if (this.times[i] <= sim_time) idx = i
    }
    this.value = idx < 0 ? this.default_value : this.values[idx]
  }
}

/**
 * Value applied only at given times, zero otherwise.
 * @param {string} name
 * @param {number[]} values
 * @param {number[]} times
 */
class Impulse extends Equation {
  constructor (name, values, times) {
    super(name, 0, () => 0)
    const len = Math.min(values.length, times.length)
    this.values = values.slice(0, len)
    this.times = times.slice(0, len)
  }

  /** Restore zero. */
  reset () {
    Element.prototype.reset.call(this)
  }

  /**
   * Sum the impulses falling in this step, as a rate.
   * @param {number} dt
   * @param {number} sim_time
   */
  update (dt, sim_time) {
    let total = 0
    for (let i = 0; i < this.times.length; i++) {
      if (this.times[i] > sim_time - dt && this.times[i] <= sim_time) {
        total += this.values[i]
      }
    }
    this.value = total > 0 ? total / dt : 0
  }
}

/**
 * Parse a comma-separated list of numbers from an input widget.
 * @param {?string} str - Text to parse.
 * @param {number[]} fallback - Used when str is missing or invalid.
 * @returns {number[]}
 */
function _parse_csv (str, fallback) {
  if (str === undefined || str === null) return fallback
  const trimmed = String(str).trim()
  if (trimmed === '') return []
  const parts = trimmed.split(',').map(s => parseFloat(s.trim())).filter(n => !isNaN(n))
  return parts.length > 0 ? parts : fallback
}

/**
 * Rate of transfer between two pools.
 * @param {string} name
 * @param {Function} rate_func
 * @param {?Pool} [src]
 * @param {?Pool} [dest]
 * @param {boolean} [discrete] - Round volumes to integers.
 * @param {boolean} [stochastic] - Add gamma noise in Monte Carlo runs.
 * @param {?Function} [variance]
 * @param {?Function} [when_func] - Guard.
 * @param {?number} [limit] - Cap on total volume.
 */
class Flow extends Element {
  constructor (name, rate_func, src = null, dest = null, discrete = false, stochastic = false, variance = null, when_func = null, limit = null) {
    super(name, 0)
    this.rate_func = rate_func
    this.src = src
    this.dest = dest
    this.discrete = discrete
    this.stochastic = stochastic
    this.variance = variance
    this.when_func = when_func
    this.limit = limit
    this.limit_reached = false
    this.cumulative = 0
    this.rem = 0

    if (src) src.outflows.push(this)
    if (dest) dest.inflows.push(this)
  }

  /**
   * Reset and evaluate once at t=0, like Python Flow.reset().
   * @param {number} [dt=1]
   * @param {boolean} [stochastic_enabled=false]
   */
  reset (dt = 1, stochastic_enabled = false) {
    super.reset()
    this.rem = 0
    this.limit_reached = false
    this.cumulative = 0
    this.value = this._calc(dt, stochastic_enabled) / dt
    this.value_hist[0] = this.value
  }

  /**
   * Compute this step's rate.
   * @param {number} dt
   * @param {boolean} stochastic_enabled
   */
  update (dt, stochastic_enabled) {
    this.value = this._calc(dt, stochastic_enabled) / dt
  }

  /**
   * Volume moved this step (mirrors Python Flow.calc).
   * @param {number} dt
   * @param {boolean} stochastic_enabled
   * @returns {number}
   */
  _calc (dt, stochastic_enabled) {
    if (this.when_func !== null && !this.when_func()) {
      return 0
    }

    let rate = this.rate_func()
    if (this.stochastic && stochastic_enabled && rate > 0) {
      const variance = (this.variance !== null ? this.variance : rate) / dt
      if (variance > 0) {
        const alpha = rate * rate / variance
        const beta = variance / rate
        rate = _gamma_random(alpha, beta)
      }
    }
    let volume = rate * dt
    if (this.discrete) {
      volume += this.rem
      const rounded = _py_round(volume)
      this.rem = volume - rounded
      volume = rounded
    }

    if (this.limit !== null) {
      if (!this.limit_reached) {
        if ((this.cumulative + volume) > this.limit) {
          volume = this.limit - this.cumulative
          this.limit_reached = true
        } else if ((this.cumulative + volume) < -this.limit) {
          volume = -this.limit - this.cumulative
          this.limit_reached = true
        }
        this.cumulative += volume
      } else {
        volume = 0
      }
    }

    return volume
  }
}

/** Event queue ordered by time, then priority. */
class MinHeap {
  constructor () {
    this._data = []
  }

  /**
   * @returns {number} Number of queued events.
   */
  get length () {
    return this._data.length
  }

  /**
   * @returns {SimEvent} Next event without removing it.
   */
  peek () {
    return this._data[0]
  }

  /**
   * @param {SimEvent} item
   */
  push (item) {
    this._data.push(item)
    this._bubbleUp(this._data.length - 1)
  }

  /**
   * @returns {SimEvent} Next event, removed from the queue.
   */
  pop () {
    const top = this._data[0]
    const last = this._data.pop()
    if (this._data.length > 0) {
      this._data[0] = last
      this._sinkDown(0)
    }
    return top
  }

  /** Move item i up to restore heap order. */
  _bubbleUp (i) {
    while (i > 0) {
      const parent = (i - 1) >> 1
      if (this._cmp(this._data[i], this._data[parent]) < 0) {
        [this._data[i], this._data[parent]] = [this._data[parent], this._data[i]]
        i = parent
      } else {
        break
      }
    }
  }

  /** Move item i down to restore heap order. */
  _sinkDown (i) {
    const n = this._data.length
    while (true) {
      let smallest = i
      const left = 2 * i + 1
      const right = 2 * i + 2
      if (left < n && this._cmp(this._data[left], this._data[smallest]) < 0) smallest = left
      if (right < n && this._cmp(this._data[right], this._data[smallest]) < 0) smallest = right
      if (smallest !== i) {
        [this._data[i], this._data[smallest]] = [this._data[smallest], this._data[i]]
        i = smallest
      } else {
        break
      }
    }
  }

  /** Earlier time first; higher priority first on ties. */
  _cmp (a, b) {
    if (a.time !== b.time) return a.time - b.time
    return b.priority - a.priority
  }
}

/**
 * Wait marker: relative delay.
 * @param {number} delay
 */
class Delay {
  constructor (delay) { this.delay = delay }
}

/**
 * Wait marker: absolute simulation time.
 * @param {number} time
 */
class Time {
  constructor (time) { this.time = time }
}

/**
 * Wait marker: calendar date (YYYY-MM-DD).
 * @param {string} dateStr - YYYY-MM-DD.
 */
class DateMarker {
  constructor (dateStr) { this.dateStr = dateStr }
}

/**
 * Wait marker: named message.
 * @param {string} message
 */
class MessageWait {
  constructor (message) { this.message = message }
}

/**
 * Start marker: condition that starts a process.
 * @param {Function} condFn
 */
class ConditionStart {
  constructor (condFn) { this.condFn = condFn }
}

/**
 * Scheduled run of a process generator.
 * @param {Function} routine - Process function or generator.
 * @param {Object} [opts] - time, args, priority, origin, parent.
 */
class SimEvent {
  constructor (routine, { time = null, args = [], priority = 0, origin = null, parent = null } = {}) {
    this.routine = routine
    this.time = time
    this.args = args
    this.priority = priority
    this.origin = origin
    this.parent = parent
    this.finished = false
    this._generator = null
  }

  /**
   * Schedule the event according to what the process yielded.
   * @param {*} y
   */
  _yieldReturn (y) {
    if (y instanceof Delay) {
      this.time = this.parent.sim_time + y.delay
      this.parent.event_queue.push(this)
    } else if (y instanceof Time) {
      this.time = y.time
      this.parent.event_queue.push(this)
    } else if (y instanceof DateMarker) {
      const ctx = this.parent
      const startMs = new Date(ctx.start_date + 'T00:00:00').getTime()
      const targetMs = new Date(y.dateStr + 'T00:00:00').getTime()
      this.time = (targetMs - startMs) / ctx.tunit_ms + ctx.t_start
      ctx.event_queue.push(this)
    } else if (y instanceof MessageWait) {
      const ctx = this.parent
      if (!ctx.messages[y.message]) ctx.messages[y.message] = []
      ctx.messages[y.message].push(this)
    } else if (y instanceof SimEvent) {
      y.time = this.parent.sim_time
      y.origin = this
      y.run()
    }
  }

  /**
   * Continue the process, passing in a value.
   * @param {*} value
   */
  resume (value) {
    if (this.finished) return
    try {
      const { value: y, done } = this._generator.next(value)
      if (done) {
        this.finished = true
        if (this.origin) this.origin.resume(y)
      } else {
        this._yieldReturn(y)
      }
    } catch (e) {
      this.finished = true
      console.error('Process error:', e)
    }
  }

  /** Start or continue the process. */
  run () {
    if (this.finished) return

    if (this._generator) {
      this.resume(undefined)
      return
    }

    const result = this.routine(...this.args)

    if (result && typeof result.next === 'function') {
      this._generator = result
      try {
        const { value: y, done } = this._generator.next()
        if (done) {
          this.finished = true
          if (this.origin) this.origin.resume(y)
        } else {
          this._yieldReturn(y)
        }
      } catch (e) {
        this.finished = true
        console.error('Process error:', e)
      }
    } else {
      this.finished = true
      if (this.origin) this.origin.resume(result)
    }
  }

  /**
   * Start now, or schedule by a wait marker.
   * @param {Delay|Time|DateMarker} [startMarker]
   */
  start (startMarker) {
    if (startMarker) {
      if (startMarker instanceof Delay) {
        this.time = this.parent.sim_time + startMarker.delay
        this.parent.event_queue.push(this)
      } else if (startMarker instanceof Time) {
        this.time = startMarker.time
        this.parent.event_queue.push(this)
      } else if (startMarker instanceof DateMarker) {
        const ctx = this.parent
        const startMs = new Date(ctx.start_date + 'T00:00:00').getTime()
        const targetMs = new Date(startMarker.dateStr + 'T00:00:00').getTime()
        this.time = (targetMs - startMs) / ctx.tunit_ms + ctx.t_start
        ctx.event_queue.push(this)
      }
    } else {
      this.run()
    }
  }
}

/**
 * Process defined in the model; schedules its start.
 * @param {Function} routine
 * @param {Object} [opts] - start, priority, parent.
 */
class Process {
  constructor (routine, { start = null, priority = 0, parent = null } = {}) {
    this.routine = routine
    this._start = start
    this.priority = priority
    this.parent = parent
  }

  /** Schedule the process start for a new run. */
  reset () {
    if (this._start) {
      if (this._start instanceof ConditionStart) {
        const self = this
        const wrapper = new SimEvent(function * () {
          while (true) {
            yield wait_step(1)
            if (self._start.condFn()) break
          }
          const procEv = new SimEvent(self.routine, {
            time: self.parent.sim_time,
            priority: self.priority,
            parent: self.parent
          })
          yield procEv
        }, { time: this.parent.sim_time, priority: this.priority, parent: this.parent })
        this.parent.event_queue.push(wrapper)
      } else {
        const ev = new SimEvent(this.routine, {
          time: 0,
          priority: this.priority,
          parent: this.parent
        })
        if (this._start instanceof Delay) {
          ev.time = this.parent.sim_time + this._start.delay
        } else if (this._start instanceof Time) {
          ev.time = this._start.time
        } else if (this._start instanceof DateMarker) {
          const ctx = this.parent
          const startMs = new Date(ctx.start_date + 'T00:00:00').getTime()
          const targetMs = new Date(this._start.dateStr + 'T00:00:00').getTime()
          ev.time = (targetMs - startMs) / ctx.tunit_ms + ctx.t_start
        }
        this.parent.event_queue.push(ev)
      }
    }
  }

  /**
   * Create an event to run the process as a sub-process.
   * @returns {SimEvent}
   */
  call (...args) {
    return new SimEvent(this.routine, {
      time: this.parent.sim_time,
      args,
      priority: this.priority,
      parent: this.parent
    })
  }
}

// Reassigned by run_simulation() in simulation_loop.js, so it must stay `let`
let sim_context = null // eslint-disable-line prefer-const

/**
 * Wait for a relative delay.
 * @param {number} d
 * @returns {Delay}
 */
function wait_delay (d) { return new Delay(d) }
/**
 * Wait until an absolute time.
 * @param {number} t
 * @returns {Time}
 */
function wait_time (t) { return new Time(t) }
/**
 * Wait for n simulation steps.
 * @param {number} [n=1]
 * @returns {Delay}
 */
function wait_step (n) { return new Delay((n || 1) * sim_context.dt) }
/**
 * Wait until the simulation start time.
 * @returns {Time}
 */
function wait_sim_start () { return new Time(sim_context.t_start) }
/**
 * Wait until a calendar date.
 * @param {string} dateStr - YYYY-MM-DD.
 * @returns {DateMarker}
 */
function wait_date (dateStr) { return new DateMarker(dateStr) }

/**
 * Wait until condFn() is true, checked every step.
 * @param {Function} condFn
 * @returns {SimEvent}
 */
function wait_condition (condFn) {
  return new SimEvent(function * () {
    while (true) {
      yield wait_step(1)
      if (condFn()) break
    }
  }, { time: sim_context.sim_time, parent: sim_context })
}

/**
 * Wait for a message; resumes with the sent value.
 * @param {string} msg
 * @returns {SimEvent}
 */
function wait_message (msg) {
  const ev = new SimEvent(function * () {
    if (!sim_context.messages[msg]) sim_context.messages[msg] = []
    sim_context.messages[msg].push(ev)
    const val = yield
    return val
  }, { time: sim_context.sim_time, parent: sim_context })
  return ev
}

/**
 * Send a message to all processes waiting for it.
 * @param {string} msg
 * @param {*} [value]
 */
function send_message (msg, value) {
  if (sim_context.messages && sim_context.messages[msg]) {
    const events = sim_context.messages[msg]
    delete sim_context.messages[msg]
    for (const ev of events) {
      ev.resume(value !== undefined ? value : null)
    }
  }
}

/**
 * Wrap a wait marker in an event so it can be combined.
 * @param {Object} marker
 * @param {Object} parent - Simulation context.
 * @returns {SimEvent}
 */
function _wrapWaitMarker (marker, parent) {
  return new SimEvent(function * () {
    yield marker
  }, { time: parent.sim_time, parent })
}

/**
 * Wait for the first of several waits to finish.
 * @returns {SimEvent}
 */
function wait_any () {
  const args = Array.from(arguments)
  const parent = sim_context
  const subEvents = []
  const ev = new SimEvent(function * () {
    for (const arg of args) {
      let sub = arg
      if (!(sub instanceof SimEvent)) sub = _wrapWaitMarker(sub, parent)
      sub.origin = ev
      subEvents.push(sub)
      sub.time = parent.sim_time
      sub.run()
    }
    const result = yield
    for (const sub of subEvents) {
      if (sub.origin === ev) sub.origin = null
    }
    return result
  }, { time: parent.sim_time, parent })
  return ev
}

/**
 * Wait for all of several waits to finish.
 * @returns {SimEvent}
 */
function wait_all () {
  const args = Array.from(arguments)
  const parent = sim_context
  const ev = new SimEvent(function * () {
    for (const arg of args) {
      let sub = arg
      if (!(sub instanceof SimEvent)) sub = _wrapWaitMarker(sub, parent)
      sub.origin = ev
      sub.time = parent.sim_time
      sub.run()
    }
    const results = []
    for (let i = 0; i < args.length; i++) {
      const val = yield
      results.push(val)
    }
    return results
  }, { time: parent.sim_time, parent })
  return ev
}

/**
 * Run several waits one after another.
 * @returns {SimEvent}
 */
function wait_sequence () {
  const args = Array.from(arguments)
  const parent = sim_context
  const ev = new SimEvent(function * () {
    const results = []
    for (const arg of args) {
      let sub = arg
      if (!(sub instanceof SimEvent)) sub = _wrapWaitMarker(sub, parent)
      const val = yield sub
      results.push(val)
    }
    return results
  }, { time: parent.sim_time, parent })
  return ev
}
