import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../services/api';

/**
 * AI Support Chatbot widget for LaunchDarkly observability demo.
 *
 * Floating chat bubble (bottom-right, above FeedbackWidget) that opens
 * a chat panel.  Messages are sent to /api/chat which forwards to
 * chat-service → Ollama.  Model and prompt are controlled by the LD
 * AI Config "support-chatbot".
 *
 * Exposes window.__sendChatMessage(text) so the Playwright simulator
 * can exercise the chatbot programmatically.
 */

const styles = {
  trigger: {
    position: 'fixed',
    bottom: '84px',
    right: '24px',
    width: '48px',
    height: '48px',
    borderRadius: '50%',
    background: '#10B981',
    color: '#fff',
    border: 'none',
    cursor: 'pointer',
    fontSize: '22px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 2px 8px rgba(0,0,0,0.25)',
    zIndex: 9998,
  },
  panel: {
    position: 'fixed',
    bottom: '144px',
    right: '24px',
    width: '360px',
    height: '440px',
    background: '#1a1a2e',
    border: '1px solid #333',
    borderRadius: '12px',
    zIndex: 9998,
    boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
    color: '#e0e0e0',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  header: {
    padding: '14px 16px',
    borderBottom: '1px solid #333',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerTitle: {
    margin: 0,
    fontSize: '15px',
    fontWeight: 600,
    color: '#fff',
  },
  headerSub: {
    margin: 0,
    fontSize: '11px',
    color: '#888',
  },
  messages: {
    flex: 1,
    overflowY: 'auto',
    padding: '12px 16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  userMsg: {
    alignSelf: 'flex-end',
    background: '#10B981',
    color: '#fff',
    padding: '8px 12px',
    borderRadius: '12px 12px 2px 12px',
    maxWidth: '80%',
    fontSize: '13px',
    lineHeight: '1.4',
    wordBreak: 'break-word',
  },
  botMsg: {
    alignSelf: 'flex-start',
    background: '#2a2a3e',
    color: '#e0e0e0',
    padding: '8px 12px',
    borderRadius: '12px 12px 12px 2px',
    maxWidth: '80%',
    fontSize: '13px',
    lineHeight: '1.4',
    wordBreak: 'break-word',
  },
  feedbackRow: {
    display: 'flex',
    gap: '6px',
    marginTop: '4px',
  },
  feedbackBtn: {
    background: 'transparent',
    border: '1px solid #444',
    borderRadius: '6px',
    color: '#888',
    cursor: 'pointer',
    fontSize: '14px',
    padding: '2px 8px',
    lineHeight: '1.4',
  },
  feedbackBtnActive: {
    background: 'transparent',
    border: '1px solid #10B981',
    borderRadius: '6px',
    color: '#10B981',
    cursor: 'default',
    fontSize: '14px',
    padding: '2px 8px',
    lineHeight: '1.4',
  },
  typing: {
    alignSelf: 'flex-start',
    color: '#888',
    fontSize: '12px',
    fontStyle: 'italic',
    padding: '4px 0',
  },
  inputRow: {
    display: 'flex',
    padding: '10px 12px',
    borderTop: '1px solid #333',
    gap: '8px',
  },
  input: {
    flex: 1,
    background: '#111',
    border: '1px solid #444',
    borderRadius: '8px',
    color: '#e0e0e0',
    padding: '8px 12px',
    fontSize: '13px',
    outline: 'none',
  },
  sendBtn: {
    background: '#10B981',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    padding: '8px 14px',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '13px',
  },
  sendBtnDisabled: {
    background: '#333',
    color: '#666',
    border: 'none',
    borderRadius: '8px',
    padding: '8px 14px',
    cursor: 'not-allowed',
    fontWeight: 600,
    fontSize: '13px',
  },
};

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const sendFeedback = useCallback(async (msgIndex, sentiment) => {
    const msg = messages[msgIndex];
    if (!msg || !msg.generationId || msg.feedback) return;

    // Optimistically mark feedback
    setMessages((prev) => prev.map((m, i) =>
      i === msgIndex ? { ...m, feedback: sentiment } : m
    ));

    await api.chatFeedback(msg.generationId, sentiment);
  }, [messages]);

  const sendMessage = useCallback(async (text) => {
    const userText = text.trim();
    if (!userText) return null;

    setMessages((prev) => [...prev, { role: 'user', content: userText }]);
    setLoading(true);

    try {
      const result = await api.chat(userText);
      const botResponse = result.success && result.data?.response
        ? result.data.response
        : "Sorry, I couldn't process your request right now.";
      const generationId = result.data?.generation_id || null;

      setMessages((prev) => [...prev, {
        role: 'bot',
        content: botResponse,
        generationId,
        feedback: null,
      }]);
      setLoading(false);
      return botResponse;
    } catch (err) {
      const fallback = "Sorry, something went wrong. Please try again.";
      setMessages((prev) => [...prev, { role: 'bot', content: fallback, generationId: null, feedback: null }]);
      setLoading(false);
      return fallback;
    }
  }, []);

  // Expose programmatic API for the simulator
  useEffect(() => {
    window.__sendChatMessage = async (text) => {
      // Open the widget if not already open
      setIsOpen(true);
      // Small delay to let React render the panel
      await new Promise((r) => setTimeout(r, 100));
      return sendMessage(text);
    };
    window.__sendChatFeedback = async (sentiment) => {
      // Find the last bot message with a generationId that hasn't been rated yet
      const idx = [...messages].reverse().findIndex(
        (m) => m.role === 'bot' && m.generationId && !m.feedback
      );
      if (idx === -1) return false;
      const realIdx = messages.length - 1 - idx;
      await sendFeedback(realIdx, sentiment);
      return true;
    };
    return () => {
      delete window.__sendChatMessage;
      delete window.__sendChatFeedback;
    };
  }, [sendMessage, sendFeedback, messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    const text = input;
    setInput('');
    sendMessage(text);
  };

  return (
    <>
      <button
        style={styles.trigger}
        onClick={() => setIsOpen(!isOpen)}
        data-testid="chat-trigger"
        aria-label="Open support chat"
      >
        {isOpen ? '\u2715' : '\uD83D\uDCAC'}
      </button>

      {isOpen && (
        <div style={styles.panel} data-testid="chat-panel">
          <div style={styles.header}>
            <div>
              <p style={styles.headerTitle}>Support Chat</p>
              <p style={styles.headerSub}>Powered by AI</p>
            </div>
          </div>

          <div style={styles.messages}>
            {messages.length === 0 && (
              <div style={{ ...styles.typing, textAlign: 'center', marginTop: '40px' }}>
                Hi! How can I help you today?
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i}>
                <div style={msg.role === 'user' ? styles.userMsg : styles.botMsg}>
                  {msg.content}
                </div>
                {msg.role === 'bot' && msg.generationId && (
                  <div style={styles.feedbackRow}>
                    <button
                      style={msg.feedback === 'positive' ? styles.feedbackBtnActive : styles.feedbackBtn}
                      onClick={() => !msg.feedback && sendFeedback(i, 'positive')}
                      disabled={!!msg.feedback}
                      data-testid="chat-feedback-positive"
                      aria-label="Thumbs up"
                    >
                      {'\uD83D\uDC4D'}
                    </button>
                    <button
                      style={msg.feedback === 'negative' ? styles.feedbackBtnActive : styles.feedbackBtn}
                      onClick={() => !msg.feedback && sendFeedback(i, 'negative')}
                      disabled={!!msg.feedback}
                      data-testid="chat-feedback-negative"
                      aria-label="Thumbs down"
                    >
                      {'\uD83D\uDC4E'}
                    </button>
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div style={styles.typing}>Thinking...</div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form style={styles.inputRow} onSubmit={handleSubmit}>
            <input
              style={styles.input}
              type="text"
              placeholder="Ask a question..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
              data-testid="chat-input"
            />
            <button
              type="submit"
              style={!input.trim() || loading ? styles.sendBtnDisabled : styles.sendBtn}
              disabled={!input.trim() || loading}
              data-testid="chat-send"
            >
              Send
            </button>
          </form>
        </div>
      )}
    </>
  );
}
