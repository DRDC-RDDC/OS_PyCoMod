function initialize_elements (inputs) {
  const elements = {}

  {{POOL_INITIALIZATION}}

  {{PARAMETER_INITIALIZATION}}

  {{EQUATION_INITIALIZATION}}

  {{FLOW_INITIALIZATION}}

  return elements
}

function initialize_processes (sim_context) {
  const elements = sim_context.elements
  const processes = []

  {{PROCESS_INITIALIZATION}}

  return processes
}
