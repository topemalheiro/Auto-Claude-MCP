#!/usr/bin/env python3
"""
Spec Creation Orchestrator
==========================

Dynamic spec creation with complexity-based phase selection.
The orchestrator self-evaluates task complexity and adapts its process accordingly.

Complexity Tiers:
- SIMPLE (1-2 files): Discovery → Quick Spec → Validate (3 phases)
- STANDARD (3-10 files): Discovery → Requirements → Context → Spec → Validate (5 phases)
- COMPLEX (10+ files/integrations): Full 8-phase pipeline with research and self-critique

The process dynamically selects phases based on:
- Number of files/services involved
- External integrations mentioned
- Infrastructure changes required
- Task keywords and scope indicators

Usage:
    python auto-build/spec_runner.py --task "Add user authentication"
    python auto-build/spec_runner.py --interactive
    python auto-build/spec_runner.py --continue 001-feature
    python auto-build/spec_runner.py --task "Fix button color" --complexity simple
"""

import asyncio
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

# Add auto-build to path
sys.path.insert(0, str(Path(__file__).parent))

from client import create_client
from validate_spec import SpecValidator, auto_fix_plan


# Configuration
MAX_RETRIES = 3
PROMPTS_DIR = Path(__file__).parent / "prompts"
SPECS_DIR = Path(__file__).parent / "specs"


class Complexity(Enum):
    """Task complexity tiers that determine which phases to run."""
    SIMPLE = "simple"      # 1-2 files, single service, no integrations
    STANDARD = "standard"  # 3-10 files, 1-2 services, minimal integrations
    COMPLEX = "complex"    # 10+ files, multiple services, external integrations


@dataclass
class ComplexityAssessment:
    """Result of analyzing task complexity."""
    complexity: Complexity
    confidence: float  # 0.0 to 1.0
    signals: dict = field(default_factory=dict)
    reasoning: str = ""

    # Detected characteristics
    estimated_files: int = 1
    estimated_services: int = 1
    external_integrations: list = field(default_factory=list)
    infrastructure_changes: bool = False

    def phases_to_run(self) -> list[str]:
        """Return list of phase names to run based on complexity."""
        if self.complexity == Complexity.SIMPLE:
            return ["discovery", "quick_spec", "validation"]
        elif self.complexity == Complexity.STANDARD:
            return ["discovery", "requirements", "context", "spec_writing", "planning", "validation"]
        else:  # COMPLEX
            return ["discovery", "requirements", "research", "context", "spec_writing", "self_critique", "planning", "validation"]


class ComplexityAnalyzer:
    """Analyzes task description and context to determine complexity."""

    # Keywords that suggest different complexity levels
    SIMPLE_KEYWORDS = [
        "fix", "typo", "update", "change", "rename", "remove", "delete",
        "adjust", "tweak", "correct", "modify", "style", "color", "text",
        "label", "button", "margin", "padding", "font", "size", "hide", "show"
    ]

    COMPLEX_KEYWORDS = [
        "integrate", "integration", "api", "sdk", "library", "package",
        "database", "migrate", "migration", "docker", "kubernetes", "deploy",
        "authentication", "oauth", "graphql", "websocket", "queue", "cache",
        "redis", "postgres", "mongo", "elasticsearch", "kafka", "rabbitmq",
        "microservice", "refactor", "architecture", "infrastructure"
    ]

    MULTI_SERVICE_KEYWORDS = [
        "backend", "frontend", "worker", "service", "api", "client",
        "server", "database", "queue", "cache", "proxy"
    ]

    def __init__(self, project_index: Optional[dict] = None):
        self.project_index = project_index or {}

    def analyze(self, task_description: str, requirements: Optional[dict] = None) -> ComplexityAssessment:
        """Analyze task and return complexity assessment."""
        task_lower = task_description.lower()
        signals = {}

        # 1. Keyword analysis
        simple_matches = sum(1 for kw in self.SIMPLE_KEYWORDS if kw in task_lower)
        complex_matches = sum(1 for kw in self.COMPLEX_KEYWORDS if kw in task_lower)
        multi_service_matches = sum(1 for kw in self.MULTI_SERVICE_KEYWORDS if kw in task_lower)

        signals["simple_keywords"] = simple_matches
        signals["complex_keywords"] = complex_matches
        signals["multi_service_keywords"] = multi_service_matches

        # 2. External integrations detection
        integrations = self._detect_integrations(task_lower)
        signals["external_integrations"] = len(integrations)

        # 3. Infrastructure changes detection
        infra_changes = self._detect_infrastructure_changes(task_lower)
        signals["infrastructure_changes"] = infra_changes

        # 4. Estimate files and services
        estimated_files = self._estimate_files(task_lower, requirements)
        estimated_services = self._estimate_services(task_lower, requirements)
        signals["estimated_files"] = estimated_files
        signals["estimated_services"] = estimated_services

        # 5. Requirements-based signals (if available)
        if requirements:
            services_involved = requirements.get("services_involved", [])
            signals["explicit_services"] = len(services_involved)
            estimated_services = max(estimated_services, len(services_involved))

        # Determine complexity
        complexity, confidence, reasoning = self._calculate_complexity(
            signals, integrations, infra_changes, estimated_files, estimated_services
        )

        return ComplexityAssessment(
            complexity=complexity,
            confidence=confidence,
            signals=signals,
            reasoning=reasoning,
            estimated_files=estimated_files,
            estimated_services=estimated_services,
            external_integrations=integrations,
            infrastructure_changes=infra_changes,
        )

    def _detect_integrations(self, task_lower: str) -> list[str]:
        """Detect external integrations mentioned in task."""
        integration_patterns = [
            r'\b(graphiti|graphql|apollo)\b',
            r'\b(stripe|paypal|payment)\b',
            r'\b(auth0|okta|oauth|jwt)\b',
            r'\b(aws|gcp|azure|s3|lambda)\b',
            r'\b(redis|memcached|cache)\b',
            r'\b(postgres|mysql|mongodb|database)\b',
            r'\b(elasticsearch|algolia|search)\b',
            r'\b(kafka|rabbitmq|sqs|queue)\b',
            r'\b(docker|kubernetes|k8s)\b',
            r'\b(openai|anthropic|llm|ai)\b',
            r'\b(sendgrid|twilio|email|sms)\b',
        ]

        found = []
        for pattern in integration_patterns:
            matches = re.findall(pattern, task_lower)
            found.extend(matches)

        return list(set(found))

    def _detect_infrastructure_changes(self, task_lower: str) -> bool:
        """Detect if task involves infrastructure changes."""
        infra_patterns = [
            r'\bdocker\b', r'\bkubernetes\b', r'\bk8s\b',
            r'\bdeploy\b', r'\binfrastructure\b', r'\bci/cd\b',
            r'\benvironment\b', r'\bconfig\b', r'\b\.env\b',
            r'\bdatabase migration\b', r'\bschema\b',
        ]

        for pattern in infra_patterns:
            if re.search(pattern, task_lower):
                return True
        return False

    def _estimate_files(self, task_lower: str, requirements: Optional[dict]) -> int:
        """Estimate number of files to be modified."""
        # Base estimate from task description
        if any(kw in task_lower for kw in ["single", "one file", "one component", "this file"]):
            return 1

        # Check for explicit file mentions
        file_mentions = len(re.findall(r'\.(tsx?|jsx?|py|go|rs|java|rb|php|vue|svelte)\b', task_lower))
        if file_mentions > 0:
            return max(1, file_mentions)

        # Heuristic based on task scope
        if any(kw in task_lower for kw in self.SIMPLE_KEYWORDS):
            return 2
        elif any(kw in task_lower for kw in ["feature", "add", "implement", "create"]):
            return 5
        elif any(kw in task_lower for kw in self.COMPLEX_KEYWORDS):
            return 15

        return 5  # Default estimate

    def _estimate_services(self, task_lower: str, requirements: Optional[dict]) -> int:
        """Estimate number of services involved."""
        service_count = sum(1 for kw in self.MULTI_SERVICE_KEYWORDS if kw in task_lower)

        # If project is a monorepo, check project_index
        if self.project_index.get("project_type") == "monorepo":
            services = self.project_index.get("services", {})
            if services:
                # Check which services are mentioned
                mentioned = sum(1 for svc in services if svc.lower() in task_lower)
                if mentioned > 0:
                    return mentioned

        return max(1, min(service_count, 5))

    def _calculate_complexity(
        self,
        signals: dict,
        integrations: list,
        infra_changes: bool,
        estimated_files: int,
        estimated_services: int,
    ) -> tuple[Complexity, float, str]:
        """Calculate final complexity based on all signals."""

        reasons = []

        # Strong indicators for SIMPLE
        if (
            estimated_files <= 2 and
            estimated_services == 1 and
            len(integrations) == 0 and
            not infra_changes and
            signals["simple_keywords"] > 0 and
            signals["complex_keywords"] == 0
        ):
            reasons.append(f"Single service, {estimated_files} file(s), no integrations")
            return Complexity.SIMPLE, 0.9, "; ".join(reasons)

        # Strong indicators for COMPLEX
        if (
            len(integrations) >= 2 or
            infra_changes or
            estimated_services >= 3 or
            estimated_files >= 10 or
            signals["complex_keywords"] >= 3
        ):
            reasons.append(f"{len(integrations)} integrations, {estimated_services} services, {estimated_files} files")
            if infra_changes:
                reasons.append("infrastructure changes detected")
            return Complexity.COMPLEX, 0.85, "; ".join(reasons)

        # Default to STANDARD
        reasons.append(f"{estimated_files} files, {estimated_services} service(s)")
        if len(integrations) > 0:
            reasons.append(f"{len(integrations)} integration(s)")

        return Complexity.STANDARD, 0.75, "; ".join(reasons)


@dataclass
class PhaseResult:
    """Result of a phase execution."""
    phase: str
    success: bool
    output_files: list[str]
    errors: list[str]
    retries: int


class SpecOrchestrator:
    """Orchestrates the spec creation process with dynamic complexity adaptation."""

    def __init__(
        self,
        project_dir: Path,
        task_description: Optional[str] = None,
        spec_name: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        complexity_override: Optional[str] = None,  # Force a specific complexity
    ):
        self.project_dir = Path(project_dir)
        self.task_description = task_description
        self.model = model
        self.complexity_override = complexity_override

        # Complexity assessment (populated during run)
        self.assessment: Optional[ComplexityAssessment] = None

        # Create spec directory
        if spec_name:
            self.spec_dir = SPECS_DIR / spec_name
        else:
            self.spec_dir = self._create_spec_dir()

        self.spec_dir.mkdir(parents=True, exist_ok=True)
        self.validator = SpecValidator(self.spec_dir)

    def _create_spec_dir(self) -> Path:
        """Create a new spec directory with incremented number."""
        existing = list(SPECS_DIR.glob("[0-9][0-9][0-9]-*"))
        next_num = len(existing) + 1

        # Generate name from task description
        if self.task_description:
            # Convert to kebab-case
            name = self.task_description.lower()
            name = "".join(c if c.isalnum() or c == " " else "" for c in name)
            name = "-".join(name.split()[:4])  # First 4 words
        else:
            name = "new-spec"

        return SPECS_DIR / f"{next_num:03d}-{name}"

    def _run_script(self, script: str, args: list[str]) -> tuple[bool, str]:
        """Run a Python script and return (success, output)."""
        script_path = Path(__file__).parent / script

        if not script_path.exists():
            return False, f"Script not found: {script_path}"

        cmd = [sys.executable, str(script_path)] + args

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr or result.stdout

        except subprocess.TimeoutExpired:
            return False, "Script timed out"
        except Exception as e:
            return False, str(e)

    async def _run_agent(
        self,
        prompt_file: str,
        additional_context: str = "",
        interactive: bool = False,
    ) -> tuple[bool, str]:
        """Run an agent with the given prompt."""
        prompt_path = PROMPTS_DIR / prompt_file

        if not prompt_path.exists():
            return False, f"Prompt not found: {prompt_path}"

        # Load prompt
        prompt = prompt_path.read_text()

        # Add context
        prompt += f"\n\n---\n\n**Spec Directory**: {self.spec_dir}\n"
        prompt += f"**Project Directory**: {self.project_dir}\n"

        if additional_context:
            prompt += f"\n{additional_context}\n"

        # Create client
        client = create_client(self.project_dir, self.spec_dir, self.model)

        try:
            async with client:
                await client.query(prompt)

                response_text = ""
                async for msg in client.receive_response():
                    msg_type = type(msg).__name__

                    if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                        for block in msg.content:
                            block_type = type(block).__name__
                            if block_type == "TextBlock" and hasattr(block, "text"):
                                response_text += block.text
                                print(block.text, end="", flush=True)
                            elif block_type == "ToolUseBlock" and hasattr(block, "name"):
                                print(f"\n[Tool: {block.name}]", flush=True)

                print()
                return True, response_text

        except Exception as e:
            return False, str(e)

    # === Phase Implementations ===

    async def phase_complexity_assessment(self) -> PhaseResult:
        """Phase 0: Assess task complexity to determine which phases to run."""
        print("\n" + "=" * 60)
        print("  PHASE 0: COMPLEXITY ASSESSMENT")
        print("=" * 60)

        # Load project index if available
        project_index = {}
        auto_build_index = Path(__file__).parent / "project_index.json"
        if auto_build_index.exists():
            with open(auto_build_index) as f:
                project_index = json.load(f)

        # Perform assessment
        analyzer = ComplexityAnalyzer(project_index)

        if self.complexity_override:
            # Manual override
            complexity = Complexity(self.complexity_override)
            self.assessment = ComplexityAssessment(
                complexity=complexity,
                confidence=1.0,
                reasoning=f"Manual override: {self.complexity_override}",
            )
            print(f"✓ Complexity override: {complexity.value.upper()}")
        else:
            # Automatic assessment
            self.assessment = analyzer.analyze(self.task_description or "")
            print(f"✓ Assessed complexity: {self.assessment.complexity.value.upper()}")
            print(f"  Confidence: {self.assessment.confidence:.0%}")
            print(f"  Reasoning: {self.assessment.reasoning}")

        # Show what phases will run
        phases = self.assessment.phases_to_run()
        print(f"\n  Phases to run ({len(phases)}):")
        for i, phase in enumerate(phases, 1):
            print(f"    {i}. {phase}")

        # Save assessment to spec dir
        assessment_file = self.spec_dir / "complexity_assessment.json"
        with open(assessment_file, "w") as f:
            json.dump({
                "complexity": self.assessment.complexity.value,
                "confidence": self.assessment.confidence,
                "reasoning": self.assessment.reasoning,
                "signals": self.assessment.signals,
                "estimated_files": self.assessment.estimated_files,
                "estimated_services": self.assessment.estimated_services,
                "external_integrations": self.assessment.external_integrations,
                "infrastructure_changes": self.assessment.infrastructure_changes,
                "phases_to_run": phases,
                "created_at": datetime.now().isoformat(),
            }, f, indent=2)

        return PhaseResult("complexity_assessment", True, [str(assessment_file)], [], 0)

    async def phase_discovery(self) -> PhaseResult:
        """Phase 1: Analyze project structure."""
        print("\n" + "=" * 60)
        print("  PHASE 1: PROJECT DISCOVERY")
        print("=" * 60)

        errors = []
        retries = 0

        for attempt in range(MAX_RETRIES):
            retries = attempt

            # Check if project_index already exists
            auto_build_index = Path(__file__).parent / "project_index.json"
            spec_index = self.spec_dir / "project_index.json"

            if auto_build_index.exists() and not spec_index.exists():
                # Copy existing index
                import shutil
                shutil.copy(auto_build_index, spec_index)
                print(f"✓ Copied existing project_index.json")
                return PhaseResult("discovery", True, [str(spec_index)], [], 0)

            if spec_index.exists():
                print(f"✓ project_index.json already exists")
                return PhaseResult("discovery", True, [str(spec_index)], [], 0)

            # Run analyzer
            print("Running project analyzer...")
            success, output = self._run_script(
                "analyzer.py",
                ["--output", str(spec_index)]
            )

            if success and spec_index.exists():
                print(f"✓ Created project_index.json")
                return PhaseResult("discovery", True, [str(spec_index)], [], retries)

            errors.append(f"Attempt {attempt + 1}: {output}")
            print(f"✗ Attempt {attempt + 1} failed: {output[:200]}")

        return PhaseResult("discovery", False, [], errors, retries)

    async def phase_requirements(self, interactive: bool = True) -> PhaseResult:
        """Phase 2: Gather requirements."""
        print("\n" + "=" * 60)
        print("  PHASE 2: REQUIREMENTS GATHERING")
        print("=" * 60)

        requirements_file = self.spec_dir / "requirements.json"

        # If we have a task description, create requirements directly
        if self.task_description and not interactive:
            requirements = {
                "task_description": self.task_description,
                "workflow_type": "feature",  # Default, agent will refine
                "services_involved": [],  # Agent will determine
                "created_at": datetime.now().isoformat(),
            }
            with open(requirements_file, "w") as f:
                json.dump(requirements, f, indent=2)
            print(f"✓ Created requirements.json from task description")
            return PhaseResult("requirements", True, [str(requirements_file)], [], 0)

        # Interactive mode - run agent
        errors = []
        for attempt in range(MAX_RETRIES):
            print(f"\nRunning requirements gatherer (attempt {attempt + 1})...")

            context = f"**Task**: {self.task_description or 'Ask user what they want to build'}\n"
            success, output = await self._run_agent(
                "spec_gatherer.md",
                additional_context=context,
                interactive=True,
            )

            if success and requirements_file.exists():
                print(f"✓ Created requirements.json")
                return PhaseResult("requirements", True, [str(requirements_file)], [], attempt)

            errors.append(f"Attempt {attempt + 1}: Agent did not create requirements.json")

        return PhaseResult("requirements", False, [], errors, MAX_RETRIES)

    async def phase_quick_spec(self) -> PhaseResult:
        """Quick spec for simple tasks - combines requirements, context, and spec in one step."""
        print("\n" + "=" * 60)
        print("  QUICK SPEC (Simple Task)")
        print("=" * 60)

        spec_file = self.spec_dir / "spec.md"
        plan_file = self.spec_dir / "implementation_plan.json"

        if spec_file.exists() and plan_file.exists():
            print(f"✓ Quick spec already exists")
            return PhaseResult("quick_spec", True, [str(spec_file), str(plan_file)], [], 0)

        errors = []
        for attempt in range(MAX_RETRIES):
            print(f"\nRunning quick spec agent (attempt {attempt + 1})...")

            context = f"""
**Task**: {self.task_description}
**Spec Directory**: {self.spec_dir}
**Complexity**: SIMPLE (1-2 files expected)

This is a SIMPLE task. Create a minimal spec and implementation plan directly.
No research or extensive analysis needed.

Create:
1. A concise spec.md with just the essential sections
2. A simple implementation_plan.json with 1-2 chunks
"""
            success, output = await self._run_agent(
                "spec_quick.md",
                additional_context=context,
            )

            if success and spec_file.exists():
                # Create minimal plan if agent didn't
                if not plan_file.exists():
                    self._create_minimal_plan()

                print(f"✓ Quick spec created")
                return PhaseResult("quick_spec", True, [str(spec_file), str(plan_file)], [], attempt)

            errors.append(f"Attempt {attempt + 1}: Quick spec agent failed")

        return PhaseResult("quick_spec", False, [], errors, MAX_RETRIES)

    def _create_minimal_plan(self):
        """Create a minimal implementation plan for simple tasks."""
        plan = {
            "spec_name": self.spec_dir.name,
            "workflow_type": "simple",
            "total_phases": 1,
            "recommended_workers": 1,
            "phases": [
                {
                    "phase": 1,
                    "name": "Implementation",
                    "description": self.task_description or "Simple implementation",
                    "depends_on": [],
                    "chunks": [
                        {
                            "id": "chunk-1-1",
                            "description": self.task_description or "Implement the change",
                            "service": "main",
                            "status": "pending",
                            "files_to_create": [],
                            "files_to_modify": [],
                            "patterns_from": [],
                            "verification": {
                                "type": "manual",
                                "run": "Verify the change works as expected"
                            }
                        }
                    ]
                }
            ],
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "complexity": "simple",
                "estimated_sessions": 1,
            }
        }

        plan_file = self.spec_dir / "implementation_plan.json"
        with open(plan_file, "w") as f:
            json.dump(plan, f, indent=2)

    async def phase_research(self) -> PhaseResult:
        """Phase 3: Research external integrations and validate assumptions."""
        print("\n" + "=" * 60)
        print("  PHASE 3: INTEGRATION RESEARCH")
        print("=" * 60)

        research_file = self.spec_dir / "research.json"
        requirements_file = self.spec_dir / "requirements.json"

        # Check if research already exists
        if research_file.exists():
            print(f"✓ research.json already exists")
            return PhaseResult("research", True, [str(research_file)], [], 0)

        # Load requirements to understand what integrations need research
        if not requirements_file.exists():
            print("⚠ No requirements.json - skipping research phase")
            # Create empty research file
            with open(research_file, "w") as f:
                json.dump({
                    "integrations_researched": [],
                    "research_skipped": True,
                    "reason": "No requirements file available",
                    "created_at": datetime.now().isoformat(),
                }, f, indent=2)
            return PhaseResult("research", True, [str(research_file)], [], 0)

        # Run research agent
        errors = []
        for attempt in range(MAX_RETRIES):
            print(f"\nRunning research agent (attempt {attempt + 1})...")
            print("This agent will validate external integrations against documentation...")

            context = f"""
**Requirements File**: {requirements_file}
**Research Output**: {research_file}

Read the requirements.json to understand what integrations/libraries are needed.
Research each external dependency to validate:
- Correct package names
- Actual API patterns
- Configuration requirements
- Known issues or gotchas

Output your findings to research.json.
"""
            success, output = await self._run_agent(
                "spec_researcher.md",
                additional_context=context,
            )

            if success and research_file.exists():
                print(f"✓ Created research.json")
                return PhaseResult("research", True, [str(research_file)], [], attempt)

            # If agent didn't create file, create minimal one
            if success and not research_file.exists():
                print("⚠ Agent completed but no research.json created, creating minimal...")
                with open(research_file, "w") as f:
                    json.dump({
                        "integrations_researched": [],
                        "research_completed": True,
                        "agent_output": output[:2000] if output else "",
                        "created_at": datetime.now().isoformat(),
                    }, f, indent=2)
                return PhaseResult("research", True, [str(research_file)], [], attempt)

            errors.append(f"Attempt {attempt + 1}: Research agent failed")

        # Create minimal research file on failure
        with open(research_file, "w") as f:
            json.dump({
                "integrations_researched": [],
                "research_failed": True,
                "errors": errors,
                "created_at": datetime.now().isoformat(),
            }, f, indent=2)
        print("⚠ Created minimal research.json (agent failed)")
        return PhaseResult("research", True, [str(research_file)], errors, MAX_RETRIES)

    async def phase_context(self) -> PhaseResult:
        """Phase 4: Discover relevant files."""
        print("\n" + "=" * 60)
        print("  PHASE 4: CONTEXT DISCOVERY")
        print("=" * 60)

        context_file = self.spec_dir / "context.json"
        requirements_file = self.spec_dir / "requirements.json"

        if context_file.exists():
            print(f"✓ context.json already exists")
            return PhaseResult("context", True, [str(context_file)], [], 0)

        # Load requirements for task description
        task = self.task_description
        services = ""

        if requirements_file.exists():
            with open(requirements_file) as f:
                req = json.load(f)
                task = req.get("task_description", task)
                services = ",".join(req.get("services_involved", []))

        errors = []
        for attempt in range(MAX_RETRIES):
            print(f"Running context discovery (attempt {attempt + 1})...")

            args = [
                "--task", task or "unknown task",
                "--output", str(context_file),
            ]
            if services:
                args.extend(["--services", services])

            success, output = self._run_script("context.py", args)

            if success and context_file.exists():
                print(f"✓ Created context.json")
                return PhaseResult("context", True, [str(context_file)], [], attempt)

            errors.append(f"Attempt {attempt + 1}: {output}")
            print(f"✗ Attempt {attempt + 1} failed")

        # Create minimal context if script fails
        minimal_context = {
            "task_description": task or "unknown task",
            "scoped_services": services.split(",") if services else [],
            "files_to_modify": [],
            "files_to_reference": [],
            "created_at": datetime.now().isoformat(),
        }
        with open(context_file, "w") as f:
            json.dump(minimal_context, f, indent=2)
        print("✓ Created minimal context.json (script failed)")
        return PhaseResult("context", True, [str(context_file)], errors, MAX_RETRIES)

    async def phase_spec_writing(self) -> PhaseResult:
        """Phase 5: Write spec.md document."""
        print("\n" + "=" * 60)
        print("  PHASE 5: SPEC DOCUMENT CREATION")
        print("=" * 60)

        spec_file = self.spec_dir / "spec.md"

        if spec_file.exists():
            # Validate existing spec
            result = self.validator.validate_spec_document()
            if result.valid:
                print(f"✓ spec.md already exists and is valid")
                return PhaseResult("spec_writing", True, [str(spec_file)], [], 0)
            print(f"⚠ spec.md exists but has issues, regenerating...")

        errors = []
        for attempt in range(MAX_RETRIES):
            print(f"\nRunning spec writer (attempt {attempt + 1})...")

            success, output = await self._run_agent("spec_writer.md")

            if success and spec_file.exists():
                # Validate
                result = self.validator.validate_spec_document()
                if result.valid:
                    print(f"✓ Created valid spec.md")
                    return PhaseResult("spec_writing", True, [str(spec_file)], [], attempt)
                else:
                    errors.append(f"Attempt {attempt + 1}: Spec invalid - {result.errors}")
                    print(f"✗ Spec created but invalid: {result.errors}")
            else:
                errors.append(f"Attempt {attempt + 1}: Agent did not create spec.md")

        return PhaseResult("spec_writing", False, [], errors, MAX_RETRIES)

    async def phase_self_critique(self) -> PhaseResult:
        """Phase 6: Self-critique the spec using extended thinking."""
        print("\n" + "=" * 60)
        print("  PHASE 6: SPEC SELF-CRITIQUE (ULTRATHINK)")
        print("=" * 60)

        spec_file = self.spec_dir / "spec.md"
        research_file = self.spec_dir / "research.json"
        critique_file = self.spec_dir / "critique_report.json"

        if not spec_file.exists():
            print("✗ No spec.md to critique")
            return PhaseResult("self_critique", False, [], ["spec.md does not exist"], 0)

        # Check if critique already done
        if critique_file.exists():
            with open(critique_file) as f:
                critique = json.load(f)
                if critique.get("issues_fixed", False) or critique.get("no_issues_found", False):
                    print(f"✓ Self-critique already completed")
                    return PhaseResult("self_critique", True, [str(critique_file)], [], 0)

        errors = []
        for attempt in range(MAX_RETRIES):
            print(f"\nRunning self-critique agent (attempt {attempt + 1})...")
            print("Using extended thinking to find issues in the spec...")

            context = f"""
**Spec File**: {spec_file}
**Research File**: {research_file}
**Critique Output**: {critique_file}

Use EXTENDED THINKING (ultrathink) to deeply analyze the spec.md:

1. **Technical Accuracy**: Do code examples match the research findings?
2. **Completeness**: Are all requirements covered? Edge cases handled?
3. **Consistency**: Do package names, APIs, and patterns match throughout?
4. **Feasibility**: Is the implementation approach realistic?

For each issue found:
- Fix it directly in spec.md
- Document what was fixed in critique_report.json

Output critique_report.json with:
{{
  "issues_found": [...],
  "issues_fixed": true/false,
  "no_issues_found": true/false,
  "critique_summary": "..."
}}
"""
            success, output = await self._run_agent(
                "spec_critic.md",
                additional_context=context,
            )

            if success:
                # Create critique report if agent didn't
                if not critique_file.exists():
                    with open(critique_file, "w") as f:
                        json.dump({
                            "issues_found": [],
                            "no_issues_found": True,
                            "critique_summary": "Agent completed without explicit issues",
                            "created_at": datetime.now().isoformat(),
                        }, f, indent=2)

                # Re-validate spec after critique
                result = self.validator.validate_spec_document()
                if result.valid:
                    print(f"✓ Self-critique completed, spec is valid")
                    return PhaseResult("self_critique", True, [str(critique_file)], [], attempt)
                else:
                    print(f"⚠ Spec invalid after critique: {result.errors}")
                    errors.append(f"Attempt {attempt + 1}: Spec still invalid after critique")
            else:
                errors.append(f"Attempt {attempt + 1}: Critique agent failed")

        # Create minimal critique report on failure
        with open(critique_file, "w") as f:
            json.dump({
                "issues_found": [],
                "critique_failed": True,
                "errors": errors,
                "created_at": datetime.now().isoformat(),
            }, f, indent=2)
        print("⚠ Self-critique failed, continuing with existing spec")
        return PhaseResult("self_critique", True, [str(critique_file)], errors, MAX_RETRIES)

    async def phase_planning(self) -> PhaseResult:
        """Phase 7: Create implementation plan."""
        print("\n" + "=" * 60)
        print("  PHASE 7: IMPLEMENTATION PLANNING")
        print("=" * 60)

        plan_file = self.spec_dir / "implementation_plan.json"

        if plan_file.exists():
            # Validate existing plan
            result = self.validator.validate_implementation_plan()
            if result.valid:
                print(f"✓ implementation_plan.json already exists and is valid")
                return PhaseResult("planning", True, [str(plan_file)], [], 0)
            print(f"⚠ Plan exists but invalid, regenerating...")

        errors = []

        # Try Python script first (deterministic)
        print("Trying planner.py (deterministic)...")
        success, output = self._run_script(
            "planner.py",
            ["--spec-dir", str(self.spec_dir)]
        )

        if success and plan_file.exists():
            # Validate
            result = self.validator.validate_implementation_plan()
            if result.valid:
                print(f"✓ Created valid implementation_plan.json via script")
                return PhaseResult("planning", True, [str(plan_file)], [], 0)
            else:
                print(f"⚠ Script output invalid, trying auto-fix...")
                if auto_fix_plan(self.spec_dir):
                    result = self.validator.validate_implementation_plan()
                    if result.valid:
                        print(f"✓ Auto-fixed implementation_plan.json")
                        return PhaseResult("planning", True, [str(plan_file)], [], 0)

                errors.append(f"Script output invalid: {result.errors}")

        # Fall back to agent
        print("\nFalling back to planner agent...")
        for attempt in range(MAX_RETRIES):
            print(f"\nRunning planner agent (attempt {attempt + 1})...")

            success, output = await self._run_agent("planner.md")

            if success and plan_file.exists():
                # Validate
                result = self.validator.validate_implementation_plan()
                if result.valid:
                    print(f"✓ Created valid implementation_plan.json via agent")
                    return PhaseResult("planning", True, [str(plan_file)], [], attempt)
                else:
                    # Try auto-fix
                    if auto_fix_plan(self.spec_dir):
                        result = self.validator.validate_implementation_plan()
                        if result.valid:
                            print(f"✓ Auto-fixed implementation_plan.json")
                            return PhaseResult("planning", True, [str(plan_file)], [], attempt)

                    errors.append(f"Agent attempt {attempt + 1}: {result.errors}")
                    print(f"✗ Plan created but invalid")
            else:
                errors.append(f"Agent attempt {attempt + 1}: Did not create plan file")

        return PhaseResult("planning", False, [], errors, MAX_RETRIES)

    async def phase_validation(self) -> PhaseResult:
        """Phase 8: Final validation."""
        print("\n" + "=" * 60)
        print("  PHASE 8: FINAL VALIDATION")
        print("=" * 60)

        results = self.validator.validate_all()
        all_valid = all(r.valid for r in results)

        for result in results:
            status = "✓" if result.valid else "✗"
            print(f"{status} {result.checkpoint}: {'PASS' if result.valid else 'FAIL'}")
            for err in result.errors:
                print(f"    Error: {err}")

        if all_valid:
            print("\n✓ All validation checks passed")
            return PhaseResult("validation", True, [], [], 0)
        else:
            errors = [
                f"{r.checkpoint}: {err}"
                for r in results
                for err in r.errors
            ]
            return PhaseResult("validation", False, [], errors, 0)

    # === Main Orchestration ===

    async def run(self, interactive: bool = True) -> bool:
        """Run the spec creation process with dynamic phase selection."""
        print("\n" + "=" * 60)
        print("  SPEC CREATION ORCHESTRATOR")
        print("=" * 60)
        print(f"\nSpec Directory: {self.spec_dir}")
        print(f"Project: {self.project_dir}")
        if self.task_description:
            print(f"Task: {self.task_description}")
        print()

        # Phase 0: Always run complexity assessment first
        result = await self.phase_complexity_assessment()
        if not result.success:
            print("✗ Complexity assessment failed")
            return False

        results = [result]

        # Map of all available phases
        all_phases = {
            "discovery": lambda: self.phase_discovery(),
            "requirements": lambda: self.phase_requirements(interactive),
            "research": lambda: self.phase_research(),
            "context": lambda: self.phase_context(),
            "spec_writing": lambda: self.phase_spec_writing(),
            "self_critique": lambda: self.phase_self_critique(),
            "planning": lambda: self.phase_planning(),
            "validation": lambda: self.phase_validation(),
            "quick_spec": lambda: self.phase_quick_spec(),
        }

        # Get phases to run based on complexity
        phases_to_run = self.assessment.phases_to_run()

        print(f"\n  Running {self.assessment.complexity.value.upper()} workflow ({len(phases_to_run)} phases)")
        print()

        for phase_name in phases_to_run:
            if phase_name not in all_phases:
                print(f"⚠ Unknown phase: {phase_name}, skipping")
                continue

            phase_fn = all_phases[phase_name]
            result = await phase_fn()
            results.append(result)

            if not result.success:
                print(f"\n✗ Phase '{phase_name}' failed after {result.retries} retries")
                print("Errors:")
                for err in result.errors:
                    print(f"  - {err}")
                print(f"\nSpec creation incomplete. Fix errors and retry.")
                return False

        # Summary
        print("\n" + "=" * 60)
        print("  SPEC CREATION COMPLETE")
        print("=" * 60)
        print(f"\nComplexity: {self.assessment.complexity.value.upper()}")
        print(f"Phases run: {len(phases_to_run)}")
        print(f"\nSpec saved to: {self.spec_dir}")
        print("\nFiles created:")
        for result in results:
            for f in result.output_files:
                print(f"  - {Path(f).name}")

        print(f"\nTo start the build:")
        print(f"  python auto-build/run.py --spec {self.spec_dir.name}")

        return True


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Dynamic spec creation with complexity-based phase selection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Complexity Tiers:
  simple    - 3 phases: Discovery → Quick Spec → Validate (1-2 files)
  standard  - 6 phases: Discovery → Requirements → Context → Spec → Plan → Validate
  complex   - 8 phases: Full pipeline with research and self-critique

Examples:
  # Simple UI fix (auto-detected as simple)
  python spec_runner.py --task "Fix button color in Header component"

  # Force simple mode
  python spec_runner.py --task "Update text" --complexity simple

  # Complex integration (auto-detected)
  python spec_runner.py --task "Add Graphiti memory integration with FalkorDB"

  # Interactive mode
  python spec_runner.py --interactive
        """
    )
    parser.add_argument(
        "--task",
        type=str,
        help="Task description (what to build)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode (gather requirements from user)",
    )
    parser.add_argument(
        "--continue",
        dest="continue_spec",
        type=str,
        help="Continue an existing spec",
    )
    parser.add_argument(
        "--complexity",
        type=str,
        choices=["simple", "standard", "complex"],
        help="Override automatic complexity detection",
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path.cwd(),
        help="Project directory (default: current directory)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="claude-sonnet-4-20250514",
        help="Model to use for agent phases",
    )

    args = parser.parse_args()

    # Find project root (look for auto-build folder)
    project_dir = args.project_dir
    if not (project_dir / "auto-build").exists():
        # Try parent directories
        for parent in project_dir.parents:
            if (parent / "auto-build").exists():
                project_dir = parent
                break

    orchestrator = SpecOrchestrator(
        project_dir=project_dir,
        task_description=args.task,
        spec_name=args.continue_spec,
        model=args.model,
        complexity_override=args.complexity,
    )

    try:
        success = asyncio.run(orchestrator.run(interactive=args.interactive or not args.task))
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nSpec creation interrupted.")
        print(f"To continue: python auto-build/spec_runner.py --continue {orchestrator.spec_dir.name}")
        sys.exit(1)


if __name__ == "__main__":
    main()
