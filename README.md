# BEST: reference booking-escrow contracts, tests, and simulations

This repository accompanies the article

> Setiawan, D., Stiawan, D., & Bin Idris, M. Y. *BEST: Design and Evaluation of a Blockchain Escrow for Tourism Bookings and Community Fund Allocation.* Revised manuscript submitted to the *Journal of Logistics, Informatics and Service Science*.

It contains everything needed to reproduce the numbers that Section 4 of the article reports for the reference contract and the models: the reference escrow contract, the verification scripts, the gas benchmark and its hard-fork checks, the transaction list of the public Sepolia campaign (including its two failed transactions), the cost model, and the discrete-event simulator.

> **Research prototype.**

**Version 1.1.0** corresponds to the first revision of the article (November 2026). Version 1.0.0 corresponded to the original submission.

## Mapping to the article

| Path | What it is | Article |
|---|---|---|
| `contracts/BookingEscrow.sol` | Six-state booking escrow; revenue split that preserves the total amount (hotel, platform, affiliate, SDG fund); push and accrue settlement | Sections 3.2.2–3.3; Fig. 2 |
| `contracts/MockStablecoin.sol` | Six-decimal ERC-20 test stablecoin | Section 3.3 |
| `contracts/test/ReentrantToken.sol` | Hostile token used only for the reentrancy test | Section 4.1 (ii) |
| `scripts/negative_tests.js` | 18 state-machine and access-control tests | Section 4.1 (i); Table 3 |
| `scripts/reentrancy_test.js` | Adversarial reentrancy test | Section 4.1 (ii) |
| `scripts/measure.js` | Gas of every function over 400 sequential bookings per mode, on-chain conservation check; `ANCHOR=1` keeps one deposit in escrow (overlapping-deposit condition); `HARDFORK=` selects the execution rules | Section 4.1 (iii), 4.2; Table 8 |
| `scripts/marginal_sdg.js` | Marginal gas of the SDG allocation | Section 4.5 |
| `scripts/sepolia_campaign.js` | Concurrent booking campaign (public Sepolia or a local Sepolia-configured chain) | Section 4.1 (v); Table 7 |
| `sim/params.py` | All model parameters | Table 6 |
| `sim/cost.py` | Cost model (H1), comparators, cancellation and worked-account cases, SDG overhead (H3) with withdrawal spreading, joint operating configurations | Sections 4.3, 4.5; Figs. 4–5; Table 9 |
| `sim/des.py` | Slot-level discrete-event simulation with a separate approval transaction; individual transactions and complete guest sequence | Section 4.4; Fig. 6 |
| `sim/diagrams.py` | Schematic figures (architecture, state model, PoC flow) | Figs. 1–3 |
| `sim/plotstyle.py` | Shared plotting style | Figs. 4–6 |
| `sim/generate_synthetic_bookings.py` | Illustrative Excel workbook of 1,000 synthetic records; **not** used for any reported number | — |

### Result files

| File | Contents | Article |
|---|---|---|
| `results/negative_tests.json`, `results/reentrancy.json` | Test outcomes | Section 4.1 |
| `results/slither.txt`, `results/slither.json` | Static analysis (Slither 0.11.6) | Section 4.1 (iv) |
| `results/gas.json` | Gas medians, escrow emptied after each booking (Hardhat, Cancun rules) | Table 8 |
| `results/gas_overlapping_deposit.json` | Same benchmark with one deposit kept in escrow | Table 8 |
| `results/gas_prague_hh2.29.json`, `results/gas_osaka_hh2.29.json` | Same benchmark under Prague and Osaka (Fusaka) rules with Hardhat 2.29.2: identical to `gas.json` | Section 4.2 |
| `results/marginal_sdg.json` | SDG marginal gas | Section 4.5 |
| `results/sepolia_public_onchain.csv` | All 75 transactions of the public campaign (hash, block, time, sender, function, booking ID where the explorer decoded it, status 1 = success / 0 = reverted, gas) | Table 7 |
| `results/dryrun_local_sepolia_like_*` | Trial run on a local Sepolia-configured chain (addresses exist only on that chain) | Section 7 |
| `results/cost.json` | All cost and H3 results; block `revision1` holds the analyses added in revision 1 | Sections 4.3, 4.5; Table 9 |
| `results/des.json` | Simulation results (S1, S3 grid, brackets) | Section 4.4 |

### Figure files

| File | Article | Produced by |
|---|---|---|
| `figures/fig2_arch.png` | Fig. 1 | `sim/diagrams.py` |
| `figures/fig3_fsm.png` | Fig. 2 | `sim/diagrams.py` |
| `figures/fig4_seq.png` | Fig. 3 | `sim/diagrams.py` |
| `figures/fig_cr.png` | Fig. 4 | `sim/cost.py` |
| `figures/fig_h3.png` | Fig. 5 | `sim/cost.py` |
| `figures/fig_latency.png` | Fig. 6 | `sim/des.py` |
| `figures/fig1_dsr.png`, `figures/fig_gas.png`, `figures/fig_tornado.png` | Not in the revised article (supplementary: DSR process, gas per function, one-at-a-time sensitivity; their content is in Table 2, Table 8, and Section 4.3) | `sim/diagrams.py`, `sim/cost.py` |

## Benchmark transaction sequence

`scripts/measure.js` deploys the token and escrow, funds 30 guest wallets, and runs 400 bookings one after another in each mode: `createBooking` → `confirmPayment` → (with probability 0.15) `cancel` → `refund`, otherwise time advance past check-out → `completeStay`. In accrue mode three recipients withdraw at the end. Because each booking finishes before the next starts, the push-mode escrow balance returns to zero after every booking; `ANCHOR=1` removes that effect. The first settlement to each of the 10 hotels is reported separately (`completeFirst`).

## Public Sepolia campaign and its two failed transactions

23 October 2026, after Sepolia's Glamsterdam upgrade; 5 guest wallets, 20 bookings, push settlement.

- BookingEscrow: [`0x96c319DA6E4DF9a6754daB94581f500B61581f51`](https://sepolia.etherscan.io/address/0x96c319DA6E4DF9a6754daB94581f500B61581f51) (same compiler metadata hash as the local build)
- MockStablecoin (mUSD): [`0xb1308c2d2146068f9B4F700E930965A775C1b580`](https://sepolia.etherscan.io/address/0xb1308c2d2146068f9B4F700E930965A775C1b580)
- 75 transactions: 12 set-up (2 deployments, 5 mints, 5 approvals) and 63 booking operations; 73 succeeded.
- Failed: `confirmPayment(7)` ([0xd965…e1](https://sepolia.etherscan.io/tx/0xd965422a44759ac615e6f434993a3bb6c65eced3effc61eb92d9795ba40b78e1)) and `confirmPayment(8)` ([0x457e…e9](https://sepolia.etherscan.io/tx/0x457e4a6abe029eae0df7e1673d32565cbdef78a82f1688a4409ff0fa7203f2e9)), both reverted with `NotGuest()`. Booking 7 belonged to wallet `0xA27C…d605` and booking 8 to `0x455c…376a` (BookingCreated events), but each wallet tried to pay the other's booking. The client paired the two concurrent bookings incorrectly; the contract rejected both payments and no funds moved. No retry was made, so bookings 7 and 8 stayed in PendingPayment.
- Fix in v1.1.0: `sepolia_campaign.js` takes the booking ID only from the guest's own `BookingCreated` event (matched by guest address and record hash) and checks `bookings(id).guest` before paying.

Local trial run:

```bash
DRYRUN=1 npx hardhat node                            # terminal 1
SKIP_FINALITY=1 LEAD_S=300 npx hardhat run scripts/sepolia_campaign.js --network localdry   # terminal 2
```

Public Sepolia (dedicated test accounts only; never commit or share private keys — `*_ephemeral_wallets.json` and `.env` are excluded by `.gitignore`):

```bash
export SEPOLIA_RPC_URL=https://...
export SEPOLIA_PRIVATE_KEY=0x...
N_BOOKINGS=20 GUESTS=5 LEAD_S=600 STAY_S=120 LABEL=sepolia_run1 \
  npx hardhat run scripts/sepolia_campaign.js --network sepolia
```

## Requirements

- Node.js 20 or later (tested with 22); Hardhat 2.22.17 (pinned). The Prague and Osaka checks used Hardhat 2.29.2.
- Python 3.10 or later with the packages in `requirements.txt`
- Optional: `slither-analyzer` 0.11.6

## Reproducing the results

```bash
npm install
npx hardhat compile                                  # Solidity 0.8.24, optimizer 200 runs, EVM target cancun

N=400 npx hardhat run scripts/measure.js                                   # -> results/gas.json
ANCHOR=1 GAS_OUT=results/gas_overlapping_deposit.json npx hardhat run scripts/measure.js
npx hardhat run scripts/marginal_sdg.js              # -> results/marginal_sdg.json
npx hardhat run scripts/negative_tests.js            # -> results/negative_tests.json (18/18 expected)
npx hardhat run scripts/reentrancy_test.js           # -> results/reentrancy.json (0 successful re-entries expected)

pip install -r requirements.txt
cd sim
python3 cost.py                                      # -> results/cost.json, Figs. 4–5
python3 des.py                                       # -> results/des.json, Fig. 6 (about 2 min)
python3 diagrams.py                                  # -> schematic figures
```

Hard-fork check (Hardhat ≥ 2.26): `HARDFORK=prague N=400 GAS_OUT=results/gas_prague.json npx hardhat run scripts/measure.js`, likewise with `osaka`.

Seeds are fixed (cost model 20261022, 200,000 synthetic bookings; simulation seeds in `des.py`). Repeated runs reproduce the reported medians exactly.

## Simulation settings (Section 4.4)

Poisson arrivals of booking requests and check-out settlements at 303.7 bookings/day × *m*; every guest new (approve → createBooking → confirmPayment, one lognormal wallet delay, median 10 s, before each of the last two); background utilization Beta(50*u*, 50(1−*u*)) independent per slot; 1% missed slots; 1-s submission cutoff; FIFO inclusion; runs start empty; the first 10% of each horizon is warm-up; only included transactions enter latency statistics, and the completed share of sequences is reported.

## What is not included

- The BEST CMS plug-in (proof of concept) is available from the corresponding author on reasonable request. Its claims in the article are limited to the functional demonstration in Section 4.1; no result of the reference contract or the models depends on it.
- No integration between the CMS and BookingEscrow, no hotel-cancellation or dispute procedure, and no Rupiah conversion are implemented (Table 5 of the article).
- All booking records are synthetic; no guest or listing data are included.

## License and citation

MIT License (see `LICENSE`). Please cite the article (see `CITATION.cff`).

Contact: Dodi Setiawan, Faculty of Engineering, Universitas Sriwijaya, Palembang, Indonesia — setiawan@pbc.ac.id
