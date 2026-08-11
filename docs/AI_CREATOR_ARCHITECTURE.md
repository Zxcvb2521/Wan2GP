# AI Creator Studio — Architecture Proposal

> Experimental design branch: `feature/ai-creator-studio`
>
> Goal: provide a compact, modern UI over WanGP without replacing WanGP's generation engine or exposing its Gradio interface to the end user.

## 1. Product goal

AI Creator Studio is a local-first creative application for turning an idea into finished media:

- text / story generation
- image generation
- video generation
- music generation
- voice / TTS
- speech / STT
- project and asset management
- simple timeline assembly
- export to final media

The first version must remain small. Advanced model parameters stay hidden until explicitly requested.

## 2. Core principle

**Do not fork or rewrite WanGP's inference stack unless required.**

WanGP remains responsible for:

- model loading and unloading
- VRAM/RAM management
- generation implementations
- model-specific settings
- LoRA handling
- existing optimizations
- media processing capabilities already implemented by WanGP
- Deepy integration

The new application owns the user experience, project state, orchestration, and normalized API.

## 3. Target architecture

```text
Browser / Desktop WebView
          |
          v
   AI Creator Frontend
 React + TypeScript + Vite
          |
     REST/WebSocket
          |
          v
   Creator Orchestrator
       FastAPI
          |
    +-----+------------------+
    |                        |
    v                        v
 WanGP Adapter          Optional LLM Adapter
    |                    (KoboldCpp later)
    v
 WanGP / Deepy
    |
 +--+---------+---------+
 |            |         |
 v            v         v
Image        Video     Audio/TTS/STT
 |
 +------------+--------+
              v
           FFmpeg
              |
              v
         Project Export
```

## 4. Why no Ollama in the first version

Ollama is not a required dependency. WanGP/Deepy should be treated as the first integrated AI backend. A separate LLM backend can be added through an adapter only when a real capability gap is identified.

## 5. Frontend information architecture

Primary navigation should contain only:

1. **Create** — image, video, music, voice, story/text.
2. **Projects** — saved creative projects.
3. **Timeline** — simple scene/audio assembly.
4. **Assets** — generated and imported media.
5. **Settings** — backend, models, storage, advanced options.

The default experience must not expose the full WanGP/Gradio parameter surface.

## 6. Create flow

### Simple mode

User chooses a media type, enters a natural-language request, optionally adds a reference, selects a small number of human-readable choices, and presses Generate.

Example:

```text
Create Video

Describe your video:
[ A fluffy little creature walks through a magical forest... ]

Reference image: [ Add ]

Quality:  Fast | Balanced | Quality
Duration: 5s
Aspect:   16:9

[ Generate ]
```

### Advanced mode

Expose model, seed, LoRA, steps, attention, quantization and other backend-specific controls only when enabled.

## 7. Project model

A project contains:

```text
project/
  project.json
  scenes/
  assets/
  audio/
  video/
  exports/
```

Every generated asset should preserve reproducibility metadata where available:

- prompt
- model/checkpoint
- seed
- dimensions
- duration
- LoRA configuration
- generation parameters
- source asset references
- creation time

## 8. Queue

All expensive operations should become jobs.

Job states:

`queued -> loading -> generating -> postprocessing -> completed`

Failure state:

`failed`

The UI should show one unified queue regardless of whether a job is image, video, audio, TTS, or an orchestration workflow.

## 9. Orchestration

A future one-click workflow should support:

```text
Idea
 -> story
 -> scene breakdown
 -> prompts
 -> images
 -> videos
 -> voices
 -> music
 -> assembly
 -> export
```

This is a second-phase feature. The first milestone is reliable single-operation generation.

## 10. Backend adapter contract

The frontend must never call WanGP-specific functions directly.

The orchestrator should expose normalized operations such as:

- `generate_image`
- `generate_video`
- `generate_music`
- `generate_voice`
- `transcribe_audio`
- `list_models`
- `list_loras`
- `get_job`
- `cancel_job`

A WanGP adapter maps these operations to the existing WanGP implementation/API.

## 11. Important constraint

Do not duplicate model implementations in the new UI project. Do not create a second VRAM manager. Do not create a second model loader. Reuse WanGP wherever possible.

## 12. Milestones

### M0 — Repository reconnaissance

Map the current WanGP entry points, Deepy controller/CLI, generation functions, Gradio bindings, model manager, queue/process locks, and any existing API/headless paths.

### M1 — Minimal shell

Create a small frontend and backend that can start alongside WanGP and display backend health.

### M2 — Image generation

Implement one normalized image-generation path and asset storage.

### M3 — Video generation

Implement video generation, progress reporting, cancellation, and result preview.

### M4 — Audio/TTS

Add music, voice, and audio operations exposed by WanGP.

### M5 — Projects and timeline

Add persistent projects, assets, simple scene ordering, audio tracks, and FFmpeg export.

### M6 — Deepy orchestration

Expose natural-language multi-step workflows after the individual primitives are stable.

### M7 — Optional KoboldCpp

Add KoboldCpp only if the integrated Deepy/LLM capabilities do not cover the desired text-generation workflow.

## 13. UX rule

The application should feel like a lightweight creative tool, not an ML laboratory.

Default screen: **one prompt, one clear action, one result.**

Advanced controls are progressive disclosure, not the default interface.
