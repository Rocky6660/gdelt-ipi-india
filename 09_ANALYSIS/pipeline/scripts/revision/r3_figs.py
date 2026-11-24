"""Revision round 3 figures (300 dpi, large fonts, no title inside the image), saved under the same names in
10_OUTPUTS/paper/final/source/:
  e5_ipi_cpi_peaks_c.png  Figure 10: the series used for the peak rule (3-month centred moving average of the monthly
                          price-family news index), the raw monthly series (thin), CPI inflation (MoSPI), peak months
  e2_eng_ver_c.png        Figure 8: English and Indian-language window news index (z), legend relabelled
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/analysis"))
import phase1 as p1  # noqa: E402

SRC = ROOT.parents[1] / "10_OUTPUTS/paper/final/source"
SW = json.loads((ROOT / "data/processed/results/d9_switch.json").read_text())
plt.rcParams.update({"font.size": 13, "axes.labelsize": 13, "legend.fontsize": 11, "xtick.labelsize": 12, "ytick.labelsize": 12})


def main() -> int:
    mon = pd.read_csv(ROOT / "data/processed/index/ipi_monthly.csv")
    mon = mon[mon.usable_d23].copy()
    mon["m"] = pd.PeriodIndex(mon.month, freq="M")
    m = mon.set_index("m")[[SW["monthly_column"]]].rename(columns={SW["monthly_column"]: "x"})
    m = m.join(p1.load_cpi(ROOT)[["cpi_yoy"]], how="left")
    m = m.reindex(pd.period_range(m.index.min(), m.index.max(), freq="M"))
    raw = 100 * m.x
    ma = raw.rolling(3, center=True, min_periods=2).mean()  # identical to the peak rule in extensions_descriptive.e5
    pk = pd.read_csv(ROOT / "data/processed/results_switched/e5_peaks.csv")
    assert np.allclose(ma.loc[pd.PeriodIndex(pk.peak_month, freq="M")].to_numpy(), 100 * pk.peak_value.to_numpy())
    x = m.index.to_timestamp()
    fig, ax = plt.subplots(figsize=(10, 4.4))
    ax.plot(x, raw, color="#9bb7cc", lw=0.9, label="News index, monthly (raw)")
    ax.plot(x, ma, color="#1f4e79", lw=2.0, label="News index, 3-month centred average")
    ax2 = ax.twinx()
    ax2.plot(x, m.cpi_yoy, color="#b03a2e", lw=1.4, label="CPI inflation (MoSPI)")
    for p in pk.peak_month:
        ax.axvline(pd.Period(p, "M").to_timestamp(), color="grey", lw=0.9, ls=":")
    ax.set_ylabel("News index, % of articles"); ax2.set_ylabel("CPI inflation, % y/y")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False)
    fig.tight_layout(); fig.savefig(SRC / "e5_ipi_cpi_peaks_c.png", dpi=300); plt.close(fig)

    d = pd.read_csv(ROOT / "data/processed/results_switched/e2_series_window.csv")
    xs = pd.to_datetime(d["round"] + "-01")
    fig, ax = plt.subplots(figsize=(10, 4.0))
    ax.plot(xs, d.eng_z, color="#1f4e79", lw=1.8, marker="o", ms=3, label="English (z)")
    ax.plot(xs, d.ver_z, color="#b03a2e", lw=1.8, marker="s", ms=3, label="Indian-language (z)")
    ax.axhline(0, color="k", lw=0.6)
    ax.set_ylabel("Window news index, standardised")
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout(); fig.savefig(SRC / "e2_eng_ver_c.png", dpi=300); plt.close(fig)
    print("figures written; window corr eng/ver", round(float(d[["ipi_eng", "ipi_ver"]].corr().iloc[0, 1]), 3), "N", len(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
