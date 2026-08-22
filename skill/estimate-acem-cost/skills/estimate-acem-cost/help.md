estimate-acem-cost — estimate AI-agent build cost (time/$) for a codebase, using the ACEM model

WHAT IT DOES
  (Experimental, unvalidated — see WARNING below.) Estimates what it
  would cost an AI coding agent to build an existing codebase, or
  forecasts token + human-review cost for a planned agentic project,
  using ACEM's Total_Cost = C_LLM + C_HITL + C_Infra model. Inventories
  the codebase into artifact types, assigns token estimates per unit,
  applies Revision Factor and Context Factor corrective multipliers,
  estimates human-in-the-loop review cost via a HITL Intensity Score,
  and runs the bundled acem_calculate.py script (optionally Monte
  Carlo simulation) to produce a p10/p50/p90 cost range.

  WARNING: ACEM has not been validated against real project data, and
  this skill's defaults are cold-start placeholders, not calibrated
  constants. Any figure produced is for exploratory/testing purposes
  only, never a guaranteed estimate.

WHAT IT NEEDS
  - An existing codebase to inventory, or a description of a planned
    project's Use Case/Story/Function Points
  - Python 3 available to run the bundled acem_calculate.py script

USAGE
  /estimate-acem-cost          Estimate cost for the current codebase
                                  or a described planned project
  /estimate-acem-cost --help   Show this message and exit

FLAGS
  --help    Show this help message without making any changes
