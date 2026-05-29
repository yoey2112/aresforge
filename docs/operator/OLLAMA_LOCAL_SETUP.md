# Ollama Local Setup

## Purpose

This document provides the Windows PowerShell setup and validation steps for the planned local Ollama models used by AresForge.

This is a setup and validation guide only. It does not wire Ollama into live AresForge workflows.

## Local model plan

| AresForge alias | Base model | Purpose |
| --- | --- | --- |
| `aresforge-coder-local` | `qwen3-coder:30b-a3b-q4_K_M` | Coding and implementation support |
| `aresforge-reasoner-local` | `qwen3.6:27b` | Reasoning, planning, and documentation support |

The models are not intended to run concurrently on the current hardware.

## Hardware baseline

| Component | Value |
| --- | --- |
| OS | Windows |
| RAM | 48 GB |
| GPU | NVIDIA GTX 1060 |
| VRAM | 6 GB |

The GTX 1060 should not be treated as able to fully run these models in VRAM. Most inference may run through CPU and system RAM.

## Open PowerShell

Open Windows PowerShell.

Set the working location to the AresForge repo:

    Set-Location "C:\Projects\aresforge"

## Check Ollama install

Check whether Ollama is available:

    ollama --version

If the command fails, Ollama is not available in the current shell path.

## Check installed models

List installed Ollama models:

    ollama list

Confirm whether the selected base models or AresForge aliases already exist.

## Check running models

Show currently loaded or running models:

    ollama ps

AresForge’s baseline posture is one loaded large model at a time.

## Check GPU visibility

Check whether the NVIDIA GPU is visible:

    nvidia-smi

If `nvidia-smi` is unavailable, GPU visibility should be treated as unconfirmed. The selected models may still run through CPU and system RAM, but performance may be slower.

## Pull the coding model

Pull the selected coding model:

    ollama pull qwen3-coder:30b-a3b-q4_K_M

Run a direct smoke test against the base model:

    ollama run qwen3-coder:30b-a3b-q4_K_M

At the prompt, enter:

    Reply with one sentence confirming you are available for local coding assistance.

Exit the model chat after the response.

## Pull the reasoning model

Pull the selected reasoning model:

    ollama pull qwen3.6:27b

Run a direct smoke test against the base model:

    ollama run qwen3.6:27b

At the prompt, enter:

    Reply with one sentence confirming you are available for local architecture and planning assistance.

Exit the model chat after the response.

## Create the coding Modelfile

Create the coding Modelfile:

    Set-Content -Path ".\Modelfile.aresforge-coder-local" -Value @(
        "FROM qwen3-coder:30b-a3b-q4_K_M",
        "PARAMETER num_ctx 32768",
        "PARAMETER temperature 0.2",
        "PARAMETER top_p 0.9"
    )

Review the file:

    Get-Content ".\Modelfile.aresforge-coder-local"

Create the local coding alias:

    ollama create aresforge-coder-local -f ".\Modelfile.aresforge-coder-local"

Confirm it exists:

    ollama list

## Create the reasoning Modelfile

Create the reasoning Modelfile:

    Set-Content -Path ".\Modelfile.aresforge-reasoner-local" -Value @(
        "FROM qwen3.6:27b",
        "PARAMETER num_ctx 32768",
        "PARAMETER temperature 0.4",
        "PARAMETER top_p 0.9"
    )

Review the file:

    Get-Content ".\Modelfile.aresforge-reasoner-local"

Create the local reasoning alias:

    ollama create aresforge-reasoner-local -f ".\Modelfile.aresforge-reasoner-local"

Confirm it exists:

    ollama list

## Run the coding alias

Run the AresForge coding alias:

    ollama run aresforge-coder-local

At the prompt, enter:

    You are the local AresForge coding model. Reply with a short confirmation and do not generate code.

Exit after the response.

## Run the reasoning alias

Before running the reasoning alias, check currently loaded models:

    ollama ps

Run the AresForge reasoning alias:

    ollama run aresforge-reasoner-local

At the prompt, enter:

    You are the local AresForge reasoning model. Reply with a short confirmation and do not produce a plan.

Exit after the response.

## Set one-model-at-a-time environment variables for the current PowerShell session

Set local session variables:

    $env:OLLAMA_MAX_LOADED_MODELS = "1"
    $env:OLLAMA_NUM_PARALLEL = "1"

Confirm the values:

    $env:OLLAMA_MAX_LOADED_MODELS
    $env:OLLAMA_NUM_PARALLEL

These values apply to the current PowerShell session.

## Set one-model-at-a-time environment variables for the current user

Set persistent user environment variables:

    [Environment]::SetEnvironmentVariable("OLLAMA_MAX_LOADED_MODELS", "1", "User")
    [Environment]::SetEnvironmentVariable("OLLAMA_NUM_PARALLEL", "1", "User")

Close and reopen PowerShell.

Confirm the values:

    [Environment]::GetEnvironmentVariable("OLLAMA_MAX_LOADED_MODELS", "User")
    [Environment]::GetEnvironmentVariable("OLLAMA_NUM_PARALLEL", "User")

## Stop or unload models

Check running models:

    ollama ps

Stop the coding alias if it is loaded:

    ollama stop aresforge-coder-local

Stop the reasoning alias if it is loaded:

    ollama stop aresforge-reasoner-local

Check again:

    ollama ps

## Troubleshooting memory or context issues

### Symptom: model fails to start

Check loaded models:

    ollama ps

Stop any loaded AresForge models:

    ollama stop aresforge-coder-local
    ollama stop aresforge-reasoner-local

Try again with only one model.

### Symptom: memory pressure, very slow startup, or context allocation failure

Create a reduced-context coding Modelfile:

    Set-Content -Path ".\Modelfile.aresforge-coder-local.16k" -Value @(
        "FROM qwen3-coder:30b-a3b-q4_K_M",
        "PARAMETER num_ctx 16384",
        "PARAMETER temperature 0.2",
        "PARAMETER top_p 0.9"
    )

Create a reduced-context coding alias:

    ollama create aresforge-coder-local-16k -f ".\Modelfile.aresforge-coder-local.16k"

Create a reduced-context reasoning Modelfile:

    Set-Content -Path ".\Modelfile.aresforge-reasoner-local.16k" -Value @(
        "FROM qwen3.6:27b",
        "PARAMETER num_ctx 16384",
        "PARAMETER temperature 0.4",
        "PARAMETER top_p 0.9"
    )

Create a reduced-context reasoning alias:

    ollama create aresforge-reasoner-local-16k -f ".\Modelfile.aresforge-reasoner-local.16k"

Test the reduced-context aliases:

    ollama run aresforge-coder-local-16k
    ollama run aresforge-reasoner-local-16k

### Symptom: GPU is not used heavily

This is expected on the current hardware. The GTX 1060 has 6 GB VRAM and should not be expected to fully load these models. CPU and system RAM inference may be the dominant path.

### Symptom: model responses are too slow

Use a smaller context alias first.

Check loaded models:

    ollama ps

Stop unused models:

    ollama stop aresforge-coder-local
    ollama stop aresforge-reasoner-local

Use 16K context aliases if needed:

    ollama run aresforge-coder-local-16k
    ollama run aresforge-reasoner-local-16k

## Pre-integration validation checklist

Before AresForge wires any workflow to Ollama:

- `ollama --version` succeeds.
- `ollama list` shows the selected base models.
- `ollama list` shows `aresforge-coder-local`.
- `ollama list` shows `aresforge-reasoner-local`.
- `ollama ps` can be used to inspect loaded models.
- `nvidia-smi` has been checked.
- The coding alias responds to a smoke prompt.
- The reasoning alias responds to a smoke prompt.
- Only one large model is loaded at a time.
- 32K context has been tested.
- 16K fallback aliases have been documented or created if needed.
- No AresForge workflow executes generated commands automatically.
- No AresForge workflow applies generated file changes automatically.
- Operator approval remains required before applying model output.