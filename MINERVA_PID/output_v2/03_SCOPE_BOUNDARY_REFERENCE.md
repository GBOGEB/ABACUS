# Scope Boundary Reference

Scope-boundary **diamond** symbols mark the **"last-meter" hand-over** between
**in-scope** assets (designed/supplied within the MINERVA CryoCell package) and
**out-of-scope** assets (infrastructure, building services, RF system delivered
by others). They appear on **Layer 1 — Scope** of every sheet, with the
hand-over note on **Layer 12 — Tags**.

## 1. Diamond code format — `TPXYYYY`

```
TP   X      YYYY
│    │      └── 4-digit serial number (0001, 0002, …)
│    └───────── category prefix (one letter, see table below)
└────────────── "TP" = Terminal Point / scope interface
```

## 2. Category prefixes

| Prefix | Category | Typical media / service |
|--------|----------|-------------------------|
| **B** | Bulk | Bulk gas / cryogen supply |
| **C** | Cryogenic | He circuits (2 K / 4.5 K / 40 K), guard |
| **E** | Electrical | Heater power, electrical feedthroughs |
| **H** | HVAC | Vacuum / venting / ventilation, relief |
| **L** | Liquid | Liquid level / liquid services |
| **S** | Steam | Steam / hot utilities |
| **W** | Water | DI cooling water, FREIA water |

The category is assigned automatically from the **function of the nearest
instrument** at each terminal point (e.g. a point next to an electric heater →
`E`, next to a level switch → `L`, next to a relief/vacuum device → `H`).

## 3. In-scope vs out-of-scope convention

- **Inside** the diamond ring → in-scope (MINERVA CryoCell).
- **Outside** the diamond ring → out-of-scope (delivered/maintained by others).
- The diamond is the single contractual/physical interface — the "last meter"
  of pipe/cable on the in-scope side terminates at the diamond.

## 4. Terminal-point register (QCELL / LB)

| Code | Cat | Category name | Source layer |
|------|-----|---------------|--------------|
| `TPC0001` | C | Cryogenic | Terminal points |
| `TPC0002` | C | Cryogenic | Terminal points |
| `TPH0003` | H | HVAC | Terminal points |
| `TPC0004` | C | Cryogenic | Terminal points |
| `TPC0005` | C | Cryogenic | Terminal points |
| `TPC0006` | C | Cryogenic | Terminal points |
| `TPE0007` | E | Electrical | Terminal points |
| `TPC0008` | C | Cryogenic | Terminal points |
| `TPC0009` | C | Cryogenic | Terminal points |
| `TPE0010` | E | Electrical | Terminal points |
| `TPE0011` | E | Electrical | Terminal points |
| `TPC0012` | C | Cryogenic | Terminal points |
| `TPC0013` | C | Cryogenic | Terminal points |
| `TPC0014` | C | Cryogenic | Terminal points |
| `TPC0015` | C | Cryogenic | Terminal points |
| `TPE0016` | E | Electrical | Terminal points |
| `TPE0017` | E | Electrical | Terminal points |
| `TPC0018` | C | Cryogenic | Terminal points |
| `TPC0019` | C | Cryogenic | Terminal points |
| `TPC0020` | C | Cryogenic | Terminal points |
| `TPL0021` | L | Liquid | Terminal points |
| `TPL0022` | L | Liquid | Terminal points |

> RFCELL terminal points are not individually tagged in the source extract;
> RFCELL scope hand-over is represented by the same diamond convention where
> coupler/water interfaces leave the cell.

## 5. Machine-readable
The full code list (per drawing) is stored in `_build_meta.json` under
`scope_codes`.
