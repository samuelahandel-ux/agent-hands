"""
AgentHands - Capability Definitions
All available capabilities with their schemas and pricing
"""

from .models import Capability

CAPABILITIES = {
    # ========================================================================
    # Browser Capabilities
    # ========================================================================
    
    "browser.screenshot": Capability(
        id="browser.screenshot",
        name="Screenshot URL",
        description="Take a screenshot of any URL. Returns PNG image as base64.",
        input_schema={
            "url": {
                "type": "string",
                "required": True,
                "description": "URL to screenshot"
            },
            "full_page": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "Capture full page (scrolled) or viewport only"
            },
            "width": {
                "type": "integer",
                "required": False,
                "default": 1280,
                "description": "Viewport width in pixels"
            },
            "height": {
                "type": "integer",
                "required": False,
                "default": 720,
                "description": "Viewport height in pixels"
            }
        },
        output_description="Base64 PNG screenshot + page title + timestamp",
        price_usdc=0.01,
        estimated_time_seconds=10,
        tier=1,
        examples=[
            {
                "input": {"url": "https://example.com"},
                "output": {"screenshot": "base64...", "title": "Example Domain"}
            }
        ]
    ),
    
    "browser.scrape": Capability(
        id="browser.scrape",
        name="Scrape Webpage",
        description="Extract structured data from a URL using CSS selectors.",
        input_schema={
            "url": {
                "type": "string",
                "required": True,
                "description": "URL to scrape"
            },
            "selectors": {
                "type": "object",
                "required": False,
                "description": "Map of field names to CSS selectors",
                "example": {"title": "h1", "price": ".price"}
            },
            "wait_for": {
                "type": "string",
                "required": False,
                "description": "CSS selector to wait for before scraping"
            },
            "extract": {
                "type": "string",
                "required": False,
                "default": "text",
                "enum": ["text", "html", "json"],
                "description": "What to extract from matched elements"
            }
        },
        output_description="Extracted data as JSON + optional screenshot",
        price_usdc=0.05,
        estimated_time_seconds=30,
        tier=2,
        examples=[
            {
                "input": {
                    "url": "https://news.ycombinator.com",
                    "selectors": {"top_story": ".titleline > a"}
                },
                "output": {"top_story": "Show HN: Something Cool"}
            }
        ]
    ),
    
    "browser.interact": Capability(
        id="browser.interact",
        name="Browser Automation",
        description="Perform interactive actions on a webpage (clicks, typing, navigation).",
        input_schema={
            "url": {
                "type": "string",
                "required": True,
                "description": "Starting URL"
            },
            "actions": {
                "type": "array",
                "required": True,
                "description": "List of actions to perform",
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["click", "type", "wait", "screenshot", "extract"]},
                        "selector": {"type": "string"},
                        "text": {"type": "string"},
                        "timeout": {"type": "integer"}
                    }
                }
            }
        },
        output_description="Final state + screenshots + execution log",
        price_usdc=0.10,
        estimated_time_seconds=60,
        tier=2,
        examples=[
            {
                "input": {
                    "url": "https://example.com/form",
                    "actions": [
                        {"action": "type", "selector": "#email", "text": "test@example.com"},
                        {"action": "click", "selector": "button[type=submit]"},
                        {"action": "wait", "selector": ".success"}
                    ]
                }
            }
        ]
    ),
    
    # ========================================================================
    # Code Execution Capabilities
    # ========================================================================
    
    "code.execute": Capability(
        id="code.execute",
        name="Execute Code",
        description="Run code and return stdout/stderr. Supports Python, Node.js, and Bash.",
        input_schema={
            "language": {
                "type": "string",
                "required": True,
                "enum": ["python", "node", "bash"],
                "description": "Programming language"
            },
            "code": {
                "type": "string",
                "required": True,
                "description": "Code to execute"
            },
            "timeout_seconds": {
                "type": "integer",
                "required": False,
                "default": 30,
                "max": 300,
                "description": "Maximum execution time"
            }
        },
        output_description="stdout, stderr, exit code, execution time",
        price_usdc=0.02,
        estimated_time_seconds=15,
        tier=1,
        examples=[
            {
                "input": {
                    "language": "python",
                    "code": "print(sum(range(100)))"
                },
                "output": {"stdout": "4950", "exit_code": 0}
            }
        ]
    ),
    
    # ========================================================================
    # File Capabilities
    # ========================================================================
    
    "file.download": Capability(
        id="file.download",
        name="Download File",
        description="Download a file from URL and return as base64.",
        input_schema={
            "url": {
                "type": "string",
                "required": True,
                "description": "URL of file to download"
            }
        },
        output_description="File content as base64 + content type + size",
        price_usdc=0.02,
        estimated_time_seconds=30,
        tier=1,
        examples=[
            {
                "input": {"url": "https://example.com/document.pdf"},
                "output": {"content_base64": "...", "content_type": "application/pdf", "size_bytes": 12345}
            }
        ]
    ),
    
    "file.convert": Capability(
        id="file.convert",
        name="Convert File",
        description="Download and convert file to different format.",
        input_schema={
            "source_url": {
                "type": "string",
                "required": True,
                "description": "URL of source file"
            },
            "output_format": {
                "type": "string",
                "required": True,
                "description": "Target format (e.g., 'pdf', 'png', 'mp3')"
            },
            "options": {
                "type": "object",
                "required": False,
                "description": "Format-specific conversion options"
            }
        },
        output_description="Converted file as base64",
        price_usdc=0.05,
        estimated_time_seconds=60,
        tier=2
    ),
    
    # ========================================================================
    # API Capabilities
    # ========================================================================
    
    "api.call": Capability(
        id="api.call",
        name="HTTP API Call",
        description="Make an HTTP request to any API endpoint.",
        input_schema={
            "url": {
                "type": "string",
                "required": True,
                "description": "API endpoint URL"
            },
            "method": {
                "type": "string",
                "required": False,
                "default": "GET",
                "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                "description": "HTTP method"
            },
            "headers": {
                "type": "object",
                "required": False,
                "description": "HTTP headers"
            },
            "body": {
                "type": "object",
                "required": False,
                "description": "Request body (for POST/PUT/PATCH)"
            }
        },
        output_description="Response status, headers, and body",
        price_usdc=0.02,
        estimated_time_seconds=10,
        tier=1,
        examples=[
            {
                "input": {
                    "url": "https://api.github.com/users/torvalds",
                    "method": "GET"
                },
                "output": {"status_code": 200, "body": {"login": "torvalds", "...": "..."}}
            }
        ]
    ),
    
    # ========================================================================
    # Blockchain Capabilities
    # ========================================================================
    
    "blockchain.balance": Capability(
        id="blockchain.balance",
        name="Check Token Balance",
        description="Check native or ERC20 token balance for any address.",
        input_schema={
            "chain": {
                "type": "string",
                "required": True,
                "enum": ["polygon", "ethereum", "base"],
                "description": "Blockchain network"
            },
            "address": {
                "type": "string",
                "required": True,
                "description": "Wallet address (0x...)"
            },
            "token": {
                "type": "string",
                "required": False,
                "default": "native",
                "description": "Token contract address or 'native' for chain token"
            }
        },
        output_description="Balance with decimals + token symbol",
        price_usdc=0.01,
        estimated_time_seconds=5,
        tier=1,
        examples=[
            {
                "input": {
                    "chain": "polygon",
                    "address": "0x...",
                    "token": "native"
                },
                "output": {"balance": 10.5, "symbol": "MATIC"}
            }
        ]
    ),
    
    "blockchain.transaction": Capability(
        id="blockchain.transaction",
        name="Send Transaction",
        description="Execute a blockchain transaction (requires pre-funding our wallet).",
        input_schema={
            "chain": {
                "type": "string",
                "required": True,
                "enum": ["polygon"],
                "description": "Blockchain network (Polygon only for MVP)"
            },
            "to": {
                "type": "string",
                "required": True,
                "description": "Recipient address"
            },
            "value": {
                "type": "string",
                "required": False,
                "description": "Native token amount in wei"
            },
            "data": {
                "type": "string",
                "required": False,
                "description": "Transaction data (for contract calls)"
            }
        },
        output_description="Transaction hash + confirmation",
        price_usdc=0.10,
        estimated_time_seconds=30,
        tier=3
    ),
}


def get_capability(capability_id: str) -> Capability:
    """Get a capability by ID."""
    if capability_id not in CAPABILITIES:
        raise ValueError(f"Unknown capability: {capability_id}")
    return CAPABILITIES[capability_id]


def list_capabilities() -> list:
    """List all available capabilities."""
    return list(CAPABILITIES.values())


def get_price(capability_id: str, priority: str = "standard") -> float:
    """Calculate price including priority multiplier."""
    base_price = CAPABILITIES[capability_id].price_usdc
    
    multipliers = {
        "standard": 1.0,
        "priority": 1.5,
        "immediate": 2.0
    }
    
    return base_price * multipliers.get(priority, 1.0)
