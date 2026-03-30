export const CONDITION_DISCLAIMER_COPY: Record<string, string> = {
  SESSION_AUTO:
    'This companion will only use your memory in this session.',
  SESSION_USER:
    'This companion will only use your memory in this session. You can review or alter it in Menu -> Memory.',
  PERSISTENT_AUTO:
    'This companion may use memory from this and future sessions.',
  PERSISTENT_USER:
    'This companion may use memory across sessions. You can review or alter it in Menu -> Memory.',
};

export function getConditionDisclaimer(conditionId: string): string {
  return (
    CONDITION_DISCLAIMER_COPY[conditionId] ??
    'This companion may use conversation memory to personalize responses.'
  );
}
