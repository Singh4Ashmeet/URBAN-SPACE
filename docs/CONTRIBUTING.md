# Contributing

## Local Workflow

```powershell
python start.py --build
python start.py --health-report
python start.py --test
```

## Guardrails

- Preserve the no-Docker local workflow.
- Do not remove existing working URLs without a migration path.
- Keep Docker optional.
- Do not introduce paid services or API-key-only dependencies.
- Add tests for behavior changes.

## Validation

Run:

```powershell
python start.py --test
```

Then restart:

```powershell
python start.py --build
```
