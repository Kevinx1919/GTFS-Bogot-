# AGENTS.md

## Project overview

This repository implements the **Bogotá GTFS Mobility Lakehouse**. It relates planned service from official versioned GTFS static feeds with observed demand from official validations and exits. GTFS-Realtime is an optional operational enrichment source and remains monitored until the provider is available. The project persists raw evidence, transforms it with Databricks and PySpark, and serves governed metrics to Power BI. n8n/Ollama may summarize approved anomalies, but it is not part of the data-processing control plane.

Schedule each source according to its publication cadence. GTFS-Realtime, when enabled, runs every 5 minutes in `America/Bogota`; static GTFS runs when a new version is published; demand sources run daily or monthly as their contracts allow. Store ingestion timestamps in UTC and convert only for operational reporting.

## Architecture boundaries

- **Raw / Volume:** immutable source files and manifests. Never alter an existing raw object.
- **Bronze:** append-only ingestion evidence and source snapshots.
- **Silver:** decoded, typed, deduplicated and quality-validated GTFS entities.
- **Gold:** documented, consumption-ready planned-offer, observed-demand and approved operational metrics at their stated grain.
- **Agent layer:** read-only access to curated anomaly/report views. It must not write data, modify thresholds, deploy code, or trigger destructive actions.

## Repository layout

Use this layout as implementation begins:

```text
src/                 Local Python helpers and shared utilities
databricks/          Notebooks, jobs/bundles and Spark code
tests/               Unit tests and small, non-sensitive fixtures
docs/                Architecture, data contracts, sources and runbooks
infra/               Declarative Databricks configuration where applicable
```

Do not commit raw GTFS snapshots, large binary protobuf files, databases, generated dashboards, virtual environments or secrets.

## Data rules

- Preserve every fetch with `run_id`, source URL, UTC capture time, HTTP status, byte length and SHA-256 hash.
- Make ingestion idempotent. A retry must not create duplicate records.
- Never infer or manufacture fields that are absent from a GTFS feed.
- Validate coordinates, timestamps, entity identifiers and impossible geographic jumps before deriving speed.
- Calculate operational speed from consecutive positions only; do not label it citywide traffic congestion.
- Never treat validations as per-vehicle occupancy, punctuality, waiting time or origin-destination data.
- Only calculate a demand-to-planned-supply proxy after verifying compatible time, location and component keys.
- Do not present statistical anomalies as trustworthy until sufficient historical baseline exists. Document the minimum history and threshold used.
- Quarantine invalid records with their rejection reason; do not silently discard them.

## Security and privacy

- Keep credentials in Databricks secrets or local environment variables only.
- `.env` files are local-only and must remain ignored.
- Redact access tokens, cookies and private configuration from logs, tests, screenshots and commits.
- Use only approved public, official data sources and preserve source attribution and license terms in `docs/sources.md`.

## Code style

- Python: type hints for public functions, `snake_case`, small functions, explicit errors, structured/loggable context.
- PySpark: explicit schemas; avoid schema inference in production; use built-in Spark functions before UDFs.
- SQL: lowercase keywords, `snake_case` identifiers, explicit column lists, no `select *` in curated layers.
- Make time zones explicit in code and SQL.
- Configuration must be environment-driven; never hardcode workspace URLs, catalog names, volume paths, endpoint URLs or secrets in reusable code.

## Learning documentation

- Every notebook block added to the project must be documented in `docs/notebook_runbook.md` before or alongside its implementation.
- Document at block level: purpose, inputs, outputs, persistent side effects, validation and material operational decisions.
- Explain code in Spanish using the project’s real values, while clearly marking values that will later become environment configuration.
- Include concise Spanish comments at the start of each logical code block and only beside non-obvious decisions. Do not explain syntax line by line or add comments that merely restate the code.
- Keep walkthroughs concise and professionally useful; implementation code is the primary source of technical detail.
- Distinguish data-plane actions (download, write, transform) from control-plane actions (catalog, schema, volume, job configuration).
- Do not advance to a downstream layer until the learner has verified and understood the result of the preceding block.

## Testing and verification

- Unit tests must use local fixtures or mocked HTTP; no external HTTP calls in the default test suite.
- Test valid and malformed feed decoding, idempotency, quality rejections, and operational-speed calculations.
- Keep fixtures minimal and sanitized.
- Before merging, run the documented formatter, linter and unit tests once they are introduced.
- Any Databricks deployment must have a dry-run/validation or a dev-environment smoke test before a production schedule is enabled.

## Git workflow

- Branch names follow `feature/<topic>`, `fix/<topic>` or `docs/<topic>`.
- Make focused commits using Conventional Commit style, for example `feat: add raw vehicle positions ingestion`.
- Do not commit unrelated local files or rewrite another contributor's work.
- Pull requests must state: source impact, layer impact, schema changes, quality checks, tests executed and rollback/operational notes.

## Definition of done

A change is complete when it includes the needed code/configuration, documentation, automated tests proportionate to risk, and a verification result. Data changes must also document lineage, grain, time zone, quality behavior and idempotency strategy.
