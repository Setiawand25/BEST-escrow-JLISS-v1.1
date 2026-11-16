"""Generates a SYNTHETIC dataset of 1,000 bookings that spans the five BEST layers.

The records are not real bookings. They are drawn from the same distributions the
manuscript uses (Table 6, sim/params.py): lognormal nightly price around SGD 378
(sigma 0.5), stay length 1 + Poisson(1) capped at 7 nights, two guests per party,
15% cancellations, and the measured median gas of the reference contract.
Derived columns are Excel formulas that reference the Parameters sheet.
Usage: python3 generate_synthetic_bookings.py [output.xlsx]
"""
import sys, hashlib, datetime as dt, pathlib
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from params import (NIGHTLY_SGD, SGD_USD, ETH_USD, RAMP_FEE, PRICE_SIGMA, LEGACY_LOW, SPEC_REVISED,
                    GAS_CREATE, GAS_CONFIRM, GAS_COMPLETE, GAS_APPROVE, GAS, SLOT_S, P_MISS, T_CUTOFF,
                    WALLET_MEDIAN_S, WALLET_SIGMA)

OUT = sys.argv[1] if len(sys.argv) > 1 else str(pathlib.Path(__file__).resolve().parents[1] / "BEST_synthetic_bookings_1000.xlsx")
N, SEED = 1000, 20261025
rng = np.random.default_rng(SEED)

# generation assumptions (documented in the README sheet)
CANCEL_SHARE = 0.15                      # as in the manuscript's conservation test
NEW_GUEST_SHARE = 0.60                   # assumption for this dataset
CHANNELS = ["CMS booking page: direct visit", "CMS booking page: content/affiliate referral"]
CH_P = np.array([0.60, 0.40])            # referral mix (assumption); shares are fixed in the contract either way
USD_IDR = 16500.0                        # assumption, update before use

stat = lambda mode, fn: next(x for x in GAS if x["mode"] == mode)["stats"][fn]["median"]
REFUND = {m: stat(m, "refund") for m in ("push", "accrue")}
CANCEL = stat("push", "cancel")

# ---------- draw the random inputs ----------
channel = rng.choice(CHANNELS, N, p=CH_P)
start = dt.date(2025, 1, 1)
checkin = [start + dt.timedelta(days=int(d)) for d in rng.integers(0, 365, N)]
nights = np.minimum(1 + rng.poisson(1.0, N), 7)
nightly_sgd = np.round(NIGHTLY_SGD * np.exp(rng.normal(0, PRICE_SIGMA, N)), 2)
guest = np.where(rng.random(N) < NEW_GUEST_SHARE, "New", "Returning")
mode = np.where(rng.random(N) < 0.5, "push", "accrue")
state = np.where(rng.random(N) < CANCEL_SHARE, "Refunded", "Completed")
wallet_s = np.round(WALLET_MEDIAN_S * np.exp(rng.normal(0, WALLET_SIGMA, N)), 1)
t_sub = rng.uniform(0, SLOT_S, N)
next_slot = np.ceil((t_sub + T_CUTOFF) / SLOT_S) * SLOT_S
missed = rng.geometric(1 - P_MISS, N) - 1
incl_s = np.round(next_slot - t_sub + SLOT_S * missed, 2)
salts = rng.integers(0, 2**63, N)

# ---------- workbook ----------
wb = Workbook()
F = "Arial"
hdr = Font(name=F, bold=True, color="FFFFFF"); body = Font(name=F, size=10)
blue = Font(name=F, size=10, color="0000FF"); bold = Font(name=F, bold=True)
thin = Side(style="thin", color="BFBFBF")
LAYER_FILL = {1: "1F3A5F", 2: "245F7A", 3: "2E86AB", 4: "3F8F5F", 5: "14365C", 0: "595959"}

# Parameters sheet
ps = wb.active; ps.title = "Parameters"
params = [
    ("Nightly price, mean (SGD)", NIGHTLY_SGD, "Authors' assumption (Section 3.4, Table 6)"),
    ("Exchange rate SGD→USD", SGD_USD, "Authors' assumption (Table 6)"),
    ("Exchange rate USD→IDR", USD_IDR, "ASSUMPTION for this dataset only – update to the rate you want to use"),
    ("Ether price (USD)", ETH_USD, "Authors' assumption, reference value (Table 6)"),
    ("Gas price (gwei)", 10, "Reference value of the cost model (Table 6)"),
    ("Conversion fee (fraction)", RAMP_FEE, "Authors' assumption (Table 6)"),
    ("Platform share (bps)", int(SPEC_REVISED["p"] * 10000), "Revised specification 90/5/3/2 (Table 2)"),
    ("Affiliate share (bps)", int(SPEC_REVISED["c"] * 10000), "Revised specification 90/5/3/2 (Table 2)"),
    ("SDG fund share (bps)", int(SPEC_REVISED["s"] * 10000), "Revised specification 90/5/3/2 (Table 2)"),
    ("Legacy cost band, lower bound", LEGACY_LOW, "OTA 15% + card 2.5% (Table 6)"),
    ("Gas: createBooking()", GAS_CREATE["push"], "Measured median, Cancun rules (Table 8)"),
    ("Gas: confirmPayment(), push", GAS_CONFIRM["push"], "Measured median (Table 8)"),
    ("Gas: confirmPayment(), accrue", GAS_CONFIRM["accrue"], "Measured median (Table 8)"),
    ("Gas: completeStay(), push", GAS_COMPLETE["push"], "Measured median (Table 8)"),
    ("Gas: completeStay(), accrue", GAS_COMPLETE["accrue"], "Measured median (Table 8)"),
    ("Gas: cancel()", CANCEL, "Measured median (Table 8)"),
    ("Gas: refund(), push", REFUND["push"], "Measured median (Table 8)"),
    ("Gas: refund(), accrue", REFUND["accrue"], "Measured median (Table 8)"),
    ("Gas: approve() for a new guest", GAS_APPROVE, "Measured (Table 8)"),
]
ps["A1"] = "Parameters (blue = editable input; every Dataset formula reads these cells)"; ps["A1"].font = bold
for j, h in enumerate(["Parameter", "Value", "Source"], 1):
    c = ps.cell(row=2, column=j, value=h); c.font = hdr; c.fill = PatternFill("solid", fgColor="595959")
P = {}
for i, (k, v, src) in enumerate(params, start=3):
    ps.cell(row=i, column=1, value=k).font = body
    c = ps.cell(row=i, column=2, value=v); c.font = blue
    if "USD→IDR" in k: c.fill = PatternFill("solid", fgColor="FFFF00")
    ps.cell(row=i, column=3, value=src).font = body
    P[k] = f"Parameters!$B${i}"
ps["B12"].number_format = "0.0%"; ps["B8"].number_format = "0.0%"
ps["B5"].number_format = "#,##0"; ps.column_dimensions["A"].width = 34; ps.column_dimensions["B"].width = 12; ps.column_dimensions["C"].width = 62

# Dataset sheet
ds = wb.create_sheet("Dataset")
cols = [  # (layer, header, width, kind)
    (0, "booking_id", 11, "v"),
    (1, "channel", 23, "v"), (1, "check_in_date", 12, "v"), (1, "nights", 7, "v"), (1, "check_out_date", 12, "f"),
    (1, "party_size", 8, "v"), (1, "guest_status", 10, "v"),
    (2, "nightly_rate_SGD", 11, "v"), (2, "booking_value_SGD", 12, "f"), (2, "fx_SGD_USD", 9, "f"),
    (2, "booking_value_USD", 12, "f"), (2, "booking_value_IDR", 14, "f"), (2, "payment_route", 30, "v"),
    (2, "conversion_fee_USD", 11, "f"),
    (3, "settlement_mode", 10, "v"), (3, "final_state", 10, "v"), (3, "escrow_amount_units", 14, "f"),
    (3, "platform_share_units", 13, "f"), (3, "affiliate_share_units", 13, "f"), (3, "sdg_share_units", 12, "f"),
    (3, "hotel_share_units", 13, "f"), (3, "refund_units", 12, "f"), (3, "conservation_ok", 11, "f"),
    (4, "record_hash_sha3", 22, "v"), (4, "wallet_approval_s", 10, "v"), (4, "record_complete", 10, "f"),
    (4, "cr_total", 9, "f"), (4, "below_legacy_band", 10, "f"),
    (5, "network", 30, "v"), (5, "inclusion_latency_s", 10, "v"), (5, "lifecycle_gas", 11, "f"), (5, "gas_cost_USD", 10, "f"),
]
L = {h: get_column_letter(i + 1) for i, (_, h, _, _) in enumerate(cols)}
LAYER_NAME = {0: "ID", 1: "Layer 1 – Client", 2: "Layer 2 – Application and payment",
              3: "Layer 3 – Smart contracts", 4: "Layer 4 – Data", 5: "Layer 5 – Blockchain"}
# row 1: layer bands (merged)
i = 0
while i < len(cols):
    lay = cols[i][0]; j = i
    while j + 1 < len(cols) and cols[j + 1][0] == lay: j += 1
    ds.merge_cells(start_row=1, start_column=i + 1, end_row=1, end_column=j + 1)
    c = ds.cell(row=1, column=i + 1, value=LAYER_NAME[lay]); c.font = hdr; c.alignment = Alignment(horizontal="center")
    for k in range(i, j + 1):
        ds.cell(row=1, column=k + 1).fill = PatternFill("solid", fgColor=LAYER_FILL[lay])
    i = j + 1
for k, (lay, h, w, _) in enumerate(cols, 1):
    c = ds.cell(row=2, column=k, value=h); c.font = hdr; c.fill = PatternFill("solid", fgColor=LAYER_FILL[lay])
    c.alignment = Alignment(wrap_text=True, vertical="center"); ds.column_dimensions[get_column_letter(k)].width = w
ds.row_dimensions[2].height = 30

bp, bc, bs = P["Platform share (bps)"], P["Affiliate share (bps)"], P["SDG fund share (bps)"]
for r in range(N):
    R = r + 3
    rec = f"BK-{r+1:04d}|{checkin[r].isoformat()}|{int(nights[r])}|{nightly_sgd[r]:.2f}|{salts[r]}"
    vals = {
        "booking_id": f"BK-{r+1:04d}", "channel": channel[r], "check_in_date": checkin[r], "nights": int(nights[r]),
        "party_size": 2, "guest_status": guest[r], "nightly_rate_SGD": float(nightly_sgd[r]),
        "payment_route": "Stablecoin escrow → licensed provider → Rupiah to hotel", "settlement_mode": mode[r], "final_state": state[r],
        "record_hash_sha3": "0x" + hashlib.sha3_256(rec.encode()).hexdigest(), "wallet_approval_s": float(wallet_s[r]),
        "network": "Ethereum EVM (simulated, Cancun gas rules)", "inclusion_latency_s": float(incl_s[r]),
    }
    f = {
        "check_out_date": f"={L['check_in_date']}{R}+{L['nights']}{R}",
        "booking_value_SGD": f"=ROUND({L['nightly_rate_SGD']}{R}*{L['nights']}{R},2)",
        "fx_SGD_USD": f"={P['Exchange rate SGD→USD']}",
        "booking_value_USD": f"=ROUND({L['booking_value_SGD']}{R}*{L['fx_SGD_USD']}{R},2)",
        "booking_value_IDR": f"=ROUND({L['booking_value_USD']}{R}*{P['Exchange rate USD→IDR']},0)",
        "conversion_fee_USD": f"=ROUND({L['booking_value_USD']}{R}*{P['Conversion fee (fraction)']},2)",
        "escrow_amount_units": f"=ROUND({L['booking_value_USD']}{R}*10^6,0)",
        "platform_share_units": f'=IF({L["final_state"]}{R}="Completed",INT({L["escrow_amount_units"]}{R}*{bp}/10000),0)',
        "affiliate_share_units": f'=IF({L["final_state"]}{R}="Completed",INT({L["escrow_amount_units"]}{R}*{bc}/10000),0)',
        "sdg_share_units": f'=IF({L["final_state"]}{R}="Completed",INT({L["escrow_amount_units"]}{R}*{bs}/10000),0)',
        "hotel_share_units": f'=IF({L["final_state"]}{R}="Completed",{L["escrow_amount_units"]}{R}-{L["platform_share_units"]}{R}-{L["affiliate_share_units"]}{R}-{L["sdg_share_units"]}{R},0)',
        "refund_units": f'=IF({L["final_state"]}{R}="Refunded",{L["escrow_amount_units"]}{R},0)',
        "conservation_ok": f"={L['platform_share_units']}{R}+{L['affiliate_share_units']}{R}+{L['sdg_share_units']}{R}+{L['hotel_share_units']}{R}+{L['refund_units']}{R}={L['escrow_amount_units']}{R}",
        "record_complete": f'=IF(COUNTBLANK(A{R}:{L["wallet_approval_s"]}{R})=0,"Complete","Missing")',
        "lifecycle_gas": (f'={P["Gas: createBooking()"]}'
                          f'+IF({L["settlement_mode"]}{R}="push",{P["Gas: confirmPayment(), push"]},{P["Gas: confirmPayment(), accrue"]})'
                          f'+IF({L["final_state"]}{R}="Completed",IF({L["settlement_mode"]}{R}="push",{P["Gas: completeStay(), push"]},{P["Gas: completeStay(), accrue"]}),'
                          f'{P["Gas: cancel()"]}+IF({L["settlement_mode"]}{R}="push",{P["Gas: refund(), push"]},{P["Gas: refund(), accrue"]}))'
                          f'+IF({L["guest_status"]}{R}="New",{P["Gas: approve() for a new guest"]},0)'),
        "gas_cost_USD": f"=ROUND({L['lifecycle_gas']}{R}*{P['Gas price (gwei)']}*10^-9*{P['Ether price (USD)']},4)",
        "cr_total": (f'=IF({L["final_state"]}{R}="Completed",{L["gas_cost_USD"]}{R}/{L["booking_value_USD"]}{R}'
                     f'+{P["Conversion fee (fraction)"]}+({bp}+{bc})/10000,"")'),
        "below_legacy_band": f'=IF({L["cr_total"]}{R}="","",{L["cr_total"]}{R}<{P["Legacy cost band, lower bound"]})',
    }
    for k, (lay, h, w, kind) in enumerate(cols, 1):
        c = ds.cell(row=R, column=k, value=vals.get(h) if kind == "v" else f[h]); c.font = body
for h, fmt in [("check_in_date", "yyyy-mm-dd"), ("check_out_date", "yyyy-mm-dd"), ("nightly_rate_SGD", "#,##0.00"),
               ("booking_value_SGD", "#,##0.00"), ("fx_SGD_USD", "0.000"), ("booking_value_USD", "#,##0.00"),
               ("booking_value_IDR", "#,##0"), ("conversion_fee_USD", "#,##0.00"), ("escrow_amount_units", "#,##0"),
               ("platform_share_units", "#,##0"), ("affiliate_share_units", "#,##0"), ("sdg_share_units", "#,##0"),
               ("hotel_share_units", "#,##0"), ("refund_units", "#,##0"), ("cr_total", "0.0%"), ("lifecycle_gas", "#,##0"),
               ("gas_cost_USD", "#,##0.0000")]:
    for R in range(3, N + 3): ds[f"{L[h]}{R}"].number_format = fmt
ds.freeze_panes = "B3"; ds.auto_filter.ref = f"A2:{get_column_letter(len(cols))}{N+2}"
ds["A2"].comment = Comment("SYNTHETIC record generated by sim/generate_synthetic_bookings.py (seed 20261025). Not a real booking.", "BEST")

# Summary sheet (formulas only)
sm = wb.create_sheet("Summary"); last = N + 2
rng_ = lambda h: f"Dataset!${L[h]}$3:${L[h]}${last}"
rows = [("Records", f"=COUNTA({rng_('booking_id')})", "0"),
        ("Completed bookings", f'=COUNTIF({rng_("final_state")},"Completed")', "0"),
        ("Canceled and refunded", f'=COUNTIF({rng_("final_state")},"Refunded")', "0"),
        ("Conservation violations", f'=COUNTIF({rng_("conservation_ok")},FALSE)', "0"),
        ("Incomplete records", f'=COUNTIF({rng_("record_complete")},"Missing")', "0"),
        ("Mean booking value (USD)", f"=AVERAGE({rng_('booking_value_USD')})", "#,##0.00"),
        ("Total escrowed (USD)", f"=SUM({rng_('escrow_amount_units')})/10^6", "#,##0.00"),
        ("SDG fund total (USD)", f"=SUM({rng_('sdg_share_units')})/10^6", "#,##0.00"),
        ("Mean CR_total, completed", f"=AVERAGE({rng_('cr_total')})", "0.0%"),
        ("Share of completed bookings below legacy band", f'=COUNTIF({rng_("below_legacy_band")},TRUE)/COUNTIF({rng_("final_state")},"Completed")', "0.0%"),
        ("Mean lifecycle gas", f"=AVERAGE({rng_('lifecycle_gas')})", "#,##0"),
        ("Mean inclusion latency (s)", f"=AVERAGE({rng_('inclusion_latency_s')})", "0.00"),
        ("Mean wallet approval (s)", f"=AVERAGE({rng_('wallet_approval_s')})", "0.0")]
sm["A1"] = "Summary of the synthetic dataset (all values are formulas)"; sm["A1"].font = bold
for i, (k, fml, fmt) in enumerate(rows, start=3):
    sm.cell(row=i, column=1, value=k).font = body
    c = sm.cell(row=i, column=2, value=fml); c.font = body; c.number_format = fmt
r0 = len(rows) + 5
sm.cell(row=r0, column=1, value="Bookings by channel").font = bold
for i, ch in enumerate(CHANNELS, start=r0 + 1):
    sm.cell(row=i, column=1, value=ch).font = body
    sm.cell(row=i, column=2, value=f'=COUNTIF({rng_("channel")},A{i})').font = body
sm.column_dimensions["A"].width = 46; sm.column_dimensions["B"].width = 16

# README sheet
rd = wb.create_sheet("README", 0)
lines = [
    ("BEST – synthetic booking dataset (1,000 records, five layers)", True),
    ("SYNTHETIC DATA. These are not real bookings, guests, or blockchain transactions.", True),
    ("Purpose: illustrate the structure of booking records across the five BEST layers (Fig. 2 of the manuscript).", False),
    ("Generator: sim/generate_synthetic_bookings.py, random seed 20261025 (re-running it reproduces the file).", False),
    ("", False),
    ("How the records are drawn (same distributions as the manuscript, Table 6):", True),
    ("• Nightly price: lognormal around SGD 378, sigma 0.5; stay length 1 + Poisson(1), capped at 7 nights; 2 guests per party.", False),
    ("• Check-in dates: uniform over 2025. Cancellations: 15% (canceled and refunded).", False),
    ("• Channel (assumption): all records are bookings made on the CMS booking page, 60% direct visits and 40% content/affiliate referrals; the revenue shares are fixed in the contract either way.", False),
    ("• New vs returning guest (assumption): 60% / 40%. Settlement mode: 50% push, 50% accrue.", False),
    ("• Wallet approval: lognormal, median 10 s, sigma 0.5. Inclusion latency: 12-s slots, 1-s cutoff, 1% missed slots.", False),
    ("", False),
    ("Formulas: value, share, gas, and cost columns are Excel formulas that read the Parameters sheet.", False),
    ("Edit only the blue cells on the Parameters sheet; the yellow cell (USD→IDR) is an assumption you should set.", False),
    ("Shares follow Eqs. (1)–(2): platform, affiliate, and SDG shares are rounded down; the hotel receives the remainder.", False),
    ("Stablecoin amounts are in base units with 6 decimals (1 USD = 1,000,000 units).", False),
    ("record_hash_sha3 is an illustrative SHA3-256 hash of the synthetic record and a random salt (no personal data).", False),
    ("No transaction hashes are included: no transactions were sent for these records.", False),
    ("", False),
    ("Layers:", True),
    ("Layer 1 – Client: channel, dates, nights, party size, guest status.", False),
    ("Layer 2 – Application and payment: prices, exchange rates, payment route, conversion fee.", False),
    ("Layer 3 – Smart contracts: settlement mode, final state, escrow amount, revenue shares, refund, conservation check.", False),
    ("Layer 4 – Data: record hash, wallet approval time, completeness check, CR_total, legacy-band check.", False),
    ("Layer 5 – Blockchain: network, inclusion latency, life-cycle gas, gas cost.", False),
]
for i, (t, b) in enumerate(lines, 1):
    c = rd.cell(row=i, column=1, value=t); c.font = Font(name=F, bold=b, size=11 if i > 1 else 13, color="C00000" if i == 2 else "000000")
rd.column_dimensions["A"].width = 120
wb.save(OUT); print(OUT)
