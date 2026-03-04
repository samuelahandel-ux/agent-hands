"""
AgentHands Client Example

This shows how other AI agents would integrate with AgentHands.
Copy this into your AI agent's tooling.
"""

import httpx
import time
from typing import Dict, Any, Optional


class AgentHandsClient:
    """
    Client for interacting with the AgentHands API.
    
    Usage:
        client = AgentHandsClient("ah_sk_live_xxx...")
        
        # Take a screenshot
        result = client.screenshot("https://example.com")
        
        # Run code
        result = client.execute_code("python", "print('Hello!')")
        
        # Check blockchain balance
        result = client.blockchain_balance("polygon", "0x...")
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.agenthands.ai"
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0
        )
    
    def _submit_and_wait(
        self,
        capability: str,
        input_data: Dict[str, Any],
        timeout: int = 120,
        poll_interval: float = 1.0
    ) -> Dict[str, Any]:
        """Submit a task and wait for completion."""
        
        # Submit task
        response = self.client.post(
            f"{self.base_url}/v1/tasks",
            json={"capability": capability, "input": input_data}
        )
        response.raise_for_status()
        task = response.json()
        task_id = task["task_id"]
        
        # Poll for completion
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = self.client.get(f"{self.base_url}/v1/tasks/{task_id}")
            result = response.json()
            
            if result["status"] == "completed":
                return result["result"]
            elif result["status"] == "failed":
                raise Exception(f"Task failed: {result.get('error', {}).get('message', 'Unknown error')}")
            
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Task {task_id} did not complete within {timeout} seconds")
    
    # ========================================================================
    # Browser Capabilities
    # ========================================================================
    
    def screenshot(
        self,
        url: str,
        full_page: bool = False,
        width: int = 1280,
        height: int = 720
    ) -> Dict[str, Any]:
        """
        Take a screenshot of a URL.
        
        Returns:
            {
                "data": {"url": str, "title": str, "timestamp": str},
                "screenshot": str (base64 PNG)
            }
        """
        return self._submit_and_wait(
            "browser.screenshot",
            {"url": url, "full_page": full_page, "width": width, "height": height}
        )
    
    def scrape(
        self,
        url: str,
        selectors: Dict[str, str] = None,
        wait_for: str = None
    ) -> Dict[str, Any]:
        """
        Scrape data from a webpage.
        
        Args:
            url: URL to scrape
            selectors: Map of field names to CSS selectors
            wait_for: CSS selector to wait for before scraping
        
        Returns:
            {"data": {field_name: extracted_value, ...}}
        """
        return self._submit_and_wait(
            "browser.scrape",
            {"url": url, "selectors": selectors or {}, "wait_for": wait_for}
        )
    
    # ========================================================================
    # Code Execution
    # ========================================================================
    
    def execute_code(
        self,
        language: str,
        code: str,
        timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """
        Execute code and return output.
        
        Args:
            language: "python", "node", or "bash"
            code: Code to execute
            timeout_seconds: Max execution time
        
        Returns:
            {"stdout": str, "stderr": str, "exit_code": int}
        """
        return self._submit_and_wait(
            "code.execute",
            {"language": language, "code": code, "timeout_seconds": timeout_seconds}
        )
    
    # ========================================================================
    # File Operations
    # ========================================================================
    
    def download_file(self, url: str) -> Dict[str, Any]:
        """
        Download a file from URL.
        
        Returns:
            {"content_base64": str, "content_type": str, "size_bytes": int}
        """
        return self._submit_and_wait("file.download", {"url": url})
    
    # ========================================================================
    # API Calls
    # ========================================================================
    
    def api_call(
        self,
        url: str,
        method: str = "GET",
        headers: Dict[str, str] = None,
        body: Any = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP API call.
        
        Returns:
            {"status_code": int, "headers": dict, "body": any}
        """
        return self._submit_and_wait(
            "api.call",
            {"url": url, "method": method, "headers": headers or {}, "body": body}
        )
    
    # ========================================================================
    # Blockchain
    # ========================================================================
    
    def blockchain_balance(
        self,
        chain: str,
        address: str,
        token: str = "native"
    ) -> Dict[str, Any]:
        """
        Check token balance on blockchain.
        
        Args:
            chain: "polygon", "ethereum", or "base"
            address: Wallet address (0x...)
            token: Token contract address or "native"
        
        Returns:
            {"balance": float, "symbol": str}
        """
        return self._submit_and_wait(
            "blockchain.balance",
            {"chain": chain, "address": address, "token": token}
        )
    
    # ========================================================================
    # Account Management
    # ========================================================================
    
    def get_balance(self) -> float:
        """Get current account balance in USDC."""
        # Need account_id - would be stored on creation
        # This is a simplified example
        response = self.client.get(f"{self.base_url}/v1/tasks")
        # Balance would be returned in account info
        return 0.0  # Placeholder
    
    def get_capabilities(self) -> list:
        """Get list of available capabilities."""
        response = self.client.get(f"{self.base_url}/v1/capabilities")
        return response.json()["capabilities"]


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Create client
    client = AgentHandsClient("ah_sk_live_xxx...")
    
    # Example 1: Screenshot
    print("Taking screenshot...")
    result = client.screenshot("https://example.com")
    print(f"Got screenshot of: {result['data']['title']}")
    print(f"Screenshot size: {len(result['screenshot'])} bytes (base64)")
    
    # Example 2: Run Python code
    print("\nRunning Python code...")
    result = client.execute_code("python", """
import json
data = {"message": "Hello from AgentHands!"}
print(json.dumps(data))
    """)
    print(f"Output: {result['data']['stdout']}")
    
    # Example 3: Check blockchain balance
    print("\nChecking Vitalik's ETH balance...")
    result = client.blockchain_balance(
        chain="ethereum",
        address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    )
    print(f"Balance: {result['data']['balance']} {result['data']['symbol']}")
