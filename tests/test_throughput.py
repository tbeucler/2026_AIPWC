"""Numerical regression tests for the throughput analysis."""

from pathlib import Path

import pandas as pd
import pytest
from pypdf import PdfReader

from aipwc_figures.throughput import (
    fit_power_law,
    load_raw_data,
    make_figure,
    select_fit_rows,
)


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "throughput" / "Throughput_Data_AIPWC.csv"


def test_raw_selection_is_stable() -> None:
    selected = select_fit_rows(load_raw_data(RAW))
    assert len(selected) == 51
    assert selected["model_name"].nunique() == 6


def test_equal_model_weighted_fit_is_reproducible() -> None:
    data = load_raw_data(RAW)
    fit = fit_power_law(data)
    totals = fit.weights.groupby(fit.observations["model_name"]).sum()
    assert totals.max() == pytest.approx(totals.min())
    assert fit.coefficient == pytest.approx(8408.990146029078, rel=1e-10)
    assert fit.exponent == pytest.approx(1.0127748533455463, rel=1e-10)
    assert fit.result.rsquared == pytest.approx(0.9640956279048623, rel=1e-10)
    assert fit.coefficient_ci95 == pytest.approx(
        (5683.239088967111, 12442.044786270888), rel=1e-10
    )
    assert fit.exponent_ci95 == pytest.approx(
        (0.9566658245622965, 1.068883882128796), rel=1e-10
    )
    robust_coefficient, robust_exponent = fit.cluster_robust_ci95
    assert robust_coefficient == pytest.approx(
        (4707.889522527792, 15019.705738134537), rel=1e-10
    )
    assert robust_exponent == pytest.approx(
        (0.8746924552370358, 1.1508572514540567), rel=1e-10
    )

    fit_dx = fit_power_law(data, "dx")
    assert fit_dx.coefficient == pytest.approx(4331.326713220614, rel=1e-10)
    assert fit_dx.exponent == pytest.approx(3.137135787275872, rel=1e-10)
    assert fit_dx.result.rsquared == pytest.approx(0.838415071288382, rel=1e-10)


def test_publication_pdf_is_valid(tmp_path: Path) -> None:
    output = tmp_path / "Figure_SYPD.pdf"
    make_figure(RAW, output)
    assert len(PdfReader(output).pages) == 1
    assert output.with_suffix(".png").is_file()
    assert (tmp_path / "throughput_fit.csv").is_file()
    assert (tmp_path / "throughput_model_offsets.csv").is_file()
    offsets = pd.read_csv(tmp_path / "throughput_model_offsets.csv")
    mean_absolute = (
        offsets.assign(absolute=offsets["mean_offset_decades"].abs())
        .groupby("fit")["absolute"]
        .mean()
    )
    assert mean_absolute["horizontal_resolution"] == pytest.approx(
        0.8078091921453278
    )
    assert mean_absolute["spatiotemporal_resolution"] == pytest.approx(
        0.24084078376958631
    )

    two_panel = tmp_path / "Figure_SYPD_two_panel.pdf"
    make_figure(RAW, two_panel, two_panel=True)
    assert len(PdfReader(two_panel).pages) == 1
    assert two_panel.with_suffix(".png").is_file()
