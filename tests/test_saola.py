"""Integration checks for the optional, Git-ignored Saola inputs."""

from pathlib import Path

import pytest
from pypdf import PdfReader

from aipwc_figures.saola import (
    DEFAULT_DATA,
    load_forecasts,
    load_observations,
    make_figure,
)


REQUIRED_EXTERNAL = [
    DEFAULT_DATA / "forecasts" / "2023_TIGGE_IFS.csv",
    DEFAULT_DATA / "forecasts" / "2023_PANGU.csv",
    DEFAULT_DATA / "forecasts" / "2023_GENC.csv",
    DEFAULT_DATA
    / "forecasts"
    / "postprocessing_panguweather_ANN_LeakyReLU,_M_2023.csv",
    DEFAULT_DATA / "ibtracs" / "ibtracs.ALL.list.v04r01.csv",
]

pytestmark = pytest.mark.skipif(
    not all(path.is_file() for path in REQUIRED_EXTERNAL),
    reason="large external Saola CSVs are not installed",
)


def test_saola_raw_inputs_and_pdf(tmp_path: Path) -> None:
    observations = load_observations()
    forecasts = load_forecasts()

    assert len(observations) == 131
    assert len(forecasts) == 1551
    assert forecasts.groupby("model")["member"].nunique().to_dict() == {
        "AI Post-Processing": 50,
        "Deterministic AI": 1,
        "Physics-based": 50,
        "Probabilistic AI": 50,
    }

    output = tmp_path / "Figure_Forecast_Saola.pdf"
    make_figure(output_path=output)
    assert len(PdfReader(output).pages) == 1
    assert output.with_suffix(".png").is_file()
