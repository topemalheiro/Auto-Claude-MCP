/**
 * Kanban Messaging Panel
 *
 * Shows active messaging configs for the current project.
 * Displayed in the kanban top bar, to the right of the RDR box.
 * Only renders when the project has at least 1 active messaging config.
 */

import { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Settings } from 'lucide-react';
import { Switch } from '../ui/switch';
import { Button } from '../ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '../ui/tooltip';
import { ScrollArea } from '../ui/scroll-area';
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

  // Derive tags/configs directly from store (no state duplication)
  const tags = settings.messagingTags ?? [];
  const configs = settings.messagingConfigs ?? [];

  const [activeConfigIds, setActiveConfigIds] = useState<string[]>([]);

  // Load project-specific active config IDs
  useEffect(() => {
    const project = projects.find(p => p.id === activeProjectId);
    setActiveConfigIds(project?.settings?.activeMessagingConfigIds ?? []);
  }, [activeProjectId, projects]);

  // Toggle a config's activation for this project (with rollback on failure)
  const toggleConfigForProject = useCallback(
    async (configId: string) => {
      if (!activeProjectId) return;

      const previousIds = activeConfigIds;
      const newIds = activeConfigIds.includes(configId)
        ? activeConfigIds.filter(id => id !== configId)
        : [...activeConfigIds, configId];

      setActiveConfigIds(newIds);
      try {
        await window.electronAPI.messaging.setActiveMessagingConfigs(activeProjectId, newIds);
      } catch (err) {
        console.error('[MessagingPanel] Failed to save active configs:', err);
        setActiveConfigIds(previousIds);
      }
    },
    [activeProjectId, activeConfigIds]
  );

  // Get tag by ID
  const getTag = (id: string) => tags.find(tag => tag.id === id);

  // Show configs that are active for this project
  const activeConfigs = configs.filter(c => activeConfigIds.includes(c.id));

  // Don't render panel if no configs are activated for this project
  if (activeConfigIds.length === 0) {
    return null;
  }

  return (
    <div className="relative border border-primary/30 rounded-lg px-3 py-2 mt-1">
      {/* Legend-style label */}
      <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 bg-background px-2 text-[10px] uppercase tracking-wider text-primary whitespace-nowrap">
        {t('tasks:kanban.messagingHeader', 'Messaging')}
      </span>

      <div className="flex items-center gap-2">
        {activeConfigs.length > 0 ? (
          <ScrollArea className="max-h-[80px] max-w-[280px]">
            <div className="flex flex-col gap-1">
              {activeConfigs.map(config => {
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
                        <span className={`text-[10px] truncate max-w-[120px] ${config.enabled ? 'text-muted-foreground' : 'text-muted-foreground/50 line-through'}`}>
                          {config.name}
                        </span>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" className="max-w-xs">
                      <p className="text-xs">
                        {!config.enabled && t('tasks:kanban.messagingDisabledGlobally', '(Disabled globally) ')}
                        {triggerTag ? `${t('tasks:kanban.messagingTag', 'Tag')}: ${triggerTag.name} | ` : ''}
                        {t('tasks:kanban.messagingTrigger', 'Trigger')}: {config.triggerStatus} | {config.receiver.type === 'rdr_mechanism' ? t('tasks:kanban.messagingRdrMechanism', 'RDR Mechanism') : `${t('tasks:kanban.messagingWindow', 'Window')}: ${config.receiver.windowTitle}`}
                      </p>
                    </TooltipContent>
                  </Tooltip>
                );
              })}
            </div>
          </ScrollArea>
        ) : (
          <span className="text-[10px] text-muted-foreground/50 italic">
            {t('tasks:kanban.messagingNoConfigs', 'No matching configs')}
          </span>
        )}

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
