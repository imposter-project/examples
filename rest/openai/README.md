# REST example: OpenAI-compatible API mock

A drop-in mock of the [OpenAI API](https://platform.openai.com/docs/api-reference)
— enough of the common endpoints for any "OpenAI compatible" AI harness to run
against it: model listing, chat completions (plain, streaming and tool calling),
legacy completions and embeddings.

Point your client's base URL at `http://localhost:8080/v1`, use any API key, and
the mock stands in for the real API. It's a plain `rest` plugin mock — every
response lives in an externalised file under [`responses/`](responses), and the
chat endpoint routes to a different file based on the request body.

## Endpoints

| Method & path | Returns |
| --- | --- |
| `GET /v1/models` | The list of available models |
| `GET /v1/models/{model}` | A single model record (echoes the id) |
| `POST /v1/chat/completions` | A chat completion — see the routing below |
| `POST /v1/completions` | A legacy text completion |
| `POST /v1/embeddings` | An embedding vector |

### Chat completion routing

The one `POST /v1/chat/completions` endpoint serves three response files,
selected by matching on the request body. The conditions are **mutually
exclusive** and checked in this order:

| When the request… | …the mock replies with | File |
| --- | --- | --- |
| sets `"stream": true` | Server-Sent Events (`text/event-stream`), one `chat.completion.chunk` per `data:` line, ending with `[DONE]` | [`chat-completion-stream.txt`](responses/chat-completion-stream.txt) |
| is **not** streaming and mentions `weather` anywhere in the body | an assistant **tool call** to `get_weather` (`finish_reason: tool_calls`) | [`chat-completion-tool-call.json`](responses/chat-completion-tool-call.json) |
| anything else | a plain assistant message (`finish_reason: stop`) | [`chat-completion.json`](responses/chat-completion.json) |

Streaming takes precedence: a request that both streams and mentions the weather
gets the stream. The requested `model` is captured from the request and
templated back into every response, so the client sees the model it asked for.

> [!NOTE]
> The mock ignores the `Authorization` header, so any API key works. The tool
> call trigger is a plain substring match for `weather` on the whole request
> body — so a request whose *tool definitions* mention the weather triggers it
> too, not only the user's message. The trigger and the fixed reply text are
> deliberately simple — the point is coherent, correctly-shaped responses, not a
> real model. Edit the files in [`responses/`](responses) to reshape any reply.

> [!IMPORTANT]
> When several resources share a path (as the three chat resources do), keep
> their conditions mutually exclusive. If two can match the same request,
> Imposter logs *"more than one resource matched"* and picks one arbitrarily.
> That's why the tool and plain resources also test `$.stream != "true"` — many
> clients stream by default, so without it a streamed weather request would
> match both the streaming and tool resources. Note `value: "true"` is quoted:
> unquoted, YAML reads it as a boolean and the body matcher never equals it.

## Run

```bash
imposter up
```

> [!TIP]
> Imposter not installed?
> ```sh
> brew install imposter-project/imposter/imposter
> ```

## Try it

### With curl

```bash
# List models
curl http://localhost:8080/v1/models

# Plain chat completion
curl http://localhost:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"Say hello"}]}'

# Tool calling (mention the weather)
curl http://localhost:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"gpt-4o","messages":[{"role":"user","content":"What is the weather in London?"}],
       "tools":[{"type":"function","function":{"name":"get_weather"}}]}'

# Streaming (Server-Sent Events)
curl -N http://localhost:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"gpt-4o","stream":true,"messages":[{"role":"user","content":"hi"}]}'

# Embeddings
curl http://localhost:8080/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"model":"text-embedding-3-small","input":"hello world"}'
```

### With the OpenAI SDK

Any OpenAI client works — just override the base URL. For example, in Python:

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8080/v1", api_key="sk-anything")
print(client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Say hello"}],
).choices[0].message.content)
```

### Verify it end to end

The [`harness/`](harness) directory has a small script that drives the mock with
the **real `openai` SDK** and checks every endpoint — handy as a smoke test or in
CI. See [`harness/README.md`](harness/README.md).

## A note on streaming

Streaming replies are complete, correctly-framed SSE: the OpenAI SDKs parse them
and reassemble the message exactly as they would from the real API (the harness
proves this). The whole event stream is sent at once rather than dribbled out
token-by-token over time — fine for wiring up and testing a client, but not a
substitute for real time-to-first-token behaviour.
