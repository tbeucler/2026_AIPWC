# AI Pathways from Weather to Climate: figure reproduction

This repository reproduces two figures from raw data, with one Python script
for each figure:

- `scripts/plot_saola.py`: the five-panel Typhoon Saola forecast figure;
- `scripts/plot_throughput.py`: the two-panel normalized-throughput figure.

Both scripts read directly from `data/raw/` and write a PDF and PNG to
`output/`. They do not modify the source data. Small inputs are tracked by Git;
the larger inputs are retrieved from the versioned Zenodo data release below.

## Quick start

In a WSL or Linux terminal, install
[uv](https://docs.astral.sh/uv/getting-started/installation/) and ensure that
Git and `curl` are available. Then run:

```bash
git clone https://github.com/tbeucler/2026_AIPWC.git
cd 2026_AIPWC

uv sync --frozen

curl -L "https://zenodo.org/api/records/22872186/files/AIPWC_figure_data_v1.0.0.zip/content" -o AIPWC_figure_data_v1.0.0.zip
echo "671052e5de6bf8d3e77cd6cccf45105615d6820b3204f5ded9b18659db1273f6  AIPWC_figure_data_v1.0.0.zip" | sha256sum --check
uv run python -c "from zipfile import ZipFile; z=ZipFile('AIPWC_figure_data_v1.0.0.zip'); z.extractall('.', [n for n in z.namelist() if '/forecasts/' in n or '/ibtracs/' in n])"
rm -f AIPWC_figure_data_v1.0.0.zip
sha256sum --check data/raw/checksums.sha256

uv run python scripts/plot_throughput.py
uv run python scripts/plot_saola.py
```

Python 3.12 is selected by `.python-version`, and `uv.lock` fixes the complete
environment. No environment activation is required. The download is 51.9 MB
and expands to approximately 547 MB.

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

The complete figure-data release is archived on Zenodo:

- pinned version: [doi:10.5281/zenodo.22872186](https://doi.org/10.5281/zenodo.22872186);
- all versions: [doi:10.5281/zenodo.22872185](https://doi.org/10.5281/zenodo.22872185);
- [direct archive download](https://zenodo.org/api/records/22872186/files/AIPWC_figure_data_v1.0.0.zip/content)
  (51.9 MB; SHA-256
  `671052e5de6bf8d3e77cd6cccf45105615d6820b3204f5ded9b18659db1273f6`).

The quick-start commands verify the complete archive and extract only the five
large files absent from Git. The file `data/raw/checksums.sha256` then verifies
every input used by the scripts. Git preserves the tracked raw text files with
LF line endings on every platform, so their byte-level checksums are stable.
The archive also contains the smaller raw inputs for standalone reuse; the
quick-start extraction leaves the Git-tracked copies in place.

## Saola figure

The forecast is initialized at 12:00 UTC on 31 August 2023 and plotted through
12:00 UTC on 3 September, a nominal 72-hour window. Lines show observations,
the ECMWF IFS ensemble mean, deterministic Pangu, the GenCast ensemble mean,
and the Pangu post-processing ensemble mean. IBTrACS intensity is read from
`USA_WIND` and `USA_PRES`. The yellow and dashed-purple shading gives the full
memberwise minimum--maximum range, matching the source figure. These ranges
describe the available ensemble members; they are not confidence or prediction
intervals. Within the plotted window, GenCast is available every 6 h from
0--72 h, IFS every 6 h from 6--72 h, and Pangu every 6 h from 6--60 h. Pangu
post-processing is available at 6, 12, 18, 24, 48, and 72 h. Curves connect
the available forecast times without temporal interpolation.

Panels (d)--(e) are valid at 06:00 UTC on 1 September 2023, as in Figure 7 of
[Zhang et al. (2025)](https://doi.org/10.1029/2025JH000792). Both display the
shared 109--119$^\circ$E, 17--25$^\circ$N domain. The source-grid spacings are
0.25$^\circ$ for CCMP and 0.0625$^\circ$ for the downscaled field.

Suggested manuscript caption:

> **AI forecast refinement for tropical cyclones, applied to Typhoon Saola
> (2023).** (a) Track forecasts compared with IBTrACS observations. (b) Maximum
> wind speed and (c) minimum sea-level pressure forecasts. Black denotes
> observations; orange the ECMWF IFS ensemble mean; solid purple Pangu; yellow
> the GenCast ensemble mean; and dashed purple the Pangu post-processing
> ensemble mean. Shading in (b)--(c) shows the full memberwise range for GenCast
> and Pangu post-processing; forecasts are connected at their available valid
> times, which differ among products. (d) Near-real-time 0.25$^\circ$ CCMP
> analysis and (e) 0.0625$^\circ$ deep-learning-downscaled wind magnitude at
> 06:00 UTC on 1 September 2023, shown over their shared domain. Colors in
> (d)--(e) show wind speed in m s$^{-1}$, and black points indicate available
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

The accelerator count is reconstructed as `hardware_count *
accelerators_per_node_assumed` and checked against the reported
`n_accelerators` column. Spreadsheet formula columns and spacer rows are not
used. The analysis excludes two downscaling configurations, four ICON-A rows
labelled `trad_cpu`, and the CAMulator Coupled configuration, for which the
primitive accelerator metadata are missing. This leaves 51 configurations
from six model families. The center lines are
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

The throughput provenance below summarizes the `source` and `Comments`
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

The figure data have their own versioned Zenodo record,
[doi:10.5281/zenodo.22872186](https://doi.org/10.5281/zenodo.22872186). The
ignored 547 MB Saola tables therefore remain outside the Git repository and
will not be duplicated in the software archive. To archive the software,
[enable the public repository in
Zenodo](https://help.zenodo.org/docs/github/enable-repository/) and create a
[GitHub release](https://help.zenodo.org/docs/github/archive-software/github-upload/).
Zenodo will archive that release and assign the code its own version DOI and
stable concept DOI.

## License

Code is released under the MIT License. Upstream datasets retain their original
terms and should be cited according to the article and source repositories.
