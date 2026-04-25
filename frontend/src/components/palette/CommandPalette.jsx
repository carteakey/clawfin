import { useEffect, useMemo, useRef, useState } from 'react';
import { useStore } from '../../store/ledger';
import { api } from '../../api/client';

const NAV_COMMANDS = [
  { id: 'nav:dashboard',    label: 'Go to Dashboard',     group: 'Go',     view: 'dashboard' },
  { id: 'nav:holdings',     label: 'Go to Holdings',      group: 'Go',     view: 'holdings' },
  { id: 'nav:accounts',     label: 'Go to Accounts',      group: 'Go',     view: 'accounts' },
  { id: 'nav:transactions', label: 'Go to Transactions',  group: 'Go',     view: 'transactions' },
  { id: 'nav:recurring',    label: 'Go to Recurring',     group: 'Go',     view: 'recurring' },
  { id: 'nav:planning',     label: 'Go to Planning',      group: 'Go',     view: 'planning' },
  { id: 'nav:import',       label: 'Go to Import',        group: 'Go',     view: 'import' },
  { id: 'nav:settings',     label: 'Go to Settings',      group: 'Go',     view: 'settings' },
];

export default function CommandPalette() {
  const paletteOpen = useStore((s) => s.paletteOpen);
  const closePalette = useStore((s) => s.closePalette);
  const setView = useStore((s) => s.setView);
  const toggleChat = useStore((s) => s.toggleChat);
  const theme = useStore((s) => s.theme);
  const setTheme = useStore((s) => s.setTheme);
  const [query, setQuery] = useState('');
  const [cursor, setCursor] = useState(0);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const inputRef = useRef(null);

  const commands = useMemo(() => {
    const actions = [
      {
        id: 'action:chat',
        label: 'Ask ClawFin (chat)',
        group: 'Action',
        hint: '⇧⌘K',
        run: () => { toggleChat(); },
      },
      {
        id: 'action:recategorize',
        label: 'Recategorize all transactions',
        group: 'Action',
        run: async () => {
          setBusy(true); setMsg('Recategorizing…');
          try {
            const r = await api.recategorize();
            setMsg(`Updated ${r.updated} / ${r.total}.`);
          } catch (e) {
            setMsg(`Error: ${e.message}`);
          } finally {
            setBusy(false);
          }
        },
      },
      {
        id: 'action:sync',
        label: 'Sync SimpleFin now',
        group: 'Action',
        run: async () => {
          setBusy(true); setMsg('Syncing…');
          try {
            const r = await api.simpleFinSync();
            setMsg(r?.imported !== undefined ? `Imported ${r.imported}, skipped ${r.skipped || 0}.` : 'Sync complete.');
          } catch (e) {
            setMsg(`Error: ${e.message}`);
          } finally {
            setBusy(false);
          }
        },
      },
      {
        id: 'action:theme',
        label: `Toggle theme (now ${theme.toUpperCase()})`,
        group: 'Action',
        run: () => setTheme(theme === 'dark' ? 'light' : 'dark'),
      },
    ];
    return [...NAV_COMMANDS, ...actions];
  }, [theme, setTheme, toggleChat]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return commands;
    return commands.filter((c) => c.label.toLowerCase().includes(q));
  }, [commands, query]);

  useEffect(() => {
    if (paletteOpen) {
      setQuery('');
      setCursor(0);
      setMsg('');
      // Focus after mount
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [paletteOpen]);

  useEffect(() => { setCursor(0); }, [query]);

  if (!paletteOpen) return null;

  const run = (cmd) => {
    if (!cmd) return;
    if (cmd.view) {
      setView(cmd.view);
      closePalette();
      return;
    }
    if (cmd.run) {
      const result = cmd.run();
      // If the command is async, keep palette open until it finishes
      if (result && typeof result.then === 'function') {
        result.finally(() => {/* leave open showing msg */});
      } else {
        closePalette();
      }
    }
  };

  const onKey = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setCursor((c) => Math.min(c + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setCursor((c) => Math.max(c - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      run(filtered[cursor]);
    } else if (e.key === 'Escape') {
      closePalette();
    }
  };

  return (
    <div
      className="palette-overlay"
      role="dialog"
      aria-modal="true"
      onMouseDown={(e) => { if (e.target === e.currentTarget) closePalette(); }}
    >
      <div className="palette" onMouseDown={(e) => e.stopPropagation()}>
        <input
          ref={inputRef}
          className="palette-input"
          placeholder="Type a command or search…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={onKey}
        />
        <ul className="palette-list" role="listbox">
          {filtered.length === 0 && (
            <li className="palette-empty">No matches.</li>
          )}
          {filtered.map((c, i) => (
            <li
              key={c.id}
              role="option"
              aria-selected={i === cursor}
              className={`palette-item ${i === cursor ? 'active' : ''}`}
              onMouseEnter={() => setCursor(i)}
              onClick={() => run(c)}
            >
              <span className="palette-group">{c.group}</span>
              <span className="palette-label">{c.label}</span>
              {c.hint && <span className="palette-hint">{c.hint}</span>}
            </li>
          ))}
        </ul>
        <div className="palette-footer">
          {busy ? <span className="loading">⏳ {msg}</span> : msg ? <span className="muted">{msg}</span> : (
            <>
              <kbd>↑↓</kbd> navigate <kbd>↵</kbd> run <kbd>Esc</kbd> close
            </>
          )}
        </div>
      </div>
    </div>
  );
}
