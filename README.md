# LLMBenchmark.ai MCP server

Ask "which model should I use for this task?" and get an answer from benchmark scores and API prices of 400+ LLMs, updated daily.

- Free. No API key. 500 requests per IP per UTC day.
- Remote server, Streamable HTTP: `https://api.llmbenchmark.ai/mcp`
- Deterministic: no LLM call inside, the same task and the same data return the same answer.
- Every answer carries the data date, the source ("LLMBenchmark.ai") and links to the pages behind the numbers.

Docs: https://llmbenchmark.ai/api

## Install

**Claude Code**

```bash
claude mcp add --transport http llmbenchmark https://api.llmbenchmark.ai/mcp
```

**Cursor** (`.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "llmbenchmark": { "url": "https://api.llmbenchmark.ai/mcp" }
  }
}
```

**Codex** (`~/.codex/config.toml`)

```toml
[mcp_servers.llmbenchmark]
url = "https://api.llmbenchmark.ai/mcp"
```

**Claude Desktop** (`claude_desktop_config.json`, through the `mcp-remote` bridge)

```json
{
  "mcpServers": {
    "llmbenchmark": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://api.llmbenchmark.ai/mcp"]
    }
  }
}
```

**Install as a local server (stdio)**

The package proxies to the hosted server, so clients that only start local commands can use it too. Needs [uv](https://docs.astral.sh/uv/).

```bash
uvx llmbenchmark-mcp
```

Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "llmbenchmark": {
      "command": "uvx",
      "args": ["llmbenchmark-mcp"]
    }
  }
}
```

Docker, built from this repository:

```bash
docker build -t llmbenchmark-mcp . && docker run -i --rm llmbenchmark-mcp
```

Set `LLMBENCHMARK_MCP_URL` to point the proxy at another endpoint.

## Tools

| Tool | What it does |
|---|---|
| `recommend_model` | Task text plus optional limits (`max_output_price_per_m`, `min_context_tokens`, `open_weights_only`, `top_k`) in, ranked models with scores, prices and a one-line reason out. |
| `get_leaderboard` | Top models on one board: overall, coding, agentic, reasoning, math, knowledge, design. |
| `compare_models` | Two models side by side on every board where both were measured. |
| `get_model` | One model: maker, prices, context, open weights, score and rank per board. |
| `get_prices` | API list prices per million tokens, cheapest first, by model or maker. |
| `list_categories` | The categories, the board behind each and the task keywords that select it. |

`recommend_model` maps the task to a category with a fixed keyword map (printed at https://llmbenchmark.ai/api#how-recommend-works), drops models that break your limits and ranks the rest on that category's board. If nothing fits your limits it says so and returns the nearest options.

## Example prompts

- "Which model should I use to refactor a React app under $5 per million output tokens?"
- "What is the best open-weight model for math with at least a 128k context window?"
- "Compare Claude Opus and GPT-6 Astra for coding."
- "Which models are cheapest on output price from DeepSeek?"

## CLI

```bash
llmbenchmark-mcp recommend "refactor a React app" --max-price 5 --open-weights
llmbenchmark-mcp tools
llmbenchmark-mcp config
```

`recommend` prints the `recommend_model` answer, `tools` lists the tool names, `config` prints the remote JSON config for Claude or Cursor. With no arguments the command runs the stdio server.

## REST

The same answers over plain HTTP:

```bash
curl "https://api.llmbenchmark.ai/v1/recommend?task=refactor+a+large+React+codebase&max_output_price_per_m=5"
```

## License

- This README and the configuration files in this repository: MIT, see `LICENSE`.
- The data the server returns: CC BY 4.0. Credit "LLMBenchmark.ai" with a link to https://llmbenchmark.ai. Each score names its source board and the day it was read; the boards keep their own terms.

Run by [Take Group](https://takegroup.pl).

<!-- mcp-name: ai.llmbenchmark/llmbenchmark -->
