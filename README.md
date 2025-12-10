# Auto-Build Framework

A production-ready framework for autonomous multi-session AI coding. Build complete applications or add features to existing projects through coordinated AI agent sessions.

## What It Does

Auto-Build uses a **multi-agent pattern** to build software autonomously:

### Spec Creation Pipeline (8 phases)
1. **Discovery** - Analyzes project structure
2. **Requirements Gatherer** - Collects user requirements interactively
3. **Research Agent** - Validates external integrations against documentation
4. **Context Discovery** - Finds relevant files in codebase
5. **Spec Writer** - Creates comprehensive spec.md
6. **Spec Critic** - Uses ultrathink to find and fix issues before implementation
7. **Planner** - Creates chunk-based implementation plan
8. **Validation** - Ensures all outputs are valid

### Implementation Pipeline
1. **Planner Agent** (Session 1) - Analyzes spec, creates chunk-based implementation plan
2. **Coder Agent** (Sessions 2+) - Implements chunks one-by-one with verification
3. **QA Reviewer Agent** - Validates all acceptance criteria before sign-off
4. **QA Fixer Agent** - Fixes issues found by QA in a self-validating loop

Each session runs with a fresh context window. Progress is tracked via `implementation_plan.json` and Git commits.

## Quick Start

### Prerequisites

- Python 3.8+
- Claude Code CLI (`npm install -g @anthropic-ai/claude-code`)

### Setup

**Step 1:** Copy the `auto-build` folder into your project

```bash
# Copy the auto-build folder to your project root
cp -r auto-build /path/to/your/project/
```

**Step 2:** Set up Python environment

```bash
cd your-project
cd auto-build

# Using uv (recommended)
uv venv && uv pip install -r requirements.txt

# Or using standard Python
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

**Step 3:** Configure environment

```bash
cp .env.example .env

# Get your OAuth token
claude setup-token

# Add the token to .env
# CLAUDE_CODE_OAUTH_TOKEN=your-token-here
```

**Step 4:** Create a spec using the orchestrator

```bash
# Activate the virtual environment
source auto-build/.venv/bin/activate

# Create a spec interactively
python auto-build/spec_runner.py --interactive

# Or with a task description
python auto-build/spec_runner.py --task "Add user authentication with OAuth"
```

The spec orchestrator will:
1. Analyze your project structure
2. Gather requirements interactively
3. **Research external integrations** against documentation
4. Discover relevant codebase context
5. Write the specification
6. **Self-critique using ultrathink** to find and fix issues
7. Generate an implementation plan
8. Validate all outputs

**Step 5:** Run the autonomous build

```bash
python auto-build/run.py --spec 001
```

### Managing Specs

```bash
# List all specs and their status
python auto-build/run.py --list

# Run a specific spec
python auto-build/run.py --spec 001
python auto-build/run.py --spec 001-feature-name

# Run with parallel workers (2-3x speedup for independent phases)
python auto-build/run.py --spec 001 --parallel 2
python auto-build/run.py --spec 001 --parallel 3

# Limit iterations for testing
python auto-build/run.py --spec 001 --max-iterations 5
```

### QA Validation

After all chunks are complete, QA validation runs automatically:

```bash
# QA runs automatically after build completes
# To skip automatic QA:
python auto-build/run.py --spec 001 --skip-qa

# Run QA validation manually on a completed build
python auto-build/run.py --spec 001 --qa

# Check QA status
python auto-build/run.py --spec 001 --qa-status
```

The QA validation loop:
1. **QA Reviewer** checks all acceptance criteria (unit tests, integration tests, E2E, browser verification, database migrations)
2. If issues found → creates `QA_FIX_REQUEST.md`
3. **QA Fixer** applies fixes
4. Loop repeats until approved (up to 50 iterations)
5. Final sign-off recorded in `implementation_plan.json`

### Spec Creation Pipeline (Dynamic Complexity)

The `spec_runner.py` orchestrator **automatically assesses task complexity** and adapts the number of phases accordingly:

```bash
# Simple task (auto-detected) - runs 3 phases
python auto-build/spec_runner.py --task "Fix button color in Header"

# Complex task (auto-detected) - runs 8 phases
python auto-build/spec_runner.py --task "Add Graphiti memory integration with FalkorDB"

# Force a specific complexity level
python auto-build/spec_runner.py --task "Update text" --complexity simple

# Interactive mode
python auto-build/spec_runner.py --interactive

# Continue an interrupted spec
python auto-build/spec_runner.py --continue 001-feature
```

**Complexity Tiers:**

| Tier | Phases | When Used |
|------|--------|-----------|
| **SIMPLE** | 3 | 1-2 files, single service, no integrations (UI fixes, text changes) |
| **STANDARD** | 6 | 3-10 files, 1-2 services, minimal integrations (features, bug fixes) |
| **COMPLEX** | 8 | 10+ files, multiple services, external integrations (integrations, migrations) |

**Phase Matrix:**

| Phase | Simple | Standard | Complex |
|-------|--------|----------|---------|
| Discovery | ✓ | ✓ | ✓ |
| Requirements | - | ✓ | ✓ |
| **Research** | - | - | ✓ |
| Context | - | ✓ | ✓ |
| Spec Writing | Quick | Full | Full |
| **Self-Critique** | - | - | ✓ |
| Planning | Auto | ✓ | ✓ |
| Validation | ✓ | ✓ | ✓ |

**Complexity Detection Signals:**
- Keywords: "fix", "typo", "color" → Simple | "integrate", "migrate", "oauth" → Complex
- External integrations detected (redis, postgres, graphiti, etc.)
- Number of files/services mentioned
- Infrastructure changes (docker, deploy, schema)

**Manual validation:**
```bash
python auto-build/validate_spec.py --spec-dir auto-build/specs/001-feature --checkpoint all
```

### Isolated Worktrees (Safe by Default)

Auto-Build uses Git worktrees to keep your work completely safe. All AI-generated code is built in a separate workspace (`.worktrees/auto-build/`) - your current files are never touched until you explicitly merge.

**How it works:**

1. When you run auto-build, it creates an isolated workspace
2. All coding happens in `.worktrees/auto-build/` on its own branch
3. You can `cd` into the worktree to test the feature before accepting
4. Only when you're satisfied, merge the changes into your project

**After a build completes, you can:**

```bash
# Test the feature in the isolated workspace
cd .worktrees/auto-build/
npm run dev  # or your project's run command

# See what was changed
python auto-build/run.py --spec 001 --review

# Add changes to your project
python auto-build/run.py --spec 001 --merge

# Discard if you don't like it (requires confirmation)
python auto-build/run.py --spec 001 --discard
```

**Key benefits:**

- **Safety**: Your uncommitted work is protected - auto-build won't touch it
- **Testability**: Run and test the feature before committing to it
- **Easy rollback**: Don't like it? Just discard the worktree
- **Parallel-safe**: Multiple workers can build without conflicts

If you have uncommitted changes, auto-build automatically uses isolated mode. With a clean working directory, you can choose between isolated (recommended) or direct mode.

### Interactive Controls

While the agent is running, you can:

```bash
# Pause and optionally add instructions
Ctrl+C (once)
# You'll be prompted to add instructions for the agent
# The agent will read these instructions when you resume

# Exit immediately without prompting
Ctrl+C (twice)
# Press Ctrl+C again during the prompt to exit
```

**Alternative (file-based):**
```bash
# Create PAUSE file to pause after current session
touch auto-build/specs/001-name/PAUSE

# Manually edit instructions file
echo "Focus on fixing the login bug first" > auto-build/specs/001-name/HUMAN_INPUT.md
```

## Project Structure

```
your-project/
├── .worktrees/              # Created during build (git-ignored)
│   └── auto-build/          # Isolated workspace for AI coding
├── auto-build/
│   ├── run.py               # Build entry point
│   ├── spec_runner.py       # Spec creation orchestrator (8-phase pipeline)
│   ├── validate_spec.py     # Spec validation with JSON schemas
│   ├── agent.py             # Session orchestration
│   ├── planner.py           # Deterministic implementation planner
│   ├── worktree.py          # Git worktree management
│   ├── workspace.py         # Workspace selection UI
│   ├── coordinator.py       # Parallel execution coordinator
│   ├── qa_loop.py           # QA validation loop
│   ├── client.py            # Claude SDK configuration
│   ├── spec_contract.json   # Spec creation contract (required outputs)
│   ├── prompts/
│   │   ├── planner.md       # Session 1 - creates implementation plan
│   │   ├── coder.md         # Sessions 2+ - implements chunks
│   │   ├── spec_gatherer.md # Requirements gathering agent
│   │   ├── spec_researcher.md # External integration research agent
│   │   ├── spec_writer.md   # Spec document creation agent
│   │   ├── spec_critic.md   # Self-critique agent (ultrathink)
│   │   ├── qa_reviewer.md   # QA validation agent
│   │   └── qa_fixer.md      # QA fix agent
│   └── specs/
│       └── 001-feature/     # Each spec in its own folder
│           ├── spec.md
│           ├── requirements.json     # User requirements (structured)
│           ├── research.json         # External integration research
│           ├── context.json          # Codebase context
│           ├── critique_report.json  # Self-critique findings
│           ├── implementation_plan.json
│           ├── qa_report.md          # QA validation report
│           └── QA_FIX_REQUEST.md     # Issues to fix (if rejected)
└── [your project files]
```

## Key Features

- **Domain Agnostic**: Works for any software project (web apps, APIs, CLIs, etc.)
- **Multi-Session**: Unlimited sessions, each with fresh context
- **Research-First Specs**: External integrations validated against documentation before implementation
- **Self-Critique**: Specs are critiqued using ultrathink to find issues before coding begins
- **Parallel Execution**: 2-3x speedup with multiple workers on independent phases
- **Isolated Worktrees**: Build in a separate workspace - your current work is never touched
- **Self-Verifying**: Agents test their work with browser automation before marking complete
- **QA Validation Loop**: Automated QA agent validates all acceptance criteria before sign-off
- **Self-Healing**: QA finds issues → Fixer agent resolves → QA re-validates (up to 50 iterations)
- **8-Phase Spec Pipeline**: Discovery → Requirements → Research → Context → Spec → Critique → Plan → Validate
- **Fix Bugs Immediately**: Agents fix discovered bugs in the same session, not later
- **Defense-in-Depth Security**: OS sandbox, filesystem restrictions, command allowlist
- **Secret Scanning**: Automatic pre-commit scanning blocks secrets with actionable fix instructions
- **Human Intervention**: Pause, add instructions, or stop at any time
- **Multiple Specs**: Track and run multiple specifications independently

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CLAUDE_CODE_OAUTH_TOKEN` | Yes | OAuth token from `claude setup-token` |
| `AUTO_BUILD_MODEL` | No | Model override (default: claude-opus-4-5-20251101) |

## Documentation

For parallel execution details:
- How parallelism works
- Performance analysis
- Best practices
- Troubleshooting

See [auto-build/PARALLEL_EXECUTION.md](auto-build/PARALLEL_EXECUTION.md)

## Acknowledgments

This framework was inspired by Anthropic's [Autonomous Coding Agent](https://github.com/anthropics/claude-quickstarts/tree/main/autonomous-coding). Thank you to the Anthropic team for their innovative work on autonomous coding systems.

## License

MIT License
