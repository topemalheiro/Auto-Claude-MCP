import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { FolderOpen, FolderPlus, ChevronRight, GitBranch, CheckCircle2, AlertCircle } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from './ui/dialog';
import { cn } from '../lib/utils';
import { addProject } from '../stores/project-store';
import { MethodologySelector } from './task-form/MethodologySelector';
import type { Project } from '../../shared/types';

type ModalStep = 'choose' | 'create-form' | 'existing-setup';

interface AddProjectModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onProjectAdded?: (project: Project, needsInit: boolean) => void;
}

export function AddProjectModal({ open, onOpenChange, onProjectAdded }: AddProjectModalProps) {
  const { t } = useTranslation('dialogs');
  const [step, setStep] = useState<ModalStep>('choose');
  const [projectName, setProjectName] = useState('');
  const [projectLocation, setProjectLocation] = useState('');
  const [initGit, setInitGit] = useState(true);
  const [methodology, setMethodology] = useState('native');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // State for existing folder setup
  const [existingFolderPath, setExistingFolderPath] = useState('');
  const [existingFolderName, setExistingFolderName] = useState('');
  const [existingIsGitRepo, setExistingIsGitRepo] = useState(false);
  const [existingHasAutoClaude, setExistingHasAutoClaude] = useState(false);

  // Reset state when modal opens
  useEffect(() => {
    if (open) {
      setStep('choose');
      setProjectName('');
      setProjectLocation('');
      setInitGit(true);
      setMethodology('native');
      setError(null);
      // Reset existing folder state
      setExistingFolderPath('');
      setExistingFolderName('');
      setExistingIsGitRepo(false);
      setExistingHasAutoClaude(false);
    }
  }, [open]);

  // Load default location on mount
  useEffect(() => {
    const loadDefaultLocation = async () => {
      try {
        const defaultDir = await window.electronAPI.getDefaultProjectLocation();
        if (defaultDir) {
          setProjectLocation(defaultDir);
        }
      } catch {
        // Ignore - will just be empty
      }
    };
    loadDefaultLocation();
  }, []);

  const handleOpenExisting = async () => {
    try {
      const path = await window.electronAPI.selectDirectory();
      if (path) {
        // Extract folder name from path
        const folderName = path.split(/[/\\]/).pop() || 'Project';
        setExistingFolderPath(path);
        setExistingFolderName(folderName);

        // Check if folder is a git repo
        try {
          const mainBranchResult = await window.electronAPI.detectMainBranch(path);
          setExistingIsGitRepo(mainBranchResult.success && !!mainBranchResult.data);
        } catch {
          setExistingIsGitRepo(false);
        }

        // Check if folder already has .auto-claude by trying to get methodology config
        try {
          const configResult = await window.electronAPI.getMethodologyConfig(path);
          if (configResult.success && configResult.data) {
            // Has .auto-claude with methodology config
            setExistingHasAutoClaude(true);
            if (configResult.data.name) {
              setMethodology(configResult.data.name);
            }
          } else {
            // Check if .auto-claude folder exists by listing the directory
            const listResult = await window.electronAPI.listDirectory(path);
            if (listResult.success && listResult.data) {
              const hasAutoClaudeFolder = listResult.data.some(
                (item) => item.name === '.auto-claude' && item.isDirectory
              );
              setExistingHasAutoClaude(hasAutoClaudeFolder);
            } else {
              setExistingHasAutoClaude(false);
            }
          }
        } catch {
          setExistingHasAutoClaude(false);
        }

        // Navigate to setup step
        setStep('existing-setup');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('addProject.failedToOpen'));
    }
  };

  const handleAddExistingProject = async () => {
    if (!existingFolderPath) {
      setError(t('addProject.locationRequired'));
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      const project = await addProject(existingFolderPath);
      if (project) {
        // Auto-detect and save the main branch for the project
        try {
          const mainBranchResult = await window.electronAPI.detectMainBranch(existingFolderPath);
          if (mainBranchResult.success && mainBranchResult.data) {
            await window.electronAPI.updateProjectSettings(project.id, {
              mainBranch: mainBranchResult.data
            });
          }
        } catch {
          // Non-fatal - main branch can be set later in settings
        }

        // Save methodology preference in project settings
        // The methodology.json will be saved AFTER initialization completes
        let projectWithSettings = project;
        try {
          await window.electronAPI.updateProjectSettings(project.id, {
            methodology
          });
          // Update local project object so it's available in pendingProject
          projectWithSettings = {
            ...project,
            settings: { ...project.settings, methodology }
          };
        } catch {
          // Non-fatal - methodology can be set later
        }

        // needsInit = true if no .auto-claude folder exists
        onProjectAdded?.(projectWithSettings, !existingHasAutoClaude);
        onOpenChange(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('addProject.failedToOpen'));
    } finally {
      setIsCreating(false);
    }
  };

  const handleSelectLocation = async () => {
    try {
      const path = await window.electronAPI.selectDirectory();
      if (path) {
        setProjectLocation(path);
      }
    } catch {
      // User cancelled - ignore
    }
  };

  const handleCreateProject = async () => {
    if (!projectName.trim()) {
      setError(t('addProject.nameRequired'));
      return;
    }
    if (!projectLocation.trim()) {
      setError(t('addProject.locationRequired'));
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      // Create the project folder
      const result = await window.electronAPI.createProjectFolder(
        projectLocation,
        projectName.trim(),
        initGit
      );

      if (!result.success || !result.data) {
        setError(result.error || 'Failed to create project folder');
        return;
      }

      // Add the project to our store
      const project = await addProject(result.data.path);
      if (project) {
        // For new projects with git init, set main branch
        // Git init creates 'main' branch by default on modern git
        if (initGit) {
          try {
            const mainBranchResult = await window.electronAPI.detectMainBranch(result.data.path);
            if (mainBranchResult.success && mainBranchResult.data) {
              await window.electronAPI.updateProjectSettings(project.id, {
                mainBranch: mainBranchResult.data
              });
            }
          } catch {
            // Non-fatal - main branch can be set later in settings
          }
        }

        // Save methodology preference in project settings (NOT methodology.json yet)
        // The methodology.json will be saved AFTER initialization completes
        // to avoid creating .auto-claude directory prematurely
        let projectWithSettings = project;
        try {
          await window.electronAPI.updateProjectSettings(project.id, {
            methodology
          });
          // Also update local project object so it's available in pendingProject
          // The IPC call updates the main store, but we need it in the object we pass
          projectWithSettings = {
            ...project,
            settings: { ...project.settings, methodology }
          };
        } catch {
          // Non-fatal - methodology can be set later
        }

        onProjectAdded?.(projectWithSettings, true); // New projects always need init
        onOpenChange(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('addProject.failedToCreate'));
    } finally {
      setIsCreating(false);
    }
  };

  const renderChooseStep = () => (
    <>
      <DialogHeader>
        <DialogTitle>{t('addProject.title')}</DialogTitle>
        <DialogDescription>
          {t('addProject.description')}
        </DialogDescription>
      </DialogHeader>

      <div className="py-4 space-y-3">
        {/* Open Existing Option */}
        <button
          onClick={handleOpenExisting}
          className={cn(
            'w-full flex items-center gap-4 p-4 rounded-xl border border-border',
            'bg-card hover:bg-accent hover:border-accent transition-all duration-200',
            'text-left group'
          )}
          aria-label={t('addProject.openExistingAriaLabel')}
        >
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-primary/10">
            <FolderOpen className="h-6 w-6 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-medium text-foreground">{t('addProject.openExisting')}</h3>
            <p className="text-sm text-muted-foreground mt-0.5">
              {t('addProject.openExistingDescription')}
            </p>
          </div>
          <ChevronRight className="h-5 w-5 text-muted-foreground group-hover:text-foreground transition-colors" />
        </button>

        {/* Create New Option */}
        <button
          onClick={() => setStep('create-form')}
          className={cn(
            'w-full flex items-center gap-4 p-4 rounded-xl border border-border',
            'bg-card hover:bg-accent hover:border-accent transition-all duration-200',
            'text-left group'
          )}
          aria-label={t('addProject.createNewAriaLabel')}
        >
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-success/10">
            <FolderPlus className="h-6 w-6 text-success" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-medium text-foreground">{t('addProject.createNew')}</h3>
            <p className="text-sm text-muted-foreground mt-0.5">
              {t('addProject.createNewDescription')}
            </p>
          </div>
          <ChevronRight className="h-5 w-5 text-muted-foreground group-hover:text-foreground transition-colors" />
        </button>
      </div>

      {error && (
        <div className="text-sm text-destructive bg-destructive/10 rounded-lg p-3 mt-2" role="alert">
          {error}
        </div>
      )}
    </>
  );

  const renderCreateForm = () => (
    <>
      <DialogHeader>
        <DialogTitle>{t('addProject.createNewTitle')}</DialogTitle>
        <DialogDescription>
          {t('addProject.createNewSubtitle')}
        </DialogDescription>
      </DialogHeader>

      <div className="py-4 space-y-4">
        {/* Project Name */}
        <div className="space-y-2">
          <Label htmlFor="project-name">{t('addProject.projectName')}</Label>
          <Input
            id="project-name"
            placeholder={t('addProject.projectNamePlaceholder')}
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            autoFocus
          />
          <p className="text-xs text-muted-foreground">
            {t('addProject.projectNameHelp')}
          </p>
        </div>

        {/* Location */}
        <div className="space-y-2">
          <Label htmlFor="project-location">{t('addProject.location')}</Label>
          <div className="flex gap-2">
            <Input
              id="project-location"
              placeholder={t('addProject.locationPlaceholder')}
              value={projectLocation}
              onChange={(e) => setProjectLocation(e.target.value)}
              className="flex-1"
            />
            <Button variant="outline" onClick={handleSelectLocation}>
              {t('addProject.browse')}
            </Button>
          </div>
          {projectLocation && projectName && (
            <p className="text-xs text-muted-foreground">
              {t('addProject.willCreate')} <code className="bg-muted px-1 py-0.5 rounded">{projectLocation}/{projectName}</code>
            </p>
          )}
        </div>

        {/* Git Init Checkbox */}
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="init-git"
            checked={initGit}
            onChange={(e) => setInitGit(e.target.checked)}
            className="h-4 w-4 rounded border-border bg-background"
          />
          <Label htmlFor="init-git" className="text-sm font-normal cursor-pointer">
            {t('addProject.initGit')}
          </Label>
        </div>

        {/* Methodology Selector */}
        <MethodologySelector
          value={methodology}
          onChange={setMethodology}
          idPrefix="create-project"
        />

        {error && (
          <div className="text-sm text-destructive bg-destructive/10 rounded-lg p-3" role="alert">
            {error}
          </div>
        )}
      </div>

      <DialogFooter>
        <Button variant="outline" onClick={() => setStep('choose')} disabled={isCreating}>
          {t('addProject.back')}
        </Button>
        <Button onClick={handleCreateProject} disabled={isCreating}>
          {isCreating ? t('addProject.creating') : t('addProject.createProject')}
        </Button>
      </DialogFooter>
    </>
  );

  const renderExistingSetup = () => (
    <>
      <DialogHeader>
        <DialogTitle>{t('addProject.existingSetupTitle', { defaultValue: 'Project Setup' })}</DialogTitle>
        <DialogDescription>
          {t('addProject.existingSetupSubtitle', { defaultValue: 'Configure Auto Claude for your existing project' })}
        </DialogDescription>
      </DialogHeader>

      <div className="py-4 space-y-4">
        {/* Selected Folder Info */}
        <div className="space-y-2">
          <Label>{t('addProject.selectedFolder', { defaultValue: 'Selected Folder' })}</Label>
          <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
            <FolderOpen className="h-5 w-5 text-primary shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="font-medium text-sm truncate">{existingFolderName}</p>
              <p className="text-xs text-muted-foreground truncate">{existingFolderPath}</p>
            </div>
          </div>
        </div>

        {/* Status Indicators */}
        <div className="space-y-2">
          <Label>{t('addProject.projectStatus', { defaultValue: 'Project Status' })}</Label>
          <div className="space-y-2">
            {/* Git Status */}
            <div className={cn(
              'flex items-center gap-2 p-2 rounded-lg text-sm',
              existingIsGitRepo ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'
            )}>
              {existingIsGitRepo ? (
                <>
                  <CheckCircle2 className="h-4 w-4 shrink-0" />
                  <span>{t('addProject.gitInitialized', { defaultValue: 'Git repository detected' })}</span>
                </>
              ) : (
                <>
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{t('addProject.gitNotInitialized', { defaultValue: 'Not a Git repository (will be initialized)' })}</span>
                </>
              )}
            </div>

            {/* Auto Claude Status */}
            <div className={cn(
              'flex items-center gap-2 p-2 rounded-lg text-sm',
              existingHasAutoClaude ? 'bg-success/10 text-success' : 'bg-muted text-muted-foreground'
            )}>
              {existingHasAutoClaude ? (
                <>
                  <CheckCircle2 className="h-4 w-4 shrink-0" />
                  <span>{t('addProject.autoClaudeExists', { defaultValue: 'Auto Claude already configured' })}</span>
                </>
              ) : (
                <>
                  <GitBranch className="h-4 w-4 shrink-0" />
                  <span>{t('addProject.autoClaudeWillInit', { defaultValue: 'Auto Claude will be initialized' })}</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Methodology Selector */}
        <div className="space-y-2">
          {existingHasAutoClaude && (
            <p className="text-xs text-muted-foreground">
              {t('addProject.methodologyNote', { defaultValue: 'You can change the methodology later in project settings.' })}
            </p>
          )}
          <MethodologySelector
            value={methodology}
            onChange={setMethodology}
            idPrefix="existing-project"
          />
        </div>

        {error && (
          <div className="text-sm text-destructive bg-destructive/10 rounded-lg p-3" role="alert">
            {error}
          </div>
        )}
      </div>

      <DialogFooter>
        <Button variant="outline" onClick={() => setStep('choose')} disabled={isCreating}>
          {t('addProject.back')}
        </Button>
        <Button onClick={handleAddExistingProject} disabled={isCreating}>
          {isCreating ? t('addProject.adding', { defaultValue: 'Adding...' }) : t('addProject.addProject', { defaultValue: 'Add Project' })}
        </Button>
      </DialogFooter>
    </>
  );

  const renderStep = () => {
    switch (step) {
      case 'choose':
        return renderChooseStep();
      case 'create-form':
        return renderCreateForm();
      case 'existing-setup':
        return renderExistingSetup();
      default:
        return renderChooseStep();
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        {renderStep()}
      </DialogContent>
    </Dialog>
  );
}
