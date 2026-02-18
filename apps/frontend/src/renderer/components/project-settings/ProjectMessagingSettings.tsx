/**
 * Project-level Messaging Settings
 *
 * Lets the user activate/deactivate global messaging configs for this project,
 * and assign tags to tasks within the project.
 * Global tag & config CRUD lives in App Settings > Messaging.
 */

import { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Tag, MessageSquare, Settings } from 'lucide-react';
import { Label } from '../ui/label';
import { Button } from '../ui/button';
import { Switch } from '../ui/switch';
import type { Project, ProjectSettings } from '../../../shared/types';
import type { TaskTag, MessagingConfig } from '../../../shared/types/messaging';

interface ProjectMessagingSettingsProps {
  project: Project;
  settings: ProjectSettings;
  setSettings: React.Dispatch<React.SetStateAction<ProjectSettings>>;
  onNavigateToAppMessaging?: () => void;
}

export function ProjectMessagingSettings({
  project,
  settings,
  setSettings,
  onNavigateToAppMessaging,
}: ProjectMessagingSettingsProps) {
  const { t } = useTranslation(['settings', 'common']);

  // Global tags & configs from app settings
  const [globalTags, setGlobalTags] = useState<TaskTag[]>([]);
  const [globalConfigs, setGlobalConfigs] = useState<MessagingConfig[]>([]);
  const [loading, setLoading] = useState(true);

  // Per-project active config IDs
  const activeIds = settings.activeMessagingConfigIds ?? [];

  // Load global configs on mount
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    window.electronAPI.messaging
      .getMessagingConfigs()
      .then((result) => {
        if (!cancelled && result.success && result.data) {
          setGlobalTags(result.data.tags);
          setGlobalConfigs(result.data.configs);
        }
      })
      .catch((err) => console.error('[ProjectMessaging] Failed to load global configs:', err))
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Toggle a config active/inactive for this project
  const toggleConfig = useCallback(
    (configId: string) => {
      const current = settings.activeMessagingConfigIds ?? [];
      const next = current.includes(configId)
        ? current.filter((id) => id !== configId)
        : [...current, configId];

      setSettings((prev) => ({
        ...prev,
        activeMessagingConfigIds: next,
      }));
    },
    [settings.activeMessagingConfigIds, setSettings],
  );

  // Helper to get tag by ID
  const getTag = (id: string) => globalTags.find((t) => t.id === id);

  if (loading) {
    return (
      <div className="text-sm text-muted-foreground px-4 py-8 text-center">
        {t('common:loading', 'Loading...')}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Description + link to global settings */}
      <div className="px-4 text-sm text-muted-foreground">
        {t(
          'settings:projectSections.messaging.activateDescription',
          'Choose which global messaging configs are active for this project. Manage tags and configs in App Settings > Messaging.',
        )}
      </div>

      {/* Available Tags (read-only display) */}
      {globalTags.length > 0 && (
        <div className="space-y-2">
          <Label className="text-sm font-medium px-4">
            <Tag className="w-3.5 h-3.5 inline mr-1.5" />
            {t('settings:messaging.tags.label', 'Tags')}
          </Label>
          <div className="flex flex-wrap gap-2 px-4">
            {globalTags.map((tag) => (
              <span
                key={tag.id}
                className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs border"
              >
                <span
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: tag.color }}
                />
                {tag.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Active Messaging Configs for this project */}
      <div className="space-y-3">
        <Label className="text-sm font-medium px-4">
          <MessageSquare className="w-3.5 h-3.5 inline mr-1.5" />
          {t(
            'settings:projectSections.messaging.activeConfigs',
            'Active Messaging Configs',
          )}
        </Label>

        {globalConfigs.length === 0 ? (
          <div className="px-4 py-6 text-center">
            <p className="text-sm text-muted-foreground mb-3">
              {t(
                'settings:projectSections.messaging.noGlobalConfigs',
                'No messaging configs defined yet. Create them in App Settings first.',
              )}
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={onNavigateToAppMessaging}
              disabled={!onNavigateToAppMessaging}
            >
              <Settings className="w-3.5 h-3.5 mr-1.5" />
              {t(
                'settings:projectSections.messaging.openAppSettings',
                'Open App Settings',
              )}
            </Button>
          </div>
        ) : (
          <div className="space-y-2 px-4">
            {globalConfigs.map((config) => {
              const triggerTag = getTag(config.triggerTag);
              const isActive = activeIds.includes(config.id);

              return (
                <div
                  key={config.id}
                  className="flex items-center gap-3 p-3 rounded-md border bg-card"
                >
                  <Switch
                    checked={isActive}
                    onCheckedChange={() => toggleConfig(config.id)}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium truncate">
                        {config.name}
                      </span>
                      {!config.enabled && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                          {t('common:disabled', 'Disabled')}
                        </span>
                      )}
                      {triggerTag && (
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] border">
                          <span
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: triggerTag.color }}
                          />
                          {triggerTag.name}
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-muted-foreground truncate">
                      {t('settings:messaging.configs.triggerOn', 'Trigger on')}:{' '}
                      {config.triggerStatus} |{' '}
                      {config.receiver.type === 'rdr_mechanism'
                        ? 'RDR Mechanism'
                        : `Window: ${config.receiver.windowTitle}`}
                    </p>
                  </div>
                </div>
              );
            })}

            <p className="text-xs text-muted-foreground pt-1">
              {t(
                'settings:projectSections.messaging.activeCount',
                '{{count}} of {{total}} configs active for this project',
                {
                  count: activeIds.filter((id) =>
                    globalConfigs.some((c) => c.id === id),
                  ).length,
                  total: globalConfigs.length,
                },
              )}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
