# 1. About SpicePy

**SpicePy** is a name coming from the merge of **SPICE** (*Simulation Program with Integrated Circuit Emphasis*) and **Python**, hence, it goes without saying that it is a _Circuit simulator written in Python_.

**SpicePy** was born as a teaching project. It is shared with students of *basic circuit theory* with two aims:

* to allow them to check the results of exercises solved analytically
* to show them how a numerical code to solve circuits is made

For the user's guide please refer to the [Wiki section](https://github.com/LuisFelipeCSouza/SpicePy/wiki).

## 1.1 What can I do with SpicePy?

SpicePy allows you to simulate:

1. **Linear circuits**
    * Operating point (`.op`)
    * Transient simulation (`.tran`)
    * AC simulation (`.ac` - linear, decade, octave sweeps)
2. **Components**
    * Resistor, capacitor, inductor
    * Independent voltage and current sources
    * Dependent sources (`VCVS`, `VCCS`, `CCVS`, `CCCS`)
3. **Transient sources**: `pwl`, `pulse`, `sin`, `exp`
4. **Post-processing**: branch voltages, currents, power, Bode plots

# 2. Installation

**Requirements**: Python >= 3.10

## 2.1 Install from PyPI

```bash
pip install spicepy
```

## 2.2 Install with uv (recommended)

```bash
# Clone the repository
git clone https://github.com/LuisFelipeCSouza/SpicePy.git
cd SpicePy

# Create venv and install
uv sync

# Run demos
uv run python demo/op_network.py
```

## 2.3 Install manually

1. Clone the repository:
   ```bash
   git clone https://github.com/LuisFelipeCSouza/SpicePy.git
   ```
2. Add the `SpicePy` folder to your Python path.

## 2.4 Google Colab

```python
!pip install spicepy
```

# 3. Quick Start

## From a netlist file

```python
from spicepy import Network, net_solve

net = Network('circuit.net')
net_solve(net)
net.print()
```

## From Python code (no file needed)

```python
from spicepy import Network, net_solve
import numpy as np

# Voltage divider: V1=10V, R1=1k, R2=2k
net = Network.from_parts(
    names=['R1', 'R2', 'V1'],
    values=[1000.0, 2000.0, 10.0],
    nodes=np.array([[1, 2], [2, 0], [1, 0]]),
    analysis=['.op'],
)

net_solve(net)
net.branch_voltage()
net.branch_current()
net.branch_power()
net.print()
```

# 4. Project Structure

```
spicepy/
├── __init__.py           # Public API
├── components.py         # ComponentType enum, Component dataclass
├── parsing.py            # Netlist parser
├── mna.py                # MNA matrix construction
├── results.py            # Post-solve analysis
├── display.py            # Print, plot, Bode
├── netsolve.py           # DC, AC, transient solvers
├── transient_sources.py  # PWL, PULSE, SIN, EXP waveforms
└── netlist.py            # Network class (container)
```

# 5. Verify the installation

Run the benchmark to validate against LTspice reference solutions:

```bash
cd benchmark
uv run python run_benchmark.py
```

Or with pytest:

```bash
uv run pytest tests/ -v
```

# 6. Development

```bash
# Install with dev dependencies
uv sync --all-extras

# Lint
uv run ruff check spicepy/

# Format
uv run ruff format spicepy/

# Tests
uv run pytest tests/ -v
```

# 7. License

MIT License - see [LICENSE](LICENSE) for details.
