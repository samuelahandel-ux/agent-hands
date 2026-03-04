#!/usr/bin/env python3
"""
AgentHands - Browser Sandbox Executor
Runs inside the browser container for isolated web automation
"""

import asyncio
import base64
import json
import sys
import os
from typing import Dict, Any, Optional


async def screenshot(
    url: str,
    full_page: bool = False,
    width: int = 1280,
    height: int = 720,
    timeout_ms: int = 30000
) -> Dict[str, Any]:
    """Take a screenshot of a URL."""
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-extensions",
                "--disable-background-networking",
                "--disable-sync",
                "--disable-translate",
            ]
        )
        
        try:
            context = await browser.new_context(
                viewport={"width": width, "height": height},
                java_script_enabled=True,
                bypass_csp=True,
            )
            page = await context.new_page()
            
            # Navigate with timeout
            await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            
            # Get page info
            title = await page.title()
            final_url = page.url
            
            # Take screenshot
            screenshot_bytes = await page.screenshot(full_page=full_page)
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode()
            
            return {
                "success": True,
                "title": title,
                "url": final_url,
                "screenshot": screenshot_b64,
            }
        
        finally:
            await browser.close()


async def scrape(
    url: str,
    selectors: Optional[Dict[str, str]] = None,
    wait_for: Optional[str] = None,
    timeout_ms: int = 30000
) -> Dict[str, Any]:
    """Scrape data from a webpage."""
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        )
        
        try:
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=timeout_ms // 2)
            
            # Extract data
            data = {
                "title": await page.title(),
                "url": page.url,
            }
            
            if selectors:
                for name, selector in selectors.items():
                    try:
                        el = await page.query_selector(selector)
                        if el:
                            data[name] = await el.inner_text()
                    except Exception:
                        data[name] = None
            else:
                # Get full page content if no selectors
                data["content"] = await page.content()
            
            # Screenshot for proof
            screenshot_bytes = await page.screenshot()
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode()
            
            return {
                "success": True,
                "data": data,
                "screenshot": screenshot_b64,
            }
        
        finally:
            await browser.close()


async def main():
    """Main entry point - parse command from stdin JSON."""
    # Read input from stdin or file
    input_path = os.environ.get("INPUT_PATH", "/app/input/request.json")
    
    if os.path.exists(input_path):
        with open(input_path) as f:
            request = json.load(f)
    else:
        request = json.loads(sys.stdin.read())
    
    action = request.get("action", "screenshot")
    
    try:
        if action == "screenshot":
            result = await screenshot(
                url=request["url"],
                full_page=request.get("full_page", False),
                width=request.get("width", 1280),
                height=request.get("height", 720),
                timeout_ms=request.get("timeout_ms", 30000)
            )
        elif action == "scrape":
            result = await scrape(
                url=request["url"],
                selectors=request.get("selectors"),
                wait_for=request.get("wait_for"),
                timeout_ms=request.get("timeout_ms", 30000)
            )
        else:
            result = {"success": False, "error": f"Unknown action: {action}"}
    
    except Exception as e:
        result = {"success": False, "error": str(e)}
    
    # Write output
    output_path = os.environ.get("OUTPUT_PATH", "/app/output/result.json")
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(result, f)
    
    # Also print to stdout for Docker
    print(json.dumps(result))


if __name__ == "__main__":
    asyncio.run(main())
