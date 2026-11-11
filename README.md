# Circuit

Standalone touchscreen hardware wallet built on Ika dWallet / 2PC-MPC signing.

## Status

| Phase | State |
|---|---|
| 1 — Hardware architecture | Draft for review: [docs/phase1/hardware-architecture.md](docs/phase1/hardware-architecture.md), [placement concept](docs/phase1/placement-concept.svg) |
| 2 — Industrial design | Not started |
| 3 — Component selection | Blocked on gate G1 (Ika user-side crypto benchmark) and datasheet verification |
| 4–5 — KiCad | Project and provisional board definition only: [hardware/README.md](hardware/README.md). No schematic sheets, no routing |
| 6–8 | Not started |

## Open gates

- **G1:** measure Ika user-side ECDSA sign and DKG on STM32U5G9 and STM32N657 dev kits. Decides the processor.
- **Datasheet pass:** component figures in Phase 1 came from search extracts, not from opened datasheets.
