# References

Design decisions in this repo trace to public literature from Yaqumo's
founding labs. Claims about Yaqumo's current internal stack are **inferred**
from open papers; proprietary details are not represented here.

All quotes below are verbatim, verified against the PDFs on file.

---

## Nakamura et al., [arXiv:2406.12247](https://arxiv.org/abs/2406.12247) (PRX 14, 041062, 2024 preprint)

*A hybrid atom tweezer array of nuclear spin and optical clock qubits*

> "we observe 99.1(1.8) % coherence retained under 20 ms exposure, yielding an imaging fidelity of 0.9992 and a survival probability of 0.988"
> — abstract

**Note:** the "99.1 % coherence" refers to the ¹⁷¹Yb qubit retention under
exposure; the "0.9992 discrimination fidelity" refers to the ¹⁷⁴Yb ancilla
readout. They are two distinct metrics (Fig. 4a and Fig. 4b respectively).

Supports: dual-isotope ¹⁷¹Yb/¹⁷⁴Yb **non-destructive ancilla imaging**
(a prerequisite for MCM, not the full MCM cycle); **20 ms imaging** is
the primary contributor to the feedback-domain latency in a 2D stack.

---

## Kusano et al., [arXiv:2501.05935](https://arxiv.org/abs/2501.05935) (2025)

*Plane-selective manipulations of nuclear spin qubits in a three-dimensional optical tweezer array*

> "This imaging system can typically focus on each plane within approximately 20 ms, which is sufficiently fast for the experiments described in this paper. Each plane is then imaged with a 60 ms exposure time."
> — §3D Optical Tweezer Array, page 2

> "the exposure time for each plane is 60 ms, and the survival probabilities after imaging are typically 89 %, 91 % and 92 % for Planes 1, 2, and 3, respectively"
> — Supplementary Material §S.1 *Atom imaging*, page 10

Supports: 3D tweezer arrays amplify the feedback-domain cost (**60 ms per
plane + 20 ms refocus**). Motivation for plane-addressing as a future IR
primitive.

---

## Kusano et al., [arXiv:2602.22883](https://arxiv.org/abs/2602.22883) (2026)

*Spin-Cat Qubit with Biased Noise in an Optical Tweezer Array*

Authors: **Toshi Kusano**, Kosuke Shibata, Chih-Han Yeh, Keito Saito, Yuma
Nakamura, Rei Yokoyama, Takumi Kashimoto, Tetsushi Takano, Yosuke Takasu,
Ryuji Takagi, Yoshiro Takahashi. Kyoto University + Yaqumo Inc. +
University of Tokyo.

> "we obtain a discrimination fidelity of 0.99984(6) with a survival probability of 0.9751(4) under an exposure time of 12 ms in a 1.09 mK trap"
> — Appendix A §1, Fig. 7

**Caveat:** ¹⁷³Yb (I = 5/2 fermion) at 1.09 mK trap depth — polarizability
and imaging conditions differ from ¹⁷¹Yb/¹⁷⁴Yb (I = 1/2, I = 0). Treat as
a lower-bound reference, not a direct spec transfer.

Supports: short-exposure imaging (**12 ms**) is feasible for ¹⁷³Yb SU(N)
protocols; sets a directional floor for the feedback budget on other Yb
isotopes.

---

## Chew, Tomita, Mahesh, Sugawa, de Léséleuc, Ohmori — *Nature Photonics* 16, 724 (2022) / [arXiv:2111.12314](https://arxiv.org/abs/2111.12314)

*Ultrafast energy exchange between two single Rydberg atoms on the nanosecond timescale*

IMS Okazaki + SOKENDAI. **This is the flagship ultrafast-gate paper.**

> "using atoms trapped in the motional ground-state of optical tweezers and excited to a Rydberg state with picosecond pulsed lasers, we observe an interaction-driven energy exchange, i.e., a Förster oscillation, occurring in a timescale of nanoseconds, two orders of magnitude faster than in any previous work with Rydberg atoms."
> — abstract

> "This ultrafast coherent dynamics gives rise to a conditional phase which is the key resource for an ultrafast controlled-Z gate."
> — abstract

**Caveat:** demonstrated on **⁸⁷Rb** atoms in optical tweezers, not Yb.
Yaqumo's differentiation rests on *adapting* this regime to Yb — a
targeted, not yet published, engineering direction.

Supports: the **100× speed advantage** claim vs. µs-regime Rydberg gate
competitors; the OPTICAL timing-domain classification for ultrafast CPA
gates in our IR. The Förster oscillation half-period observed is **~6.5 ns**, which sets the competitive anchor against µs-regime Rydberg gates.

---

## Bharti, Sugawa, Kunimi, Chauhan, Mahesh, Mizoguchi, Matsubara, Tomita, de Léséleuc, Ohmori — [arXiv:2311.15575](https://arxiv.org/abs/2311.15575) (2023)

*Strong Spin-Motion Coupling in the Ultrafast Dynamics of Rydberg Atoms*

> "We observe its clear signature on the ultrafast many-body nanosecond-dynamics of atoms excited to a Rydberg S state, using picosecond pulses, from an unity-filling atomic Mott-insulator."
> — abstract

**Caveat:** spin-motion coupling observation on Rb in a Mott insulator —
not the CZ gate paper. Cited for the ultrafast-ps-pulse timing idiom.

Supports: the ps pulse + ns dynamics separation in our OPTICAL timing
domain classification.

---

## Ohmori et al., [arXiv:1910.05292](https://arxiv.org/abs/1910.05292) (2020)

*Ultrafast Creation of Overlapping Rydberg Electrons in an Atomic BEC and Mott-Insulator Lattice*

> "The delay τ between the picosecond laser pulse and the rising edge of the electric field pulse is set to ∼ 60 ns, thus ensuring no temporal overlap between laser and electric field pulses."
> — Supplemental, page 10

Supports: the **~60 ns** optical-to-electronic coordination gap that
motivates the `OpticalDelay` primitive in `ir/nodes.py` as a non-electronic
timing object.

---

## Denecker et al., [arXiv:2411.10021](https://arxiv.org/abs/2411.10021) (2024, v2 April 2025)

*Measurement and feedforward correction of the fast phase noise of lasers*

Authors: **T. Denecker**, Y. T. Chew, O. Guillemant, G. Watanabe, T. Tomita,
K. Ohmori, S. de Léséleuc. IMS Okazaki + SOKENDAI + RIKEN RQC.

> "we present a fully-fiberized instrument detecting and correcting the fast, sub-microsecond, phase fluctuations of lasers. We demonstrate a measurement noise floor of less than 0.1 Hz²/Hz, and a noise suppression of more than 20 dB for Fourier frequencies in the 1 to 10 MHz region (reaching up to 30 dB at 3 MHz), where noise is critical for Rydberg-based quantum gates."
> — abstract

**Clarification:** this is NOT a sub-kHz Arduino-DUE servo loop. 
It is a fully-fiberized
**feedforward** correction for laser phase noise in the 1–10 MHz band —
the noise regime that limits Rydberg gate fidelity in the CPA regime.

Supports: the `StabilizationLoop` IR primitive reframed as "fast-loop
laser-phase-noise correction, optical-domain-serving". The sub-kHz /
corrected in the docstrings.

---

## Barredo, Lienhard, Scholl, de Léséleuc, Boulier, Browaeys, Lahaye — [arXiv:1908.00853](https://arxiv.org/abs/1908.00853) (2020)

*Three-Dimensional Trapping of Individual Rydberg Atoms in Ponderomotive Bottle Beam Traps*

Laboratoire Charles Fabry, Institut d'Optique Graduate School, CNRS —
**Palaiseau group** (Browaeys). de Léséleuc is a co-author (4th), not
first author. Earlier project of the de Léséleuc persona's PhD/postdoc
lineage, before IMS Okazaki.

> "An exponential fit to the experimental data (dashed line) gives a 1/e decay time of 222±3 µs, in excellent agreement with the calculated lifetime 228 µs of this state at 300 K"
> — page 3, Fig. 4 caption

**Caveat:** ⁸⁷Rb (not Yb), bottle-beam holographic trap (not Yaqumo's
tweezer geometry). Cited for Rydberg-state lifetime as the outer envelope
of gate-block duration budgeting.

Supports: **222 µs** Rydberg 84S lifetime as the classical envelope for
gate timing budget.

---

## What this repo does NOT claim

- **No paper in this list uses the word "bottleneck" about feedback loops.**
  The argument that classical-feedback dominates RF timing is this repo's
  own framing — supported by the published imaging numbers above, but not
  a direct quote from any founder paper.
- **No Yb ultrafast CZ gate has been published.** The Nature Photonics
  2022 paper (arXiv:2111.12314) demonstrated the 100× speed advantage on
  Rb-87; Yaqumo's differentiation is the *port* to Yb, which is targeted
  but not yet a published result.
- Default latency numbers baked into IR nodes (e.g., 10 ms path planning,
  15 ms camera total, "50 ms coherence budget" in the scaling plot) are
  **engineering defaults**, not literature citations. The "50 ms" figure
  in particular is a plausible order-of-magnitude anchor, not a physics
  coherence time — the ¹⁷¹Yb nuclear-spin qubit coherence clearly exceeds
  the 20 ms imaging window cited in PRX 2024 abstract (99.1(1.8) %
  retained), but the exact T₂* under imaging is not reproduced verbatim
  here; confirm against PRX 2024 main text before using as a hard spec.
- No figures, tables, or images from any paper are reproduced in this
  repo.

---

## Adopted code (with attribution — see THIRD_PARTY_NOTICES.md)

### QICK envelope library

- `src/yaqumo_shot_graph/ir/envelopes.py` adapts four pulse-envelope helpers
  verbatim from [QICK](https://github.com/openquantumhardware/qick)
  `qick_lib/qick/helpers.py` (MIT License, Open Quantum Hardware): `cosine`,
  `gauss`, `drag`, `triang`. DRAG follows PRL 116, 020501 (2016) and
  cross-references the QubiC and Qiskit-Pulse implementations per the
  upstream comment.

### QCoDeS ParameterCache idiom

- `src/yaqumo_shot_graph/ir/parameter.py` (`ParameterCache`) adapts the TTL
  cache pattern from [QCoDeS](https://github.com/QCoDeS/Qcodes)
  `src/qcodes/parameters/cache.py` (MIT License, Microsoft + Københavns
  Universitet). The QCoDeS-specific `Station`/`Instrument` coupling is
  dropped; only the `_marked_valid` / `_timestamp` / `max_val_age` core
  is kept.

### QuEL validation idiom (cited, not copied)

- Pydantic `BaseModel(validate_assignment=True)` with hex-range
  `Field(ge=0x...,le=0xFFFF_...,multiple_of=N)` constraints — the style is
  credited to QuEL's `e7awghal/wavedata.py` (Apache-2.0). No code copied,
  but the idiom informs how we validate AD9910 register words and future
  TDM waveform alignment.

---

## Miyoshi et al., *IEEE ICCE 2025* — DOI [10.1109/icce63647.2025.10930074](https://doi.org/10.1109/icce63647.2025.10930074)

*Toward Scalable Heterogeneous Controller System for Various Quantum Computer by Using Multiple FPGAs*

Authors include Takefumi Miyoshi (QuEL CTO), Takafumi Tomita (Yaqumo CSO),
Sylvain de Léséleuc (IMS Okazaki / RIKEN QC), among others. The paper
describes a multi-FPGA heterogeneous controller architecture for quantum
systems spanning neutral-atom, superconducting, and ion regimes.

PDF text was NOT extracted for this repo (IEEE paywall); citation is based
on the public abstract and author list only. Supports the 
IR slot as a reserved architectural position for this direction, without
claiming reproduction of the paper's system-level details.

