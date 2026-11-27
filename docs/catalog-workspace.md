# Catalog workspace

Open **Catalog** in the navigation to search videos, tags, transcripts, frames, scenes, jobs, stage runs, embeddings, or review notes. Each dataset lists its available fields and presets. Choose **Filter by field** to combine conditions. Select a column heading to sort, or select a record number to read the full values and open its video.

**Breakdown** groups the current selection and shows measurement statistics. Percentiles use nearest rank over the complete filtered selection. Missing values are counted separately. **Quality checks** opens the records behind each finding. Download a JSON snapshot, then load it after another processing run to compare counts. The browser reads the baseline locally.

Saved views persist in the current browser. An export contains the selected columns across all matching pages, up to 2,000 rows. Choose CSV for spreadsheets, JSON for arrays of records, or NDJSON for line-oriented processing.

## Editorial review

From **Compare videos**, choose two assets to compare technical metadata, scene coverage, approved tag overlap, and transcript vocabulary. The URL retains both video IDs. Overlap is the number of distinct shared items divided by the number in either video. A missing transcript leaves the vocabulary comparison unavailable.

On a video detail page, open **Review notes** to add feedback for the whole video or a specific time. Reviewers can edit, resolve, and reopen notes. Revisions protect concurrent edits, and the history records changes to state, category, and time. Apply the existing Alembic upgrade before enabling notes on an existing installation.

**Export video metadata** downloads an individual sidecar or a ZIP of the available files. The manifest includes approved tags and timestamp adjustments. WebVTT and FFmpeg metadata use scene boundaries. The transcript download contains plain text. Review notes stay in the editorial workflow.

## Reporting from Python

Installing the backend provides the `cinetag-catalog` command. Set `CINETAG_API_URL` to the API origin and `CINETAG_API_KEY` when authentication is enabled.

```bash
cinetag-catalog datasets
cinetag-catalog describe stages
cinetag-catalog query notes --preset open --columns title,category,body
cinetag-catalog groups videos --by codec
cinetag-catalog quality --json -o baseline.json
cinetag-catalog diff baseline.json --fail-on-increase
cinetag-catalog delivery 11 --file bundle -o video-11.zip
```

For an offline comparison, supply two saved reports with `diff baseline.json --current current.json`. With `--fail-on-increase`, exit code 3 means an existing check gained findings.
