#!/usr/bin/env python3
"""
Runtime monkey-patch to add CLAUDE_SYSTEM_PROMPT_FILE support to claude-agent-sdk.

This module provides a runtime patch for the SDK's subprocess_cli.py to support
reading system prompt from a file specified via CLAUDE_SYSTEM_PROMPT_FILE environment
variable.

This is a workaround for the lack of --system-prompt-file support in the SDK.
See: https://github.com/AndyMik90/Auto-Claude/issues/384

Usage:
    from scripts.patch_sdk_system_prompt import apply_sdk_patch
    apply_sdk_patch()
"""

import os
from pathlib import Path


def apply_sdk_patch():
    """
    Apply a runtime monkey-patch to the SDK's SubprocessCLITransport._build_command
    to support CLAUDE_SYSTEM_PROMPT_FILE environment variable.

    This function should be called once at module import time (e.g., in client.py).
    """
    try:
        from claude_agent_sdk._internal.transport.subprocess_cli import (
            SubprocessCLITransport,
        )
    except ImportError:
        # SDK not available, skip patching
        return

    # Store the original _build_command method
    original_build_command = SubprocessCLITransport._build_command

    def patched_build_command(self) -> list[str]:
        """
        Patched version of _build_command that supports CLAUDE_SYSTEM_PROMPT_FILE.

        This checks for the CLAUDE_SYSTEM_PROMPT_FILE environment variable and
        reads the system prompt from that file if it exists. This allows passing
        large system prompts that would exceed ARG_MAX limits.
        """
        cmd = original_build_command(self)

        # Check for CLAUDE_SYSTEM_PROMPT_FILE environment variable
        system_prompt_file = os.environ.get("CLAUDE_SYSTEM_PROMPT_FILE")
        if system_prompt_file and Path(system_prompt_file).exists():
            try:
                with open(system_prompt_file, encoding="utf-8") as f:
                    system_prompt_content = f.read()

                # Find and replace the --system-prompt argument in the command
                for i, arg in enumerate(cmd):
                    if arg == "--system-prompt" and i + 1 < len(cmd):
                        # Replace the system prompt value with the file contents
                        cmd[i + 1] = system_prompt_content
                        break
            except OSError as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Failed to read CLAUDE_SYSTEM_PROMPT_FILE {system_prompt_file}: {e}"
                )

        return cmd

    # Apply the monkey-patch
    SubprocessCLITransport._build_command = patched_build_command


# Auto-apply patch on import
apply_sdk_patch()
