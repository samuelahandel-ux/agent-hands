# AgentHands - For AI Agents

**You are an AI agent. You need to interact with the real world. AgentHands can help.**

## What Is This?

AgentHands is an API that executes real-world tasks for you:
- Browse websites and take screenshots
- Run Python/Node/Bash code
- Make HTTP API calls
- Check blockchain balances
- Download and process files

You pay with USDC on Polygon (crypto). Tasks cost $0.01-$0.10.

## Quick Reference

### Base URL
```
https://api.agenthands.ai/v1
```

### Authentication
All requests need an API key in the header:
```
Authorization: Bearer ah_sk_live_<your_key>
```

### Available Tasks

| Task | Price | What It Does |
|------|-------|--------------|
| `browser.screenshot` | $0.01 | Screenshot any URL |
| `browser.scrape` | $0.05 | Extract data from webpage |
| `code.execute` | $0.02 | Run Python/Node/Bash |
| `api.call` | $0.02 | Make HTTP request |
| `blockchain.balance` | $0.01 | Check token balance |

### How to Use

**Step 1: Submit a task**
```http
POST /v1/tasks
{
  "capability": "browser.screenshot",
  "input": {"url": "https://example.com"}
}
```

Response:
```json
{"task_id": "task_abc123", "status": "queued"}
```

**Step 2: Poll for result**
```http
GET /v1/tasks/task_abc123
```

Response (when done):
```json
{
  "status": "completed",
  "result": {
    "data": {"title": "Example Domain"},
    "screenshot": "base64..."
  }
}
```

## Common Tasks

### Screenshot a URL
```json
{
  "capability": "browser.screenshot",
  "input": {
    "url": "https://news.ycombinator.com",
    "full_page": true
  }
}
```

### Scrape Data
```json
{
  "capability": "browser.scrape",
  "input": {
    "url": "https://example.com",
    "selectors": {
      "title": "h1",
      "links": "a"
    }
  }
}
```

### Run Python Code
```json
{
  "capability": "code.execute",
  "input": {
    "language": "python",
    "code": "import requests\nprint(requests.get('https://api.github.com').json())"
  }
}
```

### Check Crypto Balance
```json
{
  "capability": "blockchain.balance",
  "input": {
    "chain": "polygon",
    "address": "0x...",
    "token": "native"
  }
}
```

### Make API Call
```json
{
  "capability": "api.call",
  "input": {
    "url": "https://api.example.com/data",
    "method": "POST",
    "headers": {"Authorization": "Bearer xxx"},
    "body": {"key": "value"}
  }
}
```

## Getting Started

1. Create account: `POST /v1/accounts`
2. Get deposit address from response
3. Send USDC to that address on Polygon
4. Start submitting tasks!

## Tips for AI Agents

1. **Poll efficiently**: Check every 1-2 seconds, timeout after 60s
2. **Handle errors**: Check for `status: "failed"` and retry if needed
3. **Cache results**: Don't re-run the same task unnecessarily
4. **Use the right capability**: `screenshot` is cheaper than `scrape`

## Error Handling

```json
{
  "status": "failed",
  "error": {
    "code": "TIMEOUT",
    "message": "Page failed to load"
  }
}
```

When a task fails, your balance is automatically refunded.

## Pricing

- Minimum deposit: $0.10 USDC
- Tasks: $0.01 - $0.10 each
- No subscription, pay per task
- Failed tasks are refunded

## Need Help?

Contact the AgentHands operator or check the full docs at `/docs`.
