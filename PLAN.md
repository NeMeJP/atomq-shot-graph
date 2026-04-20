# PLAN — yaqumo-shot-graph

## Scope

Thin, honest middleware that compiles a typed shot-graph IR into heterogeneous backend command streams for neutral-atom quantum experiments. Targets the Kyoto (Takahashi/Nakamura) + IMS Okazaki (Ohmori/de Léséleuc) lab realities.

All design claims trace to `../pin_list_v2.md`. Anything not pinned is not implemented.

## Non-goals

- Reproduce Yaqumo's physics performance or proprietary hardware
- Replace ARTIQ / QICK / QCoDeS / labscript (explicitly rejected vocabulary — see pin_list_v2.md §4)
- Simulate quantum state — this is **control** software, not physics
- Be a production lab runtime

## Module map

| Module | Purpose | Depends on |
|---|---|---|
| `ir/` | Typed shot-graph nodes + timing domains + DAG validation | — |
| `scheduler/` | Compile IR → per-backend command streams | `ir/` |
| `backends/` | Adapters + mocks (NI-DAQ, AD9910, camera, SLM, optical delay) | `ir/`, `backends/base.py` |
| `sim/` | Latency-budget accounting, feedback simulation | `scheduler/` |
| `export/` | OpenQASM 3, Pulser export (read-only, non-runtime) | `ir/` |
| `tests/` | pytest property + cocotb timing tests | every module |
| `examples/` | Recruiter-facing demo notebooks | everything |

## Milestones & parallelization

M1 is the critical path. After M1, up to 4 agents can run in parallel.

| ID | Milestone | Depends on | Parallel with |
|---|---|---|---|
| M0 | Repo bootstrap (root files + package skeletons) | — | — |
| **M1** | **IR core** (types, nodes, graph) | M0 | — |
| M2 | Scheduler / compiler | M1 | M3a, M5a, M5b |
| M3a | Backend ABC + BackendCommand | M1 | M2, M5a, M5b |
| M3b | NI-DAQ adapter | M3a | M3c, M3d, M3e |
| M3c | AD9910 DDS SPI model | M3a | M3b, M3d, M3e |
| M3d | Camera + SLM mocks | M3a | M3b, M3c, M3e |
| M3e | Optical delay stub | M3a | M3b, M3c, M3d |
| M4 | Sim / latency budget | M2 | M3b–e, M5a, M5b |
| M5a | OpenQASM 3 export | M1 | M2, M3a, M5b |
| M5b | Pulser export | M1 | M2, M3a, M5a |
| M6 | Dual-isotope demo notebook | M2, M3b–e, M4 | — |
| M7 | Tests + CI (progressive) | M1 | everything |

## Exit criteria per milestone

- **M0**: `pyproject.toml` installs cleanly; `import yaqumo_shot_graph` works
- **M1**: dual-isotope-feedback graph builds in pure Python and passes `graph.validate()`
- **M2**: same graph compiles to ≥ 4 backend streams
- **M3a**: backends can be registered by DeviceClass and looked up
- **M3b–e**: each backend accepts its subset of nodes and emits typed commands
- **M4**: latency budget printout shows image-feedback dominates for the demo graph
- **M5a**: OpenQASM 3 text output parses with the `openqasm3` reference parser
- **M5b**: Pulser `Sequence` object renders without error
- **M6**: notebook runs top-to-bottom on a fresh venv in < 30 s
- **M7**: `pytest` green, `ruff check` green, `mypy --strict` green in CI

## Parallelization policy

1. IR (M1) is the critical path; nothing else parallelizes before it
2. After M1 completes: M2, M3a, M5a, M5b can run as 4 parallel agents
3. After M3a completes: M3b, M3c, M3d, M3e run as 4 parallel agents
4. M4 waits on M2
5. M6 waits on M2 + M3b–e + M4
6. M7 is progressive — a per-module test task is added whenever a module task completes

## Reference

- `../pin_list_v2.md` — ground truth for all design claims
- `../research/01_mvp_strategic_engineering_report.md` — big-picture rationale
- `../research/03_mvp_thin_middleware_plan.md` — module architecture source
- `../personas/` — founder perspectives (used later for PR-review persona agents)
