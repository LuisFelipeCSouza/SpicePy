# SpicePy

**Circuit simulator written in Python.**

SpicePy is a SPICE-compatible linear circuit simulator designed as a teaching tool for basic circuit theory students. It allows you to simulate circuits with resistors, capacitors, inductors, independent sources, and all four types of dependent sources.

## Features

- **Operating point** (`.op`) — DC analysis
- **Transient** (`.tran`) — time-domain simulation with trapezoidal integration
- **AC** (`.ac`) — frequency-domain analysis (linear, decade, octave sweeps)
- **9 component types**: R, L, C, V, I, E (VCVS), F (CCCS), G (VCCS), H (CCVS)
- **4 transient sources**: PWL, PULSE, SIN, EXP
- **Bode plots** for transfer functions
- **Build programmatically** — no `.net` file required

## Quick Example

```python
from spicepy import Network, net_solve

# Voltage divider: 10V source, R1=1k, R2=2k
net = Network.from_parts(
    names=['R1', 'R2', 'V1'],
    values=[1000.0, 2000.0, 10.0],
    nodes=np.array([[1, 2], [2, 0], [1, 0]]),
    analysis=['.op'],
)

net_solve(net)
net.print()
# v(R1) = 3.333 V
# v(R2) = 6.667 V
# v(V1) =     10 V
```

## Navigation

- **[Getting Started](getting-started.md)** — installation and first steps
- **[API Reference](api/network.md)** — full documentation of all modules
- **[Examples](examples.md)** — practical circuit examples
