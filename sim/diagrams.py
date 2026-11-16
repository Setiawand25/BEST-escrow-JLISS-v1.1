"""Redraws the four schematic figures (DSR process, BEST architecture, booking FSM,
CMS plug-in sequence) at their printed size, so every font size below is a true
point size in the manuscript. Axes units are inches."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = str(__import__("pathlib").Path(__file__).resolve().parents[1] / "figures") + "/"
plt.rcParams.update({"font.family": "serif", "savefig.dpi": 300})
NAVY, TEAL, BLUE, GREEN, OCHRE, RED, GREY, INK = "#14365c", "#215f7a", "#2a78d6", "#1b8a5a", "#c98400", "#b84a3a", "#6b7280", "#0b0b0b"
FS, FSB = 8.5, 8.5  # body and bold box text (pt)


def canvas(w, h):
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, w); ax.set_ylim(0, h); ax.axis("off")
    return fig, ax


def box(ax, cx, cy, w, h, text, fc, tc="white", bold=True, ec=None, fs=FSB, lw=0):
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h, boxstyle="round,pad=0,rounding_size=0.05",
                                fc=fc, ec=ec or fc, lw=lw))
    ax.text(cx, cy, text, ha="center", va="center", color=tc, fontsize=fs,
            fontweight="bold" if bold else "normal", linespacing=1.15)


def arrow(ax, p, q, color=GREY, ls="-", both=False, rad=0.0, lw=1.3):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="<|-|>" if both else "-|>", mutation_scale=9, color=color,
                                 lw=lw, ls=ls, connectionstyle=f"arc3,rad={rad}", shrinkA=0, shrinkB=0))


# ---------- Fig. 1: DSR process (two rows, snake order) ----------
fig, ax = canvas(6.3, 1.16)
bw, bh = 1.86, 0.46
xs = [0.98, 3.15, 5.32]; y1, y2 = 0.925, 0.245
steps = [("1. Problem identification\n(Sections 1.1 and 1.2)", NAVY), ("2. Objectives of a solution\n(Sections 1.2 and 3.5)", TEAL),
         ("3. Design and development\n(Sections 3.2 and 3.3)", BLUE), ("4. Demonstration\n(Sepolia PoC, Section 3.3.1)", GREEN),
         ("5. Evaluation\n(Sections 3.5 and 4)", OCHRE), ("6. Communication\n(this paper)", RED)]
pos = [(xs[0], y1), (xs[1], y1), (xs[2], y1), (xs[2], y2), (xs[1], y2), (xs[0], y2)]
for (t, c), (x, y) in zip(steps, pos):
    box(ax, x, y, bw, bh, t, c, fs=8)
arrow(ax, (xs[0] + bw / 2, y1), (xs[1] - bw / 2, y1)); arrow(ax, (xs[1] + bw / 2, y1), (xs[2] - bw / 2, y1))
arrow(ax, (xs[2], y1 - bh / 2), (xs[2], y2 + bh / 2))
arrow(ax, (xs[2] - bw / 2, y2), (xs[1] + bw / 2, y2)); arrow(ax, (xs[1] - bw / 2, y2), (xs[0] + bw / 2, y2))
arrow(ax, (xs[1], y2 + bh / 2), (xs[1], y1 - bh / 2), color=OCHRE, ls="--")
ax.text(xs[1] + 0.07, (y1 + y2) / 2, "iterate", fontsize=8, style="italic", color=INK, va="center")
fig.savefig(OUT + "fig1_dsr.png"); plt.close(fig)

# ---------- Fig. 2: five-layer BEST architecture ----------
W, LH, GAP = 6.3, 0.52, 0.08
layers = [("Layer 1\nClient", NAVY, ["Guest booking page\n(CMS plug-in)", "MetaMask wallet\n(transaction signing)", "OTA channels\n(conventional path,\ncost baseline)"]),
          ("Layer 2\nApplication and\npayment", TEAL, ["CMS back end\n(PHP)", "Ethers.js bridge\n(prepare and submit)", "Rupiah–stablecoin\nconversion (licensed\nexternal provider)"]),
          ("Layer 3\nSmart contracts", "#2e86ab", ["BookingEscrow\n(booking, revenue\nsharing, SDG fund)", "STT contract\n(PoC)", "Mock stablecoin\n(test token)"]),
          ("Layer 4\nData", "#3f8f5f", ["Off-chain CMS\ndatabase", "Salted record hash\n(on-chain link)", "Synthetic booking\ndataset (evaluation)"]),
          ("Layer 5\nBlockchain", NAVY, ["Ethereum Sepolia\n(PoC and public\ncampaign)", "Local EVM with\nCancun gas rules\n(measurement)", "Production options:\nmainnet, layer-two,\npermissioned EVM"])]
H = len(layers) * LH + (len(layers) - 1) * GAP + 0.04
fig, ax = canvas(W, H)
LX, LW = 0.02, 1.55
for i, (name, col, comps) in enumerate(layers):
    y = H - 0.02 - LH / 2 - i * (LH + GAP)
    ax.add_patch(FancyBboxPatch((LX, y - LH / 2), W - 0.04, LH, boxstyle="round,pad=0,rounding_size=0.05", fc="#eef3f8", ec=col, lw=1.2))
    box(ax, LX + LW / 2, y, LW, LH, name, col, fs=8.5)
    x0, x1, g = LX + LW + 0.08, W - 0.1, 0.07
    cw = (x1 - x0 - g * (len(comps) - 1)) / len(comps)
    for j, c in enumerate(comps):
        box(ax, x0 + cw / 2 + j * (cw + g), y, cw, LH - 0.07, c, "white", tc=INK, bold=False, ec=col, fs=8, lw=1.0)
    if i < len(layers) - 1:
        arrow(ax, ((x0 + x1) / 2, y - LH / 2 - 0.005), ((x0 + x1) / 2, y - LH / 2 - GAP + 0.005), color=GREY, both=True, lw=1.2)
fig.savefig(OUT + "fig2_arch.png"); plt.close(fig)

# ---------- Fig. 3: finite-state model of the booking contract ----------
fig, ax = canvas(6.3, 1.95)
nw, nh = 1.2, 0.4
yt, yb = 1.2, 0.42
N = {"Created": (0.65, yt, "#1f5f7a"), "PendingPayment": (2.4, yt, BLUE), "Confirmed": (4.1, yt, GREEN),
     "Completed": (5.65, yt, NAVY), "Cancelled": (3.25, yb, RED), "Refunded": (5.0, yb, GREY)}
for k, (x, y, c) in N.items():
    box(ax, x, y, nw, nh, k, c, fs=8.5)
def lab(x, y, t, ha="center", va="bottom"):
    ax.text(x, y, t, ha=ha, va=va, fontsize=8, color=INK, linespacing=1.1)
def L(k): return N[k][0] - nw / 2
def R(k): return N[k][0] + nw / 2
arrow(ax, (R("Created"), yt), (L("PendingPayment"), yt), color=INK)
lab((R("Created") + L("PendingPayment")) / 2, yt + nh / 2 + 0.06, "createBooking()\n(atomic)")
arrow(ax, (R("PendingPayment"), yt), (L("Confirmed"), yt), color=INK)
lab((R("PendingPayment") + L("Confirmed")) / 2, yt + nh / 2 + 0.06, "confirmPayment()\n[guest; escrow funded]")
arrow(ax, (R("Confirmed"), yt), (L("Completed"), yt), color=INK)
lab((R("Confirmed") + L("Completed")) / 2 + 0.05, yt + nh / 2 + 0.06, "completeStay()\n[operator; t ≥ checkOut;\nrevenue split]")
arrow(ax, (N["PendingPayment"][0] + 0.15, yt - nh / 2), (L("Cancelled") + 0.2, yb + nh / 2), color=INK)
lab(2.55, (yt + yb) / 2 - 0.02, "cancel()\n[guest; unpaid]", ha="right", va="center")
arrow(ax, (N["Confirmed"][0] - 0.15, yt - nh / 2), (R("Cancelled") - 0.2, yb + nh / 2), color=INK)
lab(3.95, (yt + yb) / 2 - 0.02, "cancel()\n[guest; t < checkIn]", ha="left", va="center")
arrow(ax, (R("Cancelled"), yb), (L("Refunded"), yb), color=INK)
lab((R("Cancelled") + L("Refunded")) / 2, yb - nh / 2 - 0.05, "refund() [escrow > 0]", va="top")
fig.savefig(OUT + "fig3_fsm.png"); plt.close(fig)

# ---------- Fig. 4: booking-to-blockchain data path (sequence) ----------
W, top, step = 6.3, 2.43, 0.222
fig, ax = canvas(W, 2.6)
names = ["Guest", "BEST CMS\nplug-in", "MetaMask\nwallet", "STT contract\n(Sepolia)", "Etherscan\n(block explorer)"]
X = [0.62, 1.87, 3.12, 4.37, 5.62]
for x, n in zip(X, names):
    box(ax, x, top, 1.12, 0.4, n, NAVY, fs=8.5)
    ax.plot([x, x], [top - 0.2, 0.1], ls="--", color=GREY, lw=0.9)
msgs = [(0, 1, "1. Select room and dates"), (1, 2, "2. Prepare transaction"), (2, 0, "3. Signature request"),
        (0, 2, "4. Guest approves"), (2, 3, "5. Submit signed transaction"), (3, 3, "6. Execute recordBooking(),\n    emit event"),
        (3, 1, "7. Return transaction hash"), (1, 4, "8. Verify transaction hash"), (1, 0, "9. Display QR code and confirmation")]
for i, (a, b, t) in enumerate(msgs):
    y = top - 0.48 - i * step
    if a == b:
        arrow(ax, (X[a] + 0.02, y + 0.05), (X[a] + 0.02, y - 0.09), color=TEAL, rad=-1.2, lw=1.2)
        ax.text(X[a] + 0.16, y - 0.02, t, fontsize=8, va="center", ha="left", color=INK,
                bbox=dict(fc="white", ec="none", pad=0.5))
        continue
    s = 1 if b > a else -1
    arrow(ax, (X[a] + 0.03 * s, y - 0.06), (X[b] - 0.03 * s, y - 0.06), color=TEAL, lw=1.4)
    ax.text((X[a] + X[b]) / 2, y - 0.02, t, fontsize=8, ha="center", va="bottom", color=INK,
            bbox=dict(fc="white", ec="none", pad=0.4))
fig.savefig(OUT + "fig4_seq.png"); plt.close(fig)
print("ok")
