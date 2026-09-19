"""Reproduce the normalized-throughput figure from the supplied raw CSV."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

from .paths import OUTPUT, RAW


DEFAULT_DATA = RAW / "throughput" / "Throughput_Data_AIPWC.csv"
DEFAULT_OUTPUT = OUTPUT / "Figure_SYPD.pdf"
DEFAULT_TWO_PANEL_OUTPUT = OUTPUT / "Figure_SYPD_two_panel.pdf"

RAW_COLUMNS = [
    "model_name",
    "model_type",
    "horiz_res_deg",
    "vert_levels",
    "time_step_h",
    "sypd",
    "n_accelerators",
    "prognostic_vars",
]

MODEL_STYLES = {
    "SCREAM_GPU": {"marker": "v", "color": "#3B78A8", "s": 55},
    "ICON_A_GPU": {"marker": "P", "color": "#3B78A8", "s": 70},
    "CliMA": {"marker": "^", "color": "#23B8CE", "s": 60},
    "NeuralGCM": {"marker": "D", "color": "#23B8CE", "s": 52},
    "ACE2": {"marker": "o", "color": "#45A84E", "s": 52},
    "CAMulator": {"marker": "s", "color": "#45A84E", "s": 55},
}


@dataclass(frozen=True)
class ThroughputFit:
    """Weighted log-log fit and the observations used to estimate it."""

    observations: pd.DataFrame
    weights: pd.Series
    result: object
    x_column: str

    @property
    def coefficient(self) -> float:
        return float(10.0 ** np.asarray(self.result.params)[0])

    @property
    def exponent(self) -> float:
        return float(np.asarray(self.result.params)[1])

    @property
    def coefficient_ci95(self) -> tuple[float, float]:
        """Working-model WLS interval under independent log-error assumptions."""

        interval = np.asarray(self.result.conf_int(alpha=0.05))
        return float(10.0 ** interval[0, 0]), float(10.0 ** interval[0, 1])

    @property
    def exponent_ci95(self) -> tuple[float, float]:
        """Working-model WLS interval under independent log-error assumptions."""

        interval = np.asarray(self.result.conf_int(alpha=0.05))
        return float(interval[1, 0]), float(interval[1, 1])

    @property
    def cluster_robust_ci95(
        self,
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        """Small-sample cluster-robust sensitivity intervals by model."""

        robust = self.result.get_robustcov_results(
            cov_type="cluster",
            groups=self.observations["model_name"].to_numpy(),
            use_correction=True,
            df_correction=True,
        )
        interval = np.asarray(robust.conf_int(alpha=0.05))
        coefficient = (
            float(10.0 ** interval[0, 0]),
            float(10.0 ** interval[0, 1]),
        )
        exponent = float(interval[1, 0]), float(interval[1, 1])
        return coefficient, exponent

    def prediction_interval95(self, x_value: float) -> tuple[float, float]:
        """Return the 95% observation prediction interval at one positive x."""

        if x_value <= 0:
            raise ValueError("x_value must be positive")
        design = sm.add_constant(
            np.array([np.log10(x_value)]), has_constant="add"
        )
        prediction = self.result.get_prediction(design).summary_frame(alpha=0.05)
        return (
            float(10.0 ** prediction["obs_ci_lower"].iloc[0]),
            float(10.0 ** prediction["obs_ci_upper"].iloc[0]),
        )


def load_raw_data(path: Path = DEFAULT_DATA) -> pd.DataFrame:
    """Load primitive columns and derive the two plotted quantities.

    Spreadsheet formula columns in the raw file are deliberately ignored. This
    keeps the analysis auditable: every plotted value is reconstructed here.
    """

    raw = pd.read_csv(path)
    missing = sorted(set(RAW_COLUMNS) - set(raw.columns))
    if missing:
        raise ValueError(f"Missing raw throughput columns: {missing}")

    data = raw[RAW_COLUMNS].copy().dropna(how="all")
    data = data.rename(
        columns={
            "horiz_res_deg": "dx",
            "vert_levels": "nvert",
            "time_step_h": "dt",
            "n_accelerators": "nacc",
            "prognostic_vars": "nprog",
        }
    )
    for column in ["dx", "nvert", "dt", "sypd", "nacc", "nprog"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data["x"] = data["dx"] ** 2 * data["dt"]
    data["sypd_norm"] = (
        data["sypd"] * data["nprog"] * data["nvert"] / data["nacc"]
    )
    return data


def select_fit_rows(data: pd.DataFrame) -> pd.DataFrame:
    """Apply the manuscript's explicit inclusion rules."""

    keep = (
        data["model_type"].ne("downscaling")
        & ~(
            data["model_name"].eq("ICON_A_GPU")
            & data["model_type"].eq("trad_cpu")
        )
        & data["nacc"].notna()
        & np.isfinite(data["x"])
        & np.isfinite(data["sypd_norm"])
        & data["x"].gt(0)
        & data["sypd_norm"].gt(0)
    )
    return data.loc[keep].copy()


def fit_power_law(data: pd.DataFrame, x_column: str = "x") -> ThroughputFit:
    """Fit log10(SYPD_norm) on log10(x), with equal total weight per model."""

    observations = select_fit_rows(data)
    counts = observations.groupby("model_name")["model_name"].transform("count")
    weights = 1.0 / counts
    weights = weights / weights.mean()

    log_x = np.log10(observations[x_column].to_numpy())
    log_t = np.log10(observations["sypd_norm"].to_numpy())
    design = sm.add_constant(log_x)
    result = sm.WLS(log_t, design, weights=weights.to_numpy()).fit()
    return ThroughputFit(observations, weights, result, x_column)


def _prediction_data(fit: ThroughputFit):
    log_x = np.log10(fit.observations[fit.x_column].to_numpy())
    grid_log_x = np.linspace(log_x.min() - 0.04, log_x.max() + 0.04, 600)
    prediction = fit.result.get_prediction(sm.add_constant(grid_log_x)).summary_frame(
        alpha=0.05
    )
    return (
        10.0**grid_log_x,
        10.0 ** prediction["mean"].to_numpy(),
        10.0 ** prediction["obs_ci_lower"].to_numpy(),
        10.0 ** prediction["obs_ci_upper"].to_numpy(),
    )


def _plot_panel(
    ax,
    fit: ThroughputFit,
    *,
    x_label: str,
    x_limits: tuple[float, float],
    panel_label: str | None = None,
    legend_location: str | None = None,
) -> None:
    grid_x, line, lower, upper = _prediction_data(fit)
    ax.fill_between(grid_x, lower, upper, color="0.78", alpha=0.42, linewidth=0)
    ax.plot(grid_x, line, color="black", linewidth=1.35)

    for name, style in MODEL_STYLES.items():
        rows = fit.observations["model_name"].eq(name)
        ax.scatter(
            fit.observations.loc[rows, fit.x_column],
            fit.observations.loc[rows, "sypd_norm"],
            label=name,
            edgecolors="none",
            alpha=0.98,
            **style,
        )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(*x_limits)
    ax.set_ylim(3e-2, 4.5e5)
    ax.grid(which="major", color="0.84", linewidth=0.55)
    ax.grid(which="minor", color="0.90", linewidth=0.42, linestyle=":")
    ax.set_xlabel(x_label)
    if legend_location:
        ax.legend(loc=legend_location)
    if panel_label:
        ax.text(
            0.015,
            0.97,
            panel_label,
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=18,
            fontweight="bold",
        )


def _fit_record(name: str, fit: ThroughputFit) -> dict[str, float | int | str]:
    coefficient_low, coefficient_high = fit.coefficient_ci95
    exponent_low, exponent_high = fit.exponent_ci95
    robust_coefficient, robust_exponent = fit.cluster_robust_ci95
    prediction_low, prediction_high = fit.prediction_interval95(1.0)
    return {
        "fit": name,
        "x_column": fit.x_column,
        "n": len(fit.observations),
        "coefficient": fit.coefficient,
        "coefficient_ci95_low": coefficient_low,
        "coefficient_ci95_high": coefficient_high,
        "exponent": fit.exponent,
        "exponent_ci95_low": exponent_low,
        "exponent_ci95_high": exponent_high,
        "cluster_robust_coefficient_ci95_low": robust_coefficient[0],
        "cluster_robust_coefficient_ci95_high": robust_coefficient[1],
        "cluster_robust_exponent_ci95_low": robust_exponent[0],
        "cluster_robust_exponent_ci95_high": robust_exponent[1],
        "cluster_count": fit.observations["model_name"].nunique(),
        "weighted_r_squared": fit.result.rsquared,
        "prediction_reference_x": 1.0,
        "prediction_ci95_low": prediction_low,
        "prediction_ci95_high": prediction_high,
    }


def _model_offset_records(name: str, fit: ThroughputFit) -> list[dict[str, object]]:
    """Return mean per-model vertical offsets from one descriptive fit."""

    observations = fit.observations.copy()
    log_x = np.log10(observations[fit.x_column].to_numpy())
    observations["offset_decades"] = (
        np.log10(observations["sypd_norm"].to_numpy())
        - fit.result.predict(sm.add_constant(log_x))
    )
    records = []
    for model_name, rows in observations.groupby("model_name", sort=True):
        records.append(
            {
                "fit": name,
                "x_column": fit.x_column,
                "model_name": model_name,
                "n": len(rows),
                "mean_offset_decades": rows["offset_decades"].mean(),
                "minimum_offset_decades": rows["offset_decades"].min(),
                "maximum_offset_decades": rows["offset_decades"].max(),
            }
        )
    return records


def make_figure(
    data_path: Path = DEFAULT_DATA,
    output_path: Path | None = None,
    *,
    two_panel: bool = False,
) -> ThroughputFit:
    """Create a single- or two-panel publication PDF and PNG preview.

    Expected with the frozen raw CSV and equal total weight per model:
    - dx fit: SYPD_norm = 4.331e3 * dx^3.1371; working-model coefficient 95% CI
      [1.939e3, 9.676e3], exponent 95% CI [2.7418, 3.5325], R^2=0.8384.
    - dx^2 dt fit: SYPD_norm = 8.409e3 * (dx^2 dt)^1.0128;
      working-model coefficient 95% CI [5.683e3, 1.244e4], exponent 95% CI
      [0.9567, 1.0689], R^2=0.9641.
    - The equal-model mean absolute vertical offset decreases from 0.8078
      decades for dx to 0.2408 decades for dx^2 dt.
    The plotted working-model 95% observation prediction intervals vary with
    x. Their values at x=1, the working-model parameter intervals, and
    model-clustered sensitivity intervals are written to ``throughput_fit.csv``.
    """

    data = load_raw_data(data_path)
    fit_dx = fit_power_law(data, "dx")
    fit_dx2_dt = fit_power_law(data, "x")
    if output_path is None:
        output_path = DEFAULT_TWO_PANEL_OUTPUT if two_panel else DEFAULT_OUTPUT

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["STIXGeneral", "DejaVu Serif"],
            "mathtext.fontset": "stix",
            "axes.labelsize": 24,
            "xtick.labelsize": 16,
            "ytick.labelsize": 16,
            "legend.fontsize": 16,
        }
    )
    if two_panel:
        fig, axes = plt.subplots(1, 2, figsize=(15.8, 4.5), sharey=True)
        _plot_panel(
            axes[0],
            fit_dx,
            x_label=r"$\Delta x\;[{}^{\circ}]$",
            x_limits=(2e-2, 5.5),
            panel_label="(a)",
        )
        _plot_panel(
            axes[1],
            fit_dx2_dt,
            x_label=r"$(\Delta x)^2\,\Delta t\;[({}^{\circ})^2\,\mathrm{hr}]$",
            x_limits=(2e-5, 1.3e2),
            panel_label="(b)",
            legend_location="lower right",
        )
        axes[0].set_ylabel(
            r"$\mathrm{SYPD}_{\mathrm{norm}}$"
        )
    else:
        fig, ax = plt.subplots(figsize=(10.2, 4.5))
        _plot_panel(
            ax,
            fit_dx2_dt,
            x_label=r"$(\Delta x)^2\,\Delta t\;[({}^{\circ})^2\,\mathrm{hr}]$",
            x_limits=(2e-5, 1.3e2),
            legend_location="upper left",
        )
        ax.set_ylabel(
            r"$\mathrm{SYPD}_{\mathrm{norm}}$"
        )
    fig.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    fig.savefig(output_path.with_suffix(".png"), dpi=180, bbox_inches="tight")
    plt.close(fig)

    summary = pd.DataFrame(
        [
            _fit_record("horizontal_resolution", fit_dx),
            _fit_record("spatiotemporal_resolution", fit_dx2_dt),
        ]
    )
    summary.to_csv(output_path.parent / "throughput_fit.csv", index=False)
    offsets = pd.DataFrame(
        _model_offset_records("horizontal_resolution", fit_dx)
        + _model_offset_records("spatiotemporal_resolution", fit_dx2_dt)
    )
    offsets.to_csv(output_path.parent / "throughput_model_offsets.csv", index=False)
    return fit_dx2_dt
