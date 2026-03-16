import { useState, useEffect, useCallback } from 'react';
import { useLDClient } from 'launchdarkly-react-client-sdk';
import { LDRecord } from '@launchdarkly/session-replay';

/**
 * Qualitative feedback widget for LaunchDarkly.
 *
 * Sends feedback via ldClient.track('$ld:feedback', ...) so it appears
 * on the flag's Feedback tab in the LD dashboard.
 *
 * Also exposes window.__submitFeedback(flagKey, sentiment, text) so the
 * Playwright simulator can submit feedback programmatically with sentiment
 * correlated to whether the user encountered errors.
 */

const FLAG_KEYS_FOR_FEEDBACK = [
  'releaseNewUI',
  'showNewHero',
  'showNewFeatures',
  'migrate-warehouse-api',
];

const FEEDBACK_PROMPT = 'How is your experience with this feature?';

const styles = {
  trigger: {
    position: 'fixed',
    bottom: '24px',
    right: '24px',
    width: '48px',
    height: '48px',
    borderRadius: '50%',
    background: '#405BFF',
    color: '#fff',
    border: 'none',
    cursor: 'pointer',
    fontSize: '22px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 2px 8px rgba(0,0,0,0.25)',
    zIndex: 9999,
  },
  panel: {
    position: 'fixed',
    bottom: '84px',
    right: '24px',
    width: '320px',
    background: '#1a1a2e',
    border: '1px solid #333',
    borderRadius: '12px',
    padding: '20px',
    zIndex: 9999,
    boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
    color: '#e0e0e0',
  },
  title: {
    margin: '0 0 4px 0',
    fontSize: '15px',
    fontWeight: 600,
    color: '#fff',
  },
  prompt: {
    margin: '0 0 12px 0',
    fontSize: '13px',
    color: '#aaa',
  },
  sentimentRow: {
    display: 'flex',
    gap: '8px',
    marginBottom: '12px',
  },
  sentimentBtn: (active) => ({
    flex: 1,
    padding: '8px',
    border: active ? '2px solid #405BFF' : '1px solid #444',
    borderRadius: '8px',
    background: active ? 'rgba(64,91,255,0.15)' : 'transparent',
    cursor: 'pointer',
    fontSize: '20px',
    textAlign: 'center',
  }),
  textarea: {
    width: '100%',
    minHeight: '70px',
    background: '#111',
    border: '1px solid #444',
    borderRadius: '8px',
    color: '#e0e0e0',
    padding: '10px',
    fontSize: '13px',
    resize: 'vertical',
    boxSizing: 'border-box',
  },
  submit: {
    marginTop: '10px',
    width: '100%',
    padding: '10px',
    background: '#405BFF',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '14px',
  },
  submitDisabled: {
    marginTop: '10px',
    width: '100%',
    padding: '10px',
    background: '#333',
    color: '#888',
    border: 'none',
    borderRadius: '8px',
    cursor: 'not-allowed',
    fontWeight: 600,
    fontSize: '14px',
  },
  thanks: {
    textAlign: 'center',
    padding: '20px 0',
    color: '#aaa',
    fontSize: '14px',
  },
};

export default function FeedbackWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [sentiment, setSentiment] = useState(null);
  const [feedback, setFeedback] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const ldClient = useLDClient();

  const sendFeedback = useCallback((flagKey, sentimentVal, text) => {
    if (!ldClient) return false;

    const validSentiments = ['positive', 'neutral', 'negative'];
    const safeSentiment = validSentiments.includes(sentimentVal)
      ? sentimentVal
      : 'neutral';

    const data = {
      feedback_answer: text,
      flag_key: flagKey,
      sentiment: safeSentiment,
      feedback_prompt: FEEDBACK_PROMPT,
    };

    // Tie feedback to the current observability session
    const sessionID = LDRecord.getSession()?.sessionSecureID;
    if (sessionID) {
      data.o11y_session_id = sessionID;
    }

    ldClient.track('$ld:feedback', data);
    ldClient.flush();
    return true;
  }, [ldClient]);

  // Expose programmatic API for the simulator
  useEffect(() => {
    window.__submitFeedback = (flagKey, sentimentVal, text) => {
      return sendFeedback(flagKey, sentimentVal, text);
    };
    return () => { delete window.__submitFeedback; };
  }, [sendFeedback]);

  const handleSubmit = () => {
    if (!sentiment || !feedback.trim()) return;
    // Pick a random flag to associate feedback with
    const flagKey = FLAG_KEYS_FOR_FEEDBACK[
      Math.floor(Math.random() * FLAG_KEYS_FOR_FEEDBACK.length)
    ];
    sendFeedback(flagKey, sentiment, feedback.trim());
    setSubmitted(true);
    setTimeout(() => {
      setIsOpen(false);
      setSubmitted(false);
      setSentiment(null);
      setFeedback('');
    }, 2000);
  };

  return (
    <>
      <button
        style={styles.trigger}
        onClick={() => setIsOpen(!isOpen)}
        data-testid="feedback-trigger"
        aria-label="Give feedback"
      >
        {isOpen ? '\u2715' : '\u270E'}
      </button>

      {isOpen && (
        <div style={styles.panel} data-testid="feedback-panel">
          {submitted ? (
            <div style={styles.thanks}>Thanks for your feedback!</div>
          ) : (
            <>
              <p style={styles.title}>Share your feedback</p>
              <p style={styles.prompt}>{FEEDBACK_PROMPT}</p>

              <div style={styles.sentimentRow}>
                <button
                  style={styles.sentimentBtn(sentiment === 'positive')}
                  onClick={() => setSentiment('positive')}
                  data-testid="feedback-positive"
                >
                  &#128077;
                </button>
                <button
                  style={styles.sentimentBtn(sentiment === 'neutral')}
                  onClick={() => setSentiment('neutral')}
                  data-testid="feedback-neutral"
                >
                  &#128528;
                </button>
                <button
                  style={styles.sentimentBtn(sentiment === 'negative')}
                  onClick={() => setSentiment('negative')}
                  data-testid="feedback-negative"
                >
                  &#128078;
                </button>
              </div>

              <textarea
                style={styles.textarea}
                placeholder="Tell us about your experience..."
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                data-testid="feedback-text"
              />

              <button
                style={sentiment && feedback.trim()
                  ? styles.submit
                  : styles.submitDisabled}
                onClick={handleSubmit}
                disabled={!sentiment || !feedback.trim()}
                data-testid="feedback-submit"
              >
                Send Feedback
              </button>
            </>
          )}
        </div>
      )}
    </>
  );
}
