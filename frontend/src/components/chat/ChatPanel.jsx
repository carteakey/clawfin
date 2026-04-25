import { useState, useRef, useEffect } from 'react';
import { useStore } from '../../store/ledger';
import { api } from '../../api/client';

export default function ChatPanel() {
  const { chatOpen, chatMessages, chatLoading, toggleChat, sendMessage, sendBriefing } = useStore();
  const [input, setInput] = useState('');
  const [aiConfig, setAiConfig] = useState(null);
  const messagesEnd = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    api.getAIConfig().then(setAiConfig).catch(() => {});
  }, []);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  useEffect(() => {
    if (chatOpen) inputRef.current?.focus();
  }, [chatOpen]);

  const handleSend = () => {
    if (!input.trim() || chatLoading) return;
    sendMessage(input.trim());
    setInput('');
  };

  const runPreset = (briefing) => {
    if (chatLoading) return;
    sendBriefing(briefing);
  };

  const modelLabel = aiConfig
    ? `${(aiConfig.provider || 'none').toUpperCase()} · ${aiConfig.model || '—'}`
    : '';

  return (
    <div className={`chat-panel ${chatOpen ? 'open' : ''}`}>
      <div className="chat-header">
        <div>
          <div className="ch-title">Chat</div>
          {modelLabel && <div className="ch-model">{modelLabel}</div>}
        </div>
        <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
          {chatMessages.length > 0 && (
            <button type="button" className="btn btn-ghost" onClick={clearChat} style={{ padding: '2px 8px', fontSize: 10 }}>CLEAR</button>
          )}
          <button type="button" className="btn btn-ghost" onClick={toggleChat} style={{ padding: '2px 8px' }}>×</button>
        </div>
      </div>

      <div className="chat-messages">
        {chatMessages.length === 0 && (
          <div style={{ padding: 'var(--sp-5) 0' }}>
            <div className="label mb-3">Ask Your Ledger</div>
            <div className="chat-presets" style={{ gridTemplateColumns: '1fr' }}>
              <button
                type="button"
                onClick={() => runPreset({ period: 'weekly' })}
                disabled={chatLoading}
              >
                Weekly Brief
              </button>
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, lineHeight: 1.7, color: 'var(--ink-2)' }}>
              &gt; what did i spend on groceries last month<br />
              &gt; show my top 5 merchants<br />
              &gt; project my TFSA at 7% over 10y<br />
              &gt; what recurring charges do i have
            </div>
          </div>
        )}
        {chatMessages.map((msg, i) => (
          <div key={i} className={`chat-msg ${msg.role}`}>
            <div className="role">{msg.role === 'user' ? '&gt; You' : '&#8226; Assistant'}</div>
            <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
          </div>
        ))}
        {chatLoading && (
          <div className="chat-msg loading">
            <div className="role">&#8226; Assistant</div>
            <div className="num">...</div>
          </div>
        )}
        <div ref={messagesEnd} />
      </div>

      <div className="chat-input-area">
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Ask…"
          disabled={chatLoading}
        />
        <button type="button" className="btn btn-primary" onClick={handleSend} disabled={chatLoading || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}
