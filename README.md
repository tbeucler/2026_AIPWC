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

The throughput CSV, GeoTIFFs, station locations, and archived Natural Earth
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

Their original Curnagl locations are:

```text
/work/FAC/FGSE/IDYST/tbeucler/default/milton/TCBench Results/
/work/FAC/FGSE/IDYST/tbeucler/default/milton/repos/alpha_bench/tracks/ibtracs/
```

`data/raw/checksums.sha256` records every expected raw-file digest. From WSL,
verify the inputs without modifying them:

```bash
sha256sum --check data/raw/checksums.sha256
```

## Saola figure

The forecast is initialized at 12:00 UTC on 31 August 2023 and plotted through
12:00 UTC on 3 September, a nominal 72-hour window. Lines show observations,
the ECMWF IFS ensemble mean, deterministic Pangu, the GenCast ensemble mean,
and the Pangu post-processing ensemble mean. The yellow and dashed-purple
shading gives the full memberwise minimum--maximum range, matching the source
figure. These ranges describe the available ensemble members; they are not
confidence or prediction intervals. GenCast spans lead times 0--72 h, IFS and
post-processing span 6--72 h, and the available Pangu track spans 6--60 h.

Suggested manuscript caption:

> **AI forecast refinement for tropical cyclones, applied to Typhoon Saola
> (2023).** (a) Track forecasts compared with IBTrACS observations. (b) Maximum
> wind speed and (c) minimum sea-level pressure forecasts. Black denotes
> observations; orange the ECMWF IFS ensemble mean; solid purple Pangu; yellow
> the GenCast ensemble mean; and dashed purple the Pangu post-processing
> ensemble mean. Shading in (b)--(c) shows the full memberwise range for GenCast
> and Pangu post-processing. (d) Near-real-time CCMP analysis and (e)
> deep-learning-downscaled wind magnitude at the reference target time. Colors
> in (d)--(e) show wind speed in m s$^{-1}$, and black points indicate available
> in situ observations. Panels (a)--(c) use \cite{gomez2026tcbench}; panels
> (d)--(e) use \cite{zhang2025NNfusionTC}.

## Throughput figure

For horizontal grid spacing `dx` in degrees and time step `dt` in hours, the
second-panel predictor is named explicitly in the code:

```text
spatiotemporal_resolution = dx**2 * dt
```

The normalized throughput is

```text
SYPD_norm = SYPD * prognostic_vars * vertical_levels / accelerators.
```

The analysis excludes downscaling entries and the CPU-only `ICON_A_GPU` rows,
leaving 51 configurations from six model families. It fits weighted least
squares in base-10 log space, with equal total weight for each model family.
The gray bands are pointwise 95% observation prediction intervals under the
working WLS model, not confidence intervals for the fitted mean. Because the
equal-model weights are design weights rather than inverse error variances,
the script also prints model-clustered sensitivity intervals. With only six
clusters, both sets of intervals should be interpreted descriptively.

Expected results from the deposited CSV are:

```text
SYPD_norm = 4331.33 * horizontal_resolution**3.13714
coefficient 95% CI: [1938.92, 9675.72]
exponent 95% CI:    [2.74176, 3.53251]
weighted R^2:       0.838415
95% observation PI at horizontal_resolution=1: [32.95, 5.69e5]

SYPD_norm = 8408.99 * spatiotemporal_resolution**1.012775
coefficient 95% CI: [5683.24, 12442.04]
exponent 95% CI:    [0.956666, 1.068884]
clustered exponent sensitivity CI: [0.874692, 1.150857]
weighted R^2:       0.964096
95% observation PI at spatiotemporal_resolution=1: [841.45, 8.40e4]
```

The equal-model mean absolute vertical offset is 0.81 decades using horizontal
resolution alone and 0.24 decades using spatiotemporal resolution. This is a
descriptive cross-model comparison, not an intrinsic hardware or algorithmic
scaling law: hardware, precision, implementation maturity, nominal resolution,
and reported state definitions differ among entries.

## GitHub and Zenodo

For the software DOI, [enable the public repository in
Zenodo](https://help.zenodo.org/docs/github/enable-repository/) and create a
[GitHub release](https://help.zenodo.org/docs/github/archive-software/github-upload/).
Zenodo archives that release and assigns its DOI. The ignored 547 MB Saola
tables are not included in the GitHub release archive; deposit them separately
and add their DOI here before claiming that a fresh clone reproduces the Saola
figure.

## License

Code is released under the MIT License. Upstream datasets retain their original
terms and should be cited according to the article and source repositories.
