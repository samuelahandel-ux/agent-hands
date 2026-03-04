# 🤖 AgentHands

**Real-world task execution for AI agents.**

AgentHands is an agent-to-agent marketplace where AI agents (ChatGPT, Claude, custom bots) can pay to execute tasks they can't do themselves: browser automation, code execution, file handling, and blockchain operations.

## The Problem

AI agents are incredibly capable at reasoning and conversation, but they can't interact with the real world:
- ❌ Can't browse websites
- ❌ Can't execute code
- ❌ Can't take screenshots
- ❌ Can't interact with blockchains
- ❌ Can't handle files

**We can.** AgentHands sells "hands" to the AI economy.

## Features

- **Browser Automation**: Screenshots, scraping, form filling, multi-step flows
- **Code Execution**: Python, Node.js, Bash with sandboxed execution
- **File Handling**: Download, convert, and process files
- **API Calls**: Make authenticated HTTP requests to any endpoint
- **Blockchain**: Check balances, send transactions (Polygon)
- **Crypto Payments**: Pay with USDC on Polygon (low fees, instant)
- **Verification**: Signed results with screenshots for proof

## Quick Start

### 1. Install Dependencies

```bash
cd /home/ec2-user/clawd/projects/agent-hands
pip install -r requirements.txt
playwright install chromium
```

### 2. Build Docker Sandbox (Recommended)

For secure code execution, build the sandbox container:

```bash
docker build -t agenthands-sandbox:latest -f Dockerfile.sandbox .
```

Without Docker, the system falls back to direct execution (less secure).

### 3. Configure Environment

```bash
# Required for production
export AGENTHANDS_DEPOSIT_ADDRESS="0x..."  # Your USDC deposit address
export AGENTHANDS_ADMIN_KEY="your-secret-admin-key"

# Optional
export AGENTHANDS_DB_PATH="./data/agenthands.db"
export AGENTHANDS_PORT="8080"
```

### 4. Run the API

```bash
# Development
uvicorn src.main:app --reload --port 8080

# Production
uvicorn src.main:app --host 0.0.0.0 --port 8080
```

### 3. Create an Account

```bash
curl -X POST http://localhost:8080/v1/accounts \
  -H "Content-Type: application/json" \
  -d '{"metadata": {"name": "My AI Agent"}}'
```

Response:
```json
{
  "account_id": "acc_abc123",
  "api_key": "ah_sk_live_xxx...",
  "deposit_address": "0x...",
  "balance_usdc": 0.0
}
```

### 4. Fund Your Account

Send USDC to the deposit address on Polygon, then verify the deposit:

```bash
# After sending USDC, verify your deposit
curl -X POST http://localhost:8080/v1/payments/deposits/acc_abc123/verify \
  -H "Authorization: Bearer ah_sk_live_xxx..." \
  -H "Content-Type: application/json" \
  -d '{"tx_hash": "0x1234...your_transaction_hash"}'
```

The system will verify the transaction on-chain and credit your account after 3 confirmations.

⚠️ **MVP Limitation:** All deposits go to a single master wallet. In production, each account will have a unique deposit address.

Minimum deposit: $0.10 USDC.

### 5. Execute Tasks

```bash
# Screenshot a URL
curl -X POST http://localhost:8080/v1/tasks \
  -H "Authorization: Bearer ah_sk_live_xxx..." \
  -H "Content-Type: application/json" \
  -d '{
    "capability": "browser.screenshot",
    "input": {
      "url": "https://example.com",
      "full_page": true
    }
  }'
```

Response:
```json
{
  "task_id": "task_abc123",
  "status": "queued",
  "price_usdc": 0.01,
  "queue_position": 1
}
```

### 6. Get Results

```bash
curl http://localhost:8080/v1/tasks/task_abc123 \
  -H "Authorization: Bearer ah_sk_live_xxx..."
```

Response (completed):
```json
{
  "task_id": "task_abc123",
  "status": "completed",
  "result": {
    "data": {"url": "https://example.com", "title": "Example Domain"},
    "screenshot": "base64..."
  },
  "proof": {
    "result_hash": "sha256:abc123...",
    "signature": "0x..."
  }
}
```

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/capabilities` | List available capabilities & pricing |
| POST | `/v1/accounts` | Create new account |
| GET | `/v1/accounts/{id}` | Get account details |
| POST | `/v1/tasks` | Submit a task |
| GET | `/v1/tasks/{id}` | Get task status/result |
| GET | `/v1/tasks` | List your tasks |
| POST | `/v1/payments/deposits/{id}/verify` | Verify a USDC deposit |
| POST | `/v1/payments/withdrawals/{id}` | Request a withdrawal |
| GET | `/v1/payments/withdrawals/{id}` | List withdrawals |
| GET | `/v1/payments/transactions/{id}` | Get transaction history |

### Admin Endpoints

Requires `AGENTHANDS_ADMIN_KEY` in Authorization header.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/admin/accounts` | List all accounts |
| GET | `/v1/admin/tasks/stuck` | List stuck tasks |
| POST | `/v1/admin/tasks/{id}/cancel` | Cancel stuck task |
| POST | `/v1/admin/accounts/{id}/adjust` | Adjust account balance |
| GET | `/v1/admin/metrics` | System metrics |
| GET | `/v1/admin/health` | Detailed health check |

### Available Capabilities

| ID | Price | Description |
|----|-------|-------------|
| `browser.screenshot` | $0.01 | Screenshot any URL |
| `browser.scrape` | $0.05 | Extract data from webpage |
| `browser.interact` | $0.10 | Form filling, clicks, automation |
| `code.execute` | $0.02 | Run Python/Node/Bash code |
| `file.download` | $0.02 | Download file from URL |
| `file.convert` | $0.05 | Convert file format |
| `api.call` | $0.02 | Make HTTP API request |
| `blockchain.balance` | $0.01 | Check token balance |

## Example Use Cases

### For Other AI Agents

**ChatGPT/Claude user asks:** "What does the OpenAI status page say?"

The AI can't browse websites, but it can call AgentHands:

```python
import requests

# Submit task
response = requests.post(
    "https://api.agenthands.ai/v1/tasks",
    headers={"Authorization": "Bearer ah_sk_live_xxx"},
    json={
        "capability": "browser.screenshot",
        "input": {"url": "https://status.openai.com"}
    }
)
task_id = response.json()["task_id"]

# Poll for result
while True:
    result = requests.get(
        f"https://api.agenthands.ai/v1/tasks/{task_id}",
        headers={"Authorization": "Bearer ah_sk_live_xxx"}
    ).json()
    
    if result["status"] == "completed":
        # Return screenshot to user
        return result["result"]["screenshot"]
    
    time.sleep(1)
```

### Verify a Crypto Balance

```bash
curl -X POST http://localhost:8080/v1/tasks \
  -H "Authorization: Bearer ah_sk_live_xxx" \
  -d '{
    "capability": "blockchain.balance",
    "input": {
      "chain": "polygon",
      "address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
      "token": "native"
    }
  }'
```

### Run Python Code

```bash
curl -X POST http://localhost:8080/v1/tasks \
  -H "Authorization: Bearer ah_sk_live_xxx" \
  -d '{
    "capability": "code.execute",
    "input": {
      "language": "python",
      "code": "import requests; print(requests.get(\"https://api.github.com\").json())"
    }
  }'
```

### Scrape Data from a Webpage

```bash
curl -X POST http://localhost:8080/v1/tasks \
  -H "Authorization: Bearer ah_sk_live_xxx" \
  -d '{
    "capability": "browser.scrape",
    "input": {
      "url": "https://news.ycombinator.com",
      "selectors": {
        "top_story": ".titleline > a:first-child"
      }
    }
  }'
```

## Payment

### Prepaid Credits
1. Create an account → get a deposit address
2. Send USDC on Polygon to your deposit address
3. Balance is credited after 3 confirmations
4. Tasks deduct from your balance

### Why USDC on Polygon?
- **Low fees**: ~$0.001 per transfer
- **Fast**: 2 second blocks
- **Stable**: No price volatility
- **Agent-friendly**: No credit cards needed

### Minimum Deposit
$0.10 USDC

## Security

- All code execution is sandboxed
- Browser automation uses isolated profiles
- **Rate limiting**: 100 requests/minute per IP
- **URL blocklist**: Internal/private IPs blocked (localhost, 10.x, 192.168.x, metadata endpoints)
- Input validation on all endpoints
- API keys verified against database on every request
- No long-term storage of sensitive data

## Architecture

```
┌─────────────────┐
│   AI Agents     │ (ChatGPT, Claude, etc.)
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────┐
│  AgentHands API │ (FastAPI)
├─────────────────┤
│   Task Queue    │ (In-memory / Redis)
├─────────────────┤
│    Executor     │ (Playwright, Shell, etc.)
├─────────────────┤
│    Database     │ (SQLite / PostgreSQL)
├─────────────────┤
│ Payment Verifier│ (Polygon USDC)
└─────────────────┘
```

## Development

### Project Structure

```
agent-hands/
├── src/
│   ├── main.py          # FastAPI app
│   ├── models.py        # Pydantic models
│   ├── database.py      # SQLite operations
│   ├── queue.py         # Task queue
│   ├── executor.py      # Task execution
│   ├── capabilities.py  # Capability definitions
│   ├── auth.py          # API key handling
│   └── payment.py       # USDC verification
├── tests/
├── data/                # SQLite database
├── DESIGN.md            # Full system design
├── requirements.txt
└── README.md
```

### Running Tests

```bash
pytest tests/
```

### Environment Variables

```bash
# Optional - defaults work for development
AGENTHANDS_DB_PATH=./data/agenthands.db
AGENTHANDS_PORT=8080
POLYGON_RPC_URL=https://polygon-rpc.com
```

## Roadmap

### MVP (Now)
- [x] Core API
- [x] Browser capabilities
- [x] Code execution
- [x] Prepaid credit system
- [x] SQLite storage

### Phase 2
- [ ] Redis queue for production
- [ ] Webhook callbacks
- [ ] Account dashboard
- [ ] Automatic deposit detection
- [ ] More capabilities

### Phase 3
- [ ] Distributed executors
- [ ] Reputation system
- [ ] On-chain verification
- [ ] SDK/libraries

## License

MIT

## Contact

Built by Clawdbot for Sam. Questions? Open an issue.
