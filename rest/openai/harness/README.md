# Verification harness

A tiny harness that proves the mock is genuinely _OpenAI compatible_ by driving
it with the **official `openai` Python SDK** — the same client a real AI
application would use. If your harness can talk to OpenAI, and this script
passes, the mock will stand in for the real API.

It checks:

- `models.list()`
- `chat.completions.create(...)` — plain assistant reply
- `chat.completions.create(..., tools=[...])` — a tool call (`finish_reason: tool_calls`)
- `chat.completions.create(..., stream=True)` — Server-Sent Events, reassembled
- `completions.create(...)` — legacy text completion
- `embeddings.create(...)`

## Run it

First start the mock from the parent directory:

```bash
cd ..
imposter up
```

Then, in this directory, install the SDK and run the checks:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python verify.py
```

You should see every check marked `PASS`:

```
Verifying OpenAI-compatible mock at http://localhost:8080/v1

models.list
  [PASS] returns a non-empty model list — gpt-4o, gpt-4o-mini, gpt-3.5-turbo, text-embedding-3-small
...
PASS: all checks passed — the mock is OpenAI-compatible
```

The script exits `0` when everything passes and `1` if any check fails, so it
works in CI too.

## Options

Point it at a mock on a different host or port:

```bash
python verify.py --base-url http://localhost:3000/v1
# or
OPENAI_BASE_URL=http://localhost:3000/v1 python verify.py
```

`OPENAI_API_KEY` is read if set, but the mock accepts any key — you don't need a
real one.
