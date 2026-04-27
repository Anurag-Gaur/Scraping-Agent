import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Upload, FileText, Bot, User, Loader2, LogOut, Shield, Plus, MessageSquare, Clock, Sun, Moon } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ── Theme tokens ──────────────────────────────────────────────────────────────
export const THEMES = {
  light: {
    name: 'light',
    pageBg: '#F0F4F8',
    navBg: '#FFFFFF',
    navBorder: '#E2E8F0',
    sidebarBg: '#FFFFFF',
    sidebarBorder: '#E2E8F0',
    mainBg: '#F8FAFC',
    inputAreaBg: '#FFFFFF',
    inputAreaBorder: '#E2E8F0',
    inputBg: '#F8FAFC',
    inputBorder: '#CBD5E1',
    inputText: '#1E293B',
    inputPlaceholder: '#94A3B8',
    cardBg: '#FFFFFF',
    cardBorder: '#E2E8F0',
    titleText: '#0F172A',
    bodyText: '#475569',
    mutedText: '#94A3B8',
    labelText: '#64748B',
    accent: '#1B6CA8',
    accentBg: '#EFF6FF',
    accentBorder: '#BFDBFE',
    accentText: '#1D4ED8',
    userBubbleBg: 'linear-gradient(135deg, #1B6CA8, #1D4ED8)',
    userBubbleBorder: '#1D4ED8',
    userBubbleText: '#FFFFFF',
    botBubbleBg: '#FFFFFF',
    botBubbleBorder: '#E2E8F0',
    botBubbleText: '#1E293B',
    sysBubbleBg: '#F1F5F9',
    sysBubbleBorder: '#E2E8F0',
    sysBubbleText: '#64748B',
    btnBg: 'linear-gradient(135deg, #1B6CA8, #1D4ED8)',
    btnShadow: '0 2px 8px rgba(27,108,168,0.3)',
    newChatBg: '#EFF6FF',
    newChatBorder: '#BFDBFE',
    newChatText: '#1D4ED8',
    histItemBg: '#F8FAFC',
    histItemBorder: '#E2E8F0',
    histItemActive: '#EFF6FF',
    histItemActiveBorder: '#BFDBFE',
    histItemActiveText: '#1D4ED8',
    histItemText: '#475569',
    uploadBg: '#F0F9FF',
    uploadBorder: '#BAE6FD',
    uploadText: '#0369A1',
    navStatusColor: '#059669',
    mdHeading: '#1B6CA8',
    mdBody: '#1E293B',
    mdCode: '#1B6CA8',
    mdCodeBg: '#EFF6FF',
    mdCodeBorder: '#BFDBFE',
    mdBullet: '#1B6CA8',
    glowColor: 'rgba(27,108,168,0.06)',
    sparkleColors: ['#1B6CA8', '#60A5FA', '#818CF8', '#34D399'],
    toggleBg: '#F1F5F9',
    toggleBorder: '#E2E8F0',
    scrollThumb: 'rgba(27,108,168,0.2)',
  },
  dark: {
    name: 'dark',

    pageBg: '#0D1117',  // page canvas — darkest
    navBg: '#13181F',  // topbar — 1 stop lighter
    navBorder: '#2A3140',  // visible separator
    sidebarBg: '#13181F',  // sidebar same as nav
    sidebarBorder: '#2A3140',
    mainBg: '#0D1117',  // chat area
    inputAreaBg: '#13181F',  // input strip matches nav
    inputAreaBorder: '#2A3140',
    inputBg: '#1A2232',
    inputBorder: '#3A4759',
    inputText: '#E8EDF3',
    inputPlaceholder: '#5A6A80',

    cardBg: '#13181F',
    cardBorder: '#2A3140',
    titleText: '#E8EDF3',
    bodyText: '#B8C5D6',
    mutedText: '#7A8FA6',
    labelText: '#7A8FA6',

    accent: '#4D9EFF',
    accentBg: 'rgba(77,158,255,0.12)',
    accentBorder: 'rgba(77,158,255,0.35)',
    accentText: '#7DB8FF',
    userBubbleBg: 'linear-gradient(135deg, #1A5FC8, #2D7EFF)',
    userBubbleBorder: '#2563EB',
    userBubbleText: '#FFFFFF',
    botBubbleBg: '#1A2232',
    botBubbleBorder: '#2E3E54',
    botBubbleText: '#D0DCE8',

    sysBubbleBg: '#151D2A',
    sysBubbleBorder: '#2A3140',
    sysBubbleText: '#7A8FA6',

    btnBg: 'linear-gradient(135deg, #1A5FC8, #2D7EFF)',
    btnShadow: '0 2px 12px rgba(45,126,255,0.4)',

    newChatBg: 'rgba(77,158,255,0.14)',
    newChatBorder: 'rgba(77,158,255,0.4)',
    newChatText: '#7DB8FF',
    histItemBg: 'rgba(255,255,255,0.04)',
    histItemBorder: '#2A3140',
    histItemActive: 'rgba(77,158,255,0.16)',
    histItemActiveBorder: 'rgba(77,158,255,0.45)',
    histItemActiveText: '#7DB8FF',
    histItemText: '#B8C5D6',

    uploadBg: 'rgba(77,158,255,0.09)',
    uploadBorder: 'rgba(77,158,255,0.38)',
    uploadText: '#7DB8FF',

    navStatusColor: '#3DD68C',
    mdHeading: '#7DB8FF',
    mdBody: '#D0DCE8',
    mdCode: '#7DB8FF',
    mdCodeBg: 'rgba(77,158,255,0.12)',
    mdCodeBorder: 'rgba(77,158,255,0.28)',
    mdBullet: '#4D9EFF',
    glowColor: 'rgba(77,158,255,0.07)',
    sparkleColors: ['#4D9EFF', '#7DB8FF', '#A5B4FC', '#3DD68C', '#F0ABFC'],
    toggleBg: '#1A2232',
    toggleBorder: '#3A4759',
    scrollThumb: 'rgba(77,158,255,0.35)',
  },
};
function renderMarkdown(text) {
  if (!text) return '';
  let html = text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/^#### (.+)$/gm, '<h4>$1</h4>').replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>').replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>').replace(/^---$/gm, '<hr/>')
    .replace(/^[-*] (.+)$/gm, '<li>$1</li>').replace(/^\d+\. (.+)$/gm, '<li class="ordered">$1</li>');
  html = html.replace(/(<li(?! class)[\s\S]*?<\/li>\n?)+/g, m =>
    m.includes('class="ordered"') ? '<ol>' + m.replace(/ class="ordered"/g, '') + '</ol>' : '<ul>' + m + '</ul>');
  html = html.split(/\n{2,}/).map(b => {
    const t2 = b.trim(); if (!t2) return '';
    if (/^<(h[1-4]|ul|ol|hr)/.test(t2)) return t2;
    return '<p>' + t2.replace(/\n/g, '<br/>') + '</p>';
  }).join('');
  return html;
}

function generateId() { return Date.now().toString(36) + Math.random().toString(36).substr(2, 5); }
function getTimeLabel(ts) {
  if (!ts) return '';
  const d = new Date(ts), diff = Date.now() - d;
  if (diff < 60000) return 'Just now';
  if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
  if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}



export default function Chat({ theme }) {
  const t = THEMES[theme];
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const messagesEndRef = useRef(null), currentMsgsRef = useRef([]), currentSessionRef = useRef(null);

  useEffect(() => { currentMsgsRef.current = messages; }, [messages]);
  useEffect(() => { currentSessionRef.current = currentSessionId; }, [currentSessionId]);
  const scrollToBottom = useCallback(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, []);
  useEffect(() => { scrollToBottom(); }, [messages]);



  const fetchSessions = useCallback(async () => {
    setHistoryLoading(true);
    try { const r = await fetch(API_URL + '/api/history/sessions'); const d = await r.json(); setSessions(d.sessions || []); }
    catch { setSessions([]); } finally { setHistoryLoading(false); }
  }, []);

  useEffect(() => { fetchSessions(); }, [fetchSessions]);

  const saveSession = useCallback(async (sessionId, msgs) => {
    if (!sessionId || !msgs || msgs.length === 0) return;
    const title = (msgs.find(m => m.role === 'user')?.content || 'New Chat').substring(0, 60);
    try { await fetch(API_URL + '/api/history/sessions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: sessionId, title, messages: msgs }) }); await fetchSessions(); }
    catch { }
  }, [fetchSessions]);

  const loadSession = useCallback(async (sessionId) => {
    await saveSession(currentSessionRef.current, currentMsgsRef.current);
    try { const r = await fetch(API_URL + '/api/history/sessions/' + sessionId); const d = await r.json(); setCurrentSessionId(d.id); setMessages(d.messages || []); await fetchSessions(); }
    catch { console.warn('Could not load session'); }
  }, [fetchSessions, saveSession]);

  const startNewChat = useCallback(async () => {
    await saveSession(currentSessionRef.current, currentMsgsRef.current);
    setCurrentSessionId(generateId()); setMessages([]);
  }, [saveSession]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    const text = input.trim(); setInput(''); setIsLoading(true);
    let sid = currentSessionRef.current; if (!sid) { sid = generateId(); setCurrentSessionId(sid); }
    const userMsg = { role: 'user', content: text, id: generateId() };
    const botId = generateId(), botPH = { role: 'assistant', content: '', sources: [], id: botId, streaming: true };
    setMessages(prev => [...prev, userMsg, botPH]);
    try {
      const res = await fetch(API_URL + '/api/chat/stream', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: text }) });
      if (!res.ok) throw new Error('Backend error');
      const reader = res.body.getReader(), decoder = new TextDecoder('utf-8');
      let full = '', buffer = '', srcs = [];
      while (true) {
        const { done, value } = await reader.read(); if (done) break;
        buffer += decoder.decode(value, { stream: true }); const lines = buffer.split('\n'); buffer = lines.pop();
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const ds = line.substring(6).trim(); if (!ds || ds === '[DONE]') continue;
          try {
            const p = JSON.parse(ds);
            if (p.type === 'token') { full += p.content; setMessages(prev => prev.map(m => m.id === botId ? { ...m, content: full } : m)); }
            else if (p.type === 'citations') { srcs = p.citations || []; setMessages(prev => prev.map(m => m.id === botId ? { ...m, sources: srcs } : m)); }
            else if (p.type === 'status') { setMessages(prev => prev.map(m => m.id === botId ? { ...m, searchStatus: p.content } : m)); }
          } catch { }
        }
      }
      setMessages(prev => prev.map(m => m.id === botId ? { ...m, content: full, sources: srcs, streaming: false } : m));
      await saveSession(sid, [...currentMsgsRef.current.filter(m => m.id !== botId && m.id !== userMsg.id), userMsg, { role: 'assistant', content: full, sources: srcs, id: botId }]);
    } catch {
      setMessages(prev => prev.map(m => m.id === botId ? { ...m, content: 'Error communicating with backend. Please try again.', streaming: false } : m));
    } finally { setIsLoading(false); }
  };



  const handleKeyDown = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } };

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div style={{ position: 'fixed', inset: 0, display: 'flex', flexDirection: 'column', fontFamily: "'Inter','Segoe UI',system-ui,sans-serif", overflow: 'hidden', background: t.pageBg }}>


      {/* TOP NAV */}
      <header style={{ position: 'relative', zIndex: 20, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 24px', height: 56, background: t.navBg, borderBottom: `1px solid ${t.navBorder}`, boxShadow: '0 1px 3px rgba(0,0,0,0.06)' }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 32, height: 32, borderRadius: 9, background: t.btnBg, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: t.btnShadow }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 2v20M2 12h20" stroke="white" strokeWidth="2.5" strokeLinecap="round" /><circle cx="12" cy="12" r="3.5" fill="white" /></svg>
          </div>
          <div>
            <span style={{ color: t.titleText, fontWeight: 700, fontSize: 14, letterSpacing: '-0.01em' }}>AgentFinder</span>
            <span style={{ color: t.mutedText, fontSize: 13, marginLeft: 6 }}>/ Agent Discovery</span>
          </div>
        </div>

        {/* Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600, color: t.navStatusColor, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: t.navStatusColor, boxShadow: `0 0 6px ${t.navStatusColor}` }} />
          System Online
        </div>

        {/* Right controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        </div>
      </header>

      {/* BODY */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', zIndex: 10 }}>

        {/* SIDEBAR */}
        <aside style={{ width: 260, flexShrink: 0, display: 'flex', flexDirection: 'column', background: t.sidebarBg, borderRight: `1px solid ${t.sidebarBorder}` }}>

          {/* New Chat */}
          <div style={{ padding: '12px 12px 10px' }}>
            <button onClick={startNewChat} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, padding: '10px 16px', background: t.newChatBg, border: `1px solid ${t.newChatBorder}`, borderRadius: 9, color: t.newChatText, fontSize: 13, fontWeight: 700, cursor: 'pointer', transition: 'all 0.18s', fontFamily: 'inherit' }}
              onMouseEnter={e => { e.currentTarget.style.background = t.accentBg; e.currentTarget.style.boxShadow = `0 2px 8px ${t.accent}22`; }}
              onMouseLeave={e => { e.currentTarget.style.background = t.newChatBg; e.currentTarget.style.boxShadow = 'none'; }}>
              <Plus size={14} /> New Chat
            </button>
          </div>

          {/* History */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '0 12px 10px', borderBottom: `1px solid ${t.sidebarBorder}` }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 5, color: t.mutedText, fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8, padding: '2px 0' }}>
              <Clock size={10} /> Chat History
            </div>
            {historyLoading ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 4px', color: t.mutedText, fontSize: 12 }}>
                <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} /> Loading...
              </div>
            ) : sessions.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '20px 8px', color: t.mutedText, fontSize: 12, lineHeight: 1.6 }}>
                <MessageSquare size={18} style={{ margin: '0 auto 8px', display: 'block', opacity: 0.3 }} />
                No history yet.<br />Start a conversation!
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                {sessions.map(session => {
                  const isActive = session.id === currentSessionId;
                  return (
                    <button key={session.id} onClick={() => loadSession(session.id)} style={{ width: '100%', textAlign: 'left', padding: '8px 10px', background: isActive ? t.histItemActive : t.histItemBg, border: `1px solid ${isActive ? t.histItemActiveBorder : t.histItemBorder}`, borderRadius: 8, cursor: 'pointer', fontFamily: 'inherit', transition: 'all 0.15s', display: 'flex', alignItems: 'flex-start', gap: 8 }}
                      onMouseEnter={e => { if (!isActive) { e.currentTarget.style.background = t.accentBg; e.currentTarget.style.borderColor = t.accentBorder; } }}
                      onMouseLeave={e => { if (!isActive) { e.currentTarget.style.background = t.histItemBg; e.currentTarget.style.borderColor = t.histItemBorder; } }}>
                      <MessageSquare size={11} color={isActive ? t.accent : t.mutedText} style={{ flexShrink: 0, marginTop: 2 }} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ color: isActive ? t.accentText : t.histItemText, fontSize: 12, fontWeight: isActive ? 600 : 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{session.title || 'Untitled Chat'}</div>
                        <div style={{ color: t.mutedText, fontSize: 10, marginTop: 1 }}>{getTimeLabel(session.timestamp)}</div>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '12px' }}>
            <div style={{ color: t.mutedText, fontSize: 10, textAlign: 'center', marginTop: 10, lineHeight: 1.5 }}>AgentFinder AI · RAG Platform</div>
          </div>
        </aside>

        {/* MAIN */}
        <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: t.mainBg }}>

          {/* Feed */}
          <div className="chat-scroll" style={{ flex: 1, overflowY: 'auto', padding: '28px 32px', display: 'flex', flexDirection: 'column' }}>
            {messages.length === 0 ? (
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: '0 24px' }}>
                <div style={{ width: 68, height: 68, borderRadius: 20, background: t.accentBg, border: `1px solid ${t.accentBorder}`, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 22, boxShadow: `0 4px 20px ${t.accent}20` }}>
                  <Bot size={32} color={t.accent} />
                </div>
                <h2 style={{ color: t.titleText, fontSize: 24, fontWeight: 700, marginBottom: 10, letterSpacing: '-0.01em' }}>Agent Discovery Assistant</h2>
                <p style={{ color: t.bodyText, fontSize: 15, maxWidth: 440, lineHeight: 1.7, marginBottom: 28 }}>
                  Ask compliance questions and get answers with precise source citations based on the active Knowledge Base.
                </p>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
                  {['Data Analysis Agents', 'Customer Support', 'Sales Automation', 'Coding Assistants'].map((tag, i) => (
                    <button key={i} onClick={() => setInput(tag)} style={{ background: t.accentBg, border: `1px solid ${t.accentBorder}`, borderRadius: 100, padding: '6px 16px', color: t.accentText, fontSize: 12, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit', transition: 'all 0.18s' }}
                      onMouseEnter={e => { e.currentTarget.style.background = t.accent; e.currentTarget.style.color = 'white'; e.currentTarget.style.borderColor = t.accent; }}
                      onMouseLeave={e => { e.currentTarget.style.background = t.accentBg; e.currentTarget.style.color = t.accentText; e.currentTarget.style.borderColor = t.accentBorder; }}
                    >{tag}</button>
                  ))}
                </div>
              </div>
            ) : (
              <div style={{ maxWidth: 780, width: '100%', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 18 }}>
                {messages.map(msg => (
                  <div key={msg.id} style={{ display: 'flex', flexDirection: msg.role === 'user' ? 'row-reverse' : 'row', alignItems: 'flex-start', gap: 10 }}>
                    {msg.role !== 'user' && (
                      <div style={{ flexShrink: 0, width: 32, height: 32, borderRadius: 9, background: msg.role === 'system' ? t.histItemBg : t.btnBg, border: `1px solid ${msg.role === 'system' ? t.sidebarBorder : t.accent}20`, display: 'flex', alignItems: 'center', justifyContent: 'center', marginTop: 2, boxShadow: msg.role === 'assistant' ? `0 2px 8px ${t.accent}25` : 'none' }}>
                        {msg.role === 'system' ? <FileText size={14} color={t.mutedText} /> : <Bot size={15} color="white" />}
                      </div>
                    )}
                    <div style={{ maxWidth: '78%', display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {msg.searchStatus && (!msg.content || msg.streaming) && (
                        <div style={{ alignSelf: 'flex-start', background: t.histItemBg, border: `1px solid ${t.sidebarBorder}`, borderRadius: 100, padding: '4px 12px', fontSize: 11, color: t.mutedText, display: 'flex', alignItems: 'center', gap: 6 }}>
                          <Loader2 size={10} style={{ animation: 'spin 1s linear infinite' }} />
                          {msg.searchStatus}
                        </div>
                      )}
                      <div style={{ background: msg.role === 'user' ? t.userBubbleBg : msg.role === 'system' ? t.sysBubbleBg : t.botBubbleBg, border: `1px solid ${msg.role === 'user' ? t.userBubbleBorder : msg.role === 'system' ? t.sysBubbleBorder : t.botBubbleBorder}`, borderRadius: msg.role === 'user' ? '16px 4px 16px 16px' : '4px 16px 16px 16px', padding: '12px 16px', boxShadow: msg.role === 'user' ? `0 2px 12px ${t.accent}30` : '0 1px 3px rgba(0,0,0,0.06)' }}>
                        {msg.role === 'assistant' ? (
                          <div>
                            {msg.content ? (
                              <div className="md-body" dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }} />
                            ) : (
                              <div style={{ display: 'flex', alignItems: 'center', gap: 5, height: 24, padding: '0 4px' }}>
                                {[0, 150, 300].map(delay => (
                                  <div key={delay} style={{ width: 6, height: 6, borderRadius: '50%', background: t.accent, animation: `bounce 1.2s ${delay}ms infinite` }} />
                                ))}
                              </div>
                            )}
                            {msg.streaming && msg.content && <span style={{ display: 'inline-block', width: 7, height: 15, background: t.accent, borderRadius: 2, marginLeft: 3, animation: 'blink 0.8s step-end infinite', verticalAlign: 'text-bottom' }} />}
                          </div>
                        ) : (
                          <p style={{ color: msg.role === 'user' ? t.userBubbleText : msg.role === 'system' ? t.sysBubbleText : t.botBubbleText, fontSize: 14, lineHeight: 1.65, margin: 0, fontStyle: msg.role === 'system' ? 'italic' : 'normal' }}>{msg.content}</p>
                        )}
                        {msg.sources?.length > 0 && (
                          <div style={{ marginTop: 12, paddingTop: 10, borderTop: `1px solid ${t.navBorder}` }}>
                            <div style={{ color: t.mutedText, fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 7 }}>Sources</div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                              {msg.sources.map((s, i) => (
                                <div key={i} title={s.text_snippet} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, background: t.accentBg, border: `1px solid ${t.accentBorder}`, borderRadius: 6, padding: '4px 9px', cursor: 'help' }}>
                                  <FileText size={10} color={t.accent} />
                                  <span style={{ color: t.accentText, fontSize: 11, fontWeight: 600 }}>{s.source} · p.{s.page}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                    {msg.role === 'user' && (
                      <div style={{ flexShrink: 0, width: 32, height: 32, borderRadius: 9, background: t.accentBg, border: `1px solid ${t.accentBorder}`, display: 'flex', alignItems: 'center', justifyContent: 'center', marginTop: 2 }}>
                        <User size={15} color={t.accent} />
                      </div>
                    )}
                  </div>
                ))}

                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* INPUT */}
          <div style={{ flexShrink: 0, padding: '14px 24px 18px', background: t.inputAreaBg, borderTop: `1px solid ${t.inputAreaBorder}`, boxShadow: '0 -1px 4px rgba(0,0,0,0.04)' }}>
            <div style={{ maxWidth: 780, margin: '0 auto' }}>
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: 10, background: t.inputBg, border: `1px solid ${t.inputBorder}`, borderRadius: 13, padding: '8px 10px 8px 16px', boxShadow: '0 1px 4px rgba(0,0,0,0.06)', transition: 'border-color 0.2s' }}
                onFocusCapture={e => { e.currentTarget.style.borderColor = t.accent; e.currentTarget.style.boxShadow = `0 0 0 3px ${t.accent}18`; }}
                onBlurCapture={e => { e.currentTarget.style.borderColor = t.inputBorder; e.currentTarget.style.boxShadow = '0 1px 4px rgba(0,0,0,0.06)'; }}>
                <textarea value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKeyDown} disabled={isLoading}
                  placeholder="Ask about an agent's capabilities or describe a problem you need solved..." rows={1}
                  style={{ flex: 1, background: 'none', border: 'none', outline: 'none', color: t.inputText, fontSize: 14, lineHeight: 1.6, resize: 'none', fontFamily: 'inherit', padding: '4px 0', maxHeight: 120, overflowY: 'auto' }}
                  onInput={e => { e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'; }}
                />
                <button onClick={handleSend} disabled={isLoading || !input.trim()} style={{ flexShrink: 0, width: 38, height: 38, background: (isLoading || !input.trim()) ? t.histItemBg : t.btnBg, border: `1px solid ${(isLoading || !input.trim()) ? t.inputBorder : t.accent}`, borderRadius: 9, cursor: (isLoading || !input.trim()) ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: (!isLoading && input.trim()) ? t.btnShadow : 'none', transition: 'all 0.18s' }}
                  onMouseEnter={e => { if (!isLoading && input.trim()) e.currentTarget.style.transform = 'scale(1.05)'; }}
                  onMouseLeave={e => { e.currentTarget.style.transform = 'scale(1)'; }}>
                  <Send size={14} color={(!isLoading && input.trim()) ? 'white' : t.mutedText} />
                </button>
              </div>
              <p style={{ textAlign: 'center', color: t.mutedText, fontSize: 11, marginTop: 7, fontWeight: 400 }}>
                AI may make errors · Verify critical agent capabilities against their official websites · Shift+Enter for new line
              </p>
            </div>
          </div>
        </main>
      </div>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        @keyframes spin  { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
        @keyframes bounce{ 0%,80%,100%{transform:translateY(0);opacity:0.4} 40%{transform:translateY(-5px);opacity:1} }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }

        /* Scrollbar — clearly visible in dark mode */
        .chat-scroll::-webkit-scrollbar       { width: 5px }
        .chat-scroll::-webkit-scrollbar-track { background: transparent }
        .chat-scroll::-webkit-scrollbar-thumb { background: ${t.scrollThumb}; border-radius: 4px }
        .chat-scroll::-webkit-scrollbar-thumb:hover { background: ${t.accent}; }

        /* Sidebar history scrollbar */
        aside::-webkit-scrollbar       { width: 4px }
        aside::-webkit-scrollbar-track { background: transparent }
        aside::-webkit-scrollbar-thumb { background: ${t.scrollThumb}; border-radius: 3px }

        textarea::placeholder { color: ${t.inputPlaceholder} !important }
        textarea:disabled     { opacity: 0.5 }
        * { box-sizing: border-box }

        /* ── Markdown body ── */
        .md-body {
          color: ${t.mdBody};
          font-size: 14px;
          line-height: 1.78;
        }
        .md-body p { margin: 0 0 10px 0 }
        .md-body p:last-child { margin-bottom: 0 }

        /* Headings — bright accent, clearly hierarchy */
        .md-body h1,.md-body h2,.md-body h3,.md-body h4 {
          color: ${t.mdHeading};
          font-weight: 700;
          margin: 16px 0 8px;
          line-height: 1.3;
          letter-spacing: -0.01em;
        }
        .md-body h1 { font-size: 17px }
        .md-body h2 { font-size: 15px }
        .md-body h3,.md-body h4 { font-size: 14px }

        /* Lists */
        .md-body ul { margin: 8px 0 12px; padding: 0; list-style: none }
        .md-body ol { margin: 8px 0 12px; padding: 0; list-style: none; counter-reset: ol-counter }
        .md-body ul li { position: relative; padding-left: 18px; margin-bottom: 5px; color: ${t.mdBody} }
        .md-body ul li::before {
          content: '';
          position: absolute; left: 5px; top: 8px;
          width: 5px; height: 5px; border-radius: 50%;
          background: ${t.mdBullet};
          box-shadow: 0 0 4px ${t.mdBullet}80;
        }
        .md-body ol li { position: relative; padding-left: 24px; margin-bottom: 5px; counter-increment: ol-counter; color: ${t.mdBody} }
        .md-body ol li::before {
          content: counter(ol-counter) '.';
          position: absolute; left: 0;
          color: ${t.mdBullet}; font-weight: 700; font-size: 12px; top: 1px;
        }

        /* Inline styles */
        .md-body strong { color: ${t.titleText}; font-weight: 700 }
        .md-body em     { color: ${t.bodyText}; font-style: italic }

        /* Code — high contrast pill */
        .md-body code {
          background: ${t.mdCodeBg};
          border: 1px solid ${t.mdCodeBorder};
          border-radius: 5px;
          padding: 2px 7px;
          font-size: 12.5px;
          color: ${t.mdCode};
          font-family: 'JetBrains Mono','Fira Code',monospace;
          font-weight: 500;
        }
        .md-body hr { border: none; border-top: 1px solid ${t.navBorder}; margin: 14px 0 }

        /* Input focus ring — visible in dark mode */
        textarea:focus { outline: none }
      `}</style>
    </div>
  );
}
