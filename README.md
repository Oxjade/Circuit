# Circuit

Standalone touchscreen hardware wallet built on Ika dWallet / 2PC-MPC signing.

## Status

| Phase | State |
|---|---|
| 1 — Hardware architecture | Draft for review: [docs/phase1/hardware-architecture.md](docs/phase1/hardware-architecture.md), [placement concept](docs/phase1/placement-concept.svg) |
| 2 — Industrial design | Not started |
| 3 — Component selection | Blocked on gate G1 (Ika user-side crypto benchmark) and datasheet verification |
| 4–5 — KiCad | Provisional board definition and two draft schematic sheets (USB-C; haptics, buttons, debug): [hardware/README.md](hardware/README.md). No routing |
| 6–8 | Not started |

## Open gates

- **G1:** measure Ika user-side ECDSA sign and DKG on STM32U5G9 and STM32N657 dev kits. Decides the processor.
- **Architecture decision:** capability-only, share-on-device, or hybrid. See [addendum](docs/phase1/addendum-keystone-and-ika-opcount.md). The hybrid would unblock the processor choice.
- **Datasheet pass:** component figures in Phase 1 came from search extracts, not from opened datasheets.
