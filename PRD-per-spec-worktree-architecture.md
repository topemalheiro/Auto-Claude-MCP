# PRD: Per-Spec Worktree Architecture

## Executive Summary

Redesign the worktree system to support **one worktree per spec**, enabling:
- Multiple specs can be worked on simultaneously
- Each spec has its own isolated branch that persists until merge
- Clear mapping: spec → worktree → branch
- UI can show all pending branches ready for review/merge

## Current Problems

### Bug #1: Worktree Path Mismatch
- **Python:** Creates `.worktrees/auto-claude/`
- **UI:** Looks for `.worktrees/auto-claude-staging/`
- **Impact:** UI never finds worktrees

### Bug #2: Spec Name Ignored
- `get_existing_build_worktree(spec_name)` ignores the spec_name parameter
- All specs share ONE worktree
- **Impact:** Working on spec-003 would corrupt spec-002's work

### Bug #3: Single Worktree Design
- Only one worktree exists at a time
- Can only work on one spec at a time
- **Impact:** No parallel spec development

### Bug #4: Branches Deleted on Merge
- `merge_staging(delete_after=True)` deletes the branch
- **Impact:** Can't see which specs have work ready for review

---

## New Architecture

### Directory Structure

```
project/
├── .worktrees/
│   ├── 002-implement-memory/           # Worktree for spec 002
│   │   └── (full project copy)
│   ├── 003-fix-bug/                    # Worktree for spec 003
│   │   └── (full project copy)
│   └── 004-improve-ui/                 # Worktree for spec 004
│       └── (full project copy)
├── .auto-claude/
│   └── specs/
│       ├── 002-implement-memory/
│       ├── 003-fix-bug/
│       └── 004-improve-ui/
└── (rest of project)
```

### Branch Naming Convention

```
auto-claude/{spec-id}

Examples:
- auto-claude/002-implement-memory
- auto-claude/003-fix-bug
- auto-claude/004-improve-ui
```

### Worktree-to-Spec Mapping

Each worktree directory name **matches** the spec folder name:
- Spec: `.auto-claude/specs/002-implement-memory/`
- Worktree: `.worktrees/002-implement-memory/`
- Branch: `auto-claude/002-implement-memory`

This creates a **1:1:1 mapping** that's easy to reason about.

---

## Data Model Changes

### WorktreeInfo (Enhanced)

```python
@dataclass
class WorktreeInfo:
    """Information about a spec's worktree."""
    path: Path              # .worktrees/{spec-name}/
    branch: str             # auto-claude/{spec-name}
    spec_name: str          # The spec folder name (e.g., "002-implement-memory")
    base_branch: str        # Branch it was created from (e.g., "main")
    is_active: bool = True  # Whether worktree exists
    
    # Statistics (computed on demand)
    commit_count: int = 0
    files_changed: int = 0
    additions: int = 0
    deletions: int = 0
```

### WorktreeStatus (for UI)

```typescript
interface WorktreeStatus {
  exists: boolean;
  specId: string;           // Which spec this worktree is for
  worktreePath?: string;
  branch?: string;
  baseBranch?: string;
  commitCount?: number;
  filesChanged?: number;
  additions?: number;
  deletions?: number;
}
```

---

## Python Backend Changes

### 1. worktree.py - Core Changes

```python
#!/usr/bin/env python3
"""
Git Worktree Manager - Per-Spec Architecture
=============================================

Each spec gets its own worktree:
- Worktree path: .worktrees/{spec-name}/
- Branch name: auto-claude/{spec-name}

This allows:
1. Multiple specs to be worked on simultaneously
2. Each spec's changes are isolated
3. Branches persist until explicitly merged
4. Clear 1:1:1 mapping: spec → worktree → branch
"""

import asyncio
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class WorktreeError(Exception):
    """Error during worktree operations."""
    pass


@dataclass
class WorktreeInfo:
    """Information about a spec's worktree."""
    path: Path
    branch: str
    spec_name: str
    base_branch: str
    is_active: bool = True
    commit_count: int = 0
    files_changed: int = 0
    additions: int = 0
    deletions: int = 0


class WorktreeManager:
    """
    Manages per-spec Git worktrees.
    
    Each spec gets its own worktree in .worktrees/{spec-name}/ with
    a corresponding branch auto-claude/{spec-name}.
    """

    def __init__(self, project_dir: Path, base_branch: Optional[str] = None):
        self.project_dir = project_dir
        self.base_branch = base_branch or self._get_current_branch()
        self.worktrees_dir = project_dir / ".worktrees"
        self._merge_lock = asyncio.Lock()

    def _get_current_branch(self) -> str:
        """Get the current git branch."""
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=self.project_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise WorktreeError(f"Failed to get current branch: {result.stderr}")
        return result.stdout.strip()

    def _run_git(self, args: list[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
        """Run a git command and return the result."""
        return subprocess.run(
            ["git"] + args,
            cwd=cwd or self.project_dir,
            capture_output=True,
            text=True,
        )

    def setup(self) -> None:
        """Create worktrees directory if needed."""
        self.worktrees_dir.mkdir(exist_ok=True)

    # ==================== Per-Spec Worktree Methods ====================

    def get_worktree_path(self, spec_name: str) -> Path:
        """Get the worktree path for a spec."""
        return self.worktrees_dir / spec_name

    def get_branch_name(self, spec_name: str) -> str:
        """Get the branch name for a spec."""
        return f"auto-claude/{spec_name}"

    def worktree_exists(self, spec_name: str) -> bool:
        """Check if a worktree exists for a spec."""
        return self.get_worktree_path(spec_name).exists()

    def get_worktree_info(self, spec_name: str) -> Optional[WorktreeInfo]:
        """Get info about a spec's worktree."""
        worktree_path = self.get_worktree_path(spec_name)
        if not worktree_path.exists():
            return None

        branch_name = self.get_branch_name(spec_name)
        
        # Verify the branch exists in the worktree
        result = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=worktree_path)
        if result.returncode != 0:
            return None
        
        actual_branch = result.stdout.strip()
        
        # Get statistics
        stats = self._get_worktree_stats(spec_name)
        
        return WorktreeInfo(
            path=worktree_path,
            branch=actual_branch,
            spec_name=spec_name,
            base_branch=self.base_branch,
            is_active=True,
            **stats
        )

    def _get_worktree_stats(self, spec_name: str) -> dict:
        """Get diff statistics for a worktree."""
        worktree_path = self.get_worktree_path(spec_name)
        branch_name = self.get_branch_name(spec_name)
        
        stats = {
            "commit_count": 0,
            "files_changed": 0,
            "additions": 0,
            "deletions": 0,
        }
        
        if not worktree_path.exists():
            return stats
        
        # Commit count
        result = self._run_git(
            ["rev-list", "--count", f"{self.base_branch}..HEAD"],
            cwd=worktree_path
        )
        if result.returncode == 0:
            stats["commit_count"] = int(result.stdout.strip() or "0")
        
        # Diff stats
        result = self._run_git(
            ["diff", "--shortstat", f"{self.base_branch}...HEAD"],
            cwd=worktree_path
        )
        if result.returncode == 0 and result.stdout.strip():
            # Parse: "3 files changed, 50 insertions(+), 10 deletions(-)"
            import re
            match = re.search(r"(\d+) files? changed", result.stdout)
            if match:
                stats["files_changed"] = int(match.group(1))
            match = re.search(r"(\d+) insertions?", result.stdout)
            if match:
                stats["additions"] = int(match.group(1))
            match = re.search(r"(\d+) deletions?", result.stdout)
            if match:
                stats["deletions"] = int(match.group(1))
        
        return stats

    def create_worktree(self, spec_name: str) -> WorktreeInfo:
        """
        Create a worktree for a spec.
        
        Args:
            spec_name: The spec folder name (e.g., "002-implement-memory")
            
        Returns:
            WorktreeInfo for the created worktree
        """
        worktree_path = self.get_worktree_path(spec_name)
        branch_name = self.get_branch_name(spec_name)
        
        # Remove existing if present (from crashed previous run)
        if worktree_path.exists():
            self._run_git(["worktree", "remove", "--force", str(worktree_path)])
        
        # Delete branch if it exists (from previous attempt)
        self._run_git(["branch", "-D", branch_name])
        
        # Create worktree with new branch from base
        result = self._run_git([
            "worktree", "add", "-b", branch_name,
            str(worktree_path), self.base_branch
        ])
        
        if result.returncode != 0:
            raise WorktreeError(f"Failed to create worktree for {spec_name}: {result.stderr}")
        
        print(f"Created worktree: {worktree_path.name} on branch {branch_name}")
        
        return WorktreeInfo(
            path=worktree_path,
            branch=branch_name,
            spec_name=spec_name,
            base_branch=self.base_branch,
            is_active=True,
        )

    def get_or_create_worktree(self, spec_name: str) -> WorktreeInfo:
        """
        Get existing worktree or create a new one for a spec.
        
        Args:
            spec_name: The spec folder name
            
        Returns:
            WorktreeInfo for the worktree
        """
        existing = self.get_worktree_info(spec_name)
        if existing:
            print(f"Using existing worktree: {existing.path}")
            return existing
        
        return self.create_worktree(spec_name)

    def remove_worktree(self, spec_name: str, delete_branch: bool = False) -> None:
        """
        Remove a spec's worktree.
        
        Args:
            spec_name: The spec folder name
            delete_branch: Whether to also delete the branch
        """
        worktree_path = self.get_worktree_path(spec_name)
        branch_name = self.get_branch_name(spec_name)
        
        if worktree_path.exists():
            result = self._run_git(["worktree", "remove", "--force", str(worktree_path)])
            if result.returncode == 0:
                print(f"Removed worktree: {worktree_path.name}")
            else:
                print(f"Warning: Could not remove worktree: {result.stderr}")
                shutil.rmtree(worktree_path, ignore_errors=True)
        
        if delete_branch:
            self._run_git(["branch", "-D", branch_name])
            print(f"Deleted branch: {branch_name}")
        
        self._run_git(["worktree", "prune"])

    def merge_worktree(self, spec_name: str, delete_after: bool = False) -> bool:
        """
        Merge a spec's worktree branch back to base branch.
        
        Args:
            spec_name: The spec folder name
            delete_after: Whether to remove worktree and branch after merge
            
        Returns:
            True if merge succeeded
        """
        info = self.get_worktree_info(spec_name)
        if not info:
            print(f"No worktree found for spec: {spec_name}")
            return False
        
        print(f"Merging {info.branch} into {self.base_branch}...")
        
        # Switch to base branch in main project
        result = self._run_git(["checkout", self.base_branch])
        if result.returncode != 0:
            print(f"Error: Could not checkout base branch: {result.stderr}")
            return False
        
        # Merge the spec branch
        result = self._run_git([
            "merge", "--no-ff", info.branch,
            "-m", f"auto-claude: Merge {info.branch}"
        ])
        
        if result.returncode != 0:
            print(f"Merge conflict! Aborting merge...")
            self._run_git(["merge", "--abort"])
            return False
        
        print(f"Successfully merged {info.branch}")
        
        if delete_after:
            self.remove_worktree(spec_name, delete_branch=True)
        
        return True

    def commit_in_worktree(self, spec_name: str, message: str) -> bool:
        """Commit all changes in a spec's worktree."""
        worktree_path = self.get_worktree_path(spec_name)
        if not worktree_path.exists():
            return False
        
        self._run_git(["add", "."], cwd=worktree_path)
        result = self._run_git(["commit", "-m", message], cwd=worktree_path)
        
        if result.returncode == 0:
            return True
        elif "nothing to commit" in result.stdout + result.stderr:
            return True
        else:
            print(f"Commit failed: {result.stderr}")
            return False

    # ==================== Listing & Discovery ====================

    def list_all_worktrees(self) -> list[WorktreeInfo]:
        """List all spec worktrees."""
        worktrees = []
        
        if not self.worktrees_dir.exists():
            return worktrees
        
        for item in self.worktrees_dir.iterdir():
            if item.is_dir():
                info = self.get_worktree_info(item.name)
                if info:
                    worktrees.append(info)
        
        return worktrees

    def list_all_spec_branches(self) -> list[str]:
        """List all auto-claude branches (even if worktree removed)."""
        result = self._run_git(["branch", "--list", "auto-claude/*"])
        if result.returncode != 0:
            return []
        
        branches = []
        for line in result.stdout.strip().split("\n"):
            branch = line.strip().lstrip("* ")
            if branch:
                branches.append(branch)
        
        return branches

    def get_changed_files(self, spec_name: str) -> list[tuple[str, str]]:
        """Get list of changed files in a spec's worktree."""
        worktree_path = self.get_worktree_path(spec_name)
        if not worktree_path.exists():
            return []
        
        result = self._run_git(
            ["diff", "--name-status", f"{self.base_branch}...HEAD"],
            cwd=worktree_path
        )
        
        files = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                files.append((parts[0], parts[1]))
        
        return files

    def cleanup_all(self) -> None:
        """Remove all worktrees (preserves branches by default)."""
        for worktree in self.list_all_worktrees():
            self.remove_worktree(worktree.spec_name, delete_branch=False)

    def cleanup_stale_worktrees(self) -> None:
        """Remove worktrees that aren't registered with git."""
        if not self.worktrees_dir.exists():
            return
        
        # Get list of registered worktrees
        result = self._run_git(["worktree", "list", "--porcelain"])
        registered_paths = set()
        for line in result.stdout.split("\n"):
            if line.startswith("worktree "):
                registered_paths.add(Path(line.split(" ", 1)[1]))
        
        # Remove unregistered directories
        for item in self.worktrees_dir.iterdir():
            if item.is_dir() and item not in registered_paths:
                print(f"Removing stale worktree directory: {item.name}")
                shutil.rmtree(item, ignore_errors=True)
        
        self._run_git(["worktree", "prune"])
```

### 2. workspace.py - Updated Functions

```python
def get_existing_build_worktree(project_dir: Path, spec_name: str) -> Optional[Path]:
    """
    Check if there's an existing worktree FOR THIS SPECIFIC SPEC.
    
    Args:
        project_dir: The project directory
        spec_name: The spec folder name (e.g., "002-implement-memory")
        
    Returns:
        Path to worktree if it exists for this spec, None otherwise
    """
    # Per-spec worktree path
    worktree_path = project_dir / ".worktrees" / spec_name
    
    if worktree_path.exists():
        # Verify it's a valid git worktree
        git_dir = worktree_path / ".git"
        if git_dir.exists():
            return worktree_path
    
    return None


def setup_workspace(
    project_dir: Path,
    spec_name: str,
    mode: WorkspaceMode,
    source_spec_dir: Optional[Path] = None,
) -> tuple[Path, Optional[WorktreeManager], Optional[Path]]:
    """
    Set up the workspace for a specific spec.
    
    Uses per-spec worktrees - each spec gets its own isolated worktree.
    """
    if mode == WorkspaceMode.DIRECT:
        return project_dir, None, source_spec_dir

    print()
    print_status(f"Setting up workspace for {spec_name}...", "progress")

    manager = WorktreeManager(project_dir)
    manager.setup()

    # Get or create worktree FOR THIS SPECIFIC SPEC
    info = manager.get_or_create_worktree(spec_name)

    # Copy spec files to worktree if provided
    localized_spec_dir = None
    if source_spec_dir and source_spec_dir.exists():
        localized_spec_dir = copy_spec_to_worktree(
            source_spec_dir, info.path, spec_name
        )
        print_status(f"Spec files copied to workspace", "success")

    print_status(f"Workspace ready: {info.path.name}", "success")
    print()

    return info.path, manager, localized_spec_dir
```

---

## UI Backend Changes

### ipc-handlers.ts - Fixed Paths & Per-Spec Support

```typescript
/**
 * Get the worktree path for a specific spec
 */
function getWorktreePath(projectPath: string, specId: string): string {
  return path.join(projectPath, '.worktrees', specId);
}

/**
 * Get the branch name for a specific spec
 */
function getBranchName(specId: string): string {
  return `auto-claude/${specId}`;
}

/**
 * Get the worktree status for a task
 */
ipcMain.handle(
  IPC_CHANNELS.TASK_WORKTREE_STATUS,
  async (_, taskId: string): Promise<IPCResult<WorktreeStatus>> => {
    try {
      const { task, project } = findTaskAndProject(taskId);
      if (!task || !project) {
        return { success: false, error: 'Task not found' };
      }

      // Per-spec worktree path (FIXED: uses spec ID, not hardcoded name)
      const worktreePath = getWorktreePath(project.path, task.specId);

      if (!existsSync(worktreePath)) {
        return {
          success: true,
          data: { 
            exists: false,
            specId: task.specId
          }
        };
      }

      const { execSync } = require('child_process');

      try {
        // Get current branch in worktree
        const branch = execSync('git rev-parse --abbrev-ref HEAD', {
          cwd: worktreePath,
          encoding: 'utf-8'
        }).trim();

        // Get base branch
        let baseBranch = 'main';
        try {
          baseBranch = execSync('git rev-parse --abbrev-ref origin/HEAD 2>/dev/null || echo main', {
            cwd: project.path,
            encoding: 'utf-8'
          }).trim().replace('origin/', '');
        } catch {
          baseBranch = 'main';
        }

        // Get commit count
        let commitCount = 0;
        try {
          const countOutput = execSync(`git rev-list --count ${baseBranch}..HEAD 2>/dev/null || echo 0`, {
            cwd: worktreePath,
            encoding: 'utf-8'
          }).trim();
          commitCount = parseInt(countOutput, 10) || 0;
        } catch {
          commitCount = 0;
        }

        // Get diff stats
        let filesChanged = 0;
        let additions = 0;
        let deletions = 0;

        try {
          const diffStat = execSync(`git diff --shortstat ${baseBranch}...HEAD 2>/dev/null || echo ""`, {
            cwd: worktreePath,
            encoding: 'utf-8'
          }).trim();

          const filesMatch = diffStat.match(/(\d+) files? changed/);
          const addMatch = diffStat.match(/(\d+) insertions?\(\+\)/);
          const delMatch = diffStat.match(/(\d+) deletions?\(-\)/);
          
          if (filesMatch) filesChanged = parseInt(filesMatch[1], 10);
          if (addMatch) additions = parseInt(addMatch[1], 10);
          if (delMatch) deletions = parseInt(delMatch[1], 10);
        } catch {
          // Ignore diff errors
        }

        return {
          success: true,
          data: {
            exists: true,
            specId: task.specId,
            worktreePath,
            branch,
            baseBranch,
            commitCount,
            filesChanged,
            additions,
            deletions
          }
        };
      } catch (gitError) {
        console.error('Git error getting worktree status:', gitError);
        return {
          success: true,
          data: { exists: true, specId: task.specId, worktreePath }
        };
      }
    } catch (error) {
      console.error('Failed to get worktree status:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to get worktree status'
      };
    }
  }
);

/**
 * List all worktrees (for overview/dashboard)
 */
ipcMain.handle(
  'task:listWorktrees',
  async (_, projectId: string): Promise<IPCResult<WorktreeInfo[]>> => {
    try {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      const worktreesDir = path.join(project.path, '.worktrees');
      if (!existsSync(worktreesDir)) {
        return { success: true, data: [] };
      }

      const { execSync, readdirSync } = require('fs');
      const worktrees: WorktreeInfo[] = [];

      for (const specId of readdirSync(worktreesDir)) {
        const worktreePath = path.join(worktreesDir, specId);
        const stat = require('fs').statSync(worktreePath);
        
        if (!stat.isDirectory()) continue;

        try {
          const branch = execSync('git rev-parse --abbrev-ref HEAD', {
            cwd: worktreePath,
            encoding: 'utf-8'
          }).trim();

          worktrees.push({
            specId,
            worktreePath,
            branch,
            exists: true
          });
        } catch {
          // Skip invalid worktrees
        }
      }

      return { success: true, data: worktrees };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to list worktrees'
      };
    }
  }
);
```

---

## Type Definitions (shared/types.ts)

```typescript
/**
 * Worktree status for a specific spec
 */
export interface WorktreeStatus {
  exists: boolean;
  specId: string;              // Which spec this worktree is for
  worktreePath?: string;
  branch?: string;
  baseBranch?: string;
  commitCount?: number;
  filesChanged?: number;
  additions?: number;
  deletions?: number;
}

/**
 * Summary of all worktrees in a project
 */
export interface WorktreeInfo {
  specId: string;
  worktreePath: string;
  branch: string;
  exists: boolean;
}

/**
 * Result of a worktree merge operation
 */
export interface WorktreeMergeResult {
  success: boolean;
  specId: string;
  message: string;
  conflicts?: string[];       // Files with conflicts, if any
}
```

---

## Migration Strategy

### For Existing Single Worktree

When the new code detects an old-style worktree at `.worktrees/auto-claude/`:

1. **Detect the spec it belongs to** by reading the branch name:
   ```python
   # Branch: auto-claude/002-implement-memory → spec = 002-implement-memory
   ```

2. **Rename the worktree directory**:
   ```bash
   mv .worktrees/auto-claude .worktrees/002-implement-memory
   ```

3. **Update git worktree registration**:
   ```bash
   git worktree repair
   ```

### Migration Code

```python
def migrate_legacy_worktree(project_dir: Path) -> Optional[str]:
    """
    Migrate old-style single worktree to per-spec format.
    
    Returns the spec name if migration was performed, None otherwise.
    """
    legacy_path = project_dir / ".worktrees" / "auto-claude"
    
    if not legacy_path.exists():
        return None
    
    # Get the branch to determine spec name
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=legacy_path,
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        return None
    
    branch = result.stdout.strip()  # e.g., "auto-claude/002-implement-memory"
    
    if not branch.startswith("auto-claude/"):
        return None
    
    spec_name = branch.replace("auto-claude/", "")  # "002-implement-memory"
    new_path = project_dir / ".worktrees" / spec_name
    
    # Rename the directory
    legacy_path.rename(new_path)
    
    # Repair git worktree registration
    subprocess.run(
        ["git", "worktree", "repair"],
        cwd=project_dir,
        capture_output=True,
    )
    
    print(f"Migrated legacy worktree to: {new_path}")
    return spec_name
```

---

## Summary of Changes

| Component | Old Behavior | New Behavior |
|-----------|--------------|--------------|
| **Worktree Path** | `.worktrees/auto-claude/` | `.worktrees/{spec-name}/` |
| **Branch Name** | `auto-claude/{spec-name}` | Same (unchanged) |
| **Worktree Count** | ONE for all specs | ONE per spec |
| **UI Path** | `.worktrees/auto-claude-staging/` (wrong!) | `.worktrees/{spec-name}/` |
| **Branch on Merge** | Deleted by default | Preserved by default |
| **Parallel Specs** | Not supported | Fully supported |

---

## Benefits

1. **Isolation**: Each spec's work is completely isolated
2. **Parallel Work**: Can work on multiple specs simultaneously
3. **Clear Mapping**: spec → worktree → branch (1:1:1)
4. **Persistence**: Branches remain until explicitly merged
5. **Discoverability**: Easy to list all in-progress specs
6. **No More Bugs**: Fixes path mismatch, spec confusion, and branch deletion issues

---

## Implementation Checklist

- [ ] Update `worktree.py` with per-spec methods
- [ ] Update `workspace.py` functions to use spec-name paths
- [ ] Update `coordinator.py` for parallel execution
- [ ] Fix UI `ipc-handlers.ts` worktree paths
- [ ] Add migration code for legacy worktrees
- [ ] Update TypeScript types
- [ ] Add "List Worktrees" endpoint for dashboard
- [ ] Update tests
