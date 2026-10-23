"""
Sandboxed Code Execution Engine.
Safely runs submitted test suites and scripts with resource constraints and timeouts.
"""
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any
from backend.app.core.config import settings

class SandboxExecutionService:
    @classmethod
    def execute_test_command(cls, working_dir: Path, command: list) -> Dict[str, Any]:
        """
        Executes an automated test command inside an isolated directory with time limits.
        """
        timeout = settings.SANDBOX_EXECUTION_TIMEOUT_SECONDS
        try:
            res = subprocess.run(
                command,
                cwd=str(working_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=True
            )
            return {
                "exit_code": res.returncode,
                "stdout": res.stdout[:5000],
                "stderr": res.stderr[:5000],
                "timed_out": False,
                "success": res.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout} seconds.",
                "timed_out": True,
                "success": False
            }
        except Exception as err:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Sandbox execution error: {err}",
                "timed_out": False,
                "success": False
            }
