# Examples

## Voltage Divider

A classic voltage divider with V1=10V, R1=1k, R2=2k:

```python
from spicepy import Network, net_solve
import numpy as np

net = Network.from_parts(
    names=['R1', 'R2', 'V1'],
    values=[1000.0, 2000.0, 10.0],
    nodes=np.array([[1, 2], [2, 0], [1, 0]]),
    analysis=['.op'],
)

net_solve(net)
net.print()
```

**Result:**
```
v(R1) = 3.333 V    (across R1)
v(R2) = 6.667 V    (across R2)
v(V1) =     10 V   (source)
```

## Current Divider

Two resistors in parallel driven by a 2mA current source:

```python
net = Network.from_parts(
    names=['R1', 'R2', 'I1'],
    values=[1000.0, 2000.0, 0.002],
    nodes=np.array([[1, 0], [1, 0], [1, 0]]),
    analysis=['.op'],
)

net_solve(net)
net.branch_voltage()
net.branch_current()
net.branch_power()
net.print()
```

## RC Low-Pass Filter (AC)

```python
net = Network.from_parts(
    names=['R1', 'C1', 'V1'],
    values=[1000.0, 1e-6, 1.0],  # R=1k, C=1uF, V=1V
    nodes=np.array([[1, 2], [2, 0], [1, 0]]),
    analysis=['.ac', 'dec', '10', '1', '1Meg'],
)

net_solve(net)
net.bode(decibel=True)
```

## RLC Series Circuit (Transient)

```python
net = Network.from_parts(
    names=['R1', 'L1', 'C1', 'V1'],
    values=[100.0, 1e-3, 1e-6, 5.0],  # R=100, L=1mH, C=1uF, V=5V
    nodes=np.array([[1, 2], [2, 3], [3, 0], [1, 0]]),
    IC={'L1': 0.0, 'C1': 0.0},
    analysis=['.tran', '1e-7', '5e-3'],
)

net_solve(net)
net.plot()
```

## VCVS (Voltage-Controlled Voltage Source)

An ideal amplifier with gain=10:

```python
net = Network.from_parts(
    names=['R1', 'R2', 'V1', 'E1'],
    values=[1000.0, 1000.0, 1.0, 10.0],  # gain=10
    nodes=np.array([
        [1, 0],   # R1
        [2, 0],   # R2 (output)
        [1, 0],   # V1 (input)
        [2, 0],   # E1 (VCVS output)
    ]),
    analysis=['.op'],
    control_source={'E1': ['1', '0']},  # senses V(1,0)
)

net_solve(net)
net.print()
# v(E1) ≈ 10V (10x the input)
```

## CCCS (Current-Controlled Current Source)

```python
net = Network.from_parts(
    names=['R1', 'R2', 'V1', 'F1'],
    values=[1000.0, 500.0, 10.0, 3.0],  # gain=3
    nodes=np.array([
        [1, 0],   # R1
        [2, 0],   # R2
        [1, 0],   # V1
        [2, 0],   # F1
    ]),
    analysis=['.op'],
    control_source={'F1': 'V1'},  # senses current through V1
)

net_solve(net)
net.branch_current()
net.print()
```
