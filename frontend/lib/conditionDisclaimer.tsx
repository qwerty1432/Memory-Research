import { ReactNode } from 'react';

export const CONDITION_DISCLAIMER_COPY: Record<string, ReactNode> = {
  SESSION_AUTO: (
    <>
      This companion will only use your memory <strong>in this session</strong>. All information
      will be reset - the AI <strong>won&apos;t remember anything</strong> in the next session.
    </>
  ),
  PERSISTENT_AUTO: (
    <>
      This companion uses memory automatically. <strong>All information will be carried to the next session</strong>{' '}
      of chat.
    </>
  ),
  PERSISTENT_USER: (
    <>
      This companion automatically saves memories from your conversation and uses them{' '}
      <strong>across sessions</strong>. You can review, edit, or delete any of them in
      Menu -&gt; Memory. <strong>Any memories you delete will not carry into future sessions.</strong>
    </>
  ),
};

export function getConditionDisclaimer(conditionId: string): ReactNode {
  return (
    CONDITION_DISCLAIMER_COPY[conditionId] ?? 'This companion may use conversation memory to personalize responses.'
  );
}
