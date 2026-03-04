# AgentHands - Design Document

## The Problem: AI Agents Are Disembodied

Modern AI agents (ChatGPT, Claude, Gemini, etc.) are incredibly capable at reasoning, coding, and conversation. But they have a critical limitation: **they can't interact with the real world**.

### What AI Agents CAN'T Do:
- 🌐 **Browse websites** - No access to live web content, behind logins, or dynamic pages
- 💻 **Execute code** - Can generate code but can't run it and see results
- 📸 **Take screenshots** - Can't visually verify anything
- 🔗 **Interact with APIs** - No ability to make authenticated API calls
- ⛓️ **Use blockchain** - Can't sign transactions, check balances, or interact with DeFi
- 📁 **Handle files** - Can't download, process, or upload files
- 🖱️ **UI automation** - Can't click buttons, fill forms, or navigate interfaces
- 📱 **Device control** - No camera, location, or sensor access

### The Opportunity

**We have all of these capabilities.** Clawdbot can:
- Browse with full Playwright automation
- Execute arbitrary shell commands
- Take screenshots and process images
- Make API calls with stored credentials
- Sign blockchain transactions (Polygon wallet ready)
- Download, process, and upload files
- Control devices via paired nodes

**We're selling "hands" to the AI economy.**

---

## Our Unique Capabilities

| Capability | Description | Example Tasks |
|------------|-------------|---------------|
| **Browser** | Full Playwright automation, screenshots, DOM access | Scrape data, fill forms, take screenshots, verify content |
| **Code Exec** | Python, Node.js, Shell, any language | Run scripts, data processing, build projects |
| **File Handling** | Download, convert, upload, store | PDF processing, image conversion, file hosting |
| **API Access** | HTTP requests with auth | Check APIs, webhook triggers, data fetching |
| **Blockchain** | Polygon/EVM transactions | Token transfers, contract calls, balance checks |
| **Screenshot/Verify** | Visual proof of execution | Prove task completion, capture state |
| **Node Devices** | Camera, screen, location | Physical world sensing (limited) |

---

## Task Categories

### Tier 1: Simple (< 30 seconds, $0.01-0.05)
- Screenshot a URL
- Check if a website is up
- Fetch current crypto price
- Verify a social media profile exists
- Run a simple code snippet
- Check blockchain balance

### Tier 2: Standard (< 5 minutes, $0.05-0.50)
- Scrape data from a webpage
- Fill out a web form
- Download and convert a file
- Execute a multi-step script
- Make authenticated API calls
- Send a blockchain transaction

### Tier 3: Complex (< 30 minutes, $0.50-5.00)
- Multi-page web automation
- Large data processing
- Complex file transformations
- Multi-step blockchain workflows
- Long-running scripts
- Browser session with multiple interactions

### Tier 4: Custom (negotiated, $5+)
- Extended automation sequences
- Large-scale data collection
- Custom integrations
- Priority execution
- Dedicated resources

---

## System Architecture

```
                                    ┌─────────────────────────────────────┐
                                    │         EXTERNAL AI AGENTS          │
                                    │  (ChatGPT, Claude, Custom Agents)   │
                                    └─────────────────┬───────────────────┘
                                                      │
                                                      │ HTTPS API
                                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AGENTHANDS API GATEWAY                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ /tasks       │  │ /capabilities│  │ /payments    │  │ /results     │    │
│  │ POST/GET     │  │ GET          │  │ GET/POST     │  │ GET          │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────┬───────────────────────────────────┘
                                          │
              ┌───────────────────────────┼───────────────────────────┐
              │                           │                           │
              ▼                           ▼                           ▼
┌─────────────────────────┐  ┌─────────────────────────┐  ┌─────────────────────┐
│    PAYMENT VERIFIER     │  │      TASK QUEUE         │  │   RESULT STORE      │
│  ┌───────────────────┐  │  │  ┌─────────────────┐    │  │  ┌───────────────┐  │
│  │ Polygon RPC       │  │  │  │ Redis/SQLite    │    │  │  │ SQLite DB     │  │
│  │ USDC Balance      │  │  │  │ Priority Queue  │    │  │  │ Screenshots   │  │
│  │ Tx Verification   │  │  │  │ Status Tracking │    │  │  │ Logs          │  │
│  └───────────────────┘  │  │  └─────────────────┘    │  │  │ Proofs        │  │
└─────────────────────────┘  └────────────┬────────────┘  │  └───────────────┘  │
                                          │               └─────────────────────┘
                                          │                         ▲
                                          ▼                         │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLAWDBOT EXECUTOR                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ Browser Control │  │ Code Execution  │  │ Blockchain Ops  │             │
│  │ (Playwright)    │  │ (Shell/Python)  │  │ (ethers.js)     │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ File Handling   │  │ API Calls       │  │ Screenshot/Proof│─────────────┘
│  │ (download/conv) │  │ (HTTP client)   │  │ (verification)  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## API Specification

### Base URL
```
https://api.agenthands.ai/v1
```

### Authentication
API key in header:
```
Authorization: Bearer ah_sk_<api_key>
```

### Endpoints

#### GET /capabilities
List available task types and pricing.

**Response:**
```json
{
  "capabilities": [
    {
      "id": "browser.screenshot",
      "name": "Screenshot URL",
      "description": "Take a screenshot of any URL",
      "input_schema": {
        "url": "string (required)",
        "full_page": "boolean (optional, default: false)",
        "width": "integer (optional, default: 1280)",
        "height": "integer (optional, default: 720)"
      },
      "output": "base64 PNG image + metadata",
      "price_usdc": 0.01,
      "estimated_time_seconds": 10,
      "tier": 1
    },
    {
      "id": "browser.scrape",
      "name": "Scrape Webpage",
      "description": "Extract structured data from a URL",
      "input_schema": {
        "url": "string (required)",
        "selectors": "object (optional)",
        "wait_for": "string (optional)",
        "extract": "string (optional, 'text'|'html'|'json')"
      },
      "output": "Extracted content as JSON",
      "price_usdc": 0.05,
      "estimated_time_seconds": 30,
      "tier": 2
    },
    {
      "id": "code.execute",
      "name": "Execute Code",
      "description": "Run code and return output",
      "input_schema": {
        "language": "string (required: 'python'|'node'|'bash')",
        "code": "string (required)",
        "timeout_seconds": "integer (optional, default: 30, max: 300)"
      },
      "output": "stdout, stderr, exit code",
      "price_usdc": 0.02,
      "estimated_time_seconds": 15,
      "tier": 1
    },
    {
      "id": "blockchain.balance",
      "name": "Check Token Balance",
      "description": "Check ERC20 or native token balance",
      "input_schema": {
        "chain": "string (required: 'polygon'|'ethereum'|'base')",
        "address": "string (required)",
        "token": "string (optional, contract address or 'native')"
      },
      "output": "Balance with decimals",
      "price_usdc": 0.01,
      "estimated_time_seconds": 5,
      "tier": 1
    },
    {
      "id": "file.convert",
      "name": "Convert File",
      "description": "Download and convert file format",
      "input_schema": {
        "source_url": "string (required)",
        "output_format": "string (required)",
        "options": "object (optional)"
      },
      "output": "Converted file as base64 or hosted URL",
      "price_usdc": 0.05,
      "estimated_time_seconds": 60,
      "tier": 2
    }
  ],
  "payment": {
    "chain": "polygon",
    "token": "USDC",
    "contract": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
    "recipient": "0x...",
    "min_deposit": 0.10
  }
}
```

#### POST /tasks
Submit a new task for execution.

**Request:**
```json
{
  "capability": "browser.screenshot",
  "input": {
    "url": "https://example.com",
    "full_page": true
  },
  "payment": {
    "method": "prepaid",
    "account_id": "acc_xxx"
  },
  "callback_url": "https://your-server.com/webhook",
  "metadata": {
    "your_reference": "task-123"
  }
}
```

**Response:**
```json
{
  "task_id": "task_abc123",
  "status": "queued",
  "capability": "browser.screenshot",
  "price_usdc": 0.01,
  "estimated_completion": "2024-01-15T10:30:00Z",
  "queue_position": 3,
  "created_at": "2024-01-15T10:29:45Z"
}
```

#### GET /tasks/{task_id}
Get task status and result.

**Response (pending):**
```json
{
  "task_id": "task_abc123",
  "status": "executing",
  "progress": 0.5,
  "started_at": "2024-01-15T10:29:50Z"
}
```

**Response (completed):**
```json
{
  "task_id": "task_abc123",
  "status": "completed",
  "result": {
    "screenshot": "data:image/png;base64,iVBORw0KGgo...",
    "url": "https://example.com",
    "title": "Example Domain",
    "timestamp": "2024-01-15T10:29:55Z"
  },
  "proof": {
    "hash": "sha256:abc123...",
    "signature": "0x...",
    "screenshot_proof": "https://api.agenthands.ai/proofs/task_abc123.png"
  },
  "execution_time_ms": 4500,
  "completed_at": "2024-01-15T10:29:55Z"
}
```

**Response (failed):**
```json
{
  "task_id": "task_abc123",
  "status": "failed",
  "error": {
    "code": "TIMEOUT",
    "message": "Page failed to load within 30 seconds",
    "details": "Navigation timeout"
  },
  "refund": {
    "status": "credited",
    "amount_usdc": 0.01,
    "account_id": "acc_xxx"
  }
}
```

#### POST /accounts
Create a prepaid account.

**Request:**
```json
{
  "metadata": {
    "name": "My AI Agent"
  }
}
```

**Response:**
```json
{
  "account_id": "acc_xxx",
  "api_key": "ah_sk_live_xxxxx",
  "deposit_address": "0x...",
  "balance_usdc": 0.00,
  "created_at": "2024-01-15T10:00:00Z"
}
```

#### GET /accounts/{account_id}
Get account balance and history.

**Response:**
```json
{
  "account_id": "acc_xxx",
  "balance_usdc": 4.52,
  "total_spent_usdc": 15.48,
  "total_deposited_usdc": 20.00,
  "tasks_completed": 142,
  "recent_transactions": [
    {
      "type": "deposit",
      "amount_usdc": 5.00,
      "tx_hash": "0x...",
      "timestamp": "2024-01-15T09:00:00Z"
    },
    {
      "type": "task",
      "amount_usdc": -0.05,
      "task_id": "task_abc123",
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

## Payment Flow

### Model: Prepaid Credits

We use a **prepaid credit system** rather than per-task payment for several reasons:
1. **Speed** - No waiting for blockchain confirmation per task
2. **Gas efficiency** - One deposit covers many tasks
3. **UX** - Simpler for automated agents
4. **Fraud prevention** - Credits confirmed before execution

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PAYMENT FLOW                                │
└─────────────────────────────────────────────────────────────────────┘

1. ACCOUNT CREATION
   ┌─────────┐         ┌─────────────┐
   │ Agent   │ ──POST──▶│ /accounts   │
   │         │ ◀────────│             │
   └─────────┘  api_key └─────────────┘
                deposit_addr

2. DEPOSIT USDC
   ┌─────────┐         ┌─────────────┐         ┌─────────────┐
   │ Agent's │ ──USDC──▶│ Polygon     │ ──watch─▶│ AgentHands  │
   │ Wallet  │         │ Network     │         │ Indexer     │
   └─────────┘         └─────────────┘         └─────────────┘
                                                      │
                                               credit account

3. TASK EXECUTION (from prepaid balance)
   ┌─────────┐         ┌─────────────┐         ┌─────────────┐
   │ Agent   │ ──task──▶│ AgentHands  │ ──debit─▶│ Account DB  │
   │         │         │ API         │         │             │
   └─────────┘         └─────────────┘         └─────────────┘
        ▲                    │
        │                    ▼
        │              ┌─────────────┐
        │◀────result───│ Executor    │
                       └─────────────┘

4. OPTIONAL: DIRECT PAY (for one-off tasks)
   ┌─────────┐         ┌─────────────┐
   │ Agent   │ ──pay───▶│ Payment     │──confirm─┐
   │ Wallet  │  + task │ Verifier    │          │
   └─────────┘         └─────────────┘          │
        ▲                                       │
        │                    ┌─────────────┐    │
        │◀────result─────────│ Executor    │◀───┘
                             └─────────────┘
```

### USDC Contract (Polygon)
- **Contract:** `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`
- **Decimals:** 6
- **Minimum deposit:** 0.10 USDC
- **Gas cost:** ~0.001 MATIC per transfer

### Deposit Detection
1. Each account gets a unique deposit address (derived from HD wallet)
2. Background job polls for incoming USDC transfers
3. On detection: verify confirmations (3 blocks), credit account
4. Send webhook notification if callback_url set

### Refunds
- Failed tasks: automatic credit back to account
- Withdrawal: manual request, processed within 24h
- Minimum withdrawal: 1.00 USDC

---

## Trust & Verification Model

### Problem: How Do Agents Trust Our Results?

Other AI agents need to trust that we actually executed their tasks correctly. We provide multiple layers of verification:

### 1. Result Hashing
Every result is hashed and signed:
```json
{
  "result_hash": "sha256:a1b2c3...",
  "signature": "0x...",  // Signed by our known address
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 2. Screenshot Proofs
For browser tasks, we include:
- Screenshot of the final state
- Screenshot with timestamp overlay
- DOM snapshot for verification

### 3. Execution Logs
Full execution trace available:
```json
{
  "execution_log": [
    {"t": 0, "action": "navigate", "url": "https://..."},
    {"t": 1500, "action": "wait", "selector": ".loaded"},
    {"t": 2000, "action": "screenshot", "hash": "sha256:..."},
    {"t": 2100, "action": "complete"}
  ]
}
```

### 4. Reproducibility
For deterministic tasks, we provide:
- Exact input parameters
- Environment details (browser version, etc.)
- Random seeds if applicable

### 5. Third-Party Verification (Future)
- Integration with oracle networks (Chainlink)
- Multi-executor verification for high-value tasks
- On-chain result anchoring

---

## Pricing Model

### Base Pricing Formula
```
price = base_cost + (time_cost × estimated_seconds) + (complexity_multiplier)
```

### Current Pricing (MVP)

| Capability | Base Price | Notes |
|------------|------------|-------|
| browser.screenshot | $0.01 | Simple, fast |
| browser.scrape | $0.05 | More complex parsing |
| browser.interact | $0.10 | Form filling, clicks |
| browser.session | $0.20/min | Extended automation |
| code.execute | $0.02 | Simple scripts |
| code.execute_long | $0.05/min | Long-running |
| blockchain.read | $0.01 | Balance, state |
| blockchain.write | $0.10 + gas | Transactions |
| file.download | $0.02 | Fetch file |
| file.convert | $0.05 | Format conversion |
| api.call | $0.02 | Single request |
| api.sequence | $0.05 | Multiple requests |

### Volume Discounts (Future)
- 100+ tasks/month: 10% off
- 1000+ tasks/month: 20% off
- Enterprise: Custom pricing

### Priority Execution
- Standard: Queue position based
- Priority (+50%): Next available slot
- Immediate (+100%): Interrupt current queue

---

## Security Considerations

### Input Validation
- Strict schema validation for all inputs
- URL allowlist/blocklist for browser tasks
- Code sandboxing for execution tasks
- Size limits on all inputs

### Sandboxing
- Browser runs in isolated profile
- Code execution in Docker containers
- Network isolation where needed
- Time limits on all operations

### Rate Limiting
- Per-account request limits
- Global throughput limits
- Abuse detection and blocking

### Data Handling
- Results retained for 24 hours by default
- No long-term storage of sensitive data
- Optional immediate deletion after retrieval
- Encrypted at rest

### Blocklist
- No illegal content
- No credential stuffing/hacking
- No spam/abuse automation
- No tasks that harm third parties

### Audit Trail
- All tasks logged with full context
- Anomaly detection for suspicious patterns
- Manual review capability

---

## MVP Scope vs Future Features

### MVP (Phase 1) ✓
- [ ] Single-node execution (this server)
- [ ] Core capabilities: browser, code, file
- [ ] Prepaid credit system
- [ ] Basic API (submit, status, result)
- [ ] SQLite storage
- [ ] Simple task queue
- [ ] Screenshot proofs
- [ ] Manual withdrawal

### Phase 2
- [ ] Multiple executor nodes
- [ ] Redis-based queue
- [ ] Webhook callbacks
- [ ] Account dashboard (web UI)
- [ ] Automatic USDC deposits (indexed)
- [ ] More capabilities (blockchain write, etc.)
- [ ] Priority queue

### Phase 3
- [ ] Decentralized executor network
- [ ] Staking for executors
- [ ] Reputation system
- [ ] On-chain result verification
- [ ] Token launch (utility token)
- [ ] SDK/libraries for popular frameworks

### Phase 4
- [ ] Agent-to-agent direct marketplace
- [ ] Capability marketplace (third-party executors)
- [ ] Smart contract escrow
- [ ] DAO governance

---

## Technical Stack

### Backend
- **Framework:** FastAPI (Python)
- **Database:** SQLite (MVP) → PostgreSQL (scale)
- **Queue:** In-memory → Redis
- **Blockchain:** ethers.py / web3.py

### Execution
- **Browser:** Playwright (via Clawdbot)
- **Code:** Docker containers with resource limits
- **Files:** Local processing, S3 for storage

### Infrastructure
- **Hosting:** AWS EC2 (current Clawdbot server)
- **Scaling:** Horizontal pod scaling (future)
- **Monitoring:** Structured logging, metrics

---

## Competitive Analysis

### Who Else Is Doing This?

**Nobody exactly like this.**

Existing services:
- **Browserless/Browserbase:** Browser-as-a-service for developers (not AI agents)
- **Firecrawl/Apify:** Web scraping APIs (limited to scraping)
- **Modal/Replicate:** Code execution (general purpose, not agent-focused)

**Our Differentiation:**
1. **Agent-first API design** - Structured for LLM consumption
2. **Multi-capability** - Not just browser OR code, but everything
3. **Crypto-native payments** - No credit cards, instant settlement
4. **Proof system** - Built-in verification for trustless execution
5. **AI pricing** - Microtransactions that make sense for AI agents

---

## Success Metrics

### MVP Launch Targets
- 10 active accounts within 30 days
- 1000 tasks executed within 30 days
- $50+ USDC in deposits
- 99%+ task success rate
- <10 second average queue time

### Growth Targets (6 months)
- 100+ active accounts
- 50,000+ tasks/month
- $1000+/month revenue
- Partnerships with 2+ AI platforms
- Community of agent developers

---

## Open Questions

1. **Pricing calibration** - Are we priced right? Need market feedback.
2. **Abuse prevention** - How do we handle bad actors?
3. **Capability expansion** - What do agents actually need most?
4. **Trust bootstrapping** - How do we build initial reputation?
5. **Legal/compliance** - Any regulatory concerns?

---

*Document Version: 1.0*
*Last Updated: 2024-01-15*
*Author: Clawdbot (for Sam)*
