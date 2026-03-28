import { useState, useRef, useEffect } from 'react';
import { useStore } from '../../store/ledger';
import { X } from 'lucide-react';

export default function ChatPanel() {
  const { chatOpen, chatMessages, chatLoading, toggleChat, sendMessage } = useStore();
  const [input, setInput] = useState('');
  const messagesEnd = useRef(null);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const handleSend = () => {
    if (!input.trim() || chatLoading) return;
    sendMessage(input.trim());
    setInput('');
  };

  return (
    <div className={`chat-panel ${chatOpen ? 'open' : ''}`}>
      <div className="chat-header">
        <h3>🐾 ClawFin Chat</h3>
        <button onClick={toggleChat} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-dim)' }}>
          <X size={18} />
        </button>
      </div>

      <div className="chat-messages">
        {chatMessages.length === 0 && (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '40px 0', fontSize: '13px' }}>
            <div style={{ fontSize: '32px', marginBottom: '12px' }}>🐾</div>
            Ask me about your finances.<br />
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              "What did I spend on groceries this month?"<br />
              "Show my top 5 merchants"<br />
              "Project my TFSA growth over 10 years"
            </span>
          </div>
        )}
        {chatMessages.map((msg, i) => (
          <div key={i} className={`chat-msg ${msg.role}`}>
            {msg.content}
          </div>
        ))}
        {chatLoading && (
          <div className="chat-msg assistant loading" style={{ width: '60px' }}>•••</div>
        )}
        <div ref={messagesEnd} />
      </div>

      <div className="chat-input-area">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Ask about your finances..."
          disabled={chatLoading}
        />
        <button onClick={handleSend} disabled={chatLoading}>Send</button>
      </div>
    </div>
  );
}
