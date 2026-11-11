# Phase 1 addendum: Keystone 3 as a reference, and a counted Ika workload

Date: 2026-11-11. Sources: Keystone 3 schematic and BOM v3.2 published in `KeystoneHQ/keystone3-firmware/hardware/v3.2` (read directly), and a source read of `dwallet-labs/inkrypto` (nothing built or run).

## 1. What Keystone 3 actually contains

| Block | Keystone 3 (v3.2 BOM / schematic) |
|---|---|
| Main MCU | MegaHunt MH1903, BGA169. Linker script: 1 MB SRAM, 15 MB flash region |
| External memory | 64 Mbit QSPI PSRAM (APS6404L), 2 x 128 Mbit NOR flash (PY25Q128HA) |
| Secure elements | Maxim DS28S60, Microchip ATECC608B, Maxim MAX32520 |
| Display | 3.97" 480x800, 8-bit 8080 parallel, 40-pin FPC; capacitive touch on I2C |
| Backlight | SGM3726 boost LED driver, 40 mA |
| Charger | Awinic AW32001 (I2C), NTC input |
| Regulation | Four 3.3 V LDOs (SGM2028 x3, ME6119), switched by MCU enables. No buck-boost |
| Battery sensing | Resistor divider into an MCU ADC, gated by a FET. No fuel-gauge IC |
| Tamper | CR2016 coin cell feeding an always-on backup rail, tamper sensor inputs |
| USB | Separate port board: USB-C, two 5.1k CC resistors, WS3222D 6.8 V over-voltage protector, ESD diodes |
| Other | Camera (DVP), fingerprint module, microSD, vibration motor on a transistor, power key |
| Protection habits | 22 ohm series resistors on SPI/I2C lines to secure elements, 0402 ESD diode on almost every external signal |

So the observation is correct: electrically a hardware wallet is one secure MCU, memory, secure elements, a display and a simple power chain.

## 2. What Circuit should take from it

- **Power can be simpler than the Phase 1 proposal.** Linear charger plus LDOs plus ADC battery sensing is a shipped pattern. The buck-boost and fuel-gauge IC become optional improvements, not requirements. LDOs from a Li-Po mean the 3.3 V rail sags below about 3.4–3.5 V of cell voltage, which costs usable capacity; that is the trade.
- **A coin cell is the conventional answer to tamper during storage** (open risk R20).
- **An over-voltage protector on VBUS** next to the connector is cheap and removes reliance on the charger's input rating.
- **1 MB internal RAM plus 8 MB PSRAM** is what a multi-chain parser and UI used in practice. This supports choosing an MCU with multi-MB RAM (STM32U5G9: 3 MB internal).

## 3. Where Circuit differs from Keystone

Keystone signs with ordinary private keys. One signature is a few milliseconds on any MCU. Circuit's device, as specified in the brief, computes the user side of Ika 2PC-MPC. Counted from source for one ECDSA signature (EVM, Bitcoin legacy/SegWit):

| Work | Count |
|---|---|
| Variable-base class-group exponentiations, 256-bit public exponent | 12 |
| Variable-base, 1006-bit secret exponent | 8 |
| Variable-base, 1198-bit secret exponent | 8 |
| Fixed-base, 941-bit exponent | 8 |
| Total class-group form operations, table-free with a 4-bit window | about 28,000 doublings + 7,500 compositions |
| secp256k1 scalar multiplications | about 95 |

- Each form operation is several ~930-bit multiplications plus a partial extended GCD and a reduction, run in constant time over 2048-bit containers.
- The reference code speeds this up with lookup tables of about 395 KB each (built per call) and multi-MB fixed tables; a device port would have to reimplement encryption and linear evaluation without them.
- No timing data exists anywhere in the Ika repositories. The estimate stays at minutes per ECDSA signature on a 160 MHz Cortex-M33, unmeasured.

Schnorr-family signing (Solana, Sui, Bitcoin Taproot) has no class-group work on the user side. DKG can also be made light on the device: the class-group part of the DKG round is discarded by the reference code, leaving one mandatory share-encryption proof (four fixed-base 941-bit exponentiations) per wallet.

Other points confirmed in this pass:

- The device does not need to verify the presign; the protocol tolerates an unverified one by re-randomizing.
- The encrypted user share and its proof are mandatory for a zero-trust dWallet.
- Encryption-key registration is Ed25519 only. `DWalletCap` has no constraint on its owner's signature scheme.
- A presign must never be used twice; an offline device relies on the network to refuse reuse.
- First acceptance of the network's parameters is trust-on-first-use unless a 256-bit commitment is pinned on the device.

## 4. The decision this forces

Ika gives two places where the device can be the authority:

| | A. Device holds the on-chain capability only | B. Device holds the user share (the brief as written) |
|---|---|---|
| What the device signs | The Sui transaction that calls `approve_message` for the exact payload it displayed | That, plus the user-side 2PC-MPC message |
| Where the user share lives | Companion app | Device |
| Device crypto | One standard signature | Class-group proofs for ECDSA chains |
| Hardware | Keystone-class; any candidate MCU works | Processor undecided for ECDSA chains |
| What a compromised companion can do | Nothing without the device's approval, unless Ika's network also colludes or fails to enforce the capability | Nothing, cryptographically |
| Lost-device handling | Move the capability | Same, and the share copy on the old device stays valid |

**Recommended [proposal]: a hybrid.**

- The device always holds the capability key in the secure element and always parses, displays and approves the exact payload. This applies to every chain.
- For Solana, Sui and Taproot the device also holds the user share and computes the user-side signature, because it is cheap.
- For EVM and Bitcoin ECDSA the user share stays in the companion in the first hardware revision, and moves onto the device if the benchmark later shows acceptable times.

With the hybrid, the processor no longer blocks the schematic: STM32U5G9 is sufficient, and gate G1 becomes a later upgrade question instead of a blocker. The cost is that ECDSA chains depend on Ika's network enforcing the capability, which is weaker than the brief's intent and must be stated plainly in the product's security claims.
