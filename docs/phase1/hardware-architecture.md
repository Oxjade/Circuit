# Circuit — Phase 1: Hardware Architecture

Status: draft for review, 2026-11-11. Nothing in this document is a final part selection; Phase 3 locks parts.

## 0. Read this first

### How far the numbers are verified

- **Ika facts** were read from source: `dwallet-labs/ika` @ `186c0b3d` and `dwallet-labs/inkrypto` @ `26378df7`. Nothing was built or run, so every timing and memory figure for Ika is an estimate.
- **Component figures** come from search-index extracts of manufacturer and distributor pages. This session's network policy blocked st.com, nxp.com, ti.com, infineon.com, digikey.com, mouser.com and similar, so no datasheet PDF was opened directly. Exceptions read first-hand: TROPIC01 datasheet, Trezor/Coldcard/Keystone firmware repos, Apple Core NFC and Android NFC docs.
- **Prices and stock** are undated snapshots.
- Tags used below: **[C]** confirmed in a primary source read directly, **[E]** extracted from a cited page via search, **[EST]** my estimate, **[U]** unverified, **[P]** proposal.
- Before Phase 3 every [E] and [U] value on a shortlisted part must be re-read from its datasheet. Rule 3 of the brief (no selection without checking datasheets) is not yet satisfied for any part.

### Three findings that change the brief

1. **The stock Ika client cannot run on an STM32U5.** It is a `std` Rust crate, the WASM build is 4.1 MB [C], and the protocol public parameters it holds in RAM work out to about 44 MB per curve [EST from type definitions]. A purpose-built `no_std` port is required whatever processor is chosen.
2. **Signing cost depends on the chain.**
   - Solana, Sui and Bitcoin Taproot use Schnorr-family signing. The user side is elliptic-curve-only: one nonce, one hash, one scalar equation [C]. This fits a Cortex-M33 easily.
   - EVM and Bitcoin legacy/SegWit use ECDSA. The user side needs two class-group homomorphic evaluations with zero-knowledge proofs plus six EC proofs [C]. Estimate on a 160 MHz M33: 1–5 minutes per signature [EST]. Wallet creation (DKG) has similar class-group cost for every curve, once per wallet.
3. **Ika recovery does not revoke.** Re-encrypting a user share to a new device creates another copy; the old copy stays valid [C]. There is no guardian recovery in the protocol, only an example Move app ("ikavery") that gates the on-chain capability with m-of-n approval [C]. Real revocation therefore has to happen at the on-chain capability (`DWalletCap`), not at the share.

### Consequence: one gate before the MCU can be chosen

**Gate G1 — user-side crypto benchmark.** Until this is measured, the MCU decision is open. See section 3.4.

---

## 1. System hardware block diagram

```
                                  ┌──────────────────────────────────────────────┐
   USB-C receptacle               │              SECURE DOMAIN                   │
 ┌──────────────┐  D+/D-  ┌─────┐ │ ┌──────────────────────────────────────────┐ │
 │ VBUS CC1 CC2 ├────────►│ ESD ├─┼►│ USB (device)                             │ │
 └──┬───┬───┬───┘         └─────┘ │ │                                          │ │
    │   └───┴─ 5.1k Rd x2, CC ────┼►│ ADC (source current detect)              │ │
    │          20 V-tolerant ESD  │ │                                          │ │
    ▼                             │ │            MAIN MCU                      │ │
 ┌────────────────┐  I2C-SYS      │ │   TrustZone: secure world = boot, keys,  │ │
 │ Charger +      │◄──────────────┼►│   Ika core, parsers, UI, confirm logic   │ │
 │ power path     │  INT          │ │                                          │ │
 │ (ship mode)    │               │ │ LTDC RGB565 / FMC ──► 3.5" IPS LCD       │ │
 └──┬─────────┬───┘               │ │ SPI (init)        ──► LCD driver IC      │ │
    │ BAT     │ SYS               │ │ I2C-TOUCH + INT/RST ◄► cap-touch ctrl    │ │
    ▼         ▼                   │ │ PWM ──► backlight driver                 │ │
 ┌───────┐ ┌──────────────┐       │ │ GPIO (wake) ◄── CONFIRM button           │ │
 │ Li-Po │ │ Buck-boost   │ 3V3   │ │ GPIO (wake) ◄── POWER/LOCK button        │ │
 │ + PCM │ │ 3.3 V main   ├──────►│ │ I2C-SE (dedicated) ◄► Secure element     │ │
 │ + NTC │ └──────┬───────┘       │ │ OCTOSPI (optional) ◄► NOR flash          │ │
 └──┬────┘        │               │ │ Tamper pins, RTC, LSE 32.768 kHz         │ │
    │        load switches        │ │ SWD ◄── Tag-Connect pads (locked in prod)│ │
 ┌──┴────┐   ├─► LCD + backlight  │ └───────┬───────────────┬──────────────────┘ │
 │ Fuel  │   ├─► BLE module       └─────────┼───────────────┼────────────────────┘
 │ gauge │   ├─► NFC tag IC                 │ UART+RTS/CTS  │ I2C-SYS + field-detect
 └───────┘   └─► Haptic driver ─► LRA       ▼               ▼
  (I2C-SYS)      (I2C-SYS)          ┌──────────────┐  ┌─────────────┐
                                    │ BLE module   │  │ NFC dynamic │─── coil + ferrite
                                    │ (untrusted   │  │ tag IC      │    (rear cover)
                                    │  transport)  │  │ (untrusted) │
                                    └──────────────┘  └─────────────┘
```

Trust boundary: USB, BLE and NFC are all untrusted byte pipes. The MCU's secure world terminates one authenticated, encrypted application protocol over all three. The radio chips never see keys or plaintext.

Power rails (proposal): VBUS 5 V → charger → SYS (3.0–4.4 V) → buck-boost → 3V3_MAIN. Switched branches: 3V3_LCD, 3V3_BLE, 3V3_NFC, 3V3_HAPT. Backlight rail from a boost LED driver if the panel's LEDs are in series. A 1.8 V rail is added only if the chosen MCU or memory needs it.

---

## 2. Preliminary component architecture

| Function | Proposed primary | Alternate | Status |
|---|---|---|---|
| Main MCU | STM32U5G9 (M33, 160 MHz, 4 MB flash, 3 MB RAM) | STM32N657 (M55, 800 MHz); application processor if G1 fails | Open until G1 |
| Secure element | Infineon OPTIGA Trust M V3 | NXP SE050E; Tropic Square TROPIC01 as optional second SE | Proposal |
| Display | Displaytech DT035CTFT-IPS-SHB-PTS (3.5" IPS 320x480, ST7796, SPI + 16-bit RGB, 850 cd/m²) | BuyDisplay ER-TFT035IPS-6 + ER-TPC035-6 (ILI9488, 8080) | Proposal |
| Touch | Whatever the panel integrates (ST1633i on primary, FT6236 on alternate) | — | Follows panel |
| BLE | Raytac AN54LQ-15 module (nRF54L15), custom serial-pipe firmware | Raytac MDBT50Q-1MV2 (nRF52840) | Proposal |
| NFC | NXP NT3H2111 (NTAG I2C plus, Type 2) | ST ST25DV04KC (Type 5) | Decide after coupling test |
| Charger | TI BQ25180 (I2C linear, power path, ship mode) | Nordic nPM1300; TI BQ25896 if linear heat is a problem | Proposal |
| Main 3.3 V | TI TPS631000 buck-boost (1.5 A) | TPS63802; TPS63900 only if peak < 400 mA | Proposal |
| Fuel gauge | ADI MAX17260 | MAX17262 | Proposal |
| Battery | 503562-class Li-Po with PCM, about 1200–1265 mAh | Renata ICP543759PMT 1320 mAh | Depends on Phase 2 thickness |
| Haptics | TI DRV2605L + 8 mm LRA (Vybronics VG0832012) | DRV2625 | Optional feature |
| Buttons | Panasonic EVQ-P7 side-push (3.5 x 2.9 x 1.35 mm, 0.2 mm travel) | C&K KMR2 | Proposal |
| External flash | Winbond W25Q128JV (only if needed for assets/audit log) | W25Q256JV | Optional |
| USB protection | ST USBLC6-2SC6 on D±; 20 V-tolerant CC protection (TI TPD4S311 class) | TPD6S300 | Proposal |
| USB-C receptacle | 16-pin USB 2.0 type; exact part open (no mid-mount part verified) | GCT USB4105-GF-A, Hroparts TYPE-C-31-M-12 | Open |
| Debug | Tag-Connect TC2030-NL footprint | 10-pin 1.27 mm header on Rev A only | Proposal |

---

## 3. MCU requirements and candidate comparison

### 3.1 What the MCU must do

| Requirement | Driver |
|---|---|
| Run a `no_std` Rust port of Ika's user side | Sections 0 and 3.3 |
| Hold the user secret share and class-group decryption key in RAM while signing | Neither can live in a secure element (section 4.1) |
| Isolate secret-handling code from USB/BLE/NFC parsers | TrustZone or equivalent |
| Secure boot, signed firmware, anti-rollback, debug lock | Brief section 11 |
| Framebuffer for 320x480 RGB565 = 307,200 bytes | Smooth UI without SPI tearing |
| USB device, 3x I2C, UART, SPI, PWM, ADC, tamper, RTC | Section 9 |
| µA-class sleep | Battery product |
| Rust and RTOS support | embassy-stm32 and Zephyr both list U5, H5, H7RS, N6 [C] |

### 3.2 Candidates

| Part | Core / max | CoreMark | Flash | RAM | Isolation | USB | Display | Sleep | Price snapshot |
|---|---|---|---|---|---|---|---|---|---|
| STM32U585 | M33 160 MHz | 651 | 2 MB | 786 KB | TrustZone | FS | none | Stop 2 4–9 µA | $5.98 @100 |
| **STM32U5G9** | M33 160 MHz | 655 | 4 MB | 3 MB | TrustZone | HS, PHY on chip | LTDC, DSI | Stop 2 4–15.5 µA | $19.98 @1, $12.83 @1k |
| STM32H573 | M33 250 MHz | 1023 | 2 MB | 640 KB | TrustZone | FS | [U] | [U] | $9.53 @1 |
| STM32H7S7 | M7 600 MHz | 3196 | 64 KB boot | 620 KB | No TrustZone | HS | LTDC | [U] | ~$10 @reel |
| **STM32N657** | M55 800 MHz | 3360–3616 | none | 4.2 MB | TrustZone | HS, PHY on chip | LTDC | Stop about 9 mA (forum post) | $21.44 @1 |
| STM32MP135 | Cortex-A7 1 GHz | [U] | none | external DDR | TrustZone-A | HS | LCD | [U] | €8.93 @1 |

All figures [E]. The STM32U5 and N6 list side-channel-resistant AES and PKA. The PKA will not accelerate class-group arithmetic, so constant-time behaviour of that code is a software problem on any of these parts.

Precedent [C]: Trezor Safe 5 uses STM32U58x + OPTIGA Trust M. Trezor Safe 7 uses STM32U5G + TROPIC01 + OPTIGA, with an nRF52832 radio and nPM1300 PMIC. Ledger Stax/Flex use ST33K1M5 + STM32WB35. Coldcard Q uses STM32L4S + ATECC608 + DS28C36B. Passport Prime uses a Cortex-A5 SAMA5D27 + ATECC608C.

### 3.3 Estimated cost of Ika's user side on a 160 MHz Cortex-M33

| Operation | When | Flash | RAM | Time | Verdict |
|---|---|---|---|---|---|
| Schnorr-family sign (EdDSA, Taproot) | Every Solana / Sui / Taproot signature | < 150 KB | < 32 KB | 10–50 ms | Comfortable |
| DKG proof, EC part | Once per wallet | — | — | 1–5 s | Fine |
| ECDSA sign (secp256k1) | Every EVM / BTC legacy / SegWit signature | 300–600 KB | 100–300 KB | 1–5 min | Not acceptable as a product |
| Share encryption + proof, class-group keygen | Once per wallet, and on device replacement | similar | similar | tens of seconds to minutes | Tolerable as a one-time setup step |

All [EST], nothing measured. The estimate assumes a port without the 44 MB lookup tables.

### 3.4 Gate G1 and what follows from each outcome

Measurements needed, in order:

1. Run inkrypto's ignored `benchmark` tests natively on x86 to get "Centralized Party Total Time" for ECDSA sign, Schnorr sign and DKG. I attempted this; the session's permission policy blocked building external code.
2. Dump the serialized sizes of the protocol public parameters and the sign and DKG messages from a testnet session.
3. Cross-compile one `prove_committed_linear_evaluation` for `thumbv8m.main-none-eabihf` and time it on an STM32U5G9J-DK2 and an STM32N6570-DK, recording peak heap.

| G1 result for ECDSA sign | Processor | Product consequence |
|---|---|---|
| ≤ ~10 s on U5G9 | STM32U5G9 | All four ecosystems on-device, low-power design as drawn |
| Too slow on U5G9, ≤ ~10 s on N657 | STM32N657 | Flashless MCU, external NOR, multi-rail supply, hard power-gating in sleep, harder BGA |
| Too slow on both | Application processor with DDR (64-bit preferred for big-integer speed) | Different product: multi-stage secure boot, DDR layout, higher power, larger board. Re-plan Phases 2–5 |
| Any | STM32U5G9 with reduced scope | Ship Solana, Sui and Taproot on-device; EVM and BTC ECDSA deferred |

**Recommendation [P]:** buy both dev kits, run G1 before Phase 3, and keep STM32U5G9 as the working assumption for Phases 1–2 because it has the strongest wallet precedent, the lowest sleep current and enough RAM for a table-free port. Do not order custom PCBs before G1 closes.

Rejected: U585 and H573 (RAM too small for the ECDSA port plus framebuffer, FS USB only on H573), H7S7 (no TrustZone), i.MX RT1170 (flagged not-for-new-designs at DigiKey [E]), nRF54H20 (restricted sampling [E]).

---

## 4. Secure-element requirements and candidate comparison

### 4.1 What a secure element can and cannot do for Ika

| Secret | Nature | In a secure element? |
|---|---|---|
| User secret key share (one 32-byte scalar per dWallet) | Used inside protocol arithmetic (`z = k + e·x`, ECDSA proofs), not a standard signature | No. Lives on the MCU, stored encrypted under an SE-gated key |
| Class-group decryption key | Class-group math | No |
| 32-byte root seed (derives the class-group key and an Ed25519 "encryption signer" key) | Opaque bytes | Stored wrapped; released only after PIN |
| Sui account key that owns the `DWalletCap` | Standard signature key | **Yes.** This is the on-chain authority: `approve_message` requires the cap [C] |
| Device identity / attestation key | Standard signature key | Yes |

So no secure element runs any part of 2PC-MPC. Its job is: PIN-gated release of the storage key with a hardware attempt limit, a non-extractable authority key, device attestation, and monotonic counters for anti-rollback and replay protection.

Design point [P]: put the `DWalletCap`-owning Sui key in the secure element. Then a thief who extracts MCU flash gets an encrypted share and no ability to authorize a signature on-chain, and a lost device is revoked by moving the cap. Sui accepts Ed25519, secp256k1 and secp256r1 account keys; I state the secp256r1 option from prior knowledge and it must be confirmed against current Sui docs [U].

### 4.2 Candidates

| Part | secp256k1 | Ed25519 | P-256 | PIN-gated release with hardware attempt limit | Cert | Interface, package | SDK | Price snapshot |
|---|---|---|---|---|---|---|---|---|
| Infineon OPTIGA Trust M V3 (SLS32AIA010MK) | No | No | Yes | Yes. 4 monotonic counters, counter-limited objects; Trezor's flow is public [C] | CC EAL6+ | I2C, USON-10 3x3 | MIT C library, no NDA | $0.60–1.55 |
| NXP SE050E2HQ1/Z01Z3Z | Family yes; E2 row [U] | Family yes | Yes | UserID attempt counter, confirmed only at forum level | CC EAL6+ | I2C, HX2QFN20 3x3 | NXP middleware; Rust `se05x` crate is LGPL-3.0 | $3.72–3.87 @1 |
| Tropic Square TROPIC01 (TR01-C2P-T301) | No | Yes | Yes | Yes. MAC-and-Destroy PIN engine, 16 monotonic counters [C] | None found | SPI, QFN32 4x4 | libtropic, BSD-3-Clause-Clear | Not public |
| Microchip ATECC608C | No | No | Yes | Host-built from 2 counters + HMAC | JIL High [E] | I2C, UDFN8 | cryptoauthlib; full datasheet under NDA | ~$0.70–1.22 |
| ST STSAFE-A120 | No | Variant-dependent | Yes | [U] | CC EAL5+ | I2C, UFDFPN8 | STSELib | $2.66 @1 |
| Microchip TA101 | Sign only | Yes | Yes | [U] | [U] | SPI/I2C, SOIC-8 | [U] | [U] |

Figures [E] unless tagged. Other facts: SE050 power-down draws about 0.45 mA unless deep power-down is used. TROPIC01 idles at about 1.95 mA and sleeps at about 0.95 mA, is 3.3 V only, and had a 2026 laser fault-injection finding against its firmware verification; it must be power-gated if used.

### 4.3 Recommendation [P]

1. **OPTIGA Trust M V3 as primary.** Its PIN-stretching and attempt-limit flow is documented and field-proven, the host library is MIT-licensed, and it holds the Sui authority key as secp256r1. Risk: depends on the Sui secp256r1 confirmation above; no Rust driver verified.
2. **SE050E as the alternate**, and the fallback if the authority key must be Ed25519. It was the brief's initial candidate and is not ruled out. It needs its E2 feature table and attempt-limit behaviour confirmed in NXP AN12436 / the APDU spec before it can be primary.
3. **TROPIC01 as an optional second SE** from a different vendor, following the Trezor Safe 7 pattern. Decide in Phase 3; reserve board area.

Test before proceeding: on dev kits, implement PIN-gated secret release on both OPTIGA and SE050, measure unlock latency and sleep current, and confirm a Sui transaction signed by the SE verifies on testnet.

---

## 5. Display and touchscreen architecture

### 5.1 Candidates (all 3.5" IPS 320x480)

| Module | Driver | Interfaces | Outline mm | Brightness | Touch IC | Price @1 | Stock |
|---|---|---|---|---|---|---|---|
| Displaytech DT035CTFT-IPS-SHB-PTS | ST7796 | 4-wire SPI + 16-bit RGB | 54.4 x 86.24, thickness [U] | 850 cd/m² | Sitronix ST1633i | $52.71 Mouser | 158 Mouser, 283 DigiKey UK |
| BuyDisplay ER-TFT035IPS-6 + ER-TPC035-6 | ILI9488 | SPI, 8080 8/9/16-bit, RGB; 50-pin 0.5 mm FPC | 54.5 x 83.0 x 2.3 without touch | 300 cd/m² | FT6236 | ~$13 (breakout variant) | Maker stock |
| DisplayModule DM-TFT35-431 | ST7796S | SPI / MCU / RGB | 54.58 x 83.57 x 2.18 | 600 cd/m² | [U] | $39.90 | [U] |
| Focus LCDs E35RG13248LW2M450-C | ILI9488 | SPI, RGB, MCU | 61.9 x 91.04 x 3.88 with touch | 450 nits | FT6236 | $85.88 | 9 |
| Waveshare 3.5" Capacitive Touch LCD (SKU 29318) | ST7796S | SPI only, on carrier PCB | 61.0 x 92.44 | [U] | FT6336U | $18.99 | [U] |

All [E]. Active area for this glass size is 48.96 x 73.44 mm.

### 5.2 Interface decision

- A full frame is 307,200 bytes. The ST7796S SPI write cycle is 66 ns minimum, about 15 MHz, which gives about 6 full frames per second in spec [E]. SPI therefore only works with partial updates.
- **Proposal: drive the panel from the MCU's LTDC over 16-bit RGB, with SPI used for initialisation only**, and keep the framebuffer in internal RAM (10% of the U5G9's 3 MB). This costs about 20 pins and removes tearing. It also keeps displayed transaction data out of any external memory.
- If the BuyDisplay panel is used instead, drive it over 8080 16-bit through FMC; ILI9488 over SPI is worse than ST7796 (commonly 3 bytes per pixel) [U].
- Backlight: LED count, series/parallel wiring and current are unverified for every panel. Series LEDs need a boost driver (TI TPS61169 class); parallel LEDs can run from 3.3 V with a PWM FET. Decide from the panel datasheet.

### 5.3 Other notes

- No 3.0–3.2" panel at 320x480 was found; smaller means dropping to 240x400 or 240x320, or a custom panel.
- AMOLED at this size is not realistic for a documented prototype: no touch-integrated part with a public datasheet was found.
- Security: the touch controller and LCD buses are owned by the secure world only. The confirm action must come from the physical button, never from touch alone.
- Test on a dev kit: backlight current at target brightness, tearing with the TE pin, touch through the cover lens with the NFC coil and ferrite behind the panel, touch wake latency and sleep current.

**Recommendation [P]:** Displaytech as primary because it is the only one with distributor stock and a formal spec; BuyDisplay as the cost-down alternate. Buy a Waveshare 29318 for early ST7796 firmware work.

---

## 6. Connectivity architecture

### 6.1 Common rule

One application protocol runs over all three transports: authenticated key exchange at pairing, then encrypted, sequence-numbered frames carrying request ID, session ID and expiry. Protocol design belongs to Phase 6 and should use an existing, reviewed handshake pattern rather than a new one.

### 6.2 USB-C

- USB 2.0 device, 5 V sink only, no Power Delivery.
- 5.1 kΩ Rd on each of CC1 and CC2, separately. The MCU ADC reads the CC voltage to detect a 0.5 / 1.5 / 3 A source and sets the charger input limit.
- ESD: USBLC6-2SC6 on D± [E]. CC pins sit next to VBUS in the connector, so CC protection must tolerate 20 V (TPD4S311 class) [E].
- The BQ25180 input is 25 V tolerant [E], which covers a faulty charger without a separate over-voltage switch.
- Firmware servicing: a bootloader-only USB class that accepts signed images and nothing else. No vendor ROM DFU in production.
- Open: U5G9 has an HS PHY on chip, but full-speed is enough for this traffic; choose in Phase 4.

### 6.3 Bluetooth LE

- **Split design: a separate certified module used as an untrusted transport.** Putting the radio stack in the secure MCU (STM32WBA-style) would add a large link-layer and host stack to the trusted code and tie radio updates to wallet firmware updates.
- The module runs small custom firmware that exposes one GATT service as a framed serial pipe over UART with RTS/CTS. Standard HCI would put the Bluetooth host stack on the secure MCU, which is the attack surface this split is meant to avoid.
- The MCU can cut the module's supply with a load switch.

| Module | SoC | Size mm | RX / TX current | Price @1 | Note |
|---|---|---|---|---|---|
| Raytac AN54LQ-15 | nRF54L15 | 13.7 x 9.5 x 1.8 | 3.3–3.6 / 5–8.3 mA | $4.25 | Primary. Zephyr board support in tree [C]; module certification IDs [U] |
| Raytac MDBT50Q-1MV2 | nRF52840 | 10.5 x 15.5 x 2.05 | 4.6 / 4.8 mA (SoC) | $6.15 | Alternate, most mature |
| u-blox ANNA-B112 | nRF52832 | 6.5 x 6.5 x 1.2 | TX 5.3 mA | ~$8–10 | Smallest; availability patchy |

All [E]. Antenna keep-out dimensions were not retrievable and must come from the module drawing in Phase 2. Module certification only holds under the vendor's stated layout conditions.

### 6.4 NFC

Use case: the phone is the reader; the device presents a fresh, signed pairing payload. No secrets cross NFC.

| Part | Standard | Buffer | Wake | Price @1 | Note |
|---|---|---|---|---|---|
| NXP NT3H2111 / NT3H2211 | ISO 14443A, NFC Type 2 | 64-byte SRAM pass-through | Field-detect pin | $1.45 | Type 2 is in Android's mandatory NDEF set [C] |
| ST ST25DV04KC | ISO 15693, NFC Type 5 | 256-byte mailbox | GPO | ~€0.81 | iOS path proven by ST; Android Type 5 NDEF is device-dependent [C] |
| NXP NTA5332 (NTAG 5 boost) | Type 5, active load modulation | 256-byte SRAM | Event pin [U] | $1.91 | Fallback for a very small coil |
| NXP PN7160 / ST25R3916B | Full controller, card emulation | — | IRQ | $4–9 | Only if a Type 4 APDU exchange is needed; not justified here |

- iOS background tag reading needs an NDEF URI record that is a universal link, on iPhone XS or later [C]. So the pairing payload is a universal-link URL carrying an ephemeral public value and a signature.
- The LCD metal frame and battery pouch detune the coil. Plan a ferrite sheet between coil and metal and tune in the final stack (ST AN2866, NXP AN11276).
- **Proposal:** NT3H2111 primary, ST25DV04KC alternate. This ranking rests on Android's documented guarantee; RF coupling in the real enclosure could reverse it, so both get dev-kit tests before selection.

---

## 7. Battery and power-management architecture

### 7.1 Architecture [P]

| Block | Part | Key facts [E] |
|---|---|---|
| Charger + power path | TI BQ25180YBGR | I2C, linear, up to 1 A, JEITA, 25 V-tolerant input, ship mode 15 nA shutdown / 3.2 µA with button wake, pushbutton input. DSBGA-8, about 1.8 x 1.0 mm |
| Main rail | TI TPS631000 | Buck-boost, 1.5 A at 3.3 V for VIN ≥ 2.7 V, 8 µA quiescent |
| Fuel gauge | ADI MAX17260 | 5.1 µA |
| Branch switches | TI TPS22916 | 2 A, 10 nA leakage |
| Backlight | TI TPS61169 if LEDs are in series | Up to 38 V string |
| Haptics | TI DRV2605L + 8 mm LRA | I2C, 4 µA shutdown |
| Cell | 503562-class Li-Po with PCM | About 62–63.5 x 34–36 x 5–5.8 mm, 1200–1265 mAh; Jauch LP503562JU or Adafruit 258 |

Why discrete instead of an integrated PMIC:

- nPM1300's bucks are 200 mA each and cannot boost, so a separate buck-boost is needed anyway [E]. It remains the alternate because it adds CC detection, a watchdog and 370 nA ship mode, and Trezor Safe 7 uses it [C].
- MAX77654 / MAX77658 are rejected: 300 mA charge limit [E].
- TPS63900 (75 nA quiescent) is limited to 400 mA, which is marginal against a 450–500 mA peak [E].

### 7.2 Preliminary power budget, 1200 mAh

| State | Battery current | Life |
|---|---|---|
| Ship mode | 3–7 µA | Limited by cell self-discharge |
| Deep sleep | 12–25 µA | Limited by cell self-discharge |
| Standby with BLE advertising at about 1 s | 35–70 µA | 2–3.9 years on paper |
| Active UI, backlight 50% | 62–140 mA | 8.6–19 h continuous |
| Signing burst with haptic | up to about 450 mA | about 0.2 mAh per 2 s event |
| Charging from a 500 mA port | — | about 3.5–4 h |

Most inputs are assumed, not measured: MCU active current, backlight power, BLE average and protection-circuit drain. Example day: 10 minutes active plus standby is about 18 mAh, or roughly two months per charge. If G1 forces minute-long ECDSA signing, each such signature costs on the order of 1–3 mAh and this table must be redone.

### 7.3 Known issues to design around

- **Charger heat.** A linear charger at 600 mA dissipates about 0.8–1.2 W in a sealed enclosure and will throttle. If that is unacceptable, switch to BQ25896.
- **Tamper versus ship mode.** Ship mode cuts power to the MCU, so tamper detection during shipping needs an always-on path of a few µA ahead of the ship switch. Decide in Phase 4.
- **Dead-battery boot** on USB alone is unverified for the BQ25180.
- **Cell logistics.** Cells need a UN38.3 test summary to ship; maximum charge rate was not found for any candidate, so 0.5C is an assumption.
- **Package.** BQ25180 is a 0.4 mm-class wafer-level package; confirm the assembler can place it.

Test before proceeding: 3.3 V rail droop during crypto + haptic + backlight at 3.0–3.3 V cell voltage, charger temperature rise in a closed box, ship-mode entry/exit and real current, behaviour on 0.5 / 1.5 / 3 A sources.

---

## 8. Preliminary internal placement concept

Drawing: [placement-concept.svg](placement-concept.svg)

- **Envelope estimate: about 60 x 94 x 12–12.5 mm.** A 3.5" panel is 54.4–54.6 mm wide and 83–86 mm tall on its own, so the device cannot be narrower than about 58 mm. This is roughly credit-card footprint plus 8 mm in each direction.
- **Frame-shaped PCB with the battery in a cut-out**, both under the display. Stacking a full PCB under the battery would add about 3 mm.
- BLE antenna in a top corner with a copper keep-out. NFC coil on the rear cover over a ferrite sheet. USB-C at bottom centre with the charger and inductor beside it.
- Both buttons on one long edge, as side-actuated switches on the PCB edge. The confirm button is larger and separated from power/lock.
- If 12 mm is too thick for the product, the levers are a thinner, wider cell (reduces capacity or needs a custom cell) or a smaller display.

Every dimension is an estimate to be redone in CAD in Phase 2 from the chosen parts' mechanical drawings.

---

## 9. Hardware interface and peripheral matrix

Assumes the STM32U5G9 working choice.

| Peripheral | MCU interface | Signals | Wake source | Power-gated | World |
|---|---|---|---|---|---|
| LCD pixel data | LTDC RGB565 | 16 data + CLK, DE, HSYNC, VSYNC | — | Yes | Secure |
| LCD control | SPI1 + GPIO | SCK, MOSI, CS, DC, RESET, TE | — | Yes | Secure |
| Backlight | Timer PWM | 1 + enable | — | Yes | Secure |
| Touch controller | I2C1 (dedicated) | SDA, SCL, INT, RST | INT | With LCD | Secure |
| Secure element | I2C2 (dedicated) | SDA, SCL, RST/enable | — | Optional | Secure |
| Second SE (optional, TROPIC01) | SPI2 | 4 + power enable | — | Yes | Secure |
| System bus: charger, gauge, haptic driver, NFC tag | I2C3 | SDA, SCL | — | Partly | Secure driver |
| Charger | GPIO | INT | Yes | No | — |
| Fuel gauge | GPIO | ALRT | Yes | No | — |
| NFC tag | GPIO | Field-detect, power enable | Yes | Yes | Non-secure data path |
| BLE module | USART1 + GPIO | TX, RX, RTS, CTS, RESET, wake, power enable | Wake line | Yes | Non-secure data path |
| USB | USB OTG | D+, D−, VBUS sense | VBUS | — | Non-secure data path |
| USB-C CC | ADC | CC1, CC2 | — | — | — |
| Confirm button | GPIO, hardware debounced | 1 | Yes | — | Secure, read directly |
| Power/lock button | GPIO + charger pushbutton pin | 1 | Yes | — | Secure |
| Haptic driver | GPIO | Enable/trigger | — | Yes | — |
| External NOR (optional) | OCTOSPI | 6 (quad) | — | Optional | Encrypted contents only |
| Tamper | TAMP pins | 2–4 (count [U]) | Yes | Backup domain | Secure |
| Clocks | HSE, LSE | 4 | — | — | — |
| Debug | SWD | SWDIO, SWCLK, NRST, optional SWO | — | — | Locked in production |

Pin estimate: about 75–80 signals, so a package of 100 pins or more. The LQFP144 is 20 x 20 mm and does not fit the frame PCB; a BGA variant is needed, and its exact ordering code is unverified.

Bus rules: the secure element and the touch controller each get their own I2C bus so that a misbehaving or probed peripheral on the system bus cannot stall or observe PIN entry or SE traffic.

---

## 10. Unresolved engineering questions and risks

### 10.1 Blocking

| # | Question | Why it matters | How to close |
|---|---|---|---|
| R1 | Measured time and RAM of user-side ECDSA sign and DKG on M33 / M55 | Decides the processor and possibly the product class | Gate G1, section 3.4 |
| R2 | Can a `no_std`, table-free, constant-time port of the centralized party be built without modifying the protocol? | Brief forbids rewriting Ika cryptography; a port still needs independent review | Scope with Ika's maintainers; ask whether an embedded build is planned |
| R3 | What must the device verify about data the host supplies (presign output, network public output, protocol parameters)? The device has no chain access | A lying host is the main adversary | Protocol review with Ika; pin the dWallet public output at enrollment |
| R4 | Recovery design given no revocation and no protocol-level guardians | The 2-of-3 guardian proposal has to be built at the `DWalletCap` level, e.g. on the ikavery pattern | Design study before Phase 6; check whether share refresh is on Ika's roadmap |
| R5 | Datasheet verification of every shortlisted part | Brief rule 3 | Allow vendor and distributor hosts in this session, or supply PDFs |

### 10.2 Architecture

| # | Risk | Mitigation |
|---|---|---|
| R6 | The device must sign two things per operation: its Ika contribution and the Sui transaction calling `approve_message` / `request_sign`. It must check that the message in that Sui call is the transaction it displayed | Sui parser for the Ika calls is mandatory on-device even for non-Sui targets |
| R7 | Presign expiry is not enforced on-chain at the commit read | Device enforces request expiry itself |
| R8 | Legacy class-group key derivation differs between 32-bit and 64-bit targets | Use the V2 platform-independent derivation only |
| R9 | Which signature algorithms are enabled on Ika mainnet today is unchecked | Query on-chain config |
| R10 | Side-channel and fault resistance of class-group code on a general MCU is unstudied | Independent review; do not claim resistance |
| R11 | Sui secp256r1 account support (needed for the OPTIGA option) stated from memory | Confirm in Sui docs; otherwise SE050E or TROPIC01 for Ed25519 |
| R12 | A weaker fallback exists: Ika "shared" mode, where the user share is public and the device only guards the cap key. It would run on any MCU but trusts the network fully and is irreversible | Record as rejected unless G1 fails and scope cannot be cut |

### 10.3 Hardware

| # | Risk | Mitigation |
|---|---|---|
| R13 | Device envelope about 60 x 94 x 12 mm may not match the "compact" intent | Decide in Phase 2 with a printed mock-up |
| R14 | NFC coupling behind LCD frame and battery; Type 2 versus Type 5 | Dev-kit tests on several phones with the real stack |
| R15 | BLE antenna detuning by battery, LCD and hand; module certification conditions | Follow module layout rules; pre-scan |
| R16 | Linear charger heat in a sealed enclosure | Thermal test; BQ25896 fallback |
| R17 | Panel backlight wiring, thickness with touch, and FPC pinout unverified | Order samples and datasheets first |
| R18 | Fine-pitch BGA and wafer-level packages raise fabrication class and assembly cost | Confirm assembler capability before Phase 4 |
| R19 | No verified mid-mount 16-pin USB-C receptacle | Phase 2/3 search with mechanical drawings |
| R20 | Tamper monitoring is lost in ship mode | Always-on tamper path decision in Phase 4 |
| R21 | STM32N657 stop current in the mA range if G1 selects it | Hard power-gate; redo power budget |

### 10.4 Cost snapshot (prototype quantity, electronics only)

Display $13–53, MCU $13–21, battery $10–25, BLE $4–6, secure element $1–4, charger $2, NFC $1.50, flash $2, plus regulators, gauge, haptics, connectors and passives. Roughly $70–140 per unit before PCB and assembly, dominated by the display. Snapshot prices only.

---

## 11. What happens next

1. Close G1 (crypto benchmark) and R5 (datasheet verification). These are the only two items that block Phase 3.
2. Order dev kits: STM32U5G9J-DK2, STM32N6570-DK, OPTIGA Trust M and SE050 evaluation boards, Raytac AN54L15Q-DB, NTAG I2C plus and ST25DV kits, a Waveshare 29318 display, and display samples.
3. Start Phase 2 industrial design in parallel using the 60 x 94 x 12 mm envelope as the starting constraint.
