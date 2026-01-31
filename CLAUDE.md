# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Auto Claude is a multi-agent autonomous coding framework that builds software through coordinated AI agent sessions. It uses the Claude Agent SDK to run agents in isolated workspaces with security controls.

**CRITICAL: All AI interactions use the Claude Agent SDK (`claude-agent-sdk` package), NOT the Anthropic API directly.**

## Project Structure

```
autonomous-coding/
├── apps/
│   ├── backend/           # Python backend/CLI - ALL agent logic lives here
│   │   ├── core/          # Client, auth, security
│   │   ├── agents/        # Agent implementations
│   │   ├── spec_agents/   # Spec creation agents
│   │   ├── integrations/  # Graphiti, Linear, GitHub
│   │   └── prompts/       # Agent system prompts
│   └── frontend/          # Electron desktop UI
├── guides/                # Documentation
├── tests/                 # Test suite
└── scripts/               # Build and utility scripts
```

**When working with AI/LLM code:**
- Look in `apps/backend/core/client.py` for the Claude SDK client setup
- Reference `apps/backend/agents/` for working agent implementations
- Check `apps/backend/spec_agents/` for spec creation agent examples
- NEVER use `anthropic.Anthropic()` directly - always use `create_client()` from `core.client`

**Frontend (Electron Desktop App):**
- Built with Electron, React, TypeScript
- AI agents can perform E2E testing using the Electron MCP server
- When bug fixing or implementing features, use the Electron MCP server for automated testing
- See "End-to-End Testing" section below for details

## Commands

### Setup

**Requirements:**
- Python 3.12+ (required for backend)
- Node.js (for frontend)

```bash
# Install all dependencies from root
npm run install:all

# Or install separately:
# Backend (from apps/backend/)
cd apps/backend && uv venv && uv pip install -r requirements.txt

# Frontend (from apps/frontend/)
cd apps/frontend && npm install

# Authenticate (token auto-saved to Keychain)
claude
# Then type: /login
# Press Enter to open browser and complete OAuth
```

### Creating and Running Specs
```bash
cd apps/backend

# Create a spec interactively
python spec_runner.py --interactive

# Create spec from task description
python spec_runner.py --task "Add user authentication"

# Force complexity level (simple/standard/complex)
python spec_runner.py --task "Fix button" --complexity simple

# Run autonomous build
python run.py --spec 001

# List all specs
python run.py --list
```

### Workspace Management
```bash
cd apps/backend

# Review changes in isolated worktree
python run.py --spec 001 --review

# Merge completed build into project
python run.py --spec 001 --merge

# Discard build
python run.py --spec 001 --discard
```

### QA Validation
```bash
cd apps/backend

# Run QA manually
python run.py --spec 001 --qa

# Check QA status
python run.py --spec 001 --qa-status
```

### Testing
```bash
# Install test dependencies (required first time)
cd apps/backend && uv pip install -r ../../tests/requirements-test.txt

# Run all tests (use virtual environment pytest)
apps/backend/.venv/bin/pytest tests/ -v

# Run single test file
apps/backend/.venv/bin/pytest tests/test_security.py -v

# Run specific test
apps/backend/.venv/bin/pytest tests/test_security.py::test_bash_command_validation -v

# Skip slow tests
apps/backend/.venv/bin/pytest tests/ -m "not slow"

# Or from root
npm run test:backend
```

### Spec Validation
```bash
python apps/backend/validate_spec.py --spec-dir apps/backend/specs/001-feature --checkpoint all
```

### Releases
```bash
# 1. Bump version on your branch (creates commit, no tag)
node scripts/bump-version.js patch   # 2.8.0 -> 2.8.1
node scripts/bump-version.js minor   # 2.8.0 -> 2.9.0
node scripts/bump-version.js major   # 2.8.0 -> 3.0.0

# 2. Push and create PR to main
git push origin your-branch
gh pr create --base main

# 3. Merge PR → GitHub Actions automatically:
#    - Creates tag
#    - Builds all platforms
#    - Creates release with changelog
#    - Updates README
```

See [RELEASE.md](RELEASE.md) for detailed release process documentation.

## Architecture

### Core Pipeline

**Spec Creation (spec_runner.py)** - Dynamic 3-8 phase pipeline based on task complexity:
- SIMPLE (3 phases): Discovery → Quick Spec → Validate
- STANDARD (6-7 phases): Discovery → Requirements → [Research] → Context → Spec → Plan → Validate
- COMPLEX (8 phases): Full pipeline with Research and Self-Critique phases

**Implementation (run.py → agent.py)** - Multi-session build:
1. Planner Agent creates subtask-based implementation plan
2. Coder Agent implements subtasks (can spawn subagents for parallel work)
3. QA Reviewer validates acceptance criteria (can perform E2E testing via Electron MCP for frontend changes)
4. QA Fixer resolves issues in a loop (with E2E testing to verify fixes)

### Key Components (apps/backend/)

**Core Infrastructure:**
- **core/client.py** - Claude Agent SDK client factory with security hooks and tool permissions
- **core/security.py** - Dynamic command allowlisting based on detected project stack
- **core/auth.py** - OAuth token management for Claude SDK authentication
- **agents/** - Agent implementations (planner, coder, qa_reviewer, qa_fixer)
- **spec_agents/** - Spec creation agents (gatherer, researcher, writer, critic)

**Memory & Context:**
- **integrations/graphiti/** - Graphiti memory system (mandatory)
  - `queries_pkg/graphiti.py` - Main GraphitiMemory class
  - `queries_pkg/client.py` - LadybugDB client wrapper
  - `queries_pkg/queries.py` - Graph query operations
  - `queries_pkg/search.py` - Semantic search logic
  - `queries_pkg/schema.py` - Graph schema definitions
- **graphiti_config.py** - Configuration and validation for Graphiti integration
- **graphiti_providers.py** - Multi-provider factory (OpenAI, Anthropic, Azure, Ollama, Google AI)
- **agents/memory_manager.py** - Session memory orchestration

**Workspace & Security:**
- **cli/worktree.py** - Git worktree isolation for safe feature development
- **context/project_analyzer.py** - Project stack detection for dynamic tooling
- **auto_claude_tools.py** - Custom MCP tools integration

**Integrations:**
- **linear_updater.py** - Optional Linear integration for progress tracking
- **runners/github/** - GitHub Issues & PRs automation
- **Electron MCP** - E2E testing integration for QA agents (Chrome DevTools Protocol)
  - Enabled with `ELECTRON_MCP_ENABLED=true` in `.env`
  - Allows QA agents to interact with running Electron app
  - See "End-to-End Testing" section for details

### Agent Prompts (apps/backend/prompts/)

| Prompt | Purpose |
|--------|---------|
| planner.md | Creates implementation plan with subtasks |
| coder.md | Implements individual subtasks |
| coder_recovery.md | Recovers from stuck/failed subtasks |
| qa_reviewer.md | Validates acceptance criteria |
| qa_fixer.md | Fixes QA-reported issues |
| spec_gatherer.md | Collects user requirements |
| spec_researcher.md | Validates external integrations |
| spec_writer.md | Creates spec.md document |
| spec_critic.md | Self-critique using ultrathink |
| complexity_assessor.md | AI-based complexity assessment |

### Spec Directory Structure

Each spec in `.auto-claude/specs/XXX-name/` contains:
- `spec.md` - Feature specification
- `requirements.json` - Structured user requirements
- `context.json` - Discovered codebase context
- `implementation_plan.json` - Subtask-based plan with status tracking
- `qa_report.md` - QA validation results
- `QA_FIX_REQUEST.md` - Issues to fix (when rejected)

### Branching & Worktree Strategy

Auto Claude uses git worktrees for isolated builds. All branches stay LOCAL until user explicitly pushes:

```
main (user's branch)
└── auto-claude/{spec-name}  ← spec branch (isolated worktree)
```

**Key principles:**
- ONE branch per spec (`auto-claude/{spec-name}`)
- Parallel work uses subagents (agent decides when to spawn)
- NO automatic pushes to GitHub - user controls when to push
- User reviews in spec worktree (`.worktrees/{spec-name}/`)
- Final merge: spec branch → main (after user approval)

**Workflow:**
1. Build runs in isolated worktree on spec branch
2. Agent implements subtasks (can spawn subagents for parallel work)
3. User tests feature in `.worktrees/{spec-name}/`
4. User runs `--merge` to add to their project
5. User pushes to remote when ready

### Contributing to Upstream

**CRITICAL: When submitting PRs to AndyMik90/Auto-Claude, always target the `develop` branch, NOT `main`.**

**Correct workflow for contributions:**
1. Fetch upstream: `git fetch upstream`
2. Create feature branch from upstream/develop: `git checkout -b fix/my-fix upstream/develop`
3. Make changes and commit with sign-off: `git commit -s -m "fix: description"`
4. Push to your fork: `git push origin fix/my-fix`
5. Create PR targeting `develop`: `gh pr create --repo AndyMik90/Auto-Claude --base develop`

**Verify before PR:**
```bash
# Ensure only your commits are included
git log --oneline upstream/develop..HEAD
```

## Test Project for RDR Integration

**CV Project Path:** `C:\Users\topem\Desktop\CV Project`

This project is used for testing the RDR (Recover, Debug, Resend) system with MCP integration. When RDR detects tasks needing intervention in this project, it automatically prompts Claude Code via MCP to fix them.

## RDR (Recover, Debug, Resend) System

**CRITICAL: Claude Code must automatically recover from JSON errors and resume stuck tasks without manual intervention.**

### What RDR Does

RDR is Auto-Claude's automatic recovery system that:
1. **Monitors tasks** for JSON errors, incomplete work, and failures
2. **Auto-fixes JSON** errors in `implementation_plan.json` files
3. **Auto-resumes** stuck tasks by updating their status
4. **Sends recovery prompts** to Claude Code when needed via MCP
5. **Invokes Auto-Claude MCP tools** automatically when Claude Code receives RDR notifications

### RDR Recovery Priority System

**Priority 1 (95%): Task Recovery - Auto-Resume**
- Tasks with incomplete subtasks → Set `status: "start_requested"` to resume
- File watcher auto-detects changes within 2-3 seconds
- **No MCP tools needed** - just file writes

**Priority 2 (4%): Debug & Fix**
- Tasks with errors → Analyze logs, fix root cause, resume

**Priority 3 (<1%): Auto-fix JSON Errors**
- Empty/malformed JSON files → Create minimal valid JSON:
  ```json
  {
    "feature": "Auto-recovery task",
    "description": "Task recovered by RDR system",
    "created_at": "2026-01-31T00:00:00Z",
    "updated_at": "2026-01-31T00:00:00Z",
    "status": "start_requested",
    "phases": []
  }
  ```

**Priority 4 (RARE): Manual Edits**
- Only when auto-fix fails

**Priority 5 (LAST RESORT): Delete & Recreate**
- Only for corrupted worktrees

### How to Recover Tasks

**For JSON Errors (empty/malformed `implementation_plan.json`):**

```bash
# Main project
cd "/path/to/project/.auto-claude/specs"
for task in 071-marko 079-alpine-htmx-knockout 080-svelte-aurelia; do
  cat > "$task/implementation_plan.json" << 'EOF'
{
  "feature": "Auto-recovery task",
  "description": "Task recovered by RDR system",
  "created_at": "2026-01-31T00:00:00Z",
  "updated_at": "2026-01-31T00:00:00Z",
  "status": "start_requested",
  "phases": []
}
EOF
done

# Worktrees (IMPORTANT: Auto-Claude prefers worktree versions!)
cd "/path/to/project/.auto-claude/worktrees/tasks"
for task in 071-marko 079-alpine-htmx-knockout 080-svelte-aurelia; do
  if [ -d "$task" ]; then
    cat > "$task/.auto-claude/specs/$task/implementation_plan.json" << 'EOF'
{
  "feature": "Auto-recovery task",
  "description": "Task recovered by RDR system",
  "created_at": "2026-01-31T00:00:00Z",
  "updated_at": "2026-01-31T00:00:00Z",
  "status": "start_requested",
  "phases": []
}
EOF
  fi
done
```

**For Stuck Tasks (plan_review, human_review status):**

```bash
# Resume incomplete tasks by changing status to start_requested
cd "/path/to/project/.auto-claude/specs"
for task in 073-qwik 077-shadow-component-libs 081-ats-major; do
  sed -i 's/"status": "plan_review"/"status": "start_requested"/' "$task/implementation_plan.json"
done

# Do the same for worktrees
cd "/path/to/project/.auto-claude/worktrees/tasks"
for task in 073-qwik 077-shadow-component-libs 081-ats-major; do
  if [ -d "$task" ]; then
    sed -i 's/"status": "plan_review"/"status": "start_requested"/' "$task/.auto-claude/specs/$task/implementation_plan.json"
  fi
done
```

### RDR Troubleshooting

**RDR not sending messages:**
- Check startup logs for module resolution errors:
  ```
  [RDR] Failed to load window-manager (Windows-specific)
  [RDR] Failed to load MCP monitor
  ```
- If you see these errors, the RDR module imports are broken (fixed in commit 524f5b5c)

**Tasks still showing errors after recovery:**
- Verify BOTH main and worktree JSON files are fixed
- Auto-Claude prefers worktree versions over main project versions
- Check file watcher is running: `[FileWatcher] Specs watcher READY`

**RDR sending messages but not processing:**
- Check if Claude Code is busy: `[RDR] BUSY: Claude Code is processing...`
- RDR waits for idle state before sending messages
- Verify MCP monitor is loaded: `[RDR] BUSY: Claude Code is busy (MCP connection active)`

### When to Use RDR

**ALWAYS use RDR for:**
- JSON parse errors in `implementation_plan.json`
- Tasks stuck in `plan_review` or `human_review`
- Tasks showing `errors` status with no progress
- Tasks with 0 phases or incomplete subtasks

**NEVER manually edit tasks** unless RDR auto-fix fails multiple times.

### RDR → MCP Integration (Automatic Recovery)

**CRITICAL: When Claude Code receives RDR notifications, it should automatically invoke the `/auto-claude-mcp` skill to recover tasks.**

**RDR Notification Format:**
```
[Auto-Claude RDR] Tasks needing intervention:

## 071-marko: Task Name
Status: plan_review | Exit: none
Subtasks: 18/20 complete
Pending: subtask details...

Use MCP tools: get_task_error_details, submit_task_fix_request, process_rdr_batch
```

**Automatic Response Flow:**
1. **Claude Code receives RDR notification** via MCP message
2. **Invoke `/auto-claude-mcp` skill** automatically
3. **Determine project path** from context or ask user
4. **Apply Priority 1 recovery** (auto-resume incomplete tasks):
   ```bash
   cd "/path/to/project/.auto-claude/specs"
   for task in 071-marko 073-qwik; do
     sed -i 's/"status": "plan_review"/"status": "start_requested"/' "$task/implementation_plan.json"
   done
   ```
5. **Apply Priority 3 recovery** (fix JSON errors):
   ```bash
   for task in 082-ats-other 083-rte-major; do
     cat > "$task/implementation_plan.json" << 'EOF'
   {
     "feature": "Auto-recovery task",
     "description": "Task recovered by RDR system",
     "status": "start_requested",
     "phases": []
   }
   EOF
   done
   ```
6. **Confirm recovery** to user

**Project Path Resolution:**
- CV Project: `C:\Users\topem\Desktop\CV Project`
- Auto-Claude Mod: `C:\Users\topem\source\repos\Auto-Claude Mod`
- Ask user if path is unclear

**MCP Tools Usage:**
- Use file-based recovery (sed/cat) for direct task fixing
- Use MCP tools (`get_rdr_batches`, `submit_task_fix_request`) when project UUID is available
- Prefer Priority 1 (auto-resume) over Priority 2/3 when possible

## Dependabot Pull Requests

Auto-Claude uses Dependabot to keep dependencies up-to-date. **NEVER blindly merge Dependabot PRs** - always review them first.

### Dependabot Configuration

Located at [.github/dependabot.yml](.github/dependabot.yml):
- Python dependencies: Weekly scans of `/apps/backend`
- npm dependencies: Weekly scans of `/apps/frontend`
- GitHub Actions: Weekly scans of workflows
- Max 5 open PRs per ecosystem

### Review Checklist for Dependabot PRs

Before merging ANY Dependabot PR:

#### 1. Verify Package Legitimacy
```bash
# Check package exists and matches expected maintainer
npm view <package>@<version>

# For dotenv example:
npm view dotenv@17.2.3
# Should show: "published by motdotla <mot@mot.la>" (official maintainer)
```

#### 2. Check for Breaking Changes

**Semantic Versioning:**
- **Patch** (16.6.1 → 16.6.2): Bug fixes only - usually safe
- **Minor** (16.6.1 → 16.7.0): New features, backward compatible - review changes
- **Major** (16.6.1 → 17.0.0): Breaking changes - MUST test before merging

**Check changelog:**
```bash
npm view <package>@<version> homepage
# Read CHANGELOG.md or release notes
```

#### 3. Run Tests Before Merging

```bash
# Frontend changes
cd apps/frontend && npm test

# Backend changes
cd apps/backend && .venv/bin/pytest tests/ -v

# Build verification
npm run build
```

#### 4. Security Scan

```bash
# Check for known vulnerabilities
npm audit

# Or use GitHub's Security tab to see if update fixes vulnerabilities
```

### When to Accept vs Reject

| Update Type | Action |
|-------------|--------|
| **Patch updates** (16.6.1 → 16.6.2) | ✅ Usually safe - review and merge |
| **Minor updates** (16.6.0 → 16.7.0) | ⚠️ Review changes, test, then merge |
| **Major updates** (16.x → 17.x) | 🛑 DO NOT auto-merge - requires thorough testing |
| **Pre-release** (17.0.0-rc1) | 🛑 Reject unless actively testing |

### Red Flags (Potential Supply Chain Attacks)

🚨 **DO NOT MERGE** if you see:

1. **Unknown maintainer**:
   ```bash
   # Check current maintainer
   npm view <package>@<old-version>
   # Compare to new version
   npm view <package>@<new-version>
   # Maintainer should be the same
   ```

2. **Suspicious package name** (typosquatting):
   - `dottenv` instead of `dotenv`
   - `reacct` instead of `react`
   - Similar-looking names

3. **Unusual version jump**:
   - 16.6.1 → 99.0.0 (suspicious large jump)
   - 16.6.1 → 16.5.0 (downgrade - very suspicious)

4. **Package not on official registry**:
   ```bash
   npm view <package>@<version>
   # Should return package info, not "404 Not Found"
   ```

5. **Recently published with no history**:
   ```bash
   npm view <package> time
   # Check publication dates - new packages with no history are suspicious
   ```

### Example: Reviewing the dotenv 17.2.3 Update

**Dependabot PR**: Bump dotenv from 16.6.1 to 17.2.3

**Review process:**
```bash
# 1. Verify package legitimacy
$ npm view dotenv@17.2.3
dotenv@17.2.3 | BSD-2-Clause
published 4 months ago by motdotla <mot@mot.la>  # ✅ Official maintainer

# 2. Check for breaking changes
$ npm view dotenv@17.2.3 homepage
# Read https://github.com/motdotla/dotenv/blob/master/CHANGELOG.md
# Review breaking changes in 17.0.0

# 3. Decision
Major version bump (16.x → 17.x) = Breaking changes possible
Action: Close PR, schedule manual upgrade and testing later
```

### Configuring Dependabot to Block Major Updates

Update [.github/dependabot.yml](.github/dependabot.yml) to auto-reject major version bumps:

```yaml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/apps/frontend"
    schedule:
      interval: "weekly"
    # Block major version updates
    ignore:
      - dependency-name: "*"
        update-types: ["version-update:semver-major"]
```

This allows Dependabot to update minor/patch versions while blocking major versions that require manual review.

### Security Model

Three-layer defense:
1. **OS Sandbox** - Bash command isolation
2. **Filesystem Permissions** - Operations restricted to project directory
3. **Command Allowlist** - Dynamic allowlist from project analysis (security.py + project_analyzer.py)

Security profile cached in `.auto-claude-security.json`.

### Claude Agent SDK Integration

**CRITICAL: Auto Claude uses the Claude Agent SDK for ALL AI interactions. Never use the Anthropic API directly.**

**Client Location:** `apps/backend/core/client.py`

The `create_client()` function creates a configured `ClaudeSDKClient` instance with:
- Multi-layered security (sandbox, permissions, security hooks)
- Agent-specific tool permissions (planner, coder, qa_reviewer, qa_fixer)
- Dynamic MCP server integration based on project capabilities
- Extended thinking token budget control

**Example usage in agents:**
```python
from core.client import create_client

# Create SDK client (NOT raw Anthropic API client)
client = create_client(
    project_dir=project_dir,
    spec_dir=spec_dir,
    model="claude-sonnet-4-5-20250929",
    agent_type="coder",
    max_thinking_tokens=None  # or 5000/10000/16000
)

# Run agent session
response = client.create_agent_session(
    name="coder-agent-session",
    starting_message="Implement the authentication feature"
)
```

**Why use the SDK:**
- Pre-configured security (sandbox, allowlists, hooks)
- Automatic MCP server integration (Context7, Linear, Graphiti, Electron, Puppeteer)
- Tool permissions based on agent role
- Session management and recovery
- Unified API across all agent types

**Where to find working examples:**
- `apps/backend/agents/planner.py` - Planner agent
- `apps/backend/agents/coder.py` - Coder agent
- `apps/backend/agents/qa_reviewer.py` - QA reviewer
- `apps/backend/agents/qa_fixer.py` - QA fixer
- `apps/backend/spec_agents/` - Spec creation agents

### Memory System

**Graphiti Memory (Mandatory)** - `integrations/graphiti/`

Auto Claude uses Graphiti as its primary memory system with embedded LadybugDB (no Docker required):

- **Graph database with semantic search** - Knowledge graph for cross-session context
- **Session insights** - Patterns, gotchas, discoveries automatically extracted
- **Multi-provider support:**
  - LLM: OpenAI, Anthropic, Azure OpenAI, Ollama, Google AI (Gemini)
  - Embedders: OpenAI, Voyage AI, Azure OpenAI, Ollama, Google AI
- **Modular architecture:** (`integrations/graphiti/queries_pkg/`)
  - `graphiti.py` - Main GraphitiMemory class
  - `client.py` - LadybugDB client wrapper
  - `queries.py` - Graph query operations
  - `search.py` - Semantic search logic
  - `schema.py` - Graph schema definitions

**Configuration:**
- Set provider credentials in `apps/backend/.env` (see `.env.example`)
- Required env vars: `GRAPHITI_ENABLED=true`, `ANTHROPIC_API_KEY` or other provider keys
- Memory data stored in `.auto-claude/specs/XXX/graphiti/`

**Usage in agents:**
```python
from integrations.graphiti.memory import get_graphiti_memory

memory = get_graphiti_memory(spec_dir, project_dir)
context = memory.get_context_for_session("Implementing feature X")
memory.add_session_insight("Pattern: use React hooks for state")
```

## Development Guidelines

### Frontend Internationalization (i18n)

**CRITICAL: Always use i18n translation keys for all user-facing text in the frontend.**

The frontend uses `react-i18next` for internationalization. All labels, buttons, messages, and user-facing text MUST use translation keys.

**Translation file locations:**
- `apps/frontend/src/shared/i18n/locales/en/*.json` - English translations
- `apps/frontend/src/shared/i18n/locales/fr/*.json` - French translations

**Translation namespaces:**
- `common.json` - Shared labels, buttons, common terms
- `navigation.json` - Sidebar navigation items, sections
- `settings.json` - Settings page content
- `dialogs.json` - Dialog boxes and modals
- `tasks.json` - Task/spec related content
- `errors.json` - Error messages (structured error information with substitution support)
- `onboarding.json` - Onboarding wizard content
- `welcome.json` - Welcome screen content

**Usage pattern:**
```tsx
import { useTranslation } from 'react-i18next';

// In component
const { t } = useTranslation(['navigation', 'common']);

// Use translation keys, NOT hardcoded strings
<span>{t('navigation:items.githubPRs')}</span>  // ✅ CORRECT
<span>GitHub PRs</span>                          // ❌ WRONG
```

**Error messages with substitution:**

```tsx
// For error messages with dynamic content, use interpolation
const { t } = useTranslation(['errors']);

// errors.json: { "task": { "parseError": "Failed to parse: {{error}}" } }
<span>{t('errors:task.parseError', { error: errorMessage })}</span>
```

**When adding new UI text:**
1. Add the translation key to ALL language files (at minimum: `en/*.json` and `fr/*.json`)
2. Use `namespace:section.key` format (e.g., `navigation:items.githubPRs`)
3. Never use hardcoded strings in JSX/TSX files

### Cross-Platform Development

**CRITICAL: This project supports Windows, macOS, and Linux. Platform-specific bugs are the #1 source of breakage.**

#### The Problem

When developers on macOS fix something using Mac-specific assumptions, it breaks on Windows. When Windows developers fix something, it breaks on macOS. This happens because:

1. **CI only tested on Linux** - Platform-specific bugs weren't caught until after merge
2. **Scattered platform checks** - `process.platform === 'win32'` checks were spread across 50+ files
3. **Hardcoded paths** - Direct paths like `C:\Program Files` or `/opt/homebrew/bin` throughout code

#### The Solution

**1. Centralized Platform Abstraction**

All platform-specific code now lives in dedicated modules:

- **Frontend:** `apps/frontend/src/main/platform/`
- **Backend:** `apps/backend/core/platform/`

**Import from these modules instead of checking `process.platform` directly:**

```typescript
// ❌ WRONG - Direct platform check
if (process.platform === 'win32') {
  // Windows logic
}

// ✅ CORRECT - Use abstraction
import { isWindows, getPathDelimiter } from './platform';

if (isWindows()) {
  // Windows logic
}
```

**2. Multi-Platform CI**

CI now tests on **all three platforms** (Windows, macOS, Linux). A PR cannot merge unless all platforms pass:

```yaml
# .github/workflows/ci.yml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
```

**3. Platform Module API**

The platform module provides:

| Function | Purpose |
|----------|---------|
| `isWindows()` / `isMacOS()` / `isLinux()` | OS detection |
| `getPathDelimiter()` | Get `;` (Windows) or `:` (Unix) |
| `getExecutableExtension()` | Get `.exe` (Windows) or `` (Unix) |
| `findExecutable(name)` | Find executables across platforms |
| `getBinaryDirectories()` | Get platform-specific bin paths |
| `requiresShell(command)` | Check if .cmd/.bat needs shell on Windows |

**4. Path Handling Best Practices**

```typescript
// ❌ WRONG - Hardcoded Windows path
const claudePath = 'C:\\Program Files\\Claude\\claude.exe';

// ❌ WRONG - Hardcoded macOS path
const brewPath = '/opt/homebrew/bin/python3';

// ❌ WRONG - Manual path joining
const fullPath = dir + '/subdir/file.txt';

// ✅ CORRECT - Use platform abstraction
import { findExecutable, joinPaths } from './platform';

const claudePath = await findExecutable('claude');
const fullPath = joinPaths(dir, 'subdir', 'file.txt');
```

**5. Testing Platform-Specific Code**

```typescript
// Mock process.platform for testing
import { isWindows } from './platform';

// In tests, use jest.mock or similar
jest.mock('./platform', () => ({
  isWindows: () => true  // Simulate Windows
}));
```

**6. When You Need Platform-Specific Code**

If you must write platform-specific code:

1. **Add it to the platform module** - Not scattered in your feature code
2. **Write tests for all platforms** - Mock `process.platform` to test each case
3. **Use feature detection** - Check for file/path existence, not just OS name
4. **Document why** - Explain the platform difference in comments

**7. Submitting Platform-Specific Fixes**

When fixing a platform-specific bug:

1. Ensure your fix doesn't break other platforms
2. Test locally if you have access to other OSs
3. Rely on CI to catch issues you can't test
4. Consider adding a test that mocks other platforms

**Example: Adding a New Tool Detection**

```typescript
// ✅ CORRECT - Add to platform/paths.ts
export function getMyToolPaths(): string[] {
  if (isWindows()) {
    return [
      joinPaths('C:', 'Program Files', 'MyTool', 'tool.exe'),
      // ... more Windows paths
    ];
  }
  return [
    joinPaths('/usr', 'local', 'bin', 'mytool'),
    // ... more Unix paths
  ];
}

// ✅ CORRECT - Use in your code
import { findExecutable, getMyToolPaths } from './platform';

const toolPath = await findExecutable('mytool', getMyToolPaths());
```

### End-to-End Testing (Electron App)

**IMPORTANT: When bug fixing or implementing new features in the frontend, AI agents can perform automated E2E testing using the Electron MCP server.**

The Electron MCP server allows QA agents to interact with the running Electron app via Chrome DevTools Protocol:

**Setup:**
1. Start the Electron app with remote debugging enabled:
   ```bash
   npm run dev  # Already configured with --remote-debugging-port=9222
   ```

2. Enable Electron MCP in `apps/backend/.env`:
   ```bash
   ELECTRON_MCP_ENABLED=true
   ELECTRON_DEBUG_PORT=9222  # Default port
   ```

**Available Testing Capabilities:**

QA agents (`qa_reviewer` and `qa_fixer`) automatically get access to Electron MCP tools:

1. **Window Management**
   - `mcp__electron__get_electron_window_info` - Get info about running windows
   - `mcp__electron__take_screenshot` - Capture screenshots for visual verification

2. **UI Interaction**
   - `mcp__electron__send_command_to_electron` with commands:
     - `click_by_text` - Click buttons/links by visible text
     - `click_by_selector` - Click elements by CSS selector
     - `fill_input` - Fill form fields by placeholder or selector
     - `select_option` - Select dropdown options
     - `send_keyboard_shortcut` - Send keyboard shortcuts (Enter, Ctrl+N, etc.)
     - `navigate_to_hash` - Navigate to hash routes (#settings, #create, etc.)

3. **Page Inspection**
   - `get_page_structure` - Get organized overview of page elements
   - `debug_elements` - Get debugging info about buttons and forms
   - `verify_form_state` - Check form state and validation
   - `eval` - Execute custom JavaScript code

4. **Logging**
   - `mcp__electron__read_electron_logs` - Read console logs for debugging

**Example E2E Test Flow:**

```python
# 1. Agent takes screenshot to see current state
agent: "Take a screenshot to see the current UI"
# Uses: mcp__electron__take_screenshot

# 2. Agent inspects page structure
agent: "Get page structure to find available buttons"
# Uses: mcp__electron__send_command_to_electron (command: "get_page_structure")

# 3. Agent clicks a button to navigate
agent: "Click the 'Create New Spec' button"
# Uses: mcp__electron__send_command_to_electron (command: "click_by_text", args: {text: "Create New Spec"})

# 4. Agent fills out a form
agent: "Fill the task description field"
# Uses: mcp__electron__send_command_to_electron (command: "fill_input", args: {placeholder: "Describe your task", value: "Add login feature"})

# 5. Agent submits and verifies
agent: "Click Submit and verify success"
# Uses: click_by_text → take_screenshot → verify result
```

**When to Use E2E Testing:**

- **Bug Fixes**: Reproduce the bug, apply fix, verify it's resolved
- **New Features**: Implement feature, test the UI flow end-to-end
- **UI Changes**: Verify visual changes and interactions work correctly
- **Form Validation**: Test form submission, validation, error handling

**Configuration in `core/client.py`:**

The client automatically enables Electron MCP tools for QA agents when:
- Project is detected as Electron (`is_electron` capability)
- `ELECTRON_MCP_ENABLED=true` is set
- Agent type is `qa_reviewer` or `qa_fixer`

**Note:** Screenshots are automatically compressed (1280x720, quality 60, JPEG) to stay under Claude SDK's 1MB JSON message buffer limit.

## Running the Application

**As a standalone CLI tool**:
```bash
cd apps/backend
python run.py --spec 001
```

**With the Electron frontend**:
```bash
npm start        # Build and run desktop app
npm run dev      # Run in development mode (includes --remote-debugging-port=9222 for E2E testing)
```

**For E2E Testing with QA Agents:**
1. Start the Electron app: `npm run dev`
2. Enable Electron MCP in `apps/backend/.env`: `ELECTRON_MCP_ENABLED=true`
3. Run QA: `python run.py --spec 001 --qa`
4. QA agents will automatically interact with the running app for testing

**Project data storage:**
- `.auto-claude/specs/` - Per-project data (specs, plans, QA reports, memory) - gitignored

## Auto-Claude MCP Integration (For Claude Code)

**IMPORTANT: When the user asks to create tasks for Auto-Claude, ALWAYS use the MCP server tools automatically.**

**AUTO-REFRESH IS AUTOMATIC**: When tasks are created via MCP or direct file creation, the Electron UI auto-refreshes within 2-3 seconds. No manual refresh needed.

### How to Create Tasks (For Claude Code)

**ALWAYS create tasks using this exact method:**

```bash
# 1. Create spec directory
mkdir -p ".auto-claude/specs/XXX-task-name"

# 2. Create implementation_plan.json with status "pending"
cat > ".auto-claude/specs/XXX-task-name/implementation_plan.json" << 'EOF'
{
  "feature": "Task Title",
  "description": "Task description",
  "created_at": "2026-01-28T00:00:00Z",
  "updated_at": "2026-01-28T00:00:00Z",
  "status": "pending",
  "phases": []
}
EOF
```

**Critical requirements:**
- `status` MUST be `"pending"` (maps to Planning/backlog column)
- The target project MUST be selected in the Auto-Claude UI
- File watcher triggers refresh within 2-3 seconds

**Status mapping:**
- `"pending"` → Planning (backlog)
- `"in_progress"` → In Progress
- `"ai_review"` → AI Review
- `"human_review"` → Human Review
- `"done"` → Done

### When to Use Auto-Claude MCP

Use the Auto-Claude MCP tools when the user says things like:
- "Create a task for Auto-Claude"
- "Queue this for Auto-Claude"
- "Run this overnight in Auto-Claude"
- "Add this to Auto-Claude"
- "Batch these tasks"
- Any request involving autonomous task execution

### Automatic Workflow

When creating Auto-Claude tasks, follow this workflow automatically:

1. **Get the project ID** from the Auto-Claude UI or use `list_tasks` to find it

2. **Create the task(s)** using `create_task` or `start_batch`:
   ```json
   {
     "projectId": "<project-uuid>",
     "description": "User's task description",
     "options": {
       "profile": "auto",
       "requireReviewBeforeCoding": false
     }
   }
   ```

3. **Set up shutdown monitoring** (if user wants overnight/batch runs):
   ```json
   {
     "projectId": "<project-uuid>",
     "taskIds": ["task-id-1", "task-id-2"],
     "onComplete": {
       "command": "shutdown",
       "args": ["/s", "/t", "120"],
       "delaySeconds": 60
     }
   }
   ```

### Profile Selection

| User Says | Profile | Reason |
|-----------|---------|--------|
| "simple", "quick", "fast" | `quick` | Low thinking, fast iterations |
| "complex", "deep", "architectural" | `complex` | Maximum reasoning |
| "overnight", "batch" | `balanced` | Cost-efficient for multiple tasks |
| Nothing specific | `auto` | Smart defaults |

### Shutdown Feature

When the user mentions "shutdown when done", "overnight run", or similar:

1. Create tasks with `start_batch` or multiple `create_task` calls
2. Call `wait_for_human_review` with the `onComplete` parameter:
   - Windows: `"command": "shutdown", "args": ["/s", "/t", "120"]`
   - macOS/Linux: `"command": "shutdown", "args": ["-h", "+2"]`
   - The `delaySeconds` gives a grace period before executing

### Example Conversation

```
User: "Create 3 tasks for Auto-Claude and shutdown when all reach human review"

Claude Code should automatically:
1. Call start_batch with the 3 tasks
2. Call wait_for_human_review with taskIds and shutdown onComplete
3. Report back that tasks are queued and monitoring is active
```

### MCP Tools Reference

| Tool | Purpose |
|------|---------|
| `create_task` | Create single task with full configuration |
| `list_tasks` | List tasks for a project |
| `get_task_status` | Check task status |
| `start_task` | Start task execution |
| `start_batch` | Create and start multiple tasks |
| `wait_for_human_review` | Monitor tasks and run callback when all reach Human Review |

### Direct File Triggering (Without MCP)

Tasks can be triggered by writing files directly with `status: "start_requested"`:

```bash
mkdir -p ".auto-claude/specs/065-my-task"
echo '{}' > ".auto-claude/specs/065-my-task/task_metadata.json"
cat > ".auto-claude/specs/065-my-task/implementation_plan.json" << 'EOF'
{
  "feature": "My Task",
  "description": "Task description",
  "status": "start_requested",
  "phases": [{"name": "Phase 1", "status": "pending"}]
}
EOF
```

The file watcher auto-starts the task within 2-3 seconds.

### Task Chaining (Auto-Start on Completion)

Add a `chain` field to auto-start the next task when the current one completes:

```json
{
  "feature": "Task A",
  "status": "pending",
  "chain": {
    "next_task_id": "066-task-b",
    "on_completion": "auto_start",
    "require_approval": false
  }
}
```

**Chain fields:**
- `next_task_id` - Spec ID of the next task
- `on_completion` - Set to `"auto_start"` for automatic triggering
- `require_approval` - If `true`, waits for human approval

**Example: A → B → C chain**
```
065-task-a (chains to 066) → completes → auto-triggers
066-task-b (chains to 067) → completes → auto-triggers
067-task-c (no chain) → completes → done
```
