"""
AgentHands - Input/Output Validation
Schema validation for task inputs and outputs
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse


# Maximum string lengths for sanitization
MAX_CODE_LENGTH = 100000  # 100KB
MAX_URL_LENGTH = 2048
MAX_STRING_LENGTH = 10000
MAX_SELECTOR_LENGTH = 500


class ValidationError(Exception):
    """Validation error with details."""
    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.message = message
        self.value = value
        super().__init__(f"{field}: {message}")


def sanitize_string(value: str, max_length: int = MAX_STRING_LENGTH) -> str:
    """
    Sanitize a string value.
    - Truncate to max length
    - Remove null bytes
    - Strip leading/trailing whitespace
    """
    if not isinstance(value, str):
        return str(value)[:max_length]
    
    # Remove null bytes (can cause issues in many systems)
    value = value.replace("\x00", "")
    
    # Truncate
    value = value[:max_length]
    
    # Strip whitespace
    value = value.strip()
    
    return value


def validate_url(url: str, field_name: str = "url") -> str:
    """
    Validate and sanitize a URL.
    
    Raises ValidationError if invalid.
    Returns sanitized URL.
    """
    url = sanitize_string(url, MAX_URL_LENGTH)
    
    if not url:
        raise ValidationError(field_name, "URL is required")
    
    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception:
        raise ValidationError(field_name, "Invalid URL format")
    
    # Must have scheme and netloc
    if not parsed.scheme:
        raise ValidationError(field_name, "URL must include scheme (http:// or https://)")
    
    if parsed.scheme not in ("http", "https"):
        raise ValidationError(field_name, "Only HTTP and HTTPS URLs are allowed")
    
    if not parsed.netloc:
        raise ValidationError(field_name, "URL must include a hostname")
    
    return url


def validate_code(code: str, language: str) -> str:
    """
    Validate code input.
    
    Basic sanitization - actual security comes from sandbox.
    """
    code = sanitize_string(code, MAX_CODE_LENGTH)
    
    if not code:
        raise ValidationError("code", "Code is required")
    
    if language not in ("python", "node", "bash"):
        raise ValidationError("language", f"Unsupported language: {language}")
    
    return code


def validate_selectors(selectors: Dict[str, str]) -> Dict[str, str]:
    """
    Validate CSS selectors dictionary.
    """
    if not isinstance(selectors, dict):
        raise ValidationError("selectors", "Selectors must be an object")
    
    validated = {}
    for name, selector in selectors.items():
        # Sanitize name
        name = sanitize_string(str(name), 100)
        if not name:
            continue
        
        # Sanitize selector
        selector = sanitize_string(str(selector), MAX_SELECTOR_LENGTH)
        if not selector:
            continue
        
        validated[name] = selector
    
    return validated


def validate_browser_screenshot_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate browser.screenshot input."""
    validated = {}
    
    # Required: url
    validated["url"] = validate_url(input_data.get("url", ""))
    
    # Optional: full_page (boolean)
    validated["full_page"] = bool(input_data.get("full_page", False))
    
    # Optional: width (integer, 100-4000)
    width = input_data.get("width", 1280)
    try:
        width = int(width)
        width = max(100, min(4000, width))
    except (ValueError, TypeError):
        width = 1280
    validated["width"] = width
    
    # Optional: height (integer, 100-4000)
    height = input_data.get("height", 720)
    try:
        height = int(height)
        height = max(100, min(4000, height))
    except (ValueError, TypeError):
        height = 720
    validated["height"] = height
    
    return validated


def validate_browser_scrape_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate browser.scrape input."""
    validated = {}
    
    # Required: url
    validated["url"] = validate_url(input_data.get("url", ""))
    
    # Optional: selectors
    if "selectors" in input_data:
        validated["selectors"] = validate_selectors(input_data["selectors"])
    
    # Optional: wait_for
    if "wait_for" in input_data:
        validated["wait_for"] = sanitize_string(str(input_data["wait_for"]), MAX_SELECTOR_LENGTH)
    
    # Optional: extract
    extract = input_data.get("extract", "text")
    if extract not in ("text", "html", "json"):
        extract = "text"
    validated["extract"] = extract
    
    return validated


def validate_code_execute_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate code.execute input."""
    validated = {}
    
    # Required: language
    language = input_data.get("language", "")
    if language not in ("python", "node", "bash"):
        raise ValidationError("language", f"Unsupported language: {language}. Use: python, node, bash")
    validated["language"] = language
    
    # Required: code
    validated["code"] = validate_code(input_data.get("code", ""), language)
    
    # Optional: timeout_seconds
    timeout = input_data.get("timeout_seconds", 30)
    try:
        timeout = int(timeout)
        timeout = max(1, min(300, timeout))  # 1-300 seconds
    except (ValueError, TypeError):
        timeout = 30
    validated["timeout_seconds"] = timeout
    
    return validated


def validate_file_download_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate file.download input."""
    validated = {}
    validated["url"] = validate_url(input_data.get("url", ""))
    return validated


def validate_api_call_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate api.call input."""
    validated = {}
    
    # Required: url
    validated["url"] = validate_url(input_data.get("url", ""))
    
    # Optional: method
    method = input_data.get("method", "GET").upper()
    if method not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
        method = "GET"
    validated["method"] = method
    
    # Optional: headers (sanitize keys and values)
    if "headers" in input_data and isinstance(input_data["headers"], dict):
        validated["headers"] = {
            sanitize_string(str(k), 100): sanitize_string(str(v), 1000)
            for k, v in input_data["headers"].items()
        }
    
    # Optional: body (pass through, will be JSON serialized)
    if "body" in input_data:
        validated["body"] = input_data["body"]
    
    return validated


def validate_blockchain_balance_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate blockchain.balance input."""
    validated = {}
    
    # Required: chain
    chain = input_data.get("chain", "")
    if chain not in ("polygon", "ethereum", "base"):
        raise ValidationError("chain", f"Unsupported chain: {chain}. Use: polygon, ethereum, base")
    validated["chain"] = chain
    
    # Required: address
    address = input_data.get("address", "")
    if not address or not re.match(r"^0x[a-fA-F0-9]{40}$", address):
        raise ValidationError("address", "Invalid Ethereum address format")
    validated["address"] = address.lower()
    
    # Optional: token
    token = input_data.get("token", "native")
    if token != "native" and not re.match(r"^0x[a-fA-F0-9]{40}$", token):
        raise ValidationError("token", "Token must be 'native' or a valid contract address")
    validated["token"] = token.lower() if token != "native" else "native"
    
    return validated


# Validator registry
VALIDATORS = {
    "browser.screenshot": validate_browser_screenshot_input,
    "browser.scrape": validate_browser_scrape_input,
    "browser.interact": lambda x: x,  # TODO: Implement
    "code.execute": validate_code_execute_input,
    "file.download": validate_file_download_input,
    "file.convert": lambda x: x,  # TODO: Implement
    "api.call": validate_api_call_input,
    "blockchain.balance": validate_blockchain_balance_input,
    "blockchain.transaction": lambda x: x,  # TODO: Implement
}


def validate_task_input(capability: str, input_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Validate task input against capability schema.
    
    Returns:
        Tuple of (validated_input, error_message)
        If error_message is not None, validation failed.
    """
    validator = VALIDATORS.get(capability)
    
    if not validator:
        return input_data, None  # No validator, pass through
    
    try:
        validated = validator(input_data)
        return validated, None
    except ValidationError as e:
        return input_data, f"Invalid input for {e.field}: {e.message}"
    except Exception as e:
        return input_data, f"Validation error: {str(e)}"
