# Third-party notices

This repository adapts small, verbatim-attributed code fragments from the
following open-source projects. Each fragment is clearly marked in its
source file with an attribution header pointing back here.

---

## QICK — `qick_lib/qick/helpers.py`

**License:** MIT
**Copyright:** Open Quantum Hardware
**Upstream:** https://github.com/openquantumhardware/qick
**Adapted in:** `src/yaqumo_shot_graph/ir/envelopes.py` (cosine, gauss, drag, triang)

```
MIT License

Copyright (c) Open Quantum Hardware

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## QCoDeS — `src/qcodes/parameters/cache.py`

**License:** MIT
**Copyright:** (c) 2015-2023 Microsoft Corporation and Københavns Universitet
**Upstream:** https://github.com/QCoDeS/Qcodes
**Adapted in:** `src/yaqumo_shot_graph/ir/parameter.py` (`ParameterCache`)

```
MIT License

Copyright (c) 2015-2023 by Microsoft Corporation and Københavns Universitet

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## QuEL quelware — `e7awghal/src/e7awghal/wavedata.py` (citation only, idiom reuse)

**License:** Apache-2.0
**Copyright:** QuEL Inc.
**Upstream:** https://github.com/quel-inc/quelware
**Referenced in:** `REFERENCES.md` — for the pydantic `BaseModel(validate_assignment=True)`
idiom with hex-range `Field(ge=0x0..., le=0xFFFF_...)` constraints and
`multiple_of` alignment. Our IR nodes do not copy code from quelware, but we
adopt their validation style where hardware-word alignment matters.

Full Apache-2.0 license text: https://www.apache.org/licenses/LICENSE-2.0

---

## Not currently adopted, but publicly referenced

These projects are discussed in the research notes (internal design notes / research/)
but no code from them has been copied into this repository:

- **labscript** — BSD-2-Clause (Monash University, 2013). Referenced in
  `REFERENCES.md` as an architectural comparison for Device hierarchies.
  https://github.com/labscript-suite/labscript
- **cocotb** — BSD-3-Clause (Potential Ventures Ltd, SolarFlare Communications).
  Referenced as a test-harness-style comparison only.
  https://github.com/cocotb/cocotb
- **ARTIQ** — LGPL-3.0. Explicitly NOT copied; the LGPL copyleft is
  incompatible with this repository's PolyForm Noncommercial license.
  https://github.com/m-labs/artiq
- **pyadi-iio** — Analog Devices BSD-style with patent clause. Not adopted.

---

## How this interacts with the repository's license

The repository at large is licensed under **PolyForm Noncommercial 1.0.0**
(see `LICENSE`). Files that adapt MIT or Apache-licensed fragments from
the projects above carry their own attribution header and continue to
honour the original project's license terms for *that fragment*. The
combination is legally permitted because PolyForm NC is compatible with
downstream inclusion of permissive-licensed code.
