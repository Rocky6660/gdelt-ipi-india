"""Scale the nonecon_* sampling weights in the audit key by R (population_meta.json), 23 Nov 2026.
The non-ECON population exists only on the 19 seeded window days of the approved non-ECON pull, so its design
weights are multiplied by R = non-ECON window-day articles (all days) / non-ECON articles (19 days), as in the
Mode B day rule; metrics on these strata are day-clustered. Idempotent: writes weight_factor_nonecon and keeps
sampling_weight_unscaled."""
import json
from pathlib import Path
import pandas as pd
root = Path(__file__).resolve().parents[2]
kp = root / "data/interim/audit/private/audit_key.csv"
k = pd.read_csv(kp)
R = json.loads((root / "data/interim/audit/population_meta.json").read_text())["nonecon_weight_factor_R"]
if "sampling_weight_unscaled" not in k.columns:
    k["sampling_weight_unscaled"] = k.sampling_weight
m = k.stratum.str.startswith("nonecon")
k["weight_factor_nonecon"] = 1.0
k.loc[m, "weight_factor_nonecon"] = R
k["sampling_weight"] = k.sampling_weight_unscaled * k.weight_factor_nonecon
k["inclusion_prob"] = 1.0 / k.sampling_weight
k.to_csv(kp, index=False)
print(f"R={R:.3f}; scaled {int(m.sum())} nonecon rows")
