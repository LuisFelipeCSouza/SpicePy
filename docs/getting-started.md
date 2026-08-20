# Getting Started

## Installation

### From PyPI

```bash
pip install spicepy
```

### With uv (recommended for development)

```bash
git clone https://github.com/LuisFelipeCSouza/SpicePy.git
cd SpicePy
uv sync
```

### Requirements

- Python >= 3.10
- numpy
- scipy
- matplotlib

## First Steps

### From a netlist file

If you have a SPICE netlist file (`.net`), you can load it directly:

```python
from spicepy import Network, net_solve

net = Network('circuit.net')
net_solve(net)
net.print()
```

### From Python code

You can also build circuits programmatically without any file:

```python
from spicepy import Network, net_solve
import numpy as np

# Simple series circuit: V1=12V, R1=1k, R2=2k
net = Network.from_parts(
    names=['R1', 'R2', 'V1'],
    values=[1000.0, 2000.0, 12.0],
    nodes=np.array([[1, 2], [2, 0], [1, 0]]),
    analysis=['.op'],
)

net_solve(net)
net.branch_voltage()
net.branch_current()
net.branch_power()
net.print()
```

## Analysis Types

### Operating Point (`.op`)

Solves the DC operating point of the circuit:

```python
net = Network.from_parts(
    names=['R1', 'V1'],
    values=[1000.0, 5.0],
    nodes=np.array([[1, 0], [1, 0]]),
    analysis=['.op'],
)
net_solve(net)
```

### AC Analysis (`.ac`)

Frequency-domain analysis with linear, decade, or octave sweeps:

```python
net = Network('rc_filter.net')
net_solve(net)
net.bode()  # Plot Bode diagram
```

### Transient Analysis (`.tran`)

Time-domain simulation:

```python
net = Network('rlc_circuit.net')
net_solve(net)
net.plot()  # Plot waveforms
```

## Post-Processing

After solving, you can compute:

```python
net.branch_voltage()   # Branch voltages
net.branch_current()   # Branch currents
net.branch_power()     # Branch power

# Get specific values
v = net.get_voltage('R1')       # Voltage across R1
i = net.get_current('V1')       # Current through V1
v = net.get_voltage('1, 2')     # Voltage between nodes 1 and 2

# Print formatted results
net.print()                      # All quantities
net.print(variable='voltage')    # Voltages only
net.print(polar=True)            # Polar notation for AC
```
