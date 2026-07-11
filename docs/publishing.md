# Publishing DocLogs to PyPI

Use GitHub Actions so uploads happen from GitHub (avoids corporate SSL issues on local machines).

**Latest release:** `0.1.9` — https://pypi.org/project/doclogs-cli/0.1.9/

## One-time PyPI setup (trusted publishing)

Trusted publishing uses OIDC — no API token stored in GitHub.

1. Create a PyPI account: https://pypi.org/account/register/
2. Open **Account settings → Publishing** (or project settings after first release)
3. Add a **pending publisher** (before first upload) or **trusted publisher** (after project exists):

| Field | Value |
|-------|--------|
| PyPI project name | `doclogs-cli` |
| Owner | `MridulTi` |
| Repository | `DocLogs` |
| Workflow name | `publish.yml` |
| Environment name | *(leave blank)* |

Do **not** set a GitHub Environment unless you also configure one on PyPI — a mismatch causes `invalid-publisher`.

## Publish a release

Push a version tag — the workflow runs automatically:

```bash
git tag v0.1.9
git push origin v0.1.9
```

Or run manually: GitHub → **Actions** → **Publish to PyPI** → **Run workflow**.

## Bump version before each release

Edit `version` in `pyproject.toml`, commit, tag, push:

```bash
# pyproject.toml: version = "0.1.9"
git add pyproject.toml
git commit -m "Bump version to 0.1.9"
git tag v0.1.9
git push origin main --tags
```

## Verify

```bash
pip install -U doclogs-cli==0.1.9
doclog --help
```

https://pypi.org/project/doclogs-cli/

## Fallback: API token (if trusted publishing fails)

1. Create API token at https://pypi.org/manage/account/token/
2. GitHub repo **Settings → Secrets → Actions** → add `PYPI_API_TOKEN`
3. Replace the publish step in `.github/workflows/publish.yml` with:

```yaml
      - name: Publish to PyPI (API token)
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

## Local upload (optional)

Requires `pip-system-certs` on corporate Macs:

```bash
pip install pip-system-certs build twine
python -m build
TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-... twine upload dist/*
```
