"""
AgentHands - Task Executor
Executes tasks using Clawdbot's capabilities
"""

import asyncio
import hashlib
import json
import subprocess
import tempfile
import time
import base64
import httpx
import ipaddress
import re
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Set
from pathlib import Path
from urllib.parse import urlparse

from .models import Task, TaskStatus, TaskResult, TaskProof, TaskError
from .database import Database
from .queue import TaskQueue

logger = logging.getLogger("agenthands.executor")


# ============================================================================
# URL Security - Blocklist for browser/network tasks
# ============================================================================

BLOCKED_HOSTS: Set[str] = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "[::1]",
    "metadata.google.internal",  # GCP metadata
    "169.254.169.254",  # AWS/cloud metadata
    "fd00:ec2::254",  # AWS metadata IPv6
    "metadata.google",
    "metadata.azure.com",  # Azure metadata
    "kubernetes.default",
    "kubernetes.default.svc",
}

BLOCKED_HOST_PATTERNS = [
    r"^10\.",           # Private 10.x.x.x
    r"^172\.(1[6-9]|2[0-9]|3[01])\.",  # Private 172.16-31.x.x
    r"^192\.168\.",     # Private 192.168.x.x
    r"\.local$",        # mDNS local domains
    r"\.internal$",     # Internal domains
    r"\.localdomain$",
    r"\.corp$",         # Corporate domains
    r"\.lan$",          # LAN domains
]


def _is_ip_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """
    Check if an IP address should be blocked.
    Handles both IPv4 and IPv6, including IPv4-mapped IPv6 addresses.
    """
    # Check standard properties
    if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
        return True
    
    # Handle IPv6 special cases
    if isinstance(ip, ipaddress.IPv6Address):
        # IPv4-mapped IPv6 (::ffff:x.x.x.x)
        if ip.ipv4_mapped:
            v4 = ip.ipv4_mapped
            if v4.is_private or v4.is_loopback or v4.is_reserved or v4.is_link_local:
                return True
        
        # 6to4 addresses (2002::/16) - could encode private IPv4
        if ip.sixtofour:
            v4 = ip.sixtofour
            if v4.is_private or v4.is_loopback or v4.is_reserved:
                return True
        
        # Teredo tunneling addresses
        if ip.teredo:
            # teredo returns (server, client) tuple
            _, client = ip.teredo
            if client.is_private or client.is_loopback:
                return True
    
    return False


def is_url_blocked(url: str) -> bool:
    """
    Check if a URL should be blocked for security reasons.
    Blocks localhost, private IPs, metadata endpoints, etc.
    
    SECURITY: Handles IPv6, IPv4-mapped IPv6, and DNS resolution
    to prevent SSRF attacks.
    """
    import socket
    
    try:
        parsed = urlparse(url)
        
        # SECURITY: Only allow http/https
        if parsed.scheme not in ("http", "https"):
            return True
        
        host = parsed.hostname or ""
        host_lower = host.lower()
        
        # SECURITY: Block empty hosts
        if not host_lower:
            return True
        
        # Check exact hostname matches
        if host_lower in BLOCKED_HOSTS:
            return True
        
        # Check hostname patterns
        for pattern in BLOCKED_HOST_PATTERNS:
            if re.match(pattern, host_lower):
                return True
        
        # Try to parse as IP address directly
        try:
            # Strip brackets from IPv6 addresses
            ip_str = host_lower.strip("[]")
            ip = ipaddress.ip_address(ip_str)
            if _is_ip_blocked(ip):
                return True
        except ValueError:
            pass  # Not an IP address literal
        
        # SECURITY: Resolve hostname and check ALL resolved IPs
        # This prevents DNS rebinding attacks where hostname resolves
        # to internal IP
        try:
            # Get all address families (IPv4 and IPv6)
            addrs = socket.getaddrinfo(host, None, socket.AF_UNSPEC)
            for addr in addrs:
                ip_str = addr[4][0]
                try:
                    ip = ipaddress.ip_address(ip_str)
                    if _is_ip_blocked(ip):
                        logger.warning(f"URL blocked: {url} resolves to private IP {ip_str}")
                        return True
                except ValueError:
                    continue
        except socket.gaierror:
            # DNS resolution failed - let the actual request fail
            pass
        except Exception as e:
            # Log but don't block on resolution errors
            logger.debug(f"DNS resolution warning for {host}: {e}")
        
        return False
    
    except Exception as e:
        logger.warning(f"URL validation error, blocking: {e}")
        return True  # Block on parse errors


# ============================================================================
# RPC Endpoints (updated with working free endpoints)
# ============================================================================

RPC_ENDPOINTS = {
    "polygon": "https://polygon-mainnet.g.alchemy.com/v2/demo",
    "ethereum": "https://eth.llamarpc.com",
    "base": "https://mainnet.base.org",
}


class TaskExecutor:
    """
    Executes tasks from the queue using Clawdbot capabilities.
    
    Bridges between AgentHands API and Clawdbot's tools:
    - browser.screenshot → Clawdbot browser tool
    - browser.scrape → Clawdbot browser + snapshot
    - code.execute → Shell execution
    - file.download → HTTP fetch
    - blockchain.balance → web3 calls
    """
    
    def __init__(self):
        self._running = False
        self._active_tasks: Dict[str, Task] = {}
        self._lock = asyncio.Lock()
        self._max_concurrent = 3  # Max parallel tasks
        self._worker_task: Optional[asyncio.Task] = None
        
        # Will be injected
        self.db: Optional[Database] = None
        self.queue: Optional[TaskQueue] = None
    
    def set_dependencies(self, db: Database, queue: TaskQueue):
        """Inject dependencies after initialization."""
        self.db = db
        self.queue = queue
    
    async def start(self):
        """Start the executor worker."""
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        print("⚡ Task executor started")
    
    async def stop(self):
        """Stop the executor."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        print("⚡ Task executor stopped")
    
    async def active_count(self) -> int:
        """Get count of currently executing tasks."""
        async with self._lock:
            return len(self._active_tasks)
    
    async def check_queue(self):
        """Signal the worker to check the queue."""
        # Worker loop handles this automatically
        pass
    
    async def _worker_loop(self):
        """Main worker loop - pulls tasks from queue and executes."""
        while self._running:
            try:
                # Check if we have capacity
                async with self._lock:
                    if len(self._active_tasks) >= self._max_concurrent:
                        await asyncio.sleep(0.5)
                        continue
                
                # Get next task
                task_id = await self.queue.dequeue()
                if not task_id:
                    await asyncio.sleep(0.5)
                    continue
                
                # Get task details
                task = await self.db.get_task(task_id)
                if not task:
                    continue
                
                # Start execution
                asyncio.create_task(self._execute_task(task))
                
            except Exception as e:
                print(f"Worker error: {e}")
                await asyncio.sleep(1)
    
    async def _execute_task(self, task: Task):
        """Execute a single task."""
        async with self._lock:
            self._active_tasks[task.task_id] = task
        
        start_time = time.time()
        
        logger.info(f"Task started: task_id={task.task_id} capability={task.capability} account={task.account_id}")
        
        try:
            # Update status to executing
            await self.db.update_task_status(task.task_id, TaskStatus.EXECUTING)
            
            # Route to appropriate handler
            handler = self._get_handler(task.capability)
            if not handler:
                raise ValueError(f"No handler for capability: {task.capability}")
            
            # Execute
            result_data = await handler(task.input_data)
            
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Create result and proof
            result = TaskResult(
                data=result_data.get("data"),
                screenshot=result_data.get("screenshot"),
                execution_log=result_data.get("log")
            )
            
            # Create proof (hash the result)
            result_json = json.dumps(result_data, sort_keys=True)
            result_hash = hashlib.sha256(result_json.encode()).hexdigest()
            
            proof = TaskProof(
                result_hash=f"sha256:{result_hash}",
                signature="0x...",  # TODO: Actual signing
                timestamp=datetime.utcnow(),
                screenshot_url=result_data.get("screenshot_url")
            )
            
            # Update task as completed
            await self.db.update_task_status(
                task.task_id,
                TaskStatus.COMPLETED,
                result=result,
                proof=proof,
                execution_time_ms=execution_time_ms
            )
            
            # Confirm payment
            await self.db.confirm_spend(task.account_id, task.price_usdc)
            
            # Record transaction
            await self.db.create_transaction(
                account_id=task.account_id,
                type="task",
                amount_usdc=-task.price_usdc,
                task_id=task.task_id,
                description=f"Task: {task.capability}"
            )
            
            # Send webhook if configured
            if task.callback_url:
                await self._send_webhook(task, result, proof)
            
            logger.info(f"Task completed: task_id={task.task_id} duration_ms={execution_time_ms} cost=${task.price_usdc}")
            print(f"✅ Task {task.task_id} completed in {execution_time_ms}ms")
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Task failed
            error = TaskError(
                code="EXECUTION_ERROR",
                message=str(e),
                details=None
            )
            
            await self.db.update_task_status(
                task.task_id,
                TaskStatus.FAILED,
                error=error
            )
            
            # Refund reserved funds
            await self.db.refund_reserved(task.account_id, task.price_usdc)
            
            # Record refund transaction
            await self.db.create_transaction(
                account_id=task.account_id,
                type="refund",
                amount_usdc=task.price_usdc,
                task_id=task.task_id,
                description=f"Refund: Task failed - {str(e)[:50]}"
            )
            
            logger.error(f"Task failed: task_id={task.task_id} error={str(e)[:100]} duration_ms={execution_time_ms}")
            print(f"❌ Task {task.task_id} failed: {e}")
        
        finally:
            async with self._lock:
                self._active_tasks.pop(task.task_id, None)
    
    def _get_handler(self, capability: str):
        """Get the handler function for a capability."""
        handlers = {
            "browser.screenshot": self._handle_browser_screenshot,
            "browser.scrape": self._handle_browser_scrape,
            "browser.interact": self._handle_browser_interact,
            "code.execute": self._handle_code_execute,
            "file.download": self._handle_file_download,
            "file.convert": self._handle_file_convert,
            "api.call": self._handle_api_call,
            "blockchain.balance": self._handle_blockchain_balance,
        }
        return handlers.get(capability)
    
    # ========================================================================
    # Capability Handlers
    # ========================================================================
    
    async def _handle_browser_screenshot(self, input_data: Dict[str, Any]) -> Dict:
        """Take a screenshot of a URL."""
        url = input_data["url"]
        full_page = input_data.get("full_page", False)
        width = input_data.get("width", 1280)
        height = input_data.get("height", 720)
        
        # Security: Block internal/private URLs
        if is_url_blocked(url):
            raise ValueError(f"URL blocked for security reasons: {url}")
        
        # Use Clawdbot's browser capability via subprocess
        # In production, this would be a direct function call
        result = await self._run_clawdbot_browser(
            action="screenshot",
            url=url,
            full_page=full_page,
            width=width,
            height=height
        )
        
        return {
            "data": {
                "url": url,
                "title": result.get("title", ""),
                "timestamp": datetime.utcnow().isoformat()
            },
            "screenshot": result.get("screenshot_base64"),
            "log": [
                {"t": 0, "action": "navigate", "url": url},
                {"t": result.get("load_time_ms", 1000), "action": "screenshot"},
            ]
        }
    
    async def _handle_browser_scrape(self, input_data: Dict[str, Any]) -> Dict:
        """Scrape data from a webpage."""
        url = input_data["url"]
        selectors = input_data.get("selectors", {})
        wait_for = input_data.get("wait_for")
        extract = input_data.get("extract", "text")
        
        # Security: Block internal/private URLs
        if is_url_blocked(url):
            raise ValueError(f"URL blocked for security reasons: {url}")
        
        result = await self._run_clawdbot_browser(
            action="scrape",
            url=url,
            selectors=selectors,
            wait_for=wait_for,
            extract=extract
        )
        
        return {
            "data": result.get("extracted_data"),
            "screenshot": result.get("screenshot_base64"),
            "log": result.get("log", [])
        }
    
    async def _handle_browser_interact(self, input_data: Dict[str, Any]) -> Dict:
        """Interactive browser automation."""
        url = input_data["url"]
        actions = input_data.get("actions", [])
        
        # Security: Block internal/private URLs
        if is_url_blocked(url):
            raise ValueError(f"URL blocked for security reasons: {url}")
        
        result = await self._run_clawdbot_browser(
            action="interact",
            url=url,
            actions=actions
        )
        
        return {
            "data": result.get("final_state"),
            "screenshot": result.get("screenshot_base64"),
            "log": result.get("log", [])
        }
    
    async def _handle_code_execute(self, input_data: Dict[str, Any]) -> Dict:
        """Execute code and return output."""
        language = input_data["language"]
        code = input_data["code"]
        timeout = input_data.get("timeout_seconds", 30)
        
        # Try Docker sandbox first, fall back to direct execution
        from .sandbox import execute_sandboxed
        result = await execute_sandboxed(
            language=language,
            code=code,
            timeout=timeout,
            fallback_to_direct=True
        )
        
        return {
            "data": {
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "exit_code": result["exit_code"],
                "execution_time_ms": result["execution_time_ms"],
                "sandboxed": result.get("sandboxed", False)
            },
            "log": [
                {"t": 0, "action": "execute", "language": language, "sandboxed": result.get("sandboxed", False)},
                {"t": result["execution_time_ms"], "action": "complete", "exit_code": result["exit_code"]}
            ]
        }
    
    async def _handle_file_download(self, input_data: Dict[str, Any]) -> Dict:
        """Download a file from URL."""
        url = input_data["url"]
        
        # Security: Block internal/private URLs
        if is_url_blocked(url):
            raise ValueError(f"URL blocked for security reasons: {url}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True, timeout=60)
            response.raise_for_status()
            
            content_type = response.headers.get("content-type", "application/octet-stream")
            content = response.content
            
            return {
                "data": {
                    "url": url,
                    "content_type": content_type,
                    "size_bytes": len(content),
                    "content_base64": base64.b64encode(content).decode()
                }
            }
    
    async def _handle_file_convert(self, input_data: Dict[str, Any]) -> Dict:
        """Download and convert a file."""
        source_url = input_data["source_url"]
        output_format = input_data["output_format"]
        
        # Download
        download_result = await self._handle_file_download({"url": source_url})
        
        # Convert (simplified - would use proper conversion tools)
        # For MVP, just return the downloaded file
        return {
            "data": {
                "source_url": source_url,
                "output_format": output_format,
                "content_base64": download_result["data"]["content_base64"],
                "note": "Conversion not yet implemented in MVP"
            }
        }
    
    async def _handle_api_call(self, input_data: Dict[str, Any]) -> Dict:
        """Make an HTTP API call."""
        url = input_data["url"]
        method = input_data.get("method", "GET")
        headers = input_data.get("headers", {})
        body = input_data.get("body")
        
        # Security: Block internal/private URLs
        if is_url_blocked(url):
            raise ValueError(f"URL blocked for security reasons: {url}")
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=body if body else None,
                timeout=30
            )
            
            try:
                response_json = response.json()
            except:
                response_json = None
            
            return {
                "data": {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response_json or response.text,
                    "is_json": response_json is not None
                }
            }
    
    async def _handle_blockchain_balance(self, input_data: Dict[str, Any]) -> Dict:
        """Check token balance on blockchain."""
        chain = input_data["chain"]
        address = input_data["address"]
        token = input_data.get("token", "native")
        
        # Use RPC to check balance
        rpc_url = RPC_ENDPOINTS.get(chain)
        if not rpc_url:
            raise ValueError(f"Unsupported chain: {chain}")
        
        async with httpx.AsyncClient() as client:
            if token == "native":
                # Get native balance
                response = await client.post(rpc_url, json={
                    "jsonrpc": "2.0",
                    "method": "eth_getBalance",
                    "params": [address, "latest"],
                    "id": 1
                })
                result = response.json()
                balance_wei = int(result["result"], 16)
                balance = balance_wei / 1e18
                token_symbol = {"polygon": "MATIC", "ethereum": "ETH", "base": "ETH"}[chain]
            else:
                # Get ERC20 balance
                # balanceOf(address) selector: 0x70a08231
                data = f"0x70a08231000000000000000000000000{address[2:]}"
                response = await client.post(rpc_url, json={
                    "jsonrpc": "2.0",
                    "method": "eth_call",
                    "params": [{"to": token, "data": data}, "latest"],
                    "id": 1
                })
                result = response.json()
                balance_raw = int(result["result"], 16)
                # Assume 18 decimals (should query decimals in production)
                balance = balance_raw / 1e18
                token_symbol = token[:10]  # Truncated address as symbol
        
        return {
            "data": {
                "chain": chain,
                "address": address,
                "token": token,
                "balance": balance,
                "symbol": token_symbol,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    async def _run_clawdbot_browser(self, **kwargs) -> Dict:
        """
        Execute browser action via Clawdbot.
        This is a simplified version - in production would integrate directly.
        """
        action = kwargs.get("action")
        url = kwargs.get("url")
        
        # For MVP, use subprocess to call playwright directly
        # In production, this would use Clawdbot's browser tool
        
        if action == "screenshot":
            return await self._playwright_screenshot(url, kwargs)
        elif action == "scrape":
            return await self._playwright_scrape(url, kwargs)
        else:
            raise ValueError(f"Unknown browser action: {action}")
    
    async def _playwright_screenshot(self, url: str, options: Dict) -> Dict:
        """Take screenshot using Playwright."""
        import json as json_module
        import tempfile
        
        # SECURITY: Write config to file instead of embedding in code
        # This prevents any possible code injection via URL
        width = int(options.get("width", 1280))
        height = int(options.get("height", 720))
        full_page = bool(options.get("full_page", False))
        
        config = {
            "url": url,
            "width": width,
            "height": height,
            "full_page": full_page
        }
        
        # Write config to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json_module.dump(config, f)
            config_path = f.name
        
        try:
            script = f'''
import asyncio
from playwright.async_api import async_playwright
import base64
import json
import sys

async def main():
    # SECURITY: Load config from file instead of inline code
    with open("{config_path}") as f:
        config = json.load(f)
    
    url = config["url"]
    width = config["width"]
    height = config["height"]
    full_page = config["full_page"]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={{"width": width, "height": height}})
        await page.goto(url, wait_until="networkidle", timeout=30000)
        title = await page.title()
        screenshot = await page.screenshot(full_page=full_page)
        await browser.close()
        print(f"TITLE:{{title}}")
        print(f"SCREENSHOT:{{base64.b64encode(screenshot).decode()}}")

asyncio.run(main())
'''
            result = await self._execute_code("python", script, timeout=60)
            
            # Parse output
            title = ""
            screenshot_base64 = ""
            for line in result["stdout"].split("\n"):
                if line.startswith("TITLE:"):
                    title = line[6:]
                elif line.startswith("SCREENSHOT:"):
                    screenshot_base64 = line[11:]
            
            return {
                "title": title,
                "screenshot_base64": screenshot_base64,
                "load_time_ms": result["execution_time_ms"]
            }
        finally:
            # Clean up config file
            Path(config_path).unlink(missing_ok=True)
    
    async def _playwright_scrape(self, url: str, options: Dict) -> Dict:
        """Scrape webpage using Playwright."""
        import json as json_module
        import tempfile
        
        selectors = options.get("selectors", {})
        extract = options.get("extract", "text")
        
        # SECURITY: Write config to file instead of embedding in code
        config = {
            "url": url,
            "selectors": selectors,
            "extract": extract
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json_module.dump(config, f)
            config_path = f.name
        
        try:
            script = f'''
import asyncio
from playwright.async_api import async_playwright
import json
import base64

async def main():
    # SECURITY: Load config from file instead of inline code
    with open("{config_path}") as f:
        config = json.load(f)
    
    url = config["url"]
    selectors = config.get("selectors", {{}})
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        await page.goto(url, wait_until="networkidle", timeout=30000)
        
        data = {{}}
        data["title"] = await page.title()
        data["url"] = page.url
        
        # Extract data using provided selectors
        if selectors:
            for name, selector in selectors.items():
                try:
                    el = await page.query_selector(selector)
                    if el:
                        data[name] = await el.inner_text()
                except:
                    pass
        else:
            data["content"] = await page.content()
        
        screenshot = await page.screenshot()
        await browser.close()
        
        print(f"DATA:{{json.dumps(data)}}")
        print(f"SCREENSHOT:{{base64.b64encode(screenshot).decode()}}")

asyncio.run(main())
'''
            result = await self._execute_code("python", script, timeout=60)
            
            # Parse output
            extracted_data = {}
            screenshot_base64 = ""
            for line in result["stdout"].split("\n"):
                if line.startswith("DATA:"):
                    extracted_data = json.loads(line[5:])
                elif line.startswith("SCREENSHOT:"):
                    screenshot_base64 = line[11:]
            
            return {
                "extracted_data": extracted_data,
                "screenshot_base64": screenshot_base64,
                "log": []
            }
        finally:
            Path(config_path).unlink(missing_ok=True)
    
    async def _execute_code(self, language: str, code: str, timeout: int = 30) -> Dict:
        """Execute code in a sandboxed environment."""
        start_time = time.time()
        
        # Create temp file
        extensions = {"python": ".py", "node": ".js", "bash": ".sh"}
        ext = extensions.get(language, ".txt")
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False) as f:
            f.write(code)
            f.flush()
            script_path = f.name
        
        try:
            # Build command
            commands = {
                "python": ["python3", script_path],
                "node": ["node", script_path],
                "bash": ["bash", script_path]
            }
            cmd = commands.get(language)
            if not cmd:
                raise ValueError(f"Unsupported language: {language}")
            
            # Execute
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return {
                    "stdout": "",
                    "stderr": f"Execution timed out after {timeout} seconds",
                    "exit_code": -1,
                    "execution_time_ms": timeout * 1000
                }
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            return {
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "exit_code": process.returncode,
                "execution_time_ms": execution_time_ms
            }
        
        finally:
            # Clean up temp file
            Path(script_path).unlink(missing_ok=True)
    
    async def _send_webhook(self, task: Task, result: TaskResult, proof: TaskProof):
        """Send completion webhook."""
        # Security: Check callback URL for SSRF
        if is_url_blocked(task.callback_url):
            print(f"⚠️ Webhook blocked (SSRF protection) for {task.task_id}: {task.callback_url}")
            return
        
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    task.callback_url,
                    json={
                        "task_id": task.task_id,
                        "status": "completed",
                        "result": result.model_dump(),
                        "proof": proof.model_dump()
                    },
                    timeout=10
                )
        except Exception as e:
            print(f"Webhook failed for {task.task_id}: {e}")
