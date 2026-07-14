# WebSocket example: OpenClaw Gateway simulation

Simulates the operator-facing surface of the [OpenClaw Gateway WebSocket protocol](https://docs.openclaw.ai/gateway/protocol) — enough for an operator client (e.g. the lucinate TUI) to connect, browse agents/sessions/tools/tasks, hold a streamed chat, and drive most read and write RPCs against a coherent, self-consistent world.

Frame shapes follow the protocol's canonical schemas (`req`/`res`/`event` envelopes; methods echo the request `id`; `ts`/timestamp fields are numbers — epoch millis — matching the `int64` typing).

## How it's organised

The mock is **split across several `*-config.yaml` files, one per protocol domain**:

| File | Domain |
| --- | --- |
| `imposter-config.yaml` | Connection core: `on: open` challenge + tick, `connect` handshake, unknown-method fallback |
| `sessions-config.yaml` | `sessions.*` |
| `chat-config.yaml` | `chat.*` (incl. the streamed `chat.send`) |
| `agents-config.yaml` | `agents.*`, `agent.*` |
| `models-config.yaml` | `models.*` |
| `cron-config.yaml` | `cron.*` |
| `tools-config.yaml` | `commands.*`, `tools.*`, `skills.*` |
| `channels-config.yaml` | `channels.*` |
| `tasks-config.yaml` | `tasks.*`, `artifacts.*` |
| `system-config.yaml` | `system-info`, `audit.*`, `config.get`, pairing/node/environment/approval lists |

Imposter loads every `*-config.yaml` in the directory. Because they all declare `plugin: websocket` on the same wildcard `path: /*`, the engine **coalesces them into a single handler** — so one multiplexed connection serves every method, whichever file defines it. (This mirrors the real gateway, which multiplexes all methods over one connection and routes the upgrade by the `Upgrade: websocket` header rather than a URL path. Connect on whatever path your client uses, e.g. `/ws`.)

## The mock world

Everything is consistent with a single-agent, single-session gateway:

- **Agent** `main` (the default) — see `agents.list`, `agent.identity.get`.
- **Session** `main`, titled "Main conversation", currently on `claude-opus-4-8`.
- **Models** `claude-opus-4-8`, `claude-sonnet-5`, `claude-haiku-4-5` (the session's model is one of them, so the picker highlights it).
- **One cron job** `cron-daily-digest`, consistent across `cron.list` / `cron.get` / `cron.runs`.
- **One completed task** `task-1` and **one code artifact** `artifact-1`, both in session `main`.
- **One connected Telegram account** for `channels.status`.
- Pairing, node, environment and approval lists are empty (as on a simple local gateway).

Read methods return this snapshot; write/void methods are acknowledged with an `ok:true` response frame. Any method the mock does not implement returns a canonical `method_not_found` error frame.

> [!NOTE]
> A few gateway results are not pinned by the wire schema (e.g. `sessions.list`, `sessions.usage`, `cron.status`). Their payloads here are representative shapes consistent with the reference client, sufficient to render a client UI.

## Run

```bash
imposter up
```

> [!TIP]
> Imposter not installed?
> Install with Homebrew:
> ```sh
> brew install imposter-project/imposter/imposter
> ```

## Try it

### Using websocat

Using [websocat](https://github.com/vi/websocat):

```bash
websocat ws://localhost:8080/ws
```

You'll receive the `connect.challenge` event immediately, and a `tick` keepalive every 15 seconds. Then paste the handshake:

```json
{"type":"req","id":"req-1","method":"connect","params":{"minProtocol":3,"maxProtocol":4,"client":{"id":"cli","version":"0.1.0","platform":"go","mode":"cli"}}}
```

to receive `hello-ok`. Its `features.methods` advertises everything the mock implements.

### Agents

```json
{"type":"req","id":"a-1","method":"agents.list","params":{}}
{"type":"req","id":"a-2","method":"agent.identity.get","params":{"agentId":"main"}}
{"type":"req","id":"a-3","method":"agents.files.list","params":{"agentId":"main"}}
{"type":"req","id":"a-4","method":"agents.workspace.list","params":{"agentId":"main"}}
```

### Sessions

```json
{"type":"req","id":"s-1","method":"sessions.list","params":{"agentId":"main"}}
{"type":"req","id":"s-2","method":"sessions.get","params":{"key":"main"}}
{"type":"req","id":"s-3","method":"sessions.preview","params":{"keys":["main"]}}
{"type":"req","id":"s-4","method":"sessions.create","params":{"agentId":"main","key":"main"}}
{"type":"req","id":"s-5","method":"sessions.patch","params":{"key":"main","model":"claude-sonnet-5"}}
{"type":"req","id":"s-6","method":"sessions.groups.list","params":{}}
```

### Chat

```json
{"type":"req","id":"h-1","method":"chat.history","params":{"sessionKey":"main","limit":50}}
{"type":"req","id":"h-2","method":"chat.message.get","params":{"sessionKey":"main","messageId":"msg-2"}}
{"type":"req","id":"h-3","method":"chat.send","params":{"sessionKey":"main","message":"hello","idempotencyKey":"idem-1"}}
```

`chat.send` returns an acknowledgement (`runId`/`status`), then streams `agent` tool events (`start` then `result`) and `chat` events (a `delta` carrying `deltaText`, then a `final` message with `stopReason`). The `runId` is the request id and the `sessionKey` is echoed, so the client routes the events to the active run.

### Models

```json
{"type":"req","id":"m-1","method":"models.list","params":{}}
{"type":"req","id":"m-2","method":"models.probe","params":{"provider":"anthropic"}}
```

### Cron

```json
{"type":"req","id":"cr-1","method":"cron.list","params":{"enabled":"all"}}
{"type":"req","id":"cr-2","method":"cron.get","params":{"id":"cron-daily-digest"}}
{"type":"req","id":"cr-3","method":"cron.runs","params":{"id":"cron-daily-digest"}}
```

### Commands, tools and skills

```json
{"type":"req","id":"t-1","method":"commands.list","params":{"agentId":"main"}}
{"type":"req","id":"t-2","method":"tools.catalog","params":{"agentId":"main"}}
{"type":"req","id":"t-3","method":"tools.effective","params":{"sessionKey":"main"}}
{"type":"req","id":"t-4","method":"skills.status","params":{"agentId":"main"}}
{"type":"req","id":"t-5","method":"skills.search","params":{"query":"web"}}
```

### Channels

```json
{"type":"req","id":"ch-1","method":"channels.status","params":{}}
```

### Tasks and artifacts

```json
{"type":"req","id":"tk-1","method":"tasks.list","params":{}}
{"type":"req","id":"tk-2","method":"tasks.get","params":{"taskId":"task-1"}}
{"type":"req","id":"ar-1","method":"artifacts.list","params":{"sessionKey":"main"}}
{"type":"req","id":"ar-2","method":"artifacts.download","params":{"artifactId":"artifact-1"}}
```

### System, audit and config

```json
{"type":"req","id":"sy-1","method":"system-info","params":{}}
{"type":"req","id":"sy-2","method":"audit.activity.list","params":{}}
{"type":"req","id":"sy-3","method":"config.get","params":{}}
```

### Unknown methods

Any method not implemented by the mock returns an error frame:

```json
{"type":"req","id":"x-1","method":"does.not.exist","params":{}}
```

```json
{"type":"res","id":"x-1","ok":false,"error":{"code":"method_not_found","message":"This method is not implemented by the mock."}}
```

Leave the connection open to keep observing the periodic `tick` events.

### Using a real OpenClaw client

We can test this interactively using a real OpenClaw client, like [lucinate](https://github.com/lucinate-ai/lucinate).

```sh
brew install lucinate-ai/tap/lucinate
```

Start the client:

```sh
lucinate
```

Add a connection using the following settings:

- Type: OpenClaw
- URL: http://localhost:8080

Once you're connected, you can view the agent list, and start chatting!
