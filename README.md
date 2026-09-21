# AI Pathways from Weather to Climate: figure reproduction

This repository contains the raw inputs and one Python script for each of two
figures:

- `scripts/plot_saola.py`: the five-panel Typhoon Saola forecast figure;
- `scripts/plot_throughput.py`: the two-panel normalized-throughput figure.

Both scripts read directly from `data/raw/` and write a PDF and PNG to
`output/`. They do not modify the source data.

## Installation

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), clone the
repository, and run from its root:

```bash
uv sync --frozen
```

Python 3.12 is selected by `.python-version`, and `uv.lock` fixes the complete
environment. No environment activation is required.

## Reproduce the figures

```bash
uv run python scripts/plot_throughput.py
uv run python scripts/plot_saola.py
```

The scripts create:

```text
output/Figure_SYPD_two_panel.pdf
output/Figure_Forecast_Saola.pdf
```

PNG previews with the same names are also generated. The output directory is
ignored by Git.

## Raw data

The throughput CSV, GeoTIFFs, station locations, and archived
[Natural Earth](https://www.naturalearthdata.com/about/terms-of-use/) public-domain
shapefiles are stored under `data/raw/` and tracked by Git. The five Saola
forecast and observation tables total approximately 547 MB and are intentionally
not tracked:

```text
data/raw/saola/forecasts/2023_TIGGE_IFS.csv
data/raw/saola/forecasts/2023_PANGU.csv
data/raw/saola/forecasts/2023_GENC.csv
data/raw/saola/forecasts/postprocessing_panguweather_ANN_LeakyReLU,_M_2023.csv
data/raw/saola/ibtracs/ibtracs.ALL.list.v04r01.csv
```

The public archive will be added before release:

```text
Zenodo concept DOI: TO BE ADDED
Saola raw-data download: TO BE ADDED
```

Extract the downloaded archive under `data/raw/saola/` so that the five files
appear at the paths above.

`data/raw/checksums.sha256` records every expected raw-file digest. From WSL,
verify the inputs without modifying them:

```bash
sha256sum --check data/raw/checksums.sha256
```

## Saola figure

The forecast is initialized at 12:00 UTC on 31 August 2023 and plotted through
12:00 UTC on 3 September, a nominal 72-hour window. Lines show observations,
the ECMWF IFS ensemble mean, deterministic Pangu, the GenCast ensemble mean,
and the Pangu post-processing ensemble mean. IBTrACS intensity is read from
`USA_WIND` and `USA_PRES`. The yellow and dashed-purple shading gives the full
memberwise minimum--maximum range, matching the source figure. These ranges
describe the available ensemble members; they are not confidence or prediction
intervals. GenCast spans lead times 0--72 h, IFS and post-processing span
6--72 h, and the available Pangu track spans 6--60 h.

Panels (d)--(e) are valid at 06:00 UTC on 1 September 2023, as in Figure 7 of
[Zhang et al. (2025)](https://doi.org/10.1029/2025JH000792).

Suggested manuscript caption:

> **AI forecast refinement for tropical cyclones, applied to Typhoon Saola
> (2023).** (a) Track forecasts compared with IBTrACS observations. (b) Maximum
> wind speed and (c) minimum sea-level pressure forecasts. Black denotes
> observations; orange the ECMWF IFS ensemble mean; solid purple Pangu; yellow
> the GenCast ensemble mean; and dashed purple the Pangu post-processing
> ensemble mean. Shading in (b)--(c) shows the full memberwise range for GenCast
> and Pangu post-processing. (d) Near-real-time CCMP analysis and (e)
> deep-learning-downscaled wind magnitude at 06:00 UTC on 1 September 2023. Colors
> in (d)--(e) show wind speed in m s$^{-1}$, and black points indicate available
> in situ observations. Panels (a)--(c) use \cite{gomez2026tcbench}; panels
> (d)--(e) use \cite{zhang2025NNfusionTC}.

## Throughput figure

For horizontal grid spacing `dx` in degrees and time step `dt` in hours, `dt`
is the interval used to update the prognostic state. The second-panel predictor
is named explicitly in the code:

```text
spatiotemporal_resolution = dx**2 * dt
```

The normalized throughput is

```text
SYPD_norm = SYPD * prognostic_vars * vertical_levels / accelerators.
```

The analysis excludes downscaling entries and the CPU-only `ICON_A_GPU` rows,
leaving 51 configurations from six model families. The center lines are
weighted least-squares fits in base-10 log space, with equal total weight for
each model family. The gray bands are nominal 95% model-balanced CV+-style prediction
bands: each family is held out in turn, its absolute log residuals are paired
with predictions from the other five families, and every family receives equal
total calibration weight. This construction is invariant to an arbitrary
rescaling of the design weights. With only six model families it is descriptive,
not a distribution-free group-conformal coverage guarantee. The script also
prints model-clustered sensitivity intervals for the fitted coefficients.

Expected results from the deposited CSV are:

```text
SYPD_norm = 4331.33 * horizontal_resolution**3.13714
coefficient 95% CI: [1938.92, 9675.72]
exponent 95% CI:    [2.74176, 3.53251]
weighted R^2:       0.838415
nominal 95% CV+-style PI at horizontal_resolution=1: [33.78, 2.04e6]

SYPD_norm = 8408.99 * spatiotemporal_resolution**1.012775
coefficient 95% CI: [5683.24, 12442.04]
exponent 95% CI:    [0.956666, 1.068884]
clustered exponent sensitivity CI: [0.874692, 1.150857]
weighted R^2:       0.964096
nominal 95% CV+-style PI at spatiotemporal_resolution=1: [602.44, 1.60e5]
```

The equal-model mean absolute vertical offset is 0.81 decades using horizontal
resolution alone and 0.24 decades using spatiotemporal resolution. This is a
descriptive cross-model comparison, not an intrinsic hardware or algorithmic
scaling law: hardware, precision, implementation maturity, nominal resolution,
and reported state definitions differ among entries.

The throughput provenance below summarizes the `source` and `source_note`
columns of the raw CSV. Correspondence entries are not independently
accessible. The raw CSV spells Oliver Watt-Meyer's surname as
`Watts-Meyer`; that source typo is documented here rather than silently
changing the raw file.

| Model | Source recorded in the raw CSV |
| --- | --- |
| ACE2 | Oliver Watt-Meyer correspondence |
| CAMulator and CAMulator Coupled | Will Chapman correspondence |
| SCREAM | [SCREAM source](https://doi.org/10.1029/2024MS004314) |
| ICON-A | [ICON-A source](https://doi.org/10.5194/gmd-15-6985-2022) |
| CliMA | [CliMA atmosphere dynamical core preprint](https://essopenarchive.org/users/891100/articles/1268069-the-climate-modeling-alliance-atmosphere-dynamical-core-concepts-numerics-and-scaling) |
| NeuralGCM | [NeuralGCM source, Table 1](https://www.nature.com/articles/s41586-024-07744-y/tables/1) |
| R2-D2 | [R2-D2 source](https://doi.org/10.1073/pnas.2420288122) and Ignacio Lopez-Gomez correspondence |
| GenFocal | [arXiv:2412.08079](https://arxiv.org/abs/2412.08079) and Ignacio Lopez-Gomez correspondence |

## GitHub and Zenodo

For the software archive, [enable the public repository in
Zenodo](https://help.zenodo.org/docs/github/enable-repository/) and create a
[GitHub release](https://help.zenodo.org/docs/github/archive-software/github-upload/).
Zenodo archives that release and assigns a version DOI and a stable concept DOI.
The ignored 547 MB Saola tables are not included in the GitHub archive. Add them
to a data-containing Zenodo version, replace the placeholders above with the
concept DOI and download URL, and only then claim that a fresh clone reproduces
the Saola figure.

## License

Code is released under the MIT License. Upstream datasets retain their original
terms and should be cited according to the article and source repositories.
