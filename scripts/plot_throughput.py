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

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUTPUT = ROOT / "output"
DEFAULT_DATA = RAW / "throughput" / "Throughput_Data_AIPWC.csv"
DEFAULT_OUTPUT = OUTPUT / "Figure_SYPD_two_panel.pdf"

RAW_COLUMNS = [
    "model_name",
    "model_type",
    "horiz_res_deg",
    "vert_levels",
    "time_step_h",
    "sypd",
    "hardware_count",
    "accelerators_per_node_assumed",
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
MODEL_LABELS = {
    "SCREAM_GPU": "SCREAM",
    "ICON_A_GPU": "ICON-A",
}


@dataclass(frozen=True)
class ThroughputFit:
    """Weighted log-log fit and the observations used to estimate it."""

    observations: pd.DataFrame
    weights: pd.Series
    result: object
    predictor: str

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

    def prediction_interval95(self, predictor_value: float) -> tuple[float, float]:
        """Return the nominal 95% model-balanced CV+-style interval."""

        if predictor_value <= 0:
            raise ValueError("predictor_value must be positive")
        lower, upper = _cvplus_prediction_interval(
            self, np.array([predictor_value], dtype=float)
        )
        return float(lower[0]), float(upper[0])


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
            "hardware_count": "nhardware",
            "accelerators_per_node_assumed": "nacc_per_hardware",
            "n_accelerators": "nacc_reported",
            "prognostic_vars": "nprog",
        }
    )
    numeric_columns = [
        "dx",
        "nvert",
        "dt",
        "sypd",
        "nhardware",
        "nacc_per_hardware",
        "nacc_reported",
        "nprog",
    ]
    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    # Reconstruct the accelerator count from the primitive hardware columns.
    data["nacc"] = data["nhardware"] * data["nacc_per_hardware"]
    comparable = data["nacc"].notna() & data["nacc_reported"].notna()
    inconsistent = comparable & ~np.isclose(
        data["nacc"], data["nacc_reported"], equal_nan=True
    )
    if inconsistent.any():
        rows = data.loc[
            inconsistent,
            ["model_name", "nacc", "nacc_reported"],
        ].to_dict("records")
        raise ValueError(f"Accelerator-count columns disagree: {rows}")

    data["spatiotemporal_resolution"] = data["dx"] ** 2 * data["dt"]
    positive_nacc = data["nacc"].where(data["nacc"].gt(0))
    data["sypd_norm"] = (
        data["sypd"] * data["nprog"] * data["nvert"] / positive_nacc
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
        & np.isfinite(data["spatiotemporal_resolution"])
        & np.isfinite(data["sypd_norm"])
        & data["spatiotemporal_resolution"].gt(0)
        & data["sypd_norm"].gt(0)
    )
    return data.loc[keep].copy()


def fit_power_law(
    data: pd.DataFrame,
    predictor: str = "spatiotemporal_resolution",
) -> ThroughputFit:
    """Fit a log-log power law with equal total weight per model."""

    observations = select_fit_rows(data)
    if len(observations) != 51 or observations["model_name"].nunique() != 6:
        counts = observations.groupby("model_name").size().sort_index().to_dict()
        raise ValueError(
            "Expected 51 configurations from six model families; "
            f"found {len(observations)} from "
            f"{observations['model_name'].nunique()}: {counts}"
        )
    counts = observations.groupby("model_name")["model_name"].transform("count")
    weights = 1.0 / counts
    weights = weights / weights.mean()

    log_predictor = np.log10(observations[predictor].to_numpy())
    log_t = np.log10(observations["sypd_norm"].to_numpy())
    design = sm.add_constant(log_predictor)
    result = sm.WLS(log_t, design, weights=weights.to_numpy()).fit()
    return ThroughputFit(observations, weights, result, predictor)


def _weighted_order_quantile(
    values: np.ndarray, weights: np.ndarray, quantile: float
) -> float:
    """Return a discrete weighted quantile; weight scaling has no effect."""

    order = np.argsort(values)
    sorted_values = np.asarray(values)[order]
    sorted_weights = np.asarray(weights)[order]
    threshold = quantile * sorted_weights.sum()
    index = np.searchsorted(np.cumsum(sorted_weights), threshold, side="left")
    return float(sorted_values[min(index, len(sorted_values) - 1)])


def _cvplus_prediction_interval(
    fit: ThroughputFit,
    predictor_values: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Construct a model-balanced, leave-one-model-family-out CV+-style band.

    Each model family is held out in turn. Absolute log-space residuals for the
    held-out family are paired with predictions from the corresponding fit.
    Candidate bounds receive equal total weight per model family. This avoids
    interpreting design weights as inverse error variances, but six families
    are too few for a distribution-free group-conformal coverage guarantee.
    """

    predictor_values = np.asarray(predictor_values, dtype=float)
    if np.any(~np.isfinite(predictor_values)) or np.any(predictor_values <= 0):
        raise ValueError("predictor values must be finite and positive")

    observations = fit.observations
    log_predictor = np.log10(observations[fit.predictor].to_numpy())
    log_t = np.log10(observations["sypd_norm"].to_numpy())
    grid_design = sm.add_constant(
        np.log10(predictor_values), has_constant="add"
    )
    lower_candidates = np.empty((len(observations), len(predictor_values)))
    upper_candidates = np.empty_like(lower_candidates)

    for model in observations["model_name"].unique():
        train = observations["model_name"].ne(model).to_numpy()
        test = ~train
        train_counts = (
            observations.loc[train]
            .groupby("model_name")["model_name"]
            .transform("count")
        )
        train_weights = 1.0 / train_counts.to_numpy()
        held_out_fit = sm.WLS(
            log_t[train],
            sm.add_constant(log_predictor[train], has_constant="add"),
            weights=train_weights,
        ).fit()
        held_out_prediction = held_out_fit.predict(
            sm.add_constant(log_predictor[test], has_constant="add")
        )
        scores = np.abs(log_t[test] - held_out_prediction)
        grid_prediction = held_out_fit.predict(grid_design)
        lower_candidates[test] = grid_prediction[None, :] - scores[:, None]
        upper_candidates[test] = grid_prediction[None, :] + scores[:, None]

    weights = fit.weights.to_numpy()
    lower = np.array(
        [
            _weighted_order_quantile(lower_candidates[:, index], weights, 0.025)
            for index in range(len(predictor_values))
        ]
    )
    upper = np.array(
        [
            _weighted_order_quantile(upper_candidates[:, index], weights, 0.975)
            for index in range(len(predictor_values))
        ]
    )
    return 10.0**lower, 10.0**upper


def _prediction_data(fit: ThroughputFit):
    log_predictor = np.log10(fit.observations[fit.predictor].to_numpy())
    grid_log = np.linspace(
        log_predictor.min() - 0.04, log_predictor.max() + 0.04, 600
    )
    grid_x = 10.0**grid_log
    lower, upper = _cvplus_prediction_interval(fit, grid_x)
    return (
        grid_x,
        10.0 ** fit.result.predict(sm.add_constant(grid_log)),
        lower,
        upper,
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
    ax.set_axisbelow(True)
    ax.fill_between(
        grid_x, lower, upper, color="0.78", alpha=0.42, linewidth=0, zorder=1
    )
    ax.plot(grid_x, line, color="black", linewidth=1.35, zorder=2)

    for name, style in MODEL_STYLES.items():
        rows = fit.observations["model_name"].eq(name)
        ax.scatter(
            fit.observations.loc[rows, fit.predictor],
            fit.observations.loc[rows, "sypd_norm"],
            label=MODEL_LABELS.get(name, name),
            edgecolors="none",
            alpha=0.98,
            zorder=3,
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


def mean_absolute_model_offset(fit: ThroughputFit) -> float:
    """Average absolute model-mean residual, in log10 decades."""
    observations = fit.observations.copy()
    log_predictor = np.log10(observations[fit.predictor].to_numpy())
    observations["offset_decades"] = (
        np.log10(observations["sypd_norm"].to_numpy())
        - fit.result.predict(sm.add_constant(log_predictor))
    )
    model_means = observations.groupby("model_name")["offset_decades"].mean()
    return float(model_means.abs().mean())


def make_figure(
    data_path: Path = DEFAULT_DATA,
    output_path: Path = DEFAULT_OUTPUT,
) -> tuple[ThroughputFit, ThroughputFit]:
    """Create the two-panel publication PDF and PNG preview.

    Expected with the frozen raw CSV and equal total weight per model:
    - dx fit: SYPD_norm = 4.331e3 * dx^3.1371; working-model coefficient 95% CI
      [1.939e3, 9.676e3], exponent 95% CI [2.7418, 3.5325], R^2=0.8384.
    - dx^2 dt fit: SYPD_norm = 8.409e3 * (dx^2 dt)^1.0128;
      working-model coefficient 95% CI [5.683e3, 1.244e4], exponent 95% CI
      [0.9567, 1.0689], R^2=0.9641.
    - The nominal model-balanced CV+-style intervals at predictor=1 are
      [33.7772, 2.03531e6] for dx and [602.437, 159874] for dx^2 dt.
    - The equal-model mean absolute vertical offset decreases from 0.8078
      decades for dx to 0.2408 decades for dx^2 dt.
    The plotted nominal 95% prediction bands use leave-one-model-family-out
    CV+-style scores in log space. Their values at predictor=1, the parameter
    intervals, and model-clustered sensitivity intervals are printed when run.
    """

    data = load_raw_data(data_path)
    missing_accelerators = sorted(
        data.loc[data["nacc"].isna(), "model_name"].dropna().unique()
    )
    if missing_accelerators:
        print(
            "Excluded configurations with incomplete accelerator metadata: "
            + ", ".join(missing_accelerators)
        )
    fit_dx = fit_power_law(data, "dx")
    fit_spatiotemporal = fit_power_law(data, "spatiotemporal_resolution")

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
        fit_spatiotemporal,
        x_label=r"$(\Delta x)^2\,\Delta t\;[({}^{\circ})^2\,\mathrm{hr}]$",
        x_limits=(2e-5, 1.3e2),
        panel_label="(b)",
        legend_location="lower right",
    )
    axes[0].set_ylabel(r"$\mathrm{SYPD}_{\mathrm{norm}}$")
    fig.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Omit volatile timestamps so repeated runs produce the same PDF bytes.
    fig.savefig(
        output_path,
        bbox_inches="tight",
        metadata={"CreationDate": None, "ModDate": None},
    )
    fig.savefig(output_path.with_suffix(".png"), dpi=180, bbox_inches="tight")
    plt.close(fig)

    return fit_dx, fit_spatiotemporal


def print_fit(label: str, fit: ThroughputFit) -> None:
    """Print the paper-facing fit and uncertainty numbers."""

    coefficient_ci = fit.coefficient_ci95
    exponent_ci = fit.exponent_ci95
    robust_coefficient_ci, robust_exponent_ci = fit.cluster_robust_ci95
    prediction_ci = fit.prediction_interval95(1.0)
    print(
        f"{label}: n={len(fit.observations)}\n"
        f"  SYPD_norm = {fit.coefficient:.6g} * {label}^{fit.exponent:.6f}\n"
        f"  working-model coefficient 95% CI: [{coefficient_ci[0]:.6g}, "
        f"{coefficient_ci[1]:.6g}]\n"
        f"  working-model exponent 95% CI: [{exponent_ci[0]:.6f}, "
        f"{exponent_ci[1]:.6f}]\n"
        f"  cluster-robust coefficient sensitivity CI: "
        f"[{robust_coefficient_ci[0]:.6g}, {robust_coefficient_ci[1]:.6g}]\n"
        f"  cluster-robust exponent sensitivity CI: "
        f"[{robust_exponent_ci[0]:.6f}, {robust_exponent_ci[1]:.6f}]\n"
        f"  weighted R^2: {fit.result.rsquared:.6f}\n"
        f"  model-balanced CV+-style nominal 95% PI at predictor=1: "
        f"[{prediction_ci[0]:.6g}, {prediction_ci[1]:.6g}]\n"
        f"  mean absolute model offset: "
        f"{mean_absolute_model_offset(fit):.6f} decades"
    )


if __name__ == "__main__":
    horizontal_fit, spatiotemporal_fit = make_figure()
    print_fit("horizontal_resolution", horizontal_fit)
    print_fit("spatiotemporal_resolution", spatiotemporal_fit)
    print(f"Wrote {DEFAULT_OUTPUT}")
