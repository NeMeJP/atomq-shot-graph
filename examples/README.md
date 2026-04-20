# Examples

Recruiter-facing demos. See `PLAN.md` M6 and `internal design notes` §6 for the
grounded design claims each script illustrates.

## Files

### `01_dual_isotope_feedback.py`

The 3-minute demo. Builds a 11-node dual-isotope ¹⁷¹Yb/¹⁷⁴Yb mid-circuit-
measurement shot graph, compiles it through a `BackendRegistry` wired with
the concrete `NIDAQBackend`, `AD9910Backend`, `EMCCDCameraBackend`,
`SLMBackend`, `OpticalDelayBackend` adapters (plus an `arduino_lock` stub
for the persistent Ohmori fiber-MZI PID), prints the latency budget in two
framings (full shot vs inner gate-path-shot loop), runs the rearrangement-
feedback simulation to show √N wins at 10³ sites, and exports the same IR
to both OpenQASM 3 text and a Pasqal Pulser `Sequence` as proof of IR
translatability.

**Signals to the reader:** I know image-feedback dominates the neutral-atom
shot budget, I keep the three timing domains (electronic / optical /
feedback) separate, and I know the difference between an export format and
a runtime.

### `02_rearrangement_scaling.py`

Shorter companion. Scans array sizes 10 → 5000 and contrasts
`hungarian` (O(N²)) vs `sqrt_t` (O(√N)) path-planning cost per shot.
Makes concrete why production stacks cannot ship Hungarian assignment
at 10³+ sites.

**Signals to the reader:** I understand the asymptotic collapse of
classical assignment at real array sizes — and why Kim/Endres-style √N
planners are the production answer.

## Running

Each script runs with plain CPython — **no Jupyter required**:

```bash
python examples/01_dual_isotope_feedback.py
python examples/02_rearrangement_scaling.py
```

Expected runtime < 5 seconds per script on a laptop CPU.

## Jupytext / notebook rendering

Both scripts are written in **jupytext percent format** — cells delimited
by `# %%` and `# %% [markdown]`. VS Code and PyCharm render them as
notebooks natively. To convert to `.ipynb` if you want to email one to a
recruiter:

```bash
pip install jupytext
jupytext --to ipynb examples/01_dual_isotope_feedback.py
```

jupytext is **not** a default dependency of this repo — the percent-format
`.py` files are the source of truth, so they round-trip cleanly through
git and survive SSH transport.

## Smoke tests

Both examples have smoke tests in `tests/test_examples.py` that execute
each script top-to-bottom and assert on key stdout markers. This guarantees
the demo actually runs on a fresh clone — no broken notebooks in the
portfolio.
