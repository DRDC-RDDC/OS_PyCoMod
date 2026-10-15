/**
 * @file Model-specific element and process creation (filled in by Python).
 */

/**
 * Create the model elements using the current inputs.
 * @param {Object} inputs
 * @returns {Object} Elements by name.
 */
function initialize_elements (inputs) {
  const elements = {}

  {{POOL_INITIALIZATION}}

  {{PARAMETER_INITIALIZATION}}

  {{EQUATION_INITIALIZATION}}

  {{FLOW_INITIALIZATION}}

  return elements
}

/**
 * Create the model processes.
 * @param {Object} sim_context
 * @returns {Process[]}
 */
function initialize_processes (sim_context) {
  const elements = sim_context.elements
  const processes = []

  {{PROCESS_INITIALIZATION}}

  return processes
}
