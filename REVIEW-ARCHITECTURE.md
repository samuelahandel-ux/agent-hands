# AgentHands Architecture Review

**Date:** 2025-01-20  
**Reviewer:** Clawdbot Architecture Review (Subagent)  
**Verdict:** Promising concept, significant gaps before production

---

## Executive Summary

AgentHands is a creative idea — selling "hands" (execution capabilities) to AI agents. The concept is solid and the timing is right. However, the current implementation has critical security vulnerabilities, architectural shortcuts, and missing operational infrastructure that would prevent it from surviving real-world usage.

**Bottom line:** Good for a demo. Not ready for production or accepting real money.

---

## Strengths ✅

### 1. **Clear Problem Statement**
The gap between "what AI can reason about" and "what AI can do" is real. This is a genuine market need.

### 2. **Agent-First API Design**
The API is structured well for LLM consumption:
- Consistent JSON schemas
- Clear capability definitions with examples
- Predictable polling pattern
- Good documentation in `FOR_AI_AGENTS.md`

### 3. **Crypto-Native Payments**
USDC on Polygon is actually a smart choice:
- Low fees (~$0.001 per transfer)
- Fast finality (2 seconds)
- No KYC friction for AI agents
- Stable value (no volatility risk)
- Programmable money for agent ecosystems

### 4. **Solid Foundation Code**
- Clean Python with type hints
- Async throughout (FastAPI + aiosqlite)
- Proper separation of concerns (models, database, queue, executor, auth, payment)
- Pydantic models for validation

### 5. **URL Blocklist Security**
The `is_url_blocked()` function in executor.py properly blocks:
- Localhost and private IPs
- Cloud metadata endpoints (169.254.169.254)
- Internal domains
This prevents basic SSRF attacks.

### 6. **Reasonable Pricing Model**
$0.01-$0.10 per task is appropriate for microtasks. Volume discounts and priority tiers make sense.

---

## Weaknesses ⚠️

### 1. **Code Execution is a Time Bomb** 🔴 CRITICAL

The `_execute_code()` method in executor.py runs arbitrary code with NO sandboxing:

```python
# THIS IS DANGEROUS
process = await asyncio.create_subprocess_exec(
    *cmd,  # ["python3", script_path]
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
)
```

**Problems:**
- Direct file system access
- Network access to internal services
- Can read environment variables, secrets
- Can consume all CPU/memory
- Can install malware, spawn processes
- Can attack other tasks running on the same machine

**The comment "Execute in a sandboxed environment" is a lie — there's no sandbox.**

### 2. **Single Master Wallet is Dangerous** 🔴 CRITICAL

All deposits go to one address. Tracking by "memo" in transaction data is:
- Not enforced (users can skip it)
- Impossible to query without custom indexing
- Prone to deposit attribution errors
- A manual reconciliation nightmare

If you credit the wrong account, you're out that money. If users don't include memo, you can't attribute deposits.

### 3. **In-Memory Queue Loses Tasks on Restart** 🟠 HIGH

```python
class TaskQueue:
    def __init__(self):
        self._queue: List[QueueItem] = []  # GONE ON RESTART
```

If the server crashes or restarts:
- All queued tasks are lost
- Users already paid (reserved funds)
- No recovery mechanism
- `PersistentTaskQueue` exists but ISN'T USED

### 4. **No Real Deposit Detection** 🟠 HIGH

The payment verifier's `_check_deposits()` method is literally:

```python
async def _check_deposits(self):
    pass  # Placeholder for MVP
```

Users have to manually call `verify_deposit()` with a tx_hash. But there's no endpoint exposed for this! The `/v1/payments/` endpoints only show balance and transaction history.

### 5. **Proof System is Fake** 🟡 MEDIUM

The "proof" is just a SHA256 hash with a fake signature:

```python
proof = TaskProof(
    result_hash=f"sha256:{result_hash}",
    signature="0x...",  # TODO: Actual signing
)
```

This provides zero cryptographic verification. An adversary could forge any result.

### 6. **No Input Validation on Task Inputs** 🟡 MEDIUM

The capability schemas define expected inputs, but they're never actually validated:

```python
# In submit_task():
# Validate capability exists ✓
if request.capability not in CAPABILITIES:
    raise HTTPException(...)

# Validate input matches schema? ✗ MISSING
```

Users can pass arbitrary data. The executor might crash, behave unexpectedly, or expose vulnerabilities.

### 7. **Browser Automation Not Actually Connected** 🟡 MEDIUM

The executor generates a Playwright script as a string and executes it via `_execute_code()`. This means:
- No connection to Clawdbot's browser tools
- No session reuse
- Cold browser launch every time (slow)
- Playwright must be installed and working

### 8. **No Webhook Implementation** 🟡 MEDIUM

`callback_url` is accepted but `_send_webhook()` might fail silently:

```python
async def _send_webhook(self, ...):
    try:
        # POST result
    except Exception as e:
        print(f"Webhook failed...")  # Just log and move on
```

No retries, no dead letter queue, no notification to user.

### 9. **SQLite Won't Scale** 🟢 LOW (for MVP)

SQLite is fine for MVP but:
- No concurrent writes
- No replication
- Will hit limits at ~100 concurrent users
- Migration path to PostgreSQL not implemented

### 10. **No Monitoring or Alerting** 🟢 LOW (for MVP)

Zero observability:
- No metrics (Prometheus/StatsD)
- No structured logging (just `print()`)
- No error tracking (Sentry)
- No uptime monitoring
- No performance baselines

---

## Critical Issues — Must Fix Before Launch 🚨

### 1. **Sandbox Code Execution**

Options (in order of preference):

| Option | Effort | Security |
|--------|--------|----------|
| **gVisor/Firecracker microVMs** | High | Best |
| **Docker with seccomp/AppArmor** | Medium | Good |
| **nsjail** | Medium | Good |
| **Pyodide (WASM sandbox)** | Medium | Good for Python only |
| **At minimum: rlimit + chroot** | Low | Minimal |

For MVP, at least use Docker with:
```bash
docker run --rm --network none --memory 512m --cpus 0.5 \
  --read-only --user nobody:nogroup \
  python:3.11-slim python /script.py
```

### 2. **Fix Deposit Attribution**

Options:
- **HD Wallet**: Derive unique address per account (BIP32/BIP44)
- **Payment Processor**: Use Coinbase Commerce, Request Network, or similar
- **Invoice System**: Each deposit request creates a unique reference

Minimum for MVP: Require users to provide tx_hash via endpoint, verify sender address matches a registered address.

### 3. **Persist Queue State**

Either:
- Use `PersistentTaskQueue` that's already written (just wire it up!)
- Use Redis with persistence (`appendonly yes`)
- Store queue state in SQLite and reload on startup

### 4. **Add Task Recovery**

On startup:
```python
# In executor.start():
tasks = await db.get_tasks_by_status(TaskStatus.QUEUED)
for task in tasks:
    await queue.enqueue(task.task_id, task.priority)

tasks = await db.get_tasks_by_status(TaskStatus.EXECUTING)
for task in tasks:
    # Either re-queue or mark as failed
    await db.update_task_status(task.task_id, TaskStatus.FAILED, 
        error=TaskError(code="SERVER_RESTART", message="Task interrupted by server restart"))
    await db.refund_reserved(task.account_id, task.price_usdc)
```

---

## Recommendations (Prioritized)

### Priority 1: Security (do before ANY real usage)

| Item | Effort | Impact |
|------|--------|--------|
| Sandbox code execution | 2-3 days | Critical |
| Add input validation | 1 day | High |
| Rate limit per account (not just IP) | 0.5 day | Medium |
| Add request logging for audit trail | 0.5 day | Medium |

### Priority 2: Reliability (do before accepting money)

| Item | Effort | Impact |
|------|--------|--------|
| Wire up PersistentTaskQueue | 0.5 day | Critical |
| Add task recovery on startup | 0.5 day | Critical |
| Fix deposit verification endpoint | 1 day | High |
| Implement webhook retries | 0.5 day | Medium |

### Priority 3: Operations (do before public launch)

| Item | Effort | Impact |
|------|--------|--------|
| Add health check endpoints | 0.5 day | High |
| Structured logging (JSON) | 0.5 day | Medium |
| Prometheus metrics | 1 day | Medium |
| Error tracking (Sentry) | 0.5 day | Medium |

### Priority 4: Scale Prep (do when you hit limits)

| Item | Effort | Impact |
|------|--------|--------|
| PostgreSQL migration | 2 days | Medium |
| Redis queue | 1 day | Medium |
| Multiple executor workers | 2 days | Medium |
| CDN for result storage | 1 day | Low |

---

## Business Model Analysis

### Is This Viable?

**Short answer:** Maybe, but margins are razor-thin.

**Cost breakdown per $0.01 screenshot task:**
| Component | Cost |
|-----------|------|
| Compute (EC2 t3.medium) | ~$0.001 |
| Browser launch overhead | ~$0.001 |
| API costs (if using external) | $0 |
| Payment processing (polygon gas) | ~$0.0001 |
| **Total cost** | **~$0.002** |
| **Gross margin** | **~80%** |

That looks good until you factor in:
- Server running 24/7 even with no tasks
- Engineering time
- Customer support
- Fraud/abuse
- Infrastructure (DB, monitoring, etc.)

**Realistic path to profit:** Need ~10,000+ tasks/month to cover fixed costs. Volume pricing helps.

### Will AI Agents Actually Use This?

**Yes, IF:**
- You make it discoverable (OpenAPI spec, MCP integration, directories)
- It's reliable (high uptime, consistent results)
- Pricing is competitive with alternatives
- Signup friction is low

**No, IF:**
- It's flaky or slow
- Requires human intervention for deposits
- Results are unpredictable

### Competitive Moat

**Current moat:** None. Anyone can copy this.

**Potential moats:**
- First-mover in "AI agent infrastructure" space
- Reputation/trust system that's hard to fake
- Network effects (more agents → more tasks → better data → better pricing)
- Integrations with AI platforms (OpenAI plugins, Claude tools, etc.)

---

## Go-to-Market Recommendations

### 1. **Make It Discoverable**

AI agents find tools via:
- OpenAPI/Swagger (you have this at `/docs`)
- Model Context Protocol (MCP) — publish as MCP server
- AI tool directories (AgentProtocol, LangChain integrations)
- GitHub (agents search for tooling)

**Action:** Create an MCP server wrapper, publish to npm/pypi as SDK.

### 2. **Reduce Signup Friction**

Current flow:
1. Create account (API call)
2. Get deposit address
3. Go to wallet, send USDC with memo
4. Wait for... nothing (manual verification broken)
5. Hope it works

Better flow:
1. Create account
2. Get QR code + amount for exact payment
3. Automatic detection and instant credit
4. Ready to use

**Action:** Use a payment gateway or implement proper deposit indexing.

### 3. **Start With One Thing Done Well**

Instead of 8 capabilities half-working, nail ONE:

**Recommendation:** Focus on `browser.screenshot` and `browser.scrape`
- These are the most common asks
- Hardest for AI agents to do themselves
- Easiest to verify (visual proof)
- Differentiated from pure API services

### 4. **Get Design Partners**

Find 3-5 AI agent developers who will use this in exchange for feedback:
- AI coding assistants (need to verify web content)
- Crypto agents (need blockchain interactions)
- Research agents (need web scraping)

Their feedback is worth more than speculation.

---

## Security Threat Model

### Attack Vectors

| Attack | Risk | Mitigation |
|--------|------|------------|
| **SSRF via browser/API** | High | URL blocklist (implemented) |
| **Code execution breakout** | Critical | Sandboxing (NOT implemented) |
| **Deposit theft via wrong attribution** | High | HD wallets or proper verification |
| **DDoS via rate limiting bypass** | Medium | Per-account limits (not implemented) |
| **API key leakage** | Medium | Key rotation, scoped permissions |
| **Replay attacks** | Low | Task IDs are UUIDs, idempotent |

### Abuse Scenarios

1. **Free compute:** Someone could use code execution for crypto mining
2. **Web scraping at scale:** Use browser capabilities to scrape competitors
3. **Fraud testing:** Use API/browser to test stolen credit cards
4. **Spam/abuse:** Automate social media spam, account creation

**Mitigations:**
- Require meaningful deposits (current $0.10 minimum is too low for abuse prevention)
- Monitor for suspicious patterns (same IP, unusual task volume)
- Block known bad actors (IP/wallet address)
- Terms of service + ability to ban accounts

---

## What's Actually Good About This

Despite the issues, the fundamentals are right:

1. **The API design is clean.** An AI agent could easily use this.
2. **The payment model makes sense.** Crypto micropayments for AI services is the future.
3. **The architecture is extensible.** Adding new capabilities is straightforward.
4. **The documentation is LLM-friendly.** `FOR_AI_AGENTS.md` is smart.
5. **The pricing is competitive.** $0.01 for a screenshot is reasonable.

With 2-3 weeks of focused work on security and reliability, this could be a legitimate service.

---

## Final Verdict

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Concept** | ⭐⭐⭐⭐⭐ | Great idea, right timing |
| **API Design** | ⭐⭐⭐⭐ | Clean, LLM-friendly |
| **Security** | ⭐ | Dangerous as-is |
| **Reliability** | ⭐⭐ | Will lose data on restart |
| **Operations** | ⭐ | No monitoring |
| **Documentation** | ⭐⭐⭐⭐ | Good for MVP |
| **Payment System** | ⭐⭐ | Concept good, implementation broken |

### Recommendation

**Do not accept real money until:**
1. ✅ Code execution is sandboxed
2. ✅ Queue persists across restarts
3. ✅ Deposit verification actually works
4. ✅ Basic monitoring is in place

**Then:** Soft launch with 5-10 design partners, iterate based on real usage, scale gradually.

---

*This review is brutally honest because the goal is to make this actually work, not to be polite.*
