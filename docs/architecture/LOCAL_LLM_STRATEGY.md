# Local LLM Strategy

## Purpose

This document captures the planned local LLM strategy for AresForge.

AresForge is a local-first, operator-gated AI/operator control-plane. The project will eventually use local and remote model providers to assist with planning, coding, documentation, validation, and agent workflows. This document focuses only on the future local Ollama-backed model strategy.

This is not an implementation document for production-ready LLM dispatch. It is a decision and configuration gameplan so the project has a clear baseline before any broader LLM-backed workflow is promoted beyond prototype behavior.

## Current position

AresForge has an M62 operator-gated local LLM execution prototype. That prototype can call only a configured local provider after explicit gates and remains local-only, advisory-only, prototype-scoped, and non-mutating.

The current strategy scope remains conservative:

- No production-ready LLM dispatch is being added.
- No agent workflow is being connected to Ollama yet.
- No GitHub API usage is being introduced.
- No external network execution is being introduced.
- No cloud LLM access is assumed.
- All future usage must remain local-first and operator-gated until explicitly promoted through validation.

## Local hardware baseline

The initial local Ollama machine has the following hardware:

| Component | Value |
| --- | --- |
| Operating system | Windows |
| System RAM | 48 GB |
| GPU | NVIDIA GTX 1060 |
| VRAM | 6 GB |
| Ollama | Installed and running locally |

This hardware can support larger quantized local models by relying heavily on system RAM and CPU inference. The GTX 1060 with 6 GB VRAM may help partially, but it should not be treated as sufficient to fully load or accelerate the selected models in VRAM.

Speed is not the primary goal for this phase. Practical fit, repeatability, and safe local operation are more important.

## Strategy summary

AresForge will plan around two separate local Ollama models:

| Local alias | Base model | Primary role |
| --- | --- | --- |
| `aresforge-coder-local` | `qwen3-coder:30b-a3b-q4_K_M` | Coding, repo-aware implementation support, debugging, tests, code review |
| `aresforge-reasoner-local` | `qwen3.6:27b` | Architecture, planning, reasoning, decomposition, documentation, validation planning |

The two models are not expected to run at the same time.

AresForge should assume one loaded model at a time unless a future hardware upgrade or validation milestone proves concurrent loading is safe and useful.

## Coding model

### Selected model

`qwen3-coder:30b-a3b-q4_K_M`

### AresForge local alias

`aresforge-coder-local`

### Intended use

The coding model should be used for:

- Code generation
- Bug fixing
- Test creation
- Repo-aware implementation prompts
- Code review
- Patch planning
- Refactoring recommendations
- Local implementation assistance

### Selection rationale

`qwen3-coder:30b-a3b-q4_K_M` is the selected baseline because it is the strongest practical coding-focused local model currently planned for the available hardware.

The 30B-class quantized model should fit in 48 GB system RAM when context is controlled. The machine’s GTX 1060 has only 6 GB VRAM, so most inference may run on CPU and system RAM. That is acceptable for this phase because speed is not the primary priority.

The model should be treated as a local coding assistant, not an autonomous executor. AresForge should use it to generate recommendations, prompts, patches, and review notes that the operator can inspect before applying.

### Initial Modelfile

    FROM qwen3-coder:30b-a3b-q4_K_M
    PARAMETER num_ctx 32768
    PARAMETER temperature 0.2
    PARAMETER top_p 0.9

### Initial context posture

Start with `num_ctx 32768`.

If memory pressure, slow startup, instability, or context allocation failures occur, reduce to:

- `num_ctx 16384`
- then `num_ctx 8192` if needed

Do not assume the full upstream context window is practical on this hardware.

## Reasoning model

### Selected model

`qwen3.6:27b`

### AresForge local alias

`aresforge-reasoner-local`

### Intended use

The reasoning model should be used for:

- Architecture planning
- Task decomposition
- Milestone planning
- Documentation synthesis
- Risk analysis
- Validation planning
- Prompt optimization
- Design review
- Operator handoff generation

### Selection rationale

`qwen3.6:27b` is the selected reasoning and planning companion model because it provides a stronger fit for architecture, decomposition, analysis, and planning while remaining more realistic on 48 GB RAM than larger 35B+ options.

The model should be used to improve project reasoning and documentation quality, not to execute actions automatically. It should provide structured recommendations that remain operator-gated.

### Initial Modelfile

    FROM qwen3.6:27b
    PARAMETER num_ctx 32768
    PARAMETER temperature 0.4
    PARAMETER top_p 0.9

### Initial context posture

Start with `num_ctx 32768`.

If memory pressure, slow startup, instability, or context allocation failures occur, reduce to:

- `num_ctx 16384`
- then `num_ctx 8192` if needed

Do not assume large-context operation is practical by default.

## Ollama runtime posture

AresForge should document and prefer the following Ollama posture for this machine:

| Setting | Planned value | Reason |
| --- | --- | --- |
| `OLLAMA_MAX_LOADED_MODELS` | `1` | Avoid loading both large models at the same time |
| `OLLAMA_NUM_PARALLEL` | `1` | Keep local memory pressure controlled |
| Model context | 16K or 32K initial | Avoid assuming full context capacity |
| Quantization baseline | q4 | Balance model capability with local hardware limits |

## Models explicitly out of scope

The following models are not part of the baseline local plan for this hardware:

| Model | Reason |
| --- | --- |
| `qwen3-coder-next` default q4_K_M | Approximately 52 GB class footprint is too large for a 48 GB RAM baseline once runtime and context overhead are considered |
| `qwen3-coder:480b` | Not realistic for local use on this machine |
| `qwen3.6:35b` | May be possible only in constrained cases, but should not be the planned baseline |
| `qwen3-coder:30b` q8_0 | May be tested later with smaller context, but q4_K_M remains the baseline |

## Operator-gated requirements

Future local LLM integration must preserve AresForge’s local-first control-plane principles.

The local LLM layer must not:

- Automatically execute generated commands
- Automatically write files without operator approval
- Automatically create GitHub issues
- Automatically call GitHub APIs
- Automatically push commits
- Automatically run network actions
- Automatically run the next queue item
- Mutate the repo from local LLM output
- Assume cloud LLM availability
- Treat model output as trusted execution authority

The local LLM layer may initially produce:

- Draft prompts
- Draft plans
- Draft patches
- Draft documentation
- Review notes
- Validation checklists
- Suggested commands for the operator to run manually

## Future integration posture

The first implementation phase should be advisory only.

Recommended progression:

1. Document selected models and setup.
2. Add local model configuration records.
3. Add read-only model readiness checks.
4. Add prompt generation that targets a selected local model.
5. Add operator-approved local inference calls.
6. Store model responses as local artifacts.
7. Add validation and comparison flows.
8. Only later consider limited automation behind explicit operator gates.

## Validation before implementation

Before wiring models into an agent workflow, AresForge should validate:

- Ollama is installed.
- Ollama is running.
- Selected base models are pulled.
- Local aliases exist.
- Only one large model is loaded at a time.
- `ollama ps` shows expected state.
- `ollama list` shows expected model aliases.
- `nvidia-smi` confirms GPU visibility where available.
- Basic prompt-response tests work for both aliases.
- Context settings do not exceed practical memory limits.
- A model can be unloaded or stopped safely.
- AresForge can record model configuration without executing tasks.
- Operator approval is required before any generated output is applied.

## Related documents

- `docs/operator/OLLAMA_LOCAL_SETUP.md`
- `docs/architecture/LLM_TASK_ROUTING_PLAN.md`
- `docs/context/LOCAL_LLM_DECISION_RECORD.md`
