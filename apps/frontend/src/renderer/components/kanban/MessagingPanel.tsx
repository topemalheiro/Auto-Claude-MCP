/**
 * Kanban Messaging Panel
 *
 * Shows active messaging configs for the current project.
 * Displayed in the kanban top bar, to the right of the RDR box.
 */

import { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { MessageSquare, Settings } from 'lucide-react';
import { Switch } from '../ui/switch';
import { Button } from '../ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '../ui/tooltip';
import { ScrollArea } from '../ui/scroll-area';
import type { TaskTag, MessagingConfig } from '../../../shared/types/messaging';
import { useSettingsStore } from '../../stores/settings-store';
import { useProjectStore } from '../../stores/project-store';

interface MessagingPanelProps {
  onOpenSettings?: () => void;
}

export function MessagingPanel({ onOpenSettings }: MessagingPanelProps) {
  const { t } = useTranslation(['tasks', 'common']);
  const settings = useSettingsStore(s => s.settings);
  const activeProjectId = useProjectStore(s => s.activeProjectId);
  const projects = useProjectStore(s => s.projects);

  const [tags, setTags] = useState<TaskTag[]>([]);
  const [configs, setConfigs] = useState<MessagingConfig[]>([]);
  const [activeConfigIds, setActiveConfigIds] = useState<string[]>([]);

  // Load global tags/configs from settings
  useEffect(() => {
    setTags(settings.messagingTags ?? []);
    setConfigs(settings.messagingConfigs ?? []);
  }, [settings.messagingTags, settings.messagingConfigs]);

  // Load project-specific active config IDs
  useEffect(() => {
    const project = projects.find(p => p.id === activeProjectId);
    setActiveConfigIds(project?.settings?.activeMessagingConfigIds ?? []);
  }, [activeProjectId, projects]);

  // Toggle a config's activation for this project
  const toggleConfigForProject = useCallback(
    async (configId: string) => {
      if (!activeProjectId) return;
      const newIds = activeConfigIds.includes(configId)
        ? activeConfigIds.filter(id => id !== configId)
        : [...activeConfigIds, configId];

      setActiveConfigIds(newIds);
      try {
        await window.electronAPI.messaging.setActiveMessagingConfigs(activeProjectId, newIds);
      } catch (err) {
        console.error('[MessagingPanel] Failed to save active configs:', err);
      }
    },
    [activeProjectId, activeConfigIds]
  );

  // Get tag by ID
  const getTag = (id: string) => tags.find(tag => tag.id === id);

  // Only show configs that are globally enabled
  const enabledConfigs = configs.filter(c => c.enabled);

  if (enabledConfigs.length === 0) {
    return null; // Don't render panel if no configs exist
  }

  return (
    <div className="relative border border-primary/30 rounded-lg px-3 py-2 mt-1">
      {/* Legend-style label */}
      <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 bg-background px-2 text-[10px] uppercase tracking-wider text-primary whitespace-nowrap">
        {t('tasks:kanban.messagingHeader', 'Messaging')}
      </span>

      <div className="flex items-center gap-2">
        <ScrollArea className="max-h-[80px] max-w-[280px]">
          <div className="flex flex-col gap-1">
            {enabledConfigs.map(config => {
              const triggerTag = getTag(config.triggerTag);
              const isActive = activeConfigIds.includes(config.id);

              return (
                <Tooltip key={config.id}>
                  <TooltipTrigger asChild>
                    <div className="flex items-center gap-1.5 min-w-0">
                      <Switch
                        checked={isActive}
                        onCheckedChange={() => toggleConfigForProject(config.id)}
                        className="scale-75"
                      />
                      {triggerTag && (
                        <span
                          className="w-2 h-2 rounded-full flex-shrink-0"
                          style={{ backgroundColor: triggerTag.color }}
                        />
                      )}
                      <span className="text-[10px] text-muted-foreground truncate max-w-[120px]">
                        {config.name}
                      </span>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="max-w-xs">
                    <p className="text-xs">
                      {triggerTag ? `Tag: ${triggerTag.name} | ` : ''}
                      Trigger: {config.triggerStatus} | {config.receiver.type === 'rdr_mechanism' ? 'RDR Mechanism' : `Window: ${config.receiver.windowTitle}`}
                    </p>
                  </TooltipContent>
                </Tooltip>
              );
            })}
          </div>
        </ScrollArea>

        {/* Settings button */}
        {onOpenSettings && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={onOpenSettings}
                className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground flex-shrink-0"
              >
                <Settings className="h-3 w-3" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom">
              <p>{t('tasks:kanban.messagingSettings', 'Messaging Settings')}</p>
            </TooltipContent>
          </Tooltip>
        )}
      </div>
    </div>
  );
}
