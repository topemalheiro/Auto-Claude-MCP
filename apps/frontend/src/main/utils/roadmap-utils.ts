/**
 * Shared roadmap file utilities for updating feature outcomes.
 *
 * Used by task deletion (crud-handlers.ts) and archival (project-store.ts)
 * to update linked roadmap features when tasks change state.
 */

import { existsSync } from 'fs';
import { readFileWithRetry, writeFileWithRetry } from './atomic-file';
import { withFileLock } from './file-lock';

/**
 * Update roadmap features on disk when linked tasks change state.
 *
 * Finds features matching the given specIds and sets their status to 'done'
 * with the specified taskOutcome. Uses file locking and retry logic to
 * prevent concurrent write races.
 *
 * @param roadmapFile - Absolute path to roadmap.json
 * @param specIds - Spec IDs to match against feature.linked_spec_id / linkedSpecId
 * @param taskOutcome - The outcome to set on matched features
 * @param logPrefix - Prefix for log messages (e.g., '[TASK_CRUD]')
 */
export async function updateRoadmapFeatureOutcome(
  roadmapFile: string,
  specIds: string[],
  taskOutcome: 'completed' | 'deleted' | 'archived',
  logPrefix = '[Roadmap]'
): Promise<void> {
  if (!existsSync(roadmapFile)) return;

  const specIdSet = new Set(specIds);

  await withFileLock(roadmapFile, async () => {
    try {
      const content = await readFileWithRetry(roadmapFile, { encoding: 'utf-8' });
      const roadmap = JSON.parse(content as string);

      if (!roadmap.features || !Array.isArray(roadmap.features)) return;

      let changed = false;
      for (const feature of roadmap.features) {
        const linkedId = feature.linked_spec_id || feature.linkedSpecId;
        if (linkedId && specIdSet.has(linkedId) && (feature.status !== 'done' || feature.task_outcome !== taskOutcome)) {
          feature.status = 'done';
          feature.task_outcome = taskOutcome;
          changed = true;
        }
      }

      if (changed) {
        roadmap.metadata = roadmap.metadata || {};
        roadmap.metadata.updated_at = new Date().toISOString();
        await writeFileWithRetry(roadmapFile, JSON.stringify(roadmap, null, 2));
        console.log(`${logPrefix} Updated roadmap features for ${specIds.length} task(s) with outcome: ${taskOutcome}`);
      }
    } catch (err) {
      console.warn(`${logPrefix} Failed to update roadmap for tasks [${specIds.join(', ')}]:`, err);
    }
  });
}
