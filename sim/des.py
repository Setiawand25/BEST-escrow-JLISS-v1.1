"""Slot-level discrete-event simulation of booking transactions on Ethereum PoS (H2).
Writes results/des.json and figures/fig_latency.png."""
import json, sys, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import deque
from params import *

OUT = ROOT / "results"; FIG = ROOT / "figures"
MODE = "push"
# Revision 1: the one-time token approval of a new guest is now a separate transaction (approve -> createBooking ->
# confirmPayment), each preceded by its own wallet signature, as in the implemented flow and the Sepolia campaign.
G_APPROVE_TX = GAS_APPROVE
G_CREATE, G_CONFIRM, G_COMPLETE = GAS_CREATE[MODE], GAS_CONFIRM[MODE], GAS_COMPLETE[MODE]
NEW_GUEST_SHARE = 1.0        # every booking treated as a first-time guest (conservative for capacity and latency)
G_BOOKING = G_CREATE + G_CONFIRM + G_COMPLETE + NEW_GUEST_SHARE * G_APPROVE_TX
KAPPA = 50.0                 # Beta concentration of per-block background utilization: U_k ~ Beta(u*KAPPA, (1-u)*KAPPA), i.i.d. per slot
WARM_FRAC = 0.10             # transactions submitted in the first 10% of the horizon are excluded (warm-up)

def run(m, u, horizon_s, seed, warm_frac=WARM_FRAC):
    """Returns per-kind inclusion latencies (0 create, 1 confirm, 2 complete, 3 approve), finality latencies of payments,
    complete guest sequences (first submission -> payment inclusion), backlog at the end, and counts.
    Booking requests and check-out settlements arrive as independent homogeneous Poisson processes of rate lam."""
    rng = np.random.default_rng(seed)
    lam = baseline_rate() * m
    n_slots = int(horizon_s / SLOT_S)
    nb = rng.poisson(lam * horizon_s)
    t_book = np.sort(rng.uniform(0, horizon_s, nb))
    nc = rng.poisson(lam * horizon_s)
    t_comp = np.sort(rng.uniform(0, horizon_s, nc))
    w = np.exp(np.log(WALLET_MEDIAN_S) + WALLET_SIGMA * rng.standard_normal((nb, 2)))   # signature delays before create and confirm
    new = rng.random(nb) < NEW_GUEST_SHARE
    a, b = u * KAPPA, (1 - u) * KAPPA
    import heapq
    pending = []   # (submit_time, seq, gas, kind, booking_idx)
    seq = 0
    for i, t in enumerate(t_book):
        heapq.heappush(pending, (t, seq, G_APPROVE_TX if new[i] else G_CREATE, 3 if new[i] else 0, i)); seq += 1
    for t in t_comp:
        heapq.heappush(pending, (t, seq, G_COMPLETE, 2, -1)); seq += 1
    queue = deque()
    lat = {0: [], 1: [], 2: [], 3: []}; fin = []; e2e = []
    started = 0; finished = 0
    for k in range(1, n_slots + 1):
        t_slot = k * SLOT_S
        cutoff = t_slot - T_CUTOFF
        while pending and pending[0][0] <= cutoff:
            queue.append(heapq.heappop(pending))
        if rng.random() < P_MISS:
            continue
        cap = BLOCK_GAS_LIMIT * (1 - rng.beta(a, b))
        t_final = (k // SLOTS_PER_EPOCH + 3) * SLOTS_PER_EPOCH * SLOT_S
        while queue and queue[0][2] <= cap:      # FIFO; the block closes when the head does not fit (no reordering)
            ts, _, g, kind, i = queue.popleft()
            cap -= g
            if ts >= warm_frac * horizon_s:
                lat[kind].append(t_slot - ts)
                if kind == 1:
                    fin.append(t_final - ts)
            if kind == 3:
                heapq.heappush(pending, (t_slot + w[i, 0], seq, G_CREATE, 0, i)); seq += 1
            elif kind == 0:
                heapq.heappush(pending, (t_slot + w[i, 1], seq, G_CONFIRM, 1, i)); seq += 1
            elif kind == 1 and t_book[i] >= warm_frac * horizon_s:
                e2e.append(t_slot - t_book[i]); finished += 1
    started = int((t_book >= warm_frac * horizon_s).sum())
    return lat, fin, e2e, len(queue) + len(pending), {"started": started, "completed_sequences": finished}

def summarize(xs):
    xs = np.asarray(xs)
    if xs.size == 0: return None
    return {"median": float(np.median(xs)), "p95": float(np.percentile(xs, 95)), "p99": float(np.percentile(xs, 99)), "mean": float(xs.mean())}

def ci(vals):
    v = np.asarray([x for x in vals if x is not None], float)
    if v.size < 2: return None
    from scipy import stats
    h = stats.t.ppf(0.975, v.size - 1) * v.std(ddof=1) / np.sqrt(v.size)
    return [float(v.mean() - h), float(v.mean() + h)]

def rho(m, u):
    offered = baseline_rate() * m * G_BOOKING
    capacity = (1 - P_MISS) * BLOCK_GAS_LIMIT * (1 - u) / SLOT_S
    return offered / capacity

def theta_sat(u):
    return (1 - P_MISS) * BLOCK_GAS_LIMIT * (1 - u) / (SLOT_S * G_BOOKING)

res = {"G_booking": G_BOOKING, "baseline_rate": baseline_rate(), "theta_sat": {str(u): theta_sat(u) for u in (0.5, 0.9, 0.98)}}

# ---- baseline (S1), 30 replications x 3 days ----
R = 30
H1S = 3 * 86400
reps = [run(1, 0.5, H1S, 1000 + r) for r in range(R)]
gtx = lambda l: l[0] + l[1] + l[3]          # guest-signed transactions: approve, createBooking, confirmPayment
guest = [summarize(gtx(o[0])) for o in reps]
res["S1"] = {
    "reps": R, "horizon_s": H1S, "warmup_s": WARM_FRAC * H1S, "observed_s": (1 - WARM_FRAC) * H1S,
    "guest_median_mean": float(np.mean([g["median"] for g in guest])), "guest_median_ci": ci([g["median"] for g in guest]),
    "guest_p95_mean": float(np.mean([g["p95"] for g in guest])), "guest_p95_ci": ci([g["p95"] for g in guest]),
    "guest_p99_mean": float(np.mean([g["p99"] for g in guest])), "guest_p99_ci": ci([g["p99"] for g in guest]),
    "guest_mean_mean": float(np.mean([g["mean"] for g in guest])), "guest_mean_ci": ci([g["mean"] for g in guest]),
    "e2e_median_mean": float(np.mean([np.median(o[2]) for o in reps])), "e2e_median_ci": ci([np.median(o[2]) for o in reps]),
    "e2e_p95_mean": float(np.mean([np.percentile(o[2], 95) for o in reps])),
    "finality_median_mean": float(np.mean([np.median(o[1]) for o in reps])), "finality_median_ci": ci([np.median(o[1]) for o in reps]),
    "n_bookings_started_per_rep": float(np.mean([o[4]["started"] for o in reps])),
    "n_sequences_completed_per_rep": float(np.mean([o[4]["completed_sequences"] for o in reps])),
    "n_guest_tx_per_rep": float(np.mean([len(gtx(o[0])) for o in reps])),
    "n_create_confirm_tx_per_rep": float(np.mean([len(o[0][0]) + len(o[0][1]) for o in reps])),
    "expected_bookings_per_day": baseline_rate() * 86400,
    "create_mean_mean": float(np.mean([np.mean(o[0][0]) for o in reps])), "create_mean_ci": ci([np.mean(o[0][0]) for o in reps]),
    "approve_median_mean": float(np.mean([np.median(o[0][3]) for o in reps])),
    "approve_mean_mean": float(np.mean([np.mean(o[0][3]) for o in reps])), "approve_mean_ci": ci([np.mean(o[0][3]) for o in reps]),
    "confirm_median_mean": float(np.mean([np.median(o[0][1]) for o in reps])),
}
res["closed_form_mean"] = SLOT_S / 2 + T_CUTOFF + SLOT_S * P_MISS / (1 - P_MISS)

# ---- S3 stress grid (10 replications x 4 h per cell; refined near each boundary) ----
grid = {}
MS = {0.5: [1, 10, 50, 100, 200, 500, 1000, 1500, 2000, 2100, 2200, 2300, 2500],
      0.9: [1, 10, 50, 100, 200, 300, 350, 400, 450, 500],
      0.98: [1, 10, 20, 50, 60, 70, 80, 90, 100]}
for u, ms in MS.items():
    for m in ms:
        r_ = rho(m, u)
        RR = 10
        out = [run(m, u, 4 * 3600, 5000 + 97 * m + int(u * 100) * 7 + r) for r in range(RR)]
        meds = [np.median(gtx(o[0])) if gtx(o[0]) else np.nan for o in out]
        p95 = [np.percentile(gtx(o[0]), 95) if gtx(o[0]) else np.nan for o in out]
        e2e = [np.median(o[2]) if o[2] else np.nan for o in out]
        e2e95 = [np.percentile(o[2], 95) if o[2] else np.nan for o in out]
        compl = [o[4]["completed_sequences"] / max(o[4]["started"], 1) for o in out]
        grid[f"{u}|{m}"] = {"u": u, "m": m, "rho": r_, "median": float(np.nanmean(meds)), "median_ci": ci(meds),
                            "p95": float(np.nanmean(p95)), "e2e_median": float(np.nanmean(e2e)), "e2e_median_ci": ci(e2e),
                            "e2e_p95": float(np.nanmean(e2e95)), "completion_share": float(np.mean(compl)),
                            "backlog_end_mean": float(np.mean([o[3] for o in out]))}
        print(u, m, round(r_, 3), round(np.nanmean(meds), 1), round(np.nanmean(e2e), 1), round(np.mean(compl), 3), np.mean([o[3] for o in out]), file=sys.stderr)
res["S3"] = grid
# boundaries: largest m passing and smallest m failing on the simulated grid (bracketed, not exact)
bound = {}
for u in MS:
    cells = sorted([v for v in grid.values() if v["u"] == u], key=lambda v: v["m"])
    ok = [v["m"] for v in cells if v["median"] < 60 and v["rho"] < 1]
    okseq = [v["m"] for v in cells if v["e2e_median"] < 60 and v["rho"] < 1]
    hi = max(ok) if ok else None
    fail = [v["m"] for v in cells if v["m"] > (hi or 0)]
    hi2 = max(okseq) if okseq else None
    fail2 = [v["m"] for v in cells if v["m"] > (hi2 or 0)]
    bound[str(u)] = {"tx_pass": hi, "tx_fail": min(fail) if fail else None, "seq_pass": hi2, "seq_fail": min(fail2) if fail2 else None}
res["H2_boundary_m"] = bound
json.dump(res, open(OUT / "des.json", "w"), indent=1)

# ---- figure ----
import plotstyle as ps
ps.apply()
C = {0.5: (ps.BLUE, "o"), 0.9: (ps.ORANGE, "s"), 0.98: (ps.GREEN, "^")}
fig, axs = plt.subplots(1, 2, figsize=(6.3, 2.3), sharey=True)
for u, (col, mk) in C.items():
    pts = sorted([v for v in grid.values() if v["u"] == u], key=lambda v: v["m"])
    ms = [p["m"] for p in pts]
    axs[0].plot(ms, [p["median"] for p in pts], color=col, marker=mk, label=f"$u$ = {u:.2f}")
    axs[1].plot(ms, [p["e2e_median"] for p in pts], color=col, marker=mk, label=f"$u$ = {u:.2f}")
for ax, yl, t in ((axs[0], "Median latency (s)", "(a) Individual guest transaction"), (axs[1], "", "(b) Complete guest sequence")):
    ax.axhline(60, color=ps.GREY, ls="--", lw=1.0)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("Load multiplier $m$"); ax.set_title(t)
    if yl: ax.set_ylabel(yl)
axs[0].text(1.1, 70, "H2 criterion (60 s)", fontsize=7.5, color=ps.GREY)
axs[0].legend(loc="upper left", bbox_to_anchor=(0.0, 0.88))
fig.tight_layout(w_pad=1.0); fig.savefig(FIG / "fig_latency.png"); plt.close(fig)
print(json.dumps({k: res[k] for k in ("S1", "closed_form_mean", "theta_sat", "H2_boundary_m")}, indent=1))
