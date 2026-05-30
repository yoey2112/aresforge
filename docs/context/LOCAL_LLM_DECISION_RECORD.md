# Local LLM Decision Record

## Status

Accepted for future implementation planning and M75 source-of-truth reconciliation.

## Date

2026-05-29

## Decision

AresForge will plan for two separate local Ollama models:

| Role | AresForge alias | Base model |
| --- | --- | --- |
| Coding | `aresforge-coder-local` | `qwen3-coder:30b-a3b-q4_K_M` |
| Reasoning and planning | `aresforge-reasoner-local` | `qwen3.6:27b` |

The models are not intended to run concurrently on the current hardware.

## Context

AresForge is a local-first, document-driven, operator-gated AI/operator control-plane.

The project has an M62 operator-gated local LLM execution prototype, but no production-ready LLM dispatch. This decision record captures the future local Ollama model baseline so that installation, configuration, validation, and task routing can be planned before broader LLM integration is promoted beyond prototype behavior.

The current local machine has:

| Component | Value |
| --- | --- |
| OS | Windows |
| System RAM | 48 GB |
| GPU | NVIDIA GTX 1060 |
| VRAM | 6 GB |
| Ollama | Installed and running locally |

The machine can accept slower CPU/system-RAM-heavy inference. Speed is not the primary priority for this decision.

The GTX 1060 should not be treated as sufficient to fully load these models in VRAM. Most inference may run on CPU and system RAM.

## Selected coding model

`qwen3-coder:30b-a3b-q4_K_M`

AresForge alias:

    aresforge-coder-local

Rationale:

- Coding-focused model.
- Strong practical baseline for local coding support.
- 30B-class q4 quantized model is more realistic for 48 GB RAM than larger options.
- Suitable for code generation, debugging, test creation, code review, and patch planning.
- Expected to fit in system RAM when context is controlled.

Initial Modelfile:

    FROM qwen3-coder:30b-a3b-q4_K_M
    PARAMETER num_ctx 32768
    PARAMETER temperature 0.2
    PARAMETER top_p 0.9

## Selected reasoning model

`qwen3.6:27b`

AresForge alias:

    aresforge-reasoner-local

Rationale:

- Stronger fit for reasoning, planning, decomposition, and documentation support.
- More realistic on 48 GB RAM than 35B+ options.
- Suitable for architecture planning, milestone design, validation planning, risk analysis, summarization, and prompt optimization.
- Expected to fit in system RAM when context is controlled.

Initial Modelfile:

    FROM qwen3.6:27b
    PARAMETER num_ctx 32768
    PARAMETER temperature 0.4
    PARAMETER top_p 0.9

## Constraints

The decision has the following constraints:

- Do not run both selected models at the same time on the baseline machine.
- Prefer `OLLAMA_MAX_LOADED_MODELS=1`.
- Prefer `OLLAMA_NUM_PARALLEL=1`.
- Do not assume full 256K context is practical on this hardware.
- Start with 16K or 32K context.
- Reduce to 8K or 16K if memory pressure occurs.
- Treat q4 quantization as the baseline.
- Do not assume cloud LLM access.
- Do not expand beyond the M62 local-only, advisory-only, operator-gated prototype without a future approved milestone.
- Preserve operator approval before applying model output.

## Consequences

This decision creates the following consequences:

- Slower inference is expected.
- Most inference may run through CPU and system RAM.
- Context must be controlled.
- q4 quantization is the baseline.
- Larger models are deferred.
- Routing must be explicit and visible.
- AresForge must validate local readiness before wiring model calls into workflows.
- Initial LLM usage should be advisory and operator-gated.
- Automation should only be considered after local inference, artifact capture, validation, and approval flows are proven.

## Models deferred or out of scope

| Model | Decision |
| --- | --- |
| `qwen3-coder-next` default q4_K_M | Out of scope for this hardware baseline because expected footprint is too large once overhead and context are considered |
| `qwen3-coder:480b` | Out of scope for local execution |
| `qwen3.6:35b` | Deferred; not the baseline |
| `qwen3-coder:30b` q8_0 | Deferred; may be tested later with smaller context |

## Validation required before implementation

Before any AresForge workflow calls Ollama, validate:

- Ollama installation.
- Model availability.
- Alias creation.
- One-model-at-a-time runtime behavior.
- Basic prompt-response behavior.
- Memory behavior at 32K context.
- Memory behavior at 16K fallback context if needed.
- Operator approval flow for model invocation.
- Local artifact storage for prompts and responses.
- No automatic command execution.
- No automatic file modification.
- No GitHub API usage.
- No network execution.
- No automatic next-item execution.
- No repository mutation from local LLM output.

## Related documents

- `docs/architecture/LOCAL_LLM_STRATEGY.md`
- `docs/operator/OLLAMA_LOCAL_SETUP.md`
- `docs/architecture/LLM_TASK_ROUTING_PLAN.md`
