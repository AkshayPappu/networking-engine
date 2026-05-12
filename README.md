# networking-engine

Stateless terminal tool: you describe who you want to meet in natural language; it runs **web search** (Tavily or Brave), **fetches public pages**, and uses **OpenAI** to return a **ranked list of people** as **one line each** (short blurb + **evidence URLs**). The ranker still uses `why_relevant`, `outreach_angle`, and quoted evidence internally; grounding drops rows that are not supported by the fetched page text.

This is **not** a complete professional graph. Coverage depends on the search index and which pages are fetched in one run. Accuracy here means **evidence-backed**: unsupported rows are dropped after grounding checks, then **strict filters** remove hedged blurbs (`unclear`, `?`, etc.) and enforce **anchor groups** from the planner. Each anchor group represents one required concept (e.g. "previously at Company X") with several alias variants; a person must have at least one variant from **every** group present in their evidence text. This is fully generic -- no company names are hardcoded in the tool.

## Setup

Requires **Python 3.11+**. On Windows, if `python --version` is older, use the **Python Launcher** (for example `py -3.12`) for the commands below, or create a **virtual environment** so `pip` and `python` refer to the same interpreter.

```bash
cd networking-engine
py -3.12 -m venv .venv
.\.venv\Scripts\activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
copy .env.example .env
```

After install, with the venv activated, the **`scout`** command is on your PATH (for example `.venv\Scripts\scout.exe` on Windows). Try:

```bash
scout query --help
scout version
```

### Permanent setup (no `PYTHONPATH` each time)

The `PYTHONPATH=src` trick only lasts for that shell. To make **`scout query ...` work whenever you open a terminal**:

1. **Use the project venv** (above): `py -3.12 -m venv .venv` then activate then `python -m pip install -e ".[dev]"`. After that, always **`cd` into this repo** and **`.\.venv\Scripts\activate`** (Windows) or `source .venv/bin/activate` (macOS/Linux) before running commands. The package and the **`scout`** executable are installed into that venv's `Scripts/` or `bin/`, so no extra env vars are needed.

2. **If you skip a venv**, run `py -3.12 -m pip install -e ".[dev]"` (or `python -m pip ...` for your chosen interpreter), then run **`scout`** using that interpreter's `Scripts` / `bin` folder on your PATH or call `scout.exe` by full path. Avoid mixing `pip` from one Python install with a different `py -3.x` (common on Windows with multiple installs).

Edit `.env`:

- `OPENAI_API_KEY` -- required.
- `OPENAI_MODEL` -- set in `.env` only (default in `.env.example` is `gpt-4o`).
- `SEARCH_PROVIDER` -- `tavily` or `brave`.
- `TAVILY_API_KEY` or `BRAVE_API_KEY` -- matching your provider.
- Optional: `MAX_URLS` (default 25), `MAX_PEOPLE` (default 12), `HTTP_TIMEOUT_S`, `HTTP_USER_AGENT`.

### Troubleshooting (OpenAI)

If you see **429** / **insufficient_quota**, the key is valid but the **account has no usable credits** or billing is inactive. Fix it in [OpenAI billing](https://platform.openai.com/account/billing) (add a payment method or top up), or use a key from an org/project that has quota. The CLI now prints a short message instead of a full traceback for common OpenAI errors.

## Usage

```bash
scout query "Find Virginia Tech alumni working at OpenAI"
```

Planner preview only (no search, no ranking):

```bash
scout query "Find ML infra engineers at trading firms" --dry-run
```

## How it works

1. **Planner (OpenAI)** turns your question into several web search strings and emits **anchor groups** (required concepts with alias variants).
2. **Search API** returns URLs and snippets.
3. **Fetcher** downloads HTML and extracts readable text with **trafilatura**.
4. **Ranker (OpenAI)** proposes people with `why_relevant`, `outreach_angle`, and `evidence` quotes (using planner **must_have** and **anchor_groups** in the prompt).
5. **Grounding** keeps only rows whose evidence quotes appear in the text for that URL.
6. **Strict filters** drop hedged rows and enforce **anchor groups** -- every group (AND) must have at least one variant (OR) present in the person's evidence text.
7. **Output** prints one concise line per person (short blurb + evidence URLs).

## Quotas and ethics

Use your own API keys and respect provider ToS. Fetch only URLs returned by search; use a normal `User-Agent` and reasonable timeouts. Do not use this tool to bypass paywalls or log into sites as someone else.

## Tests

```bash
pytest
```

Live end-to-end runs need valid keys in `.env` and are not required for CI.
