# AI Pathways from Weather to Climate: figure reproduction

This repository reproduces two figures for *Artificial Intelligence Pathways
from Weather to Climate*:

1. the five-panel Typhoon Saola forecast-refinement case study; and
2. the normalized model-throughput comparison.

The code reads immutable source files from `data/raw/`, reconstructs all derived
quantities, and writes publication PDFs plus lightweight PNG previews to
`output/`. Raw-file checksums and numerical regression tests make silent data
changes detectable.

## Install with uv

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), clone this
repository, and run from the repository root:

```bash
uv sync --frozen
```

The repository pins Python 3.12 in `.python-version` and exact package versions
in `uv.lock`. `uv sync --frozen` creates the local `.venv` without modifying
that lock. No activation is required when commands are prefixed with `uv run`.

## Reproduce the figures

```bash
uv run aipwc-figures throughput
uv run aipwc-figures throughput --two-panel
uv run aipwc-figures saola
```

After all Saola inputs are present, both can be built together:

```bash
uv run aipwc-figures --two-panel
```

Outputs:

```text
output/Figure_SYPD.pdf
output/Figure_SYPD_two_panel.pdf
output/Figure_Forecast_Saola.pdf
output/throughput_fit.csv
output/throughput_model_offsets.csv
```

The Saola map uses archived Natural Earth 1:50 million land, ocean, and
coastline shapefiles under `data/raw/natural_earth/`; figure generation therefore
does not need to fetch map data at runtime.

## What the throughput script computes

Panel (a) uses horizontal grid spacing `dx` in degrees. Panel (b), or the
single-panel version, uses horizontal grid spacing and time step `dt` in hours:

```text
x = dx**2 * dt.
```

For simulated years per wall-clock day (`SYPD`), number of prognostic variables
`nprog`, vertical levels `nvert`, and accelerators `nacc`, the throughput proxy is

```text
SYPD_norm = SYPD * nprog * nvert / nacc.
```

The regression is weighted least squares in base-10 log space. Each model has
equal total weight, preventing models with many strong-scaling measurements
from dominating the fit. Downscaling entries are excluded, as are the
`ICON_A_GPU` CPU-only rows. The gray band is a pointwise, working-model 95%
*observation prediction* interval for an individual reported configuration,
not a confidence interval for the mean. Because it varies with the abscissa,
it is stored as a reference interval at `x = 1` in
`output/throughput_fit.csv`.

The equal-model weights are design weights, not known inverse error variances.
Consequently, the conventional WLS intervals reproduce the requested analysis
but rely on independent, homoscedastic log-errors and should not be presented
as assumption-free uncertainty. The fit table also reports small-sample
cluster-robust sensitivity intervals with model as the cluster. There are only
six clusters, so these intervals are themselves approximate; the fitted lines
and envelopes are best interpreted descriptively.

With the deposited CSV, the expected fits are:

```text
SYPD_norm = 4331.33 * dx**3.13714
working-model coefficient 95% CI: [1938.92, 9675.72]
working-model exponent 95% CI:    [2.74176, 3.53251]
weighted R^2:        0.838415

SYPD_norm = 8408.99 * (dx**2 * dt)**1.012775
working-model coefficient 95% CI: [5683.24, 12442.04]
working-model exponent 95% CI:    [0.956666, 1.068884]
cluster-robust coefficient sensitivity CI: [4707.89, 15019.71]
cluster-robust exponent sensitivity CI:    [0.874692, 1.150857]
weighted R^2:        0.964096
```

Thus `1.01 +/- 0.06` is the working-model result; model clustering widens this
to approximately `1.01 +/- 0.14`. At an abscissa of one, the corresponding
working-model 95% observation prediction intervals are
`[32.95, 5.69e5]` for panel (a) and `[841.45, 8.40e4]` for panel (b). These are
reference slices through the plotted bands, not fixed intervals for all x.

For each model, `throughput_model_offsets.csv` also records the mean vertical
log-residual from each fit. Averaging the absolute model means with equal weight
across the six models gives 0.81 decades for horizontal resolution alone and
0.24 decades after including the time step.

This is a descriptive cross-model comparison, not an intrinsic hardware or
algorithmic scaling law: hardware, precision, implementation maturity, nominal
resolution, and reported state definitions differ across entries.

## Verify

```bash
uv run pytest
```

The tests verify raw-file checksums, the 51-row throughput selection, equal
model weighting, and the fitted relation. Generated PDFs should additionally be
inspected visually before submission.

## Data provenance

See [`data/raw/README.md`](data/raw/README.md) for source locations and
filenames. The five 547 MB Saola CSVs are a local, Git-ignored cache whose
hashes are recorded in `external_checksums.sha256`; they should be deposited as
a separate Zenodo data archive. Do not edit files under `data/raw/`.

The release and data-deposit sequence is documented in
[`ZENODO_HANDOFF.md`](ZENODO_HANDOFF.md).

## License

Code in this repository is released under the MIT License. Upstream datasets
retain their own terms and should be cited according to the article and their
source repositories.
