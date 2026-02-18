import { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, Trash2, Edit, Send, Tag, MessageSquare } from 'lucide-react';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Button } from '../ui/button';
import { Switch } from '../ui/switch';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { SettingsSection } from './SettingsSection';
import type { AppSettings } from '../../../shared/types';
import type { TaskTag, MessagingConfig, MessagingReceiver, MessagingTriggerStatus } from '../../../shared/types/messaging';
import { MESSAGING_TEMPLATE_VARIABLES, DEFAULT_MESSAGE_TEMPLATE, TAG_PRESET_COLORS } from '../../../shared/types/messaging';

interface MessagingSettingsProps {
  settings: AppSettings;
  onSettingsChange: (settings: AppSettings) => void;
}

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function MessagingSettings({ settings, onSettingsChange }: MessagingSettingsProps) {
  const { t } = useTranslation(['settings', 'common']);

  // Local state for tags and configs
  const [tags, setTags] = useState<TaskTag[]>(settings.messagingTags ?? []);
  const [configs, setConfigs] = useState<MessagingConfig[]>(settings.messagingConfigs ?? []);

  // Dialog state
  const [showTagDialog, setShowTagDialog] = useState(false);
  const [showConfigDialog, setShowConfigDialog] = useState(false);
  const [editingTag, setEditingTag] = useState<TaskTag | null>(null);
  const [editingConfig, setEditingConfig] = useState<MessagingConfig | null>(null);

  // Tag form
  const [tagName, setTagName] = useState('');
  const [tagColor, setTagColor] = useState<string>(TAG_PRESET_COLORS[0]);

  // Config form
  const [configName, setConfigName] = useState('');
  const [configTriggerTag, setConfigTriggerTag] = useState('');
  const [configTriggerStatus, setConfigTriggerStatus] = useState<MessagingTriggerStatus>('human_review');
  const [configTemplate, setConfigTemplate] = useState(DEFAULT_MESSAGE_TEMPLATE);
  const [configIncludeTaskInfo, setConfigIncludeTaskInfo] = useState(true);
  const [configReceiverType, setConfigReceiverType] = useState<MessagingReceiver['type']>('rdr_mechanism');
  const [configMechanismId, setConfigMechanismId] = useState('');
  const [configWindowTitle, setConfigWindowTitle] = useState('');

  // Sync from settings when they change externally
  useEffect(() => {
    setTags(settings.messagingTags ?? []);
    setConfigs(settings.messagingConfigs ?? []);
  }, [settings.messagingTags, settings.messagingConfigs]);

  // Persist changes to app settings
  const persistChanges = useCallback(
    (newTags: TaskTag[], newConfigs: MessagingConfig[]) => {
      onSettingsChange({
        ...settings,
        messagingTags: newTags,
        messagingConfigs: newConfigs,
      });
    },
    [settings, onSettingsChange]
  );

  // ── Tag CRUD ──

  const openCreateTag = () => {
    setEditingTag(null);
    setTagName('');
    setTagColor(TAG_PRESET_COLORS[0]);
    setShowTagDialog(true);
  };

  const openEditTag = (tag: TaskTag) => {
    setEditingTag(tag);
    setTagName(tag.name);
    setTagColor(tag.color);
    setShowTagDialog(true);
  };

  const saveTag = () => {
    if (!tagName.trim()) return;

    let newTags: TaskTag[];
    if (editingTag) {
      newTags = tags.map(t =>
        t.id === editingTag.id ? { ...t, name: tagName.trim(), color: tagColor } : t
      );
    } else {
      newTags = [...tags, { id: generateId(), name: tagName.trim(), color: tagColor }];
    }
    setTags(newTags);
    persistChanges(newTags, configs);
    setShowTagDialog(false);
  };

  const deleteTag = (tagId: string) => {
    const newTags = tags.filter(t => t.id !== tagId);
    // Also remove references in configs that use this tag
    const newConfigs = configs.map(c =>
      c.triggerTag === tagId ? { ...c, triggerTag: '', enabled: false } : c
    );
    setTags(newTags);
    setConfigs(newConfigs);
    persistChanges(newTags, newConfigs);
  };

  // ── Config CRUD ──

  const openCreateConfig = () => {
    setEditingConfig(null);
    setConfigName('');
    setConfigTriggerTag(tags[0]?.id ?? '');
    setConfigTriggerStatus('human_review');
    setConfigTemplate(DEFAULT_MESSAGE_TEMPLATE);
    setConfigIncludeTaskInfo(true);
    setConfigReceiverType('rdr_mechanism');
    setConfigMechanismId(settings.activeMechanismId ?? '');
    setConfigWindowTitle('');
    setShowConfigDialog(true);
  };

  const openEditConfig = (config: MessagingConfig) => {
    setEditingConfig(config);
    setConfigName(config.name);
    setConfigTriggerTag(config.triggerTag);
    setConfigTriggerStatus(config.triggerStatus);
    setConfigTemplate(config.messageTemplate);
    setConfigIncludeTaskInfo(config.includeTaskInfo);
    setConfigReceiverType(config.receiver.type);
    setConfigMechanismId(config.receiver.mechanismId ?? '');
    setConfigWindowTitle(config.receiver.windowTitle ?? '');
    setShowConfigDialog(true);
  };

  const saveConfig = () => {
    if (!configName.trim()) return;

    const receiver: MessagingReceiver = {
      type: configReceiverType,
      ...(configReceiverType === 'rdr_mechanism' ? { mechanismId: configMechanismId } : {}),
      ...(configReceiverType === 'specific_window' ? { windowTitle: configWindowTitle } : {}),
    };

    const configData: MessagingConfig = {
      id: editingConfig?.id ?? generateId(),
      name: configName.trim(),
      enabled: editingConfig?.enabled ?? true,
      triggerTag: configTriggerTag,
      triggerStatus: configTriggerStatus,
      messageTemplate: configTemplate,
      includeTaskInfo: configIncludeTaskInfo,
      receiver,
    };

    let newConfigs: MessagingConfig[];
    if (editingConfig) {
      newConfigs = configs.map(c => (c.id === editingConfig.id ? configData : c));
    } else {
      newConfigs = [...configs, configData];
    }
    setConfigs(newConfigs);
    persistChanges(tags, newConfigs);
    setShowConfigDialog(false);
  };

  const deleteConfig = (configId: string) => {
    const newConfigs = configs.filter(c => c.id !== configId);
    setConfigs(newConfigs);
    persistChanges(tags, newConfigs);
  };

  const toggleConfig = (configId: string) => {
    const newConfigs = configs.map(c =>
      c.id === configId ? { ...c, enabled: !c.enabled } : c
    );
    setConfigs(newConfigs);
    persistChanges(tags, newConfigs);
  };

  const testConfig = async (config: MessagingConfig) => {
    try {
      await window.electronAPI.messaging.testMessagingConfig(config);
    } catch (err) {
      console.error('[Messaging] Test failed:', err);
    }
  };

  // RDR mechanisms for the receiver dropdown
  const mechanisms = settings.rdrMechanisms ?? [];

  // Helper to get tag by ID
  const getTag = (id: string) => tags.find(t => t.id === id);

  return (
    <SettingsSection
      title={t('settings:messaging.title', 'MCP Messaging System')}
      description={t(
        'settings:messaging.description',
        'Configure tag-triggered messages. When a tagged task reaches a target status, a message is automatically sent via your chosen delivery mechanism.'
      )}
    >
      {/* ── Tags Section ── */}
      <div className="space-y-3">
        <div className="flex items-center justify-between px-4">
          <Label className="text-sm font-medium">
            <Tag className="w-3.5 h-3.5 inline mr-1.5" />
            {t('settings:messaging.tags.label', 'Tags')}
          </Label>
          <Button size="sm" variant="outline" onClick={openCreateTag}>
            <Plus className="w-3.5 h-3.5 mr-1" />
            {t('common:add', 'Add')}
          </Button>
        </div>

        {tags.length === 0 ? (
          <p className="text-xs text-muted-foreground px-4">
            {t('settings:messaging.tags.empty', 'No tags defined. Create tags to use with messaging configs.')}
          </p>
        ) : (
          <div className="flex flex-wrap gap-2 px-4">
            {tags.map(tag => (
              <div
                key={tag.id}
                className="flex items-center gap-1.5 px-2 py-1 rounded-full text-xs border cursor-pointer hover:bg-accent/50 transition-colors"
                onClick={() => openEditTag(tag)}
              >
                <span
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: tag.color }}
                />
                <span>{tag.name}</span>
                <button
                  className="ml-1 text-muted-foreground hover:text-destructive"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteTag(tag.id);
                  }}
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Configs Section ── */}
      <div className="space-y-3 mt-6">
        <div className="flex items-center justify-between px-4">
          <Label className="text-sm font-medium">
            <MessageSquare className="w-3.5 h-3.5 inline mr-1.5" />
            {t('settings:messaging.configs.label', 'Messaging Configs')}
          </Label>
          <Button
            size="sm"
            variant="outline"
            onClick={openCreateConfig}
            disabled={tags.length === 0}
          >
            <Plus className="w-3.5 h-3.5 mr-1" />
            {t('common:add', 'Add')}
          </Button>
        </div>

        {configs.length === 0 ? (
          <p className="text-xs text-muted-foreground px-4">
            {t(
              'settings:messaging.configs.empty',
              'No messaging configs. Create one to send messages when tagged tasks change status.'
            )}
          </p>
        ) : (
          <div className="space-y-2 px-4">
            {configs.map(config => {
              const triggerTag = getTag(config.triggerTag);
              return (
                <div
                  key={config.id}
                  className="flex items-center gap-3 p-2.5 rounded-md border bg-card"
                >
                  <Switch
                    checked={config.enabled}
                    onCheckedChange={() => toggleConfig(config.id)}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium truncate">{config.name}</span>
                      {triggerTag && (
                        <span
                          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] border"
                        >
                          <span
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: triggerTag.color }}
                          />
                          {triggerTag.name}
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-muted-foreground truncate">
                      {t('settings:messaging.configs.triggerOn', 'Trigger on')}: {config.triggerStatus} | {config.receiver.type === 'rdr_mechanism' ? 'RDR Mechanism' : `Window: ${config.receiver.windowTitle}`}
                    </p>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => testConfig(config)}
                      title={t('settings:messaging.configs.test', 'Send test message')}
                    >
                      <Send className="w-3.5 h-3.5" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => openEditConfig(config)}
                    >
                      <Edit className="w-3.5 h-3.5" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => deleteConfig(config.id)}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Tag Dialog ── */}
      <Dialog open={showTagDialog} onOpenChange={setShowTagDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingTag
                ? t('settings:messaging.tags.edit', 'Edit Tag')
                : t('settings:messaging.tags.create', 'Create Tag')}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>{t('common:name', 'Name')}</Label>
              <Input
                value={tagName}
                onChange={e => setTagName(e.target.value)}
                placeholder="e.g. deploy, urgent, review-needed"
              />
            </div>
            <div className="space-y-2">
              <Label>{t('settings:messaging.tags.color', 'Color')}</Label>
              <div className="flex gap-2">
                {TAG_PRESET_COLORS.map(color => (
                  <button
                    key={color}
                    className={`w-7 h-7 rounded-full border-2 transition-all ${
                      tagColor === color ? 'border-foreground scale-110' : 'border-transparent'
                    }`}
                    style={{ backgroundColor: color }}
                    onClick={() => setTagColor(color)}
                  />
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowTagDialog(false)}>
              {t('common:cancel', 'Cancel')}
            </Button>
            <Button onClick={saveTag} disabled={!tagName.trim()}>
              {t('common:save', 'Save')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Config Dialog ── */}
      <Dialog open={showConfigDialog} onOpenChange={setShowConfigDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editingConfig
                ? t('settings:messaging.configs.edit', 'Edit Messaging Config')
                : t('settings:messaging.configs.create', 'Create Messaging Config')}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4 max-h-[60vh] overflow-y-auto">
            {/* Name */}
            <div className="space-y-2">
              <Label>{t('common:name', 'Name')}</Label>
              <Input
                value={configName}
                onChange={e => setConfigName(e.target.value)}
                placeholder="e.g. Deploy Notification"
              />
            </div>

            {/* Trigger Tag */}
            <div className="space-y-2">
              <Label>{t('settings:messaging.configs.triggerTag', 'Trigger Tag')}</Label>
              <Select value={configTriggerTag} onValueChange={setConfigTriggerTag}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a tag" />
                </SelectTrigger>
                <SelectContent>
                  {tags.map(tag => (
                    <SelectItem key={tag.id} value={tag.id}>
                      <span className="flex items-center gap-2">
                        <span
                          className="w-2.5 h-2.5 rounded-full"
                          style={{ backgroundColor: tag.color }}
                        />
                        {tag.name}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Trigger Status */}
            <div className="space-y-2">
              <Label>{t('settings:messaging.configs.triggerStatus', 'Trigger When Status Reaches')}</Label>
              <Select value={configTriggerStatus} onValueChange={(v) => setConfigTriggerStatus(v as MessagingTriggerStatus)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="human_review">Human Review</SelectItem>
                  <SelectItem value="ai_review">AI Review</SelectItem>
                  <SelectItem value="done">Done</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Message Template */}
            <div className="space-y-2">
              <Label>{t('settings:messaging.configs.template', 'Message Template')}</Label>
              <div className="flex flex-wrap gap-1 mb-1">
                {MESSAGING_TEMPLATE_VARIABLES.map(v => (
                  <button
                    key={v.key}
                    className="text-[10px] px-1.5 py-0.5 rounded border bg-muted hover:bg-accent transition-colors"
                    onClick={() => setConfigTemplate(prev => prev + v.key)}
                    title={v.description}
                  >
                    {v.key}
                  </button>
                ))}
              </div>
              <Textarea
                value={configTemplate}
                onChange={e => setConfigTemplate(e.target.value)}
                rows={4}
                className="font-mono text-xs"
              />
            </div>

            {/* Include Task Info */}
            <div className="flex items-center gap-3">
              <Switch
                checked={configIncludeTaskInfo}
                onCheckedChange={setConfigIncludeTaskInfo}
              />
              <Label className="text-sm">
                {t('settings:messaging.configs.includeTaskInfo', 'Include full subtask details')}
              </Label>
            </div>

            {/* Receiver */}
            <div className="space-y-2">
              <Label>{t('settings:messaging.configs.receiver', 'Delivery Method')}</Label>
              <Select
                value={configReceiverType}
                onValueChange={(v) => setConfigReceiverType(v as MessagingReceiver['type'])}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="rdr_mechanism">RDR Mechanism</SelectItem>
                  <SelectItem value="specific_window">Specific Window</SelectItem>
                </SelectContent>
              </Select>

              {configReceiverType === 'rdr_mechanism' && mechanisms.length > 0 && (
                <Select value={configMechanismId} onValueChange={setConfigMechanismId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select mechanism" />
                  </SelectTrigger>
                  <SelectContent>
                    {mechanisms.map(m => (
                      <SelectItem key={m.id} value={m.id}>
                        {m.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}

              {configReceiverType === 'specific_window' && (
                <Input
                  value={configWindowTitle}
                  onChange={e => setConfigWindowTitle(e.target.value)}
                  placeholder="Window title (e.g. Visual Studio Code)"
                />
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowConfigDialog(false)}>
              {t('common:cancel', 'Cancel')}
            </Button>
            <Button onClick={saveConfig} disabled={!configName.trim() || !configTriggerTag}>
              {t('common:save', 'Save')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </SettingsSection>
  );
}
