/**
 * Qualtrics integration utilities
 * Handles communication with Qualtrics parent window and URL parameter parsing
 */

export interface QualtricsParams {
  qualtrics_id: string | null;
  response_id: string | null;
  return_url: string | null;
  phase: number | null;
}

/**
 * Parse Qualtrics parameters from URL query string
 */
export function parseQualtricsParams(): QualtricsParams {
  if (typeof window === 'undefined') {
    return { qualtrics_id: null, response_id: null, return_url: null, phase: null };
  }

  const params = new URLSearchParams(window.location.search);
  const qualtrics_id = params.get('qualtrics_id');
  const response_id = params.get('response_id');
  const return_url = params.get('return_url');
  const phaseRaw = params.get('phase');
  const parsedPhase = phaseRaw ? Number.parseInt(phaseRaw, 10) : NaN;
  const phase = parsedPhase >= 1 && parsedPhase <= 3 ? parsedPhase : null;

  return {
    qualtrics_id,
    response_id,
    return_url,
    phase,
  };
}

/**
 * Check if running inside a Qualtrics iframe
 */
export function isInQualtricsIframe(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }
  try {
    return window.self !== window.top;
  } catch (e) {
    // If we can't access window.top, we're likely in an iframe
    return true;
  }
}

/**
 * Check if Qualtrics mode is active (has qualtrics_id parameter)
 */
export function isQualtricsMode(): boolean {
  const params = parseQualtricsParams();
  return params.response_id !== null || params.qualtrics_id !== null;
}

/**
 * Send a message to the Qualtrics parent window
 */
export function sendQualtricsMessage(action: string, data?: any): void {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    const message = {
      action,
      ...data,
    };

    console.log('Sending Qualtrics message:', message);
    
    // Always try to send to parent window
    // In iframe: sends to Qualtrics parent
    // Not in iframe: still sends (for testing), parent will be same as self
    if (window.parent) {
      window.parent.postMessage(message, '*'); // Use '*' for development, restrict in production
      console.log('postMessage sent to parent window');
    } else {
      console.warn('window.parent is not available');
    }
    
    // Also log if we're in an iframe or not
    const inIframe = window.self !== window.top;
    console.log('In iframe:', inIframe);
  } catch (e) {
    console.error('Error sending message to Qualtrics:', e);
  }
}

/**
 * Notify Qualtrics that the conversation is finished
 */
export function notifyQualtricsFinished(
  qualtrics_id: string,
  phase?: number | null,
  avatarData?: { agent_name?: string; agent_symbol?: string; agent_color?: string } | null
): void {
  const payload: any = { qualtrics_id, phase: phase ?? null };
  if (avatarData) {
    payload.agent_name = avatarData.agent_name;
    payload.agent_symbol = avatarData.agent_symbol;
    payload.agent_color = avatarData.agent_color;
  }
  sendQualtricsMessage('finish', payload);
}
