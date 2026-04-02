# simple

## codeowners — Fetch CODEOWNERS for any GitHub repository

`codeowners.py` is a small CLI utility that retrieves and displays the
CODEOWNERS rules for a given GitHub repository using the GitHub API.
It checks the three standard CODEOWNERS locations in order of precedence:

1. `.github/CODEOWNERS`
2. `CODEOWNERS`
3. `docs/CODEOWNERS`

### Requirements

- Python 3.9+
- No third-party packages required (uses `urllib` from the standard library)

### Usage

```bash
# Public repository — no token needed
python codeowners.py <owner/repo>

# Private / internal repository — supply a GitHub token
GITHUB_TOKEN=ghp_... python codeowners.py <owner/repo>

# Also show which owners apply to a specific file
python codeowners.py <owner/repo> --path src/main.py
```

### Examples

```bash
# Fetch CODEOWNERS for a public repo
python codeowners.py torvalds/linux

# Fetch for github/github (requires a token with 'repo' scope)
GITHUB_TOKEN=ghp_... python codeowners.py github/github

# Find the owners of a particular file
GITHUB_TOKEN=ghp_... python codeowners.py github/github --path app/models/user.rb
```

Example output:

```
CODEOWNERS file: .github/CODEOWNERS
────────────────────────────────────────────────────────────
  *                                        @default-owner
  *.js                                     @js-team
  /docs/                                   @docs-team

Owners for 'app/models/user.rb': @default-owner
```

### Required token scopes

| Repository type | Required scope |
|-----------------|----------------|
| Public          | *(none — anonymous API calls work)* |
| Private / internal | Classic token: **`repo`** |
| Private / internal | Fine-grained token: **Contents** (read) |

Create a token at <https://github.com/settings/tokens>, then export it:

```bash
export GITHUB_TOKEN=<your-token>
```

### Error handling

| Situation | Message shown |
|-----------|---------------|
| Repo is private / no token | HTTP 403 with step-by-step token setup instructions |
| Repo does not exist | HTTP 404 — "no CODEOWNERS file found" |
| Network error | Description of the URL error |
| No CODEOWNERS in repo | Lists all checked paths + token hint if no token set |

### Running the tests

```bash
python -m unittest test_codeowners -v
```

The test suite covers:

- Parsing: blank lines, comments, inline comments, email owners, org/team owners, line numbers
- Pattern matching: wildcards, anchored paths, `**` globs, `?` placeholders, trailing-slash directories
- Owner resolution: last-match-wins semantics, unowned paths, no matching rule