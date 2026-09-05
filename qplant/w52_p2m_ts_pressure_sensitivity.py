"""W52-P2M-R1: thermal-shield residual sensitivity across LKT HP operating window.

This is a bounded diagnostic, not strict residual closure. LKT sources bind the thermal-shield
state as 81 g/s, 40 K at HP and 60 K at HP-1 bar, while the control description allows HP
setpoint adjustment within 9..14 bara. Until the exact 2K-OP HP setpoint is source-bound,
this module reports the residual envelope across that governed window.