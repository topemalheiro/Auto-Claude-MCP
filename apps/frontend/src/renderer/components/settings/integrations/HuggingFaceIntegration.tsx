import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { RefreshCw, Loader2, CheckCircle2, AlertCircle, User, Terminal, ExternalLink } from 'lucide-react';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Switch } from '../../ui/switch';
import { Separator } from '../../ui/separator';
import { Button } from '../../ui/button';
import type { ProjectEnvConfig } from '../../../../shared/types';

// Debug logging
const DEBUG = process.env.NODE_ENV === 'development' || process.env.DEBUG === 'true';
function debugLog(message: string, data?: unknown) {
  if (DEBUG) {
    if (data !== undefined) {
      console.warn(`[HuggingFaceIntegration] ${message}`, data);
    } else {
      console.warn(`[HuggingFaceIntegration] ${message}`);
    }
  }
}

interface HuggingFaceIntegrationProps {
  envConfig: ProjectEnvConfig | null;
  updateEnvConfig: (updates: Partial<ProjectEnvConfig>) => void;
  projectPath?: string;
}

/**
 * Hugging Face integration settings component.
 * Manages HF CLI authentication and model repository configuration.
 */
export function HuggingFaceIntegration({
  envConfig,
  updateEnvConfig,
  projectPath
}: HuggingFaceIntegrationProps) {
  const { t } = useTranslation('settings');

  // CLI detection state
  const [hfCliInstalled, setHfCliInstalled] = useState<boolean | null>(null);
  const [hfCliVersion, setHfCliVersion] = useState<string | null>(null);
  const [isCheckingCli, setIsCheckingCli] = useState(false);

  // Auth state
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState<string | null>(null);
  const [isCheckingAuth, setIsCheckingAuth] = useState(false);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  debugLog('Render - projectPath:', projectPath);
  debugLog('Render - envConfig:', envConfig ? { huggingfaceEnabled: envConfig.huggingfaceEnabled, repoId: envConfig.huggingfaceRepoId } : null);

  // Check HF CLI on mount
  useEffect(() => {
    checkHfCli();
  }, []);

  // Check auth status after CLI check
  useEffect(() => {
    if (hfCliInstalled) {
      checkAuth();
    }
  }, [hfCliInstalled]);

  const checkHfCli = async () => {
    setIsCheckingCli(true);
    try {
      const result = await window.electronAPI.checkHuggingFaceCli();
      debugLog('checkHuggingFaceCli result:', result);
      if (result.success && result.data) {
        setHfCliInstalled(result.data.installed);
        setHfCliVersion(result.data.version || null);
      } else {
        setHfCliInstalled(false);
      }
    } catch (error) {
      debugLog('Error checking HF CLI:', error);
      setHfCliInstalled(false);
    } finally {
      setIsCheckingCli(false);
    }
  };

  const checkAuth = async () => {
    setIsCheckingAuth(true);
    setAuthError(null);
    try {
      const result = await window.electronAPI.checkHuggingFaceAuth();
      debugLog('checkHuggingFaceAuth result:', result);
      if (result.success && result.data) {
        setIsAuthenticated(result.data.authenticated);
        setUsername(result.data.username || null);
      } else {
        setIsAuthenticated(false);
        setUsername(null);
      }
    } catch (error) {
      debugLog('Error checking auth:', error);
      setIsAuthenticated(false);
    } finally {
      setIsCheckingAuth(false);
    }
  };

  const handleLogin = async () => {
    setIsLoggingIn(true);
    setAuthError(null);
    try {
      const result = await window.electronAPI.huggingFaceLogin();
      debugLog('huggingFaceLogin result:', result);
      if (result.success) {
        // Re-check auth status after login
        await checkAuth();
      } else {
        setAuthError(result.error || 'Login failed');
      }
    } catch (error) {
      debugLog('Error during login:', error);
      setAuthError('Login failed. Please try again.');
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleInstallCli = async () => {
    // Open HuggingFace CLI installation docs
    window.open('https://huggingface.co/docs/huggingface_hub/quick-start#installation', '_blank');
  };

  return (
    <div className="space-y-6">
      {/* Enable/Disable Toggle */}
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <Label className="text-base font-medium">{t('projectSections.huggingface.enableLabel')}</Label>
          <p className="text-sm text-muted-foreground">
            {t('projectSections.huggingface.enableDescription')}
          </p>
        </div>
        <Switch
          checked={envConfig?.huggingfaceEnabled ?? false}
          onCheckedChange={(checked) => updateEnvConfig({ huggingfaceEnabled: checked })}
        />
      </div>

      <Separator />

      {/* CLI Status */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Terminal className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">{t('projectSections.huggingface.cliStatus')}</span>
          </div>
          {isCheckingCli ? (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          ) : hfCliInstalled ? (
            <div className="flex items-center gap-2 text-sm text-success">
              <CheckCircle2 className="h-4 w-4" />
              <span>{t('projectSections.huggingface.cliInstalled')} {hfCliVersion && `(v${hfCliVersion})`}</span>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-warning" />
              <span className="text-sm text-warning">{t('projectSections.huggingface.cliNotInstalled')}</span>
              <Button variant="outline" size="sm" onClick={handleInstallCli}>
                <ExternalLink className="h-3 w-3 mr-1" />
                {t('projectSections.huggingface.installCli')}
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Auth Status */}
      {hfCliInstalled && (
        <>
          <Separator />
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <User className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">{t('projectSections.huggingface.authStatus')}</span>
              </div>
              {isCheckingAuth ? (
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              ) : isAuthenticated ? (
                <div className="flex items-center gap-2 text-sm text-success">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>{t('projectSections.huggingface.loggedInAs')} {username}</span>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 text-warning" />
                  <span className="text-sm text-warning">{t('projectSections.huggingface.notLoggedIn')}</span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleLogin}
                    disabled={isLoggingIn}
                  >
                    {isLoggingIn ? (
                      <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                    ) : null}
                    {t('projectSections.huggingface.login')}
                  </Button>
                </div>
              )}
            </div>
            {authError && (
              <p className="text-sm text-destructive">{authError}</p>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={checkAuth}
              disabled={isCheckingAuth}
            >
              <RefreshCw className={`h-3 w-3 mr-1 ${isCheckingAuth ? 'animate-spin' : ''}`} />
              {t('projectSections.huggingface.refreshStatus')}
            </Button>
          </div>
        </>
      )}

      {/* Repo Configuration */}
      {hfCliInstalled && isAuthenticated && (
        <>
          <Separator />
          <div className="space-y-3">
            <Label htmlFor="hf-repo-id">{t('projectSections.huggingface.repoIdLabel')}</Label>
            <p className="text-sm text-muted-foreground">
              {t('projectSections.huggingface.repoIdDescription')}
            </p>
            <Input
              id="hf-repo-id"
              placeholder="username/model-name"
              value={envConfig?.huggingfaceRepoId || ''}
              onChange={(e) => updateEnvConfig({ huggingfaceRepoId: e.target.value })}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-sm font-medium">{t('projectSections.huggingface.autoSyncLabel')}</Label>
              <p className="text-sm text-muted-foreground">
                {t('projectSections.huggingface.autoSyncDescription')}
              </p>
            </div>
            <Switch
              checked={envConfig?.huggingfaceAutoSync ?? false}
              onCheckedChange={(checked) => updateEnvConfig({ huggingfaceAutoSync: checked })}
            />
          </div>
        </>
      )}
    </div>
  );
}
