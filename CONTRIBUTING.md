# Contributing

## Dev Setup

```powershell
pip install -r requirements.txt
python -m unittest discover -s tests -p "test_*.py"
```

## Development Rules

- keep CLI behavior stable while refactoring
- do not commit private data or machine-local runtime state
- prefer small compatibility-preserving changes over broad rewrites
- keep GUI logic thin and push reusable logic into Python services

## Before Opening A PR

1. Run smoke tests
2. Check `git diff --stat`
3. Confirm ignored runtime artifacts stayed untracked
4. Update docs if the user workflow changed

