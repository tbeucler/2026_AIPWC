# Raw data

Files in this directory are immutable inputs. `tests/test_raw_data.py` compares
their SHA-256 hashes with the manifests so accidental edits fail loudly.

## Throughput

`throughput/Throughput_Data_AIPWC.csv` is the author-supplied spreadsheet
export. The plotting code ignores its formula columns and reconstructs every
plotted quantity from the primitive columns.

## Typhoon Saola

The two GeoTIFFs and `station_loc.txt` were copied byte-for-byte from:

```text
C:/Users/tbeucler/Documents/GitHub/sam-dawn-handover/tcbench/
Saoloa_testing/figure_Typhoon_Saola/
```

The low-resolution TIFF keeps its original filename. The high-resolution TIFF
was renamed to distinguish it, without changing its bytes.

The following top-panel inputs still need to be copied from the source HPC
directories:

```text
/work/FAC/FGSE/IDYST/tbeucler/default/milton/TCBench Results/
/work/FAC/FGSE/IDYST/tbeucler/default/milton/repos/alpha_bench/tracks/ibtracs/
```

Place these raw track/member tables under `saola/forecasts/`:

```text
2023_TIGGE_IFS.csv
2023_PANGU.csv
2023_GENC.csv
postprocessing_panguweather_ANN_LeakyReLU,_M_2023.csv
```

Place `ibtracs.ALL.list.v04r01.csv` under `saola/ibtracs/`. The script derives
ensemble means and memberwise minimum--maximum ranges, so `_results`, `_RI`, and archived
duplicates are not inputs.

These five HPC files total approximately 547 MB and are intentionally ignored
by Git. Their expected hashes are recorded in `external_checksums.sha256`; the
test verifies them when the local files are present. They must be distributed
separately from the GitHub repository, for example as a Zenodo data archive.
Until that archive exists, the listed Curnagl paths require authorized UNIL
access; a fresh public clone can reproduce only the throughput figure.

Do not subset or rewrite the source files. If an upstream file changes, update
its SHA-256 digest in `external_checksums.sha256` only after documenting why.

## Coastlines

`natural_earth/` contains the original 1:50 million Natural Earth land, ocean,
and coastline shapefiles downloaded by Cartopy from
`https://naturalearth.s3.amazonaws.com/50m_physical/`. Natural Earth vector and
raster data are public domain. The files are archived here so figure generation
does not depend on a runtime download.
