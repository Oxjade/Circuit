# Circuit

Standalone touchscreen hardware wallet built on Ika dWallet / 2PC-MPC signing.

## Status

| Phase | State |
|---|---|
| 1 — Hardware architecture | Draft for review: [docs/phase1/hardware-architecture.md](docs/phase1/hardware-architecture.md), [placement concept](docs/phase1/placement-concept.svg) |
| 2 — Industrial design | Not started |
| 3 — Component selection | MCU decided: STM32U5G9 (hybrid architecture accepted). Other parts proposed, pending datasheet verification |
| 4–5 — KiCad | Provisional board definition and three draft schematic sheets (USB-C; haptics, buttons, debug; main MCU): [hardware/README.md](hardware/README.md). No routing |
| 6–8 | Not started |

## Open gates

- **G1 (no longer blocking):** measure Ika user-side ECDSA sign on the STM32U5G9 dev kit. Decides whether the ECDSA user share can later move onto the device.
- **Datasheet pass:** component figures in Phase 1 came from search extracts, not from opened datasheets.
