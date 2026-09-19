# Zenodo handoff

Use two linked records:

1. a **software** record generated from the tagged GitHub release; and
2. a **dataset** record containing the five Git-ignored Saola CSV files.

Keeping the records separate prevents the 547 MB input dataset from entering
Git history and lets software and data receive independent versions and DOIs.
Zenodo currently permits up to 100 files and 50 GB per record, so the five CSVs
fit comfortably in one dataset record.

Official guidance:

- GitHub integration: <https://help.zenodo.org/docs/github/>
- Software metadata and `CITATION.cff`: <https://help.zenodo.org/docs/github/describe-software/>
- File limits and preparation: <https://help.zenodo.org/docs/deposit/manage-files/>
- Reserving a DOI: <https://help.zenodo.org/docs/deposit/describe-records/reserve-doi/>

## 1. Confirm redistribution rights

Before uploading, confirm that all five files may be redistributed publicly.
Do not infer permission from cluster access. Record the applicable source and
license in the dataset description.

Dataset files:

```text
2023_TIGGE_IFS.csv
2023_PANGU.csv
2023_GENC.csv
postprocessing_panguweather_ANN_LeakyReLU,_M_2023.csv
ibtracs.ALL.list.v04r01.csv
```

Also upload copies of:

```text
external_checksums.sha256
data/raw/README.md
```

## 2. Create the dataset draft first

Create a new Zenodo upload with resource type **Dataset**. Upload the five CSVs
and the two metadata/checksum files, then reserve its DOI. Do not publish yet.

Complete these fields from the article metadata:

```text
Title:
Creators and ORCIDs:
Affiliations:
Description:
Version: 1.0.0
License(s):
Keywords:
Funding:
Related article DOI (when available):
```

## 3. Connect the repository to Zenodo

Enable this GitHub repository in Zenodo before creating the GitHub release.
Add a `CITATION.cff` only after the final creator order, affiliations, ORCIDs,
software title, and license are confirmed. Do not add both `CITATION.cff` and
`.zenodo.json`; Zenodo gives `.zenodo.json` precedence when both are present.

Insert the reserved dataset DOI into `README.md` and replace the temporary
Curnagl acquisition instructions with public Zenodo download instructions.

## 4. Validate the release candidate

From a clean clone, install and test exactly as documented:

```bash
uv sync --frozen
uv run pytest
uv run aipwc-figures throughput --two-panel
uv run aipwc-figures saola
```

Before tagging, verify that the large inputs are not tracked:

```bash
git check-ignore data/raw/saola/forecasts/2023_GENC.csv
git check-ignore data/raw/saola/ibtracs/ibtracs.ALL.list.v04r01.csv
git ls-files data/raw/saola/forecasts data/raw/saola/ibtracs
```

The first two commands must print ignored paths; the last command must print
nothing.

## 5. Publish and link the records

1. Commit the final repository state and tag `v1.0.0`.
2. Create the corresponding GitHub release; the enabled Zenodo integration
   archives it as a software record.
3. Add the software DOI to the dataset record as a related identifier.
4. Add the reserved dataset DOI to the software record as a related identifier.
5. Preview both records, confirm creator order and file lists, then publish the
   dataset draft.
6. Update the repository README with the final software and dataset DOIs.

Use new Zenodo versions for later file changes rather than replacing the files
behind an existing version DOI.
