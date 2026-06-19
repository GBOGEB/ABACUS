# QPS Line S Recovery Model

This scaffold tracks the reduced transient model needed to answer RTM-261 / RTM-292 for Line S helium recovery during LOOP / loss-of-utility conditions.

## Session source basis

The current MASTER SSOT is D2.1 Conceptual Design Report for the MINERVA Cryogenic System.

Relevant source sections:

- Section 5.6.5 Loss of utility
- Section 5.6.6 Cryoplant trip
- Appendix 8.2 General PFD
- Appendix 8.3 SIMCRYOGENICS model
- Appendix 8.4 Modes

## Immediate boundary

This is not a full SIMCRYOGENICS reproduction. The first model covers only the boundary required for the Applicant response:

```text
Cryogenic users / QCELL / QVE
  -> Safety valve GHe return / Line S
  -> Recovery compressors, 1 x 50 g/s or 2 x 50 g/s
  -> Optional HP compressor acceptance path
  -> Storage / purification boundary
```

## Core equations

Line S accumulation:

```text
m_net(t) = m_in(t) - m_recovery(t) - m_HP(t)
```

Ideal-gas pressure build-up:

```text
dP/dt = m_net R_He T / V_eff
```

For helium at 300 K and V_eff = 120 m3:

```text
dP/dt [bar/min] = 0.003116 x m_net [g/s]
```

## First heat-load sensitivity

Use 8700 W as the base thermal-shield heat-load point and compare:

- 1.0x = 8700 W
- 1.2x = 10440 W

For a 40 K to 60 K shield loop, calibrated from D2.1 values around 8505 W and 81 g/s, this gives approximately:

- 83 g/s at 8700 W
- 99 g/s at 10440 W

## First scenarios

- 100 g/s inflow with 100 g/s recovery
- 112 g/s pre-HP inflow with 100 g/s recovery
- 150 g/s inflow with 100 g/s recovery
- 200 g/s peak inflow with HP compressor running
- 200 g/s peak inflow without HP compressor
- shield-maintained mitigation case

## GitHub tracking

This work is tracked under issue #581.
