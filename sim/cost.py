"""Cost-ratio (H1), SDG-allocation overhead (H3) and sensitivity analysis.
Writes results/cost.json and figures fig_gas.png, fig_cr.png, fig_tornado.png, fig_h3.png."""
import json, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from params import *

rng = np.random.default_rng(20261022)
OUT = ROOT / "results"; FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
C1, C2, C3, C4, INK, MUTED = "#2a78d6", "#eb6834", "#1baf7a", "#6250d6", "#0b0b0b", "#52514e"
plt.rcParams.update({"font.family": "serif", "font.size": 8.5, "axes.labelsize": 8.5, "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "grid.color": "#e4e3df",
                     "grid.linewidth": 0.5, "axes.spines.top": False, "axes.spines.right": False,
                     "legend.frameon": False, "savefig.dpi": 300})

def sample_values(n):
    nightly = NIGHTLY_USD * np.exp(rng.normal(0, PRICE_SIGMA, n))
    nights = np.minimum(1 + rng.poisson(NIGHTS_MEAN - 1, n), 7)
    return nightly * nights

V = sample_values(200_000)
V_MED = float(np.median(V))

def usd(gas, gwei, eth=ETH_USD): return gas * gwei * 1e-9 * eth
def cr_gas(gwei, v, mode="push", new_guest=False, eth=ETH_USD): return usd(lifecycle_gas(mode, new_guest), gwei, eth) / v
def cr_total(gwei, v, spec, mode="push", new_guest=False, eth=ETH_USD, ramp=RAMP_FEE):
    return cr_gas(gwei, v, mode, new_guest, eth) + ramp + spec["p"] + spec["c"]

res = {"V_median_usd": V_MED, "V_mean_usd": float(V.mean()), "nightly_usd": NIGHTLY_USD}
res["lifecycle_gas"] = {f"{m}{'_newguest' if ng else ''}": lifecycle_gas(m, ng) for m in ("push", "accrue") for ng in (False, True)}

# ---- H1 ----
grid = np.logspace(-1, 2, 61)
h1 = {}
for name, spec in (("original_78_15_5_2", SPEC_ORIGINAL), ("revised_90_5_3_2", SPEC_REVISED)):
    floor = RAMP_FEE + spec["p"] + spec["c"]
    # breakeven gas price at which median-booking CR_total hits the legacy lower bound
    room = LEGACY_LOW - floor
    be = {}
    for m in ("push", "accrue"):
        for ng in (False, True):
            be[f"{m}{'_newguest' if ng else ''}"] = (room * V_MED / (lifecycle_gas(m, ng) * 1e-9 * ETH_USD)) if room > 0 else None
    pts = {}
    for g in (0.5, 1, 10, 50):
        c = cr_total(g, V, spec, "push", True)
        pts[str(g)] = {"median": float(np.median(c)), "p90": float(np.percentile(c, 90)),
                       "share_below_legacy_low": float((c < LEGACY_LOW).mean())}
    h1[name] = {"non_gas_floor": floor, "breakeven_gwei_median_booking": be, "at_gwei_pushnewguest": pts}
res["H1"] = h1
# H1 robustness from the hotel's viewpoint: the SDG share also reduces what the hotel receives
h1s = {}
for name, spec in (("original_78_15_5_2", SPEC_ORIGINAL), ("revised_90_5_3_2", SPEC_REVISED)):
    floor = RAMP_FEE + spec["p"] + spec["c"] + spec["s"]
    room = LEGACY_LOW - floor
    be = {f"{m}{'_newguest' if ng else ''}": ((room * V_MED / (lifecycle_gas(m, ng) * 1e-9 * ETH_USD)) if room > 0 else None)
          for m in ("push", "accrue") for ng in (False, True)}
    pts = {}
    for g in (1, 10, 50):
        c = cr_total(g, V, spec, "push", True) + spec["s"]
        pts[str(g)] = {"median": float(np.median(c)), "share_below_legacy_low": float((c < LEGACY_LOW).mean())}
    h1s[name] = {"non_gas_floor": floor, "breakeven_gwei_median_booking": be, "at_gwei_pushnewguest": pts}
res["H1_including_sdg_share"] = h1s
# Sensitivity to the Glamsterdam repricing (EIP-8037/8038): median gas measured on public Sepolia, 23 Oct 2026
import csv, statistics
_sep = ROOT / "results" / "sepolia_public_onchain.csv"
if _sep.exists():
    _g = {}
    for r in csv.DictReader(open(_sep)):
        if r["status"] == "1": _g.setdefault(r["function"].split("(")[0], []).append(int(r["gas_used"]))
    sg = {k: statistics.median(v) for k, v in _g.items()}
    G_ret = sg["createBooking"] + sg["confirmPayment"] + sg["completeStay"]
    G_new = G_ret + sg["approve"]
    def _crg(G, g, v): return G * g * 1e-9 * ETH_USD / v
    gl = {"median_gas": sg, "lifecycle_returning_push": G_ret, "lifecycle_newguest_push": G_new,
          "ratio_to_cancun_newguest_push": G_new / lifecycle_gas("push", True),
          "ratio_to_cancun_returning_push": G_ret / lifecycle_gas("push", False)}
    for lab, extra in (("excl_sdg", 0.0), ("incl_sdg", SPEC_REVISED["s"])):
        floor = RAMP_FEE + SPEC_REVISED["p"] + SPEC_REVISED["c"] + extra
        c10 = _crg(G_new, 10, V) + floor
        gl[lab] = {"median_cr_at_10gwei": float(np.median(c10)), "share_below_legacy_low_at_10gwei": float((c10 < LEGACY_LOW).mean()),
                   "breakeven_gwei_newguest_push": (LEGACY_LOW - floor) * V_MED / (G_new * 1e-9 * ETH_USD),
                   "breakeven_gwei_returning_push": (LEGACY_LOW - floor) * V_MED / (G_ret * 1e-9 * ETH_USD)}
    gl["theta_sat_scaling"] = lifecycle_gas("push", True) / G_new
    gl["max_intermediary_share_newguest_push"] = {str(g): float(LEGACY_LOW - RAMP_FEE - _crg(G_new, g, V_MED)) for g in (1, 10, 20)}
    res["glamsterdam_sepolia_sensitivity"] = gl
res["cr_gas_median_booking"] = {str(g): {m: float(cr_gas(g, V_MED, m, True)) for m in ("push", "accrue")} for g in (0.5, 1, 10, 50)}
# maximum admissible intermediary share alpha_p + alpha_c (median booking, push, new guest)
res["max_intermediary_share"] = {str(g): float(LEGACY_LOW - RAMP_FEE - cr_gas(g, V_MED, "push", True)) for g in (1, 10, 50)}

# ---- sensitivity (tornado) on CR_total, revised spec, push, new guest, g = 10 gwei, median booking ----
G_REF = 10.0
base = cr_total(G_REF, V_MED, SPEC_REVISED, "push", True)
factors = [
    ("ETH price US$1,500–5,000", lambda lo: cr_total(G_REF, V_MED, SPEC_REVISED, "push", True, eth=1500 if lo else 5000)),
    ("Gas price 1–50 gwei", lambda lo: cr_total(1 if lo else 50, V_MED, SPEC_REVISED, "push", True)),
    ("Stay length 1–3 nights", lambda lo: cr_total(G_REF, NIGHTLY_USD * (3 if lo else 1), SPEC_REVISED, "push", True)),
    ("Ramp fee 0–1.5%", lambda lo: cr_total(G_REF, V_MED, SPEC_REVISED, "push", True, ramp=0.0 if lo else 0.015)),
    ("Settlement accrue vs push", lambda lo: cr_total(G_REF, V_MED, SPEC_REVISED, "accrue" if lo else "push", True)),
    ("Returning vs new guest", lambda lo: cr_total(G_REF, V_MED, SPEC_REVISED, "push", not lo)),
]
tor = [(n, float(f(True)), float(f(False))) for n, f in factors]
tor.sort(key=lambda t: abs(t[2] - t[1]))
res["tornado"] = {"g_ref": G_REF, "base": float(base), "factors": tor}

# ---- H3: marginal on-chain cost of the SDG allocation relative to the amount allocated ----
h3 = {}
for m in ("push", "accrue"):
    dg = GAS_SDG_MARGINAL[m] + (GAS_WITHDRAW / (baseline_rate() * 30 * 86400) if m == "accrue" else 0)  # monthly pull
    be = H3_THRESHOLD * SPEC_REVISED["s"] * V_MED / (dg * 1e-9 * ETH_USD)
    frac = {str(g): float((usd(dg, g) / (SPEC_REVISED["s"] * V) <= H3_THRESHOLD).mean()) for g in (1, 10, 50)}
    ratio_med = {str(g): float(usd(dg, g) / (SPEC_REVISED["s"] * V_MED)) for g in (1, 10, 50)}
    h3[m] = {"marginal_gas": dg, "breakeven_gwei_median": float(be), "share_bookings_meeting": frac, "ratio_median": ratio_med}
res["H3"] = h3

# ---- correctness check of the split rule (not a hypothesis) ----
amt = np.round(V[:100_000] * 1e6).astype(np.int64)
bps = np.array([500, 300, 200])
shares = (amt[:, None] * bps[None, :]) // 10_000
hotel_rem = amt - shares.sum(1)
naive_hotel = amt * 9000 // 10_000
res["split_check"] = {"n": int(amt.size), "remainder_violations": int(((hotel_rem + shares.sum(1)) != amt).sum()),
                      "naive_violations": int(((naive_hotel + shares.sum(1)) != amt).sum())}

# ---- EIP-1559 base-fee escalation during sustained congestion ----
esc = {}
for u in (0.5, 0.7, 0.9, 0.98):
    step = 1 + 0.125 * (u - EIP1559_TARGET) / EIP1559_TARGET
    esc[str(u)] = {"per_block": step, "after_25_blocks_5min": step ** 25, "after_75_blocks_15min": step ** 75}
res["eip1559"] = esc
# ================= Revision 1 analyses (reviewer requests) =================
rv = {}
gU = lambda G, g=10.0, eth=ETH_USD: G * g * 1e-9 * eth          # USD cost of G gas at g gwei
LC_NEW_PUSH = lifecycle_gas("push", True)
# booking-value parameterisation: log-location ln(NIGHTLY_USD) => NIGHTLY_USD is the MEDIAN nightly rate
rv["value_model"] = {"nightly_median_usd": NIGHTLY_USD, "nightly_mean_usd": NIGHTLY_USD * float(np.exp(PRICE_SIGMA**2 / 2)),
                     "n_samples": int(V.size), "nights_cap": 7, "V_median": V_MED, "V_mean": float(V.mean()),
                     "V_p10": float(np.percentile(V, 10)), "V_p90": float(np.percentile(V, 90))}
# smallest booking value that still meets the 17.5% comparator (revised split, new guest, push)
rv["min_value_meeting_H1"] = {str(g): gU(LC_NEW_PUSH, g) / (LEGACY_LOW - (RAMP_FEE + SPEC_REVISED["p"] + SPEC_REVISED["c"])) for g in (1, 10, 50)}
rv["example_usd50_cr_at_10gwei"] = float(cr_total(10, 50.0, SPEC_REVISED, "push", True))
# comparator without the assumed card-processing charge (OTA commission 15% only)
floor_rev = RAMP_FEE + SPEC_REVISED["p"] + SPEC_REVISED["c"]
rv["H1_comparator_15pct"] = {"breakeven_gwei_newguest_push": (0.15 - floor_rev) * V_MED / (LC_NEW_PUSH * 1e-9 * ETH_USD),
                             "breakeven_gwei_returning_accrue": (0.15 - floor_rev) * V_MED / (lifecycle_gas("accrue", False) * 1e-9 * ETH_USD),
                             "share_below_at_10gwei": float((cr_total(10, V, SPEC_REVISED, "push", True) < 0.15).mean())}
# cost of a paid-then-cancelled booking (new guest, push): approve + create + confirm + cancel + refund
G_CANCEL = next(x for x in GAS if x["mode"] == "push")["stats"]["cancel"]["median"]
G_REFUND = next(x for x in GAS if x["mode"] == "push")["stats"]["refund"]["median"]
G_PAID_CANCEL = GAS_APPROVE + GAS_CREATE["push"] + GAS_CONFIRM["push"] + G_CANCEL + G_REFUND
rv["cancellation"] = {"gas_paid_cancel_newguest_push": G_PAID_CANCEL, "usd_at_10gwei": gU(G_PAID_CANCEL),
                      "gas_completed_newguest_push": LC_NEW_PUSH, "usd_completed_at_10gwei": gU(LC_NEW_PUSH)}
mix = {}
for c in (0.10, 0.15, 0.25):   # hypothetical cancellation shares, NOT observed destination rates
    extra = c / (1 - c) * gU(G_PAID_CANCEL) / V_MED          # cancelled bookings' gas carried by completed bookings
    mix[str(c)] = {"added_pp_per_completed_booking": 100 * extra, "median_cr_total": float(cr_total(10, V_MED, SPEC_REVISED, "push", True) + extra)}
rv["cancellation_mixture_10gwei"] = mix
# worked accounts for the median booking at 10 gwei (revised split, new guest, push)
Vm = V_MED
acc = {"booking_value": Vm,
       "guest_gas_approve_create_confirm": gU(GAS_APPROVE + GAS_CREATE["push"] + GAS_CONFIRM["push"]),
       "operator_gas_completeStay": gU(GAS_COMPLETE["push"]),
       "platform_gross": SPEC_REVISED["p"] * Vm, "affiliate": SPEC_REVISED["c"] * Vm, "sdg_fund": SPEC_REVISED["s"] * Vm,
       "hotel_gross": SPEC_REVISED["h"] * Vm, "conversion_fee": RAMP_FEE * Vm}
acc["platform_net_if_it_pays_settlement_gas"] = acc["platform_gross"] - acc["operator_gas_completeStay"]
acc["hotel_net_after_conversion"] = acc["hotel_gross"] - acc["conversion_fee"]
acc["cr_total_gas_passed_through"] = (acc["guest_gas_approve_create_confirm"] + acc["operator_gas_completeStay"] + acc["platform_gross"] + acc["affiliate"] + acc["conversion_fee"]) / Vm
acc["cr_total_platform_absorbs_settlement_gas"] = (acc["guest_gas_approve_create_confirm"] + acc["platform_gross"] + acc["affiliate"] + acc["conversion_fee"]) / Vm
rv["worked_accounts_median_10gwei"] = acc
# conventional comparator: same 90/5/3/2 allocation in a CMS settling through a card gateway (no gas, no conversion)
rv["conventional_same_allocation"] = {"cr_low": SPEC_REVISED["p"] + SPEC_REVISED["c"] + 0.025, "cr_high": SPEC_REVISED["p"] + SPEC_REVISED["c"] + 0.035,
                                      "blockchain_median_cr_1_10_50": [float(np.median(cr_total(g, V, SPEC_REVISED, "push", True))) for g in (1, 10, 50)]}
# H3 with the withdrawal spread over k settlements of the same contract (accrue mode)
h3k = {}
for kk in (5, 10, 30, 100, 1000):
    dg = GAS_SDG_MARGINAL["accrue"] + GAS_WITHDRAW / kk
    h3k[str(kk)] = {"marginal_gas": dg, "eta_median_10gwei": float(usd(dg, 10) / (SPEC_REVISED["s"] * V_MED)),
                    "breakeven_gwei": float(H3_THRESHOLD * SPEC_REVISED["s"] * V_MED / (dg * 1e-9 * ETH_USD))}
rv["H3_accrue_withdrawal_spread"] = h3k
rv["H3_accrue_cheaper_than_push_if_k_ge"] = GAS_WITHDRAW / (GAS_SDG_MARGINAL["push"] - GAS_SDG_MARGINAL["accrue"])
rv["H3_push_eta_if_sdg_share_1pct_10gwei"] = float(usd(GAS_SDG_MARGINAL["push"], 10) / (0.01 * V_MED))
rv["H3_coverage_10gwei"] = {m: h3[m]["share_bookings_meeting"]["10"] for m in ("push", "accrue")}
# base-fee escalation versus an affordable fee ceiling (H1 break-even, new guest, push)
ceil = h1["revised_90_5_3_2"]["breakeven_gwei_median_booking"]["push_newguest"]
esc2 = {}
for u_ in (0.7, 0.9, 0.98):
    step = 1 + 0.125 * (u_ - EIP1559_TARGET) / EIP1559_TARGET
    for g0 in (1.0, 10.0):
        n = float(np.log(ceil / g0) / np.log(step))
        esc2[f"{u_}|{g0}"] = {"blocks_to_ceiling": n, "minutes": n * SLOT_S / 60}
# joint operating scenarios: one configuration must meet H1 and H3 together (H2 from des.json)
WD4 = 4 * GAS_WITHDRAW            # hotel, platform, affiliate and fund each withdraw once per period
def scen(mode, k, g, glam=False):
    if glam:
        G = res["glamsterdam_sepolia_sensitivity"]["lifecycle_newguest_push"]
    else:
        G = lifecycle_gas(mode, True) + (WD4 / k if mode == "accrue" else 0)
    c = G * g * 1e-9 * ETH_USD / V + RAMP_FEE + SPEC_REVISED["p"] + SPEC_REVISED["c"]
    out = {"lifecycle_gas": G, "median_cr": float(np.median(c)), "share_below_17_5": float((c < LEGACY_LOW).mean())}
    if not glam:
        dg = GAS_SDG_MARGINAL[mode] + (GAS_WITHDRAW / k if mode == "accrue" else 0)
        eta = usd(dg, g) / (SPEC_REVISED["s"] * V)
        out.update({"eta_median": float(np.median(eta)), "share_eta_le_5": float((eta <= H3_THRESHOLD).mean())})
    return out
rv["operating_scenarios"] = {"push|10": scen("push", 1, 10), "accrue_k100|10": scen("accrue", 100, 10), "accrue_k10|10": scen("accrue", 10, 10),
                             "push|50": scen("push", 1, 50), "accrue_k100|50": scen("accrue", 100, 50), "glam_push|10": scen("push", 1, 10, True)}
rv["fee_ceiling_gwei"] = ceil
rv["basefee_time_to_ceiling"] = esc2
res["revision1"] = rv
json.dump(res, open(OUT / "cost.json", "w"), indent=1)

# ================= figures =================
import plotstyle as ps
ps.apply()
W1, H1 = 3.2, 2.35  # printed size in the manuscript (in); fonts are true point sizes
LBL = {"Ramp fee 0–1.5%": "Conversion fee 0–1.5%", "ETH price US$1,500–5,000": "Ether price USD 1,500–5,000",
       "Returning vs new guest": "Guest status (returning/new)", "Settlement accrue vs push": "Settlement (accrue/push)"}

# Fig. 5: gas per function (measured), grouped horizontal bars with hatching
fig, ax = plt.subplots(figsize=(W1 - 0.22, H1))
labels = ["approve()\n(new guest)", "createBooking()", "confirmPayment()", "completeStay()", "withdraw()\n(accrue, periodic)"]
push = [GAS_APPROVE, GAS_CREATE["push"], GAS_CONFIRM["push"], GAS_COMPLETE["push"], 0]
accr = [GAS_APPROVE, GAS_CREATE["accrue"], GAS_CONFIRM["accrue"], GAS_COMPLETE["accrue"], GAS_WITHDRAW]
y = np.arange(len(labels)); h = 0.38
ax.barh(y - h/2, np.array(push) / 1e3, h, color=ps.BLUE, edgecolor=ps.INK, lw=0.5, label="Push mode")
ax.barh(y + h/2, np.array(accr) / 1e3, h, color=ps.ORANGE, edgecolor=ps.INK, lw=0.5, hatch="////", label="Accrue mode")
for yi, v in zip(y, push):
    if v: ax.text(v/1e3 + 2, yi - h/2, f"{v/1e3:.1f}", va="center", fontsize=7.5)
for yi, v in zip(y, accr):
    if v: ax.text(v/1e3 + 2, yi + h/2, f"{v/1e3:.1f}", va="center", fontsize=7.5)
ax.set_yticks(y, labels, fontsize=7.5); ax.invert_yaxis(); ps.no_minor_y(ax)
ax.set_xlabel("Median gas used (×10$^3$)"); ax.set_xlim(0, 150); ax.grid(axis="y", visible=False)
ax.legend(loc="lower right")
fig.savefig(FIG / "fig_gas.png"); plt.close(fig)

# Fig. 6: CR_total vs gas price, two specifications, with the legacy band
fig, ax = plt.subplots(figsize=(W1, H1))
ax.axhspan(LEGACY_LOW * 100, LEGACY_HIGH * 100, facecolor="#e3e3e3", lw=0)
for yb in (LEGACY_LOW, LEGACY_HIGH): ax.axhline(yb * 100, color=ps.GREY, lw=0.7, ls=":")
ax.text(0.115, 30.6, "Legacy OTA + card cost band", fontsize=7.5, color=ps.GREY)
for spec, col, lab, mk in ((SPEC_ORIGINAL, ps.ORANGE, "Initial split 78/15/5/2", "s"), (SPEC_REVISED, ps.BLUE, "Revised split 90/5/3/2", "o")):
    c = np.array([cr_total(g, V, spec, "push", True) for g in grid]) * 100
    med, p10, p90 = np.median(c, 1), np.percentile(c, 10, 1), np.percentile(c, 90, 1)
    ax.fill_between(grid, p10, p90, color=col, alpha=0.18, lw=0)
    ax.plot(grid, med, color=col, label=lab, marker=mk, markevery=6)
ax.set_xscale("log"); ax.set_xlim(0.1, 100); ax.set_ylim(0, 40)
ax.set_xlabel("Gas price (gwei)"); ax.set_ylabel(r"$CR_{total}$ (%)")
ax.legend(loc="upper left", borderaxespad=0.3)
fig.savefig(FIG / "fig_cr.png"); plt.close(fig)

# Fig. 7: tornado (one-at-a-time sensitivity)
fig, ax = plt.subplots(figsize=(W1 - 0.62, H1))
for i, (n, lo, hi) in enumerate(tor):
    ax.barh(i, (hi - base) * 100, left=base * 100, color=ps.ORANGE, edgecolor=ps.INK, lw=0.5, hatch="////", height=0.55,
            label="High setting" if i == 0 else None)
    ax.barh(i, (lo - base) * 100, left=base * 100, color=ps.BLUE, edgecolor=ps.INK, lw=0.5, height=0.55,
            label="Low setting" if i == 0 else None)
ax.axvline(base * 100, color=ps.INK, lw=0.9, ls="-")
ax.set_yticks(range(len(tor)), [LBL.get(t[0], t[0]) for t in tor], fontsize=7.5); ps.no_minor_y(ax)
ax.set_xlabel(r"$CR_{total}$ (%)" + f" (base case {base*100:.1f}%)"); ax.grid(axis="y", visible=False)
ax.legend(loc="lower right")
fig.savefig(FIG / "fig_tornado.png"); plt.close(fig)

# Fig. 8: H3 overhead ratio vs gas price
fig, ax = plt.subplots(figsize=(W1, H1))
for m, col, lab, mk in (("push", ps.BLUE, "Push (per-booking transfer)", "o"), ("accrue", ps.ORANGE, "Accrue (pooled withdrawal, large k)", "s")):
    r = [usd(h3[m]["marginal_gas"], g) / (SPEC_REVISED["s"] * V_MED) * 100 for g in grid]
    ax.plot(grid, r, color=col, label=lab, marker=mk, markevery=6)
ax.axhline(H3_THRESHOLD * 100, color=ps.GREY, lw=1.0, ls="--")
ax.text(0.12, H3_THRESHOLD * 100 * 1.25, "H3 threshold (5%)", fontsize=7.5, color=ps.GREY)
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(0.1, 100)
ax.set_xlabel("Gas price (gwei)"); ax.set_ylabel(r"Overhead $\eta$ (% of allocation)")
ax.legend(loc="lower right")
fig.savefig(FIG / "fig_h3.png"); plt.close(fig)
print(json.dumps(res, indent=1))
