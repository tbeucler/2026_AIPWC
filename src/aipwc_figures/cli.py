"""Command-line entry point for figure reproduction."""

from __future__ import annotations

import argparse

from . import saola, throughput


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "figure",
        choices=["all", "saola", "throughput"],
        nargs="?",
        default="all",
        help="Figure to build (default: all)",
    )
    parser.add_argument(
        "--two-panel",
        action="store_true",
        help="Use horizontal resolution for panel a and the existing scaling for panel b",
    )
    args = parser.parse_args()

    if args.figure in {"all", "throughput"}:
        throughput.make_figure(two_panel=args.two_panel)
        data = throughput.load_raw_data()
        for label, x_column in [
            ("horizontal resolution", "dx"),
            ("spatiotemporal resolution", "x"),
        ]:
            fit = throughput.fit_power_law(data, x_column)
            coefficient_ci = fit.coefficient_ci95
            exponent_ci = fit.exponent_ci95
            robust_coefficient_ci, robust_exponent_ci = fit.cluster_robust_ci95
            prediction_ci = fit.prediction_interval95(1.0)
            print(
                f"{label}: n={len(fit.observations)}, "
                f"SYPD_norm={fit.coefficient:.6g} x^{fit.exponent:.6f}; "
                f"working-model coefficient 95% CI=[{coefficient_ci[0]:.6g}, "
                f"{coefficient_ci[1]:.6g}]; exponent 95% CI="
                f"[{exponent_ci[0]:.6f}, {exponent_ci[1]:.6f}]; "
                f"cluster-robust sensitivity CIs: coefficient="
                f"[{robust_coefficient_ci[0]:.6g}, {robust_coefficient_ci[1]:.6g}], "
                f"exponent=[{robust_exponent_ci[0]:.6f}, "
                f"{robust_exponent_ci[1]:.6f}]; "
                f"weighted R^2={fit.result.rsquared:.6f}; observation "
                f"95% PI at x=1=[{prediction_ci[0]:.6g}, "
                f"{prediction_ci[1]:.6g}]"
            )
    if args.figure in {"all", "saola"}:
        saola.make_figure()
        print(f"Saola: wrote {saola.DEFAULT_OUTPUT}")


if __name__ == "__main__":
    main()
