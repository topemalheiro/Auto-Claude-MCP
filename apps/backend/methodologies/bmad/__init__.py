"""BMAD methodology plugin.

This plugin packages the BMAD (Business Model Agile Development) methodology
as a plugin that can be loaded through the plugin framework.

Architecture Source: architecture.md#BMAD-Plugin-Structure
Story Reference: Story 6.1 - Create BMAD Methodology Plugin Structure
"""

from apps.backend.methodologies.bmad.methodology import BMADRunner

__all__ = ["BMADRunner"]
