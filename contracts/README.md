# Versioned contracts

`purchasing-v1.json` defines supported documents, critical fields, normalization,
classification and retention boundaries. `rules-v1.json` defines explicit financial
tolerances, cumulative matching and business exclusions. Calculated totals live in
check results; they never overwrite extracted values.

The JSON schemas are generated from the strict Pydantic types:

```bash
uv run python scripts/export_schemas.py
uv run python scripts/export_schemas.py --check
```

Text offsets refer to Unicode code points in canonical page text, with an inclusive
start and exclusive end. Bounding boxes use PDF points with a top-left origin.
Decimal quantities and monetary values cross the API boundary as strings. Empty
or invalid evidence produces abstention, not a fabricated source or guessed value.

The authenticated `/api/openapi.json` endpoint describes the actual action API,
including optimistic revisions and typed correction requests. The export records
the selected model, original proposal, explicit human changes, deterministic checks
and acceptance/publication actors. Human decisions do not turn model confidence
into evidence. Schema changes require an explicit version/migration assessment.
