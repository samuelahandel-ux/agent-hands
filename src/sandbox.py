"""
AgentHands - Docker Sandbox Execution
Secure code execution in isolated containers
"""

import asyncio
import json
import tempfile
import time
import os
import shutil
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Resource limits
DEFAULT_MEMORY_LIMIT = "256m"
DEFAULT_CPU_LIMIT = "0.5"  # 50% of one core
DEFAULT_TIMEOUT = 30  # seconds
MAX_OUTPUT_SIZE = 1024 * 1024  # 1MB max output

# Container images
SANDBOX_IMAGE = "agenthands-sandbox:latest"
BROWSER_IMAGE = "agenthands-browser:latest"


@dataclass
class SandboxResult:
    """Result of sandbox execution."""
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: int
    timed_out: bool = False
    error: Optional[str] = None


class DockerSandbox:
    """
    Secure Docker-based sandbox for code execution.
    
    Security features:
    - No network access (--network none)
    - Memory limits (--memory)
    - CPU limits (--cpus)
    - Read-only filesystem except /app/output
    - No volume mounts except temp I/O dirs
    - Process killed after timeout
    - Non-root user inside container
    """
    
    def __init__(
        self,
        memory_limit: str = DEFAULT_MEMORY_LIMIT,
        cpu_limit: str = DEFAULT_CPU_LIMIT,
        network_enabled: bool = False
    ):
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.network_enabled = network_enabled
        self._docker_available: Optional[bool] = None
    
    async def is_available(self) -> bool:
        """Check if Docker is available."""
        if self._docker_available is not None:
            return self._docker_available
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "version",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await proc.wait()
            self._docker_available = proc.returncode == 0
        except Exception:
            self._docker_available = False
        
        return self._docker_available
    
    async def ensure_image(self, image: str = SANDBOX_IMAGE) -> bool:
        """Ensure the sandbox image is built."""
        # Check if image exists
        proc = await asyncio.create_subprocess_exec(
            "docker", "image", "inspect", image,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()
        
        if proc.returncode == 0:
            return True
        
        # Build image if it doesn't exist
        dockerfile = "Dockerfile.sandbox"
        if "browser" in image:
            dockerfile = "Dockerfile.browser"
        
        build_dir = Path(__file__).parent.parent
        
        proc = await asyncio.create_subprocess_exec(
            "docker", "build", "-t", image, "-f", dockerfile, ".",
            cwd=str(build_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            print(f"Failed to build sandbox image: {stderr.decode()}")
            return False
        
        return True
    
    async def execute(
        self,
        language: str,
        code: str,
        timeout: int = DEFAULT_TIMEOUT,
        input_files: Optional[Dict[str, bytes]] = None
    ) -> SandboxResult:
        """
        Execute code in a sandboxed Docker container.
        
        Args:
            language: python, node, or bash
            code: Code to execute
            timeout: Maximum execution time in seconds
            input_files: Optional dict of filename -> bytes to make available
        
        Returns:
            SandboxResult with stdout, stderr, exit_code
        """
        start_time = time.time()
        
        # Check Docker availability
        if not await self.is_available():
            return SandboxResult(
                stdout="",
                stderr="Docker is not available. Falling back to direct execution.",
                exit_code=-1,
                execution_time_ms=0,
                error="docker_unavailable"
            )
        
        # Ensure image is built
        if not await self.ensure_image(SANDBOX_IMAGE):
            return SandboxResult(
                stdout="",
                stderr="Failed to build sandbox image",
                exit_code=-1,
                execution_time_ms=0,
                error="image_build_failed"
            )
        
        # Create temp directories for I/O
        run_id = uuid.uuid4().hex[:8]
        temp_base = Path(tempfile.gettempdir()) / f"sandbox_{run_id}"
        input_dir = temp_base / "input"
        output_dir = temp_base / "output"
        
        try:
            input_dir.mkdir(parents=True, exist_ok=True)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Write code file
            extensions = {"python": ".py", "node": ".js", "bash": ".sh"}
            ext = extensions.get(language, ".txt")
            code_file = input_dir / f"code{ext}"
            code_file.write_text(code)
            
            # Write any input files
            if input_files:
                for name, content in input_files.items():
                    # Sanitize filename
                    safe_name = Path(name).name  # Remove any path components
                    (input_dir / safe_name).write_bytes(content)
            
            # Build Docker command
            commands = {
                "python": ["python3", f"/app/input/code{ext}"],
                "node": ["node", f"/app/input/code{ext}"],
                "bash": ["bash", f"/app/input/code{ext}"]
            }
            cmd = commands.get(language)
            if not cmd:
                return SandboxResult(
                    stdout="",
                    stderr=f"Unsupported language: {language}",
                    exit_code=-1,
                    execution_time_ms=0,
                    error="unsupported_language"
                )
            
            # Build docker run command
            docker_cmd = [
                "docker", "run",
                "--rm",  # Remove container after execution
                "--memory", self.memory_limit,
                "--cpus", self.cpu_limit,
                "--pids-limit", "50",  # Limit number of processes
                "--read-only",  # Read-only root filesystem
                "--tmpfs", "/tmp:size=64m",  # Small tmpfs for temp files
                "--security-opt", "no-new-privileges",
                "-v", f"{input_dir}:/app/input:ro",  # Input is read-only
                "-v", f"{output_dir}:/app/output:rw",  # Output is writable
            ]
            
            # Network isolation
            if not self.network_enabled:
                docker_cmd.extend(["--network", "none"])
            
            docker_cmd.extend([SANDBOX_IMAGE])
            docker_cmd.extend(cmd)
            
            # Execute
            proc = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )
                timed_out = False
            except asyncio.TimeoutError:
                proc.kill()
                try:
                    await proc.wait()
                except Exception:
                    pass
                stdout = b""
                stderr = f"Execution timed out after {timeout} seconds".encode()
                timed_out = True
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Truncate output if too large
            stdout_str = stdout.decode(errors="replace")[:MAX_OUTPUT_SIZE]
            stderr_str = stderr.decode(errors="replace")[:MAX_OUTPUT_SIZE]
            
            return SandboxResult(
                stdout=stdout_str,
                stderr=stderr_str,
                exit_code=proc.returncode if not timed_out else -1,
                execution_time_ms=execution_time_ms,
                timed_out=timed_out
            )
        
        finally:
            # Clean up temp directories
            try:
                shutil.rmtree(temp_base, ignore_errors=True)
            except Exception:
                pass


class BrowserSandbox:
    """
    Secure Docker-based sandbox for browser automation.
    
    Security features:
    - Limited network access (only to target URLs)
    - Memory limits
    - CPU limits
    - Screenshot-only output
    - Timeout enforcement
    """
    
    def __init__(
        self,
        memory_limit: str = "512m",
        cpu_limit: str = "1.0"
    ):
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self._docker_available: Optional[bool] = None
    
    async def is_available(self) -> bool:
        """Check if Docker is available."""
        if self._docker_available is not None:
            return self._docker_available
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "version",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await proc.wait()
            self._docker_available = proc.returncode == 0
        except Exception:
            self._docker_available = False
        
        return self._docker_available
    
    async def screenshot(
        self,
        url: str,
        full_page: bool = False,
        width: int = 1280,
        height: int = 720,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """Take a screenshot of a URL in a sandboxed browser."""
        start_time = time.time()
        
        # For now, return placeholder - full browser sandbox requires more setup
        # In production, this would run Playwright in a container
        return {
            "error": "browser_sandbox_not_implemented",
            "message": "Browser sandbox requires additional setup. Using direct execution.",
            "fallback": True
        }


# Global sandbox instances
_code_sandbox: Optional[DockerSandbox] = None
_browser_sandbox: Optional[BrowserSandbox] = None


def get_code_sandbox() -> DockerSandbox:
    """Get or create the code sandbox instance."""
    global _code_sandbox
    if _code_sandbox is None:
        _code_sandbox = DockerSandbox()
    return _code_sandbox


def get_browser_sandbox() -> BrowserSandbox:
    """Get or create the browser sandbox instance."""
    global _browser_sandbox
    if _browser_sandbox is None:
        _browser_sandbox = BrowserSandbox()
    return _browser_sandbox


async def execute_sandboxed(
    language: str,
    code: str,
    timeout: int = DEFAULT_TIMEOUT,
    fallback_to_direct: bool = False  # SECURITY: Default to False - no unsafe fallback
) -> Dict[str, Any]:
    """
    Execute code in sandbox with optional fallback to direct execution.
    
    This is the main entry point for code execution.
    Uses Docker sandbox when available.
    
    SECURITY WARNING:
    - fallback_to_direct should NEVER be True in production
    - Direct execution allows arbitrary code on host system
    - Only enable via AGENTHANDS_ALLOW_UNSAFE_FALLBACK=true env var for development
    """
    sandbox = get_code_sandbox()
    
    result = await sandbox.execute(
        language=language,
        code=code,
        timeout=timeout
    )
    
    # If Docker not available, check if unsafe fallback is explicitly allowed
    if result.error == "docker_unavailable":
        # SECURITY: Only allow fallback if EXPLICITLY enabled via env var
        allow_unsafe = os.environ.get("AGENTHANDS_ALLOW_UNSAFE_FALLBACK", "").lower() == "true"
        
        if fallback_to_direct and allow_unsafe:
            import logging
            logging.getLogger("agenthands.sandbox").warning(
                "SECURITY WARNING: Using unsafe direct code execution - Docker unavailable"
            )
            from .executor import TaskExecutor
            executor = TaskExecutor()
            direct_result = await executor._execute_code(language, code, timeout)
            return {
                "stdout": direct_result["stdout"],
                "stderr": direct_result["stderr"],
                "exit_code": direct_result["exit_code"],
                "execution_time_ms": direct_result["execution_time_ms"],
                "sandboxed": False,
                "warning": "UNSAFE: Docker not available, used direct execution"
            }
        else:
            # SAFE DEFAULT: Refuse to execute without sandbox
            return {
                "stdout": "",
                "stderr": "Code execution unavailable: Sandbox environment not ready. Please contact administrator.",
                "exit_code": -1,
                "execution_time_ms": 0,
                "sandboxed": False,
                "error": "sandbox_unavailable"
            }
    
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "execution_time_ms": result.execution_time_ms,
        "timed_out": result.timed_out,
        "sandboxed": result.error is None,
        "error": result.error
    }
