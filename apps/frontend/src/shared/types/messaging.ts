/**
 * MCP Messaging System types
 *
 * Global messaging configs stored in AppSettings, selectable per-project.
 * Tags assigned per-task in TaskMetadata.
 */

/** Tag definition (global, reusable across projects) */
export interface TaskTag {
  id: string;
  name: string;
  color: string;
}

/** Receiver configuration for message delivery */
export interface MessagingReceiver {
  type: 'rdr_mechanism' | 'specific_window';
  /** RDR mechanism ID (when type = 'rdr_mechanism') */
  mechanismId?: string;
  /** Window title pattern (when type = 'specific_window') */
  windowTitle?: string;
}

/** Messaging config definition (global, selectable per-project) */
export interface MessagingConfig {
  id: string;
  name: string;
  enabled: boolean;
  /** Tag ID that triggers this config */
  triggerTag: string;
  /** Task status that triggers the message */
  triggerStatus: MessagingTriggerStatus;
  /** Message template with {{variable}} placeholders */
  messageTemplate: string;
  /** Include full subtask details in the message (default: true) */
  includeTaskInfo: boolean;
  /** How/where to deliver the message */
  receiver: MessagingReceiver;
}

export type MessagingTriggerStatus = 'human_review' | 'done' | 'ai_review';

/** Template variables available in message templates */
export const MESSAGING_TEMPLATE_VARIABLES = [
  { key: '{{taskName}}', description: 'Task/spec title' },
  { key: '{{taskStatus}}', description: 'Current task status' },
  { key: '{{specId}}', description: 'Spec ID (e.g. "071-marko")' },
  { key: '{{projectName}}', description: 'Project name' },
  { key: '{{subtaskSummary}}', description: 'All subtasks with status' },
  { key: '{{completedCount}}', description: 'Number of completed subtasks' },
  { key: '{{totalCount}}', description: 'Total number of subtasks' },
] as const;

/** Default message template */
export const DEFAULT_MESSAGE_TEMPLATE =
  '[Auto-Claude Messaging] Task {{taskName}} ({{specId}}) reached {{taskStatus}}.\n\nProgress: {{completedCount}}/{{totalCount}} subtasks complete.';

/** Preset tag colors */
export const TAG_PRESET_COLORS = [
  '#ef4444', // red
  '#f97316', // orange
  '#eab308', // yellow
  '#22c55e', // green
  '#06b6d4', // cyan
  '#3b82f6', // blue
  '#8b5cf6', // violet
  '#ec4899', // pink
] as const;
