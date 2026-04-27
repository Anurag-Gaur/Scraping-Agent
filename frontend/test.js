
const API_URL = "http://127.0.0.1:8000";
const snippetStore = new Map();

const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const messagesList = document.getElementById('messages-list');
const chatFeed = document.getElementById('chat-feed');
const welcomeScreen = document.getElementById('welcome-screen');
const typingIndicator = document.getElementById('typing-indicator');
const fileUpload = document.getElementById('file-upload');
const uploadZone = document.getElementById('upload-zone');
const uploadTitle = document.getElementById('upload-title');
const uploadSubtitle = document.getElementById('upload-subtitle');
const newChatBtn = document.getElementById('new-chat-btn');
const historyList = document.getElementById('history-list');
const historyEmpty = document.getElementById('history-empty');

marked.setOptions({ breaks: true, gfm: true });

// ===== AUTHENTICATION STATE =====
let authToken = localStorage.getItem('pharma_rag_token') || null;
let authRole = localStorage.getItem('pharma_rag_role') || null;
let authEmail = localStorage.getItem('pharma_rag_email') || null;
let isLoginMode = true;

const authOverlay = document.getElementById('auth-overlay');
const authForm = document.getElementById('auth-form');
const authTitle = document.getElementById('auth-title');
const authSubtitle = document.getElementById('auth-subtitle');
const authSubmitBtn = document.getElementById('auth-submit-btn');
const authSwitch = document.getElementById('auth-switch');
const authRoleGroup = document.getElementById('auth-role-group');
const authError = document.getElementById('auth-error');
const currentUserEmail = document.getElementById('current-user-email');
const logoutBtn = document.getElementById('logout-btn');

function updateAuthUI() {
    if (authToken) {
        // Logged in
        authOverlay.classList.remove('active');
        document.body.classList.remove('auth-active');
        currentUserEmail.textContent = authEmail || 'User';

        if (authRole === 'User') {
            document.body.classList.add('theme-user');
        } else {
            document.body.classList.remove('theme-user');
        }

        document.getElementById('upload-wrapper').style.display = authRole === 'User' ? 'none' : 'block';

        // Initial data load after login
        fetchSessionList();
    } else {
        // Logged out
        authOverlay.classList.add('active');
        document.body.classList.add('auth-active');
    }
}

authSwitch.addEventListener('click', () => {
    isLoginMode = !isLoginMode;
    authError.style.display = 'none';
    if (isLoginMode) {
        authTitle.textContent = 'Welcome Back';
        authSubtitle.textContent = 'Log in to Pharma RAG to access compliance tools.';
        authSubmitBtn.textContent = 'Sign In';
        authSwitch.innerHTML = `Don't have an account? <span>Sign up</span>`;
        authRoleGroup.style.display = 'none';
    } else {
        authTitle.textContent = 'Create Account';
        authSubtitle.textContent = 'Sign up to build and query your knowledge base.';
        authSubmitBtn.textContent = 'Sign Up';
        authSwitch.innerHTML = `Already have an account? <span>Sign in</span>`;
        authRoleGroup.style.display = 'block';
    }
});

authForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    authError.style.display = 'none';
    const email = document.getElementById('auth-email').value;
    const password = document.getElementById('auth-password').value;
    const roleSelect = document.getElementById('auth-role');
    const role = roleSelect ? roleSelect.value : 'User';

    authSubmitBtn.disabled = true;
    authSubmitBtn.textContent = 'Processing...';

    try {
        if (!isLoginMode) {
            // Register
            const regRes = await fetch(`${API_URL}/api/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password, role })
            });

            if (!regRes.ok) {
                const errData = await regRes.json();
                throw new Error(errData.detail || 'Registration failed');
            }
        }

        // Login (happens for both existing users and right after signup)
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        const loginRes = await fetch(`${API_URL}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData
        });

        if (!loginRes.ok) {
            const errData = await loginRes.json();
            throw new Error(errData.detail || 'Login failed');
        }

        const data = await loginRes.json();

        // Save session
        authToken = data.access_token;
        authRole = data.role;
        authEmail = email;

        localStorage.setItem('pharma_rag_token', authToken);
        localStorage.setItem('pharma_rag_role', authRole);
        localStorage.setItem('pharma_rag_email', authEmail);

        authForm.reset();
        updateAuthUI();

    } catch (err) {
        authError.textContent = err.message;
        authError.style.display = 'block';
    } finally {
        authSubmitBtn.disabled = false;
        authSubmitBtn.textContent = isLoginMode ? 'Sign In' : 'Sign Up';
    }
});

logoutBtn.addEventListener('click', () => {
    authToken = null;
    authRole = null;
    authEmail = null;
    localStorage.removeItem('pharma_rag_token');
    localStorage.removeItem('pharma_rag_role');
    localStorage.removeItem('pharma_rag_email');

    // Clear current chat
    currentSessionId = null;
    currentMessages = [];
    messagesList.innerHTML = '';
    welcomeScreen.style.display = 'flex';

    updateAuthUI();
});


// ===== CHAT HISTORY STATE =====
let chatSessions = []; // loaded from server
let currentSessionId = null;
let currentMessages = [];

function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2, 5);
}

function getTimeLabel(ts) {
    const d = new Date(ts);
    const now = new Date();
    const diff = now - d;
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
    if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// ===== SERVER API FUNCTIONS =====
const getAuthHeaders = () => {
    return authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
};

async function fetchSessionList() {
    if (!authToken) return;
    try {
        const res = await fetch(`${API_URL}/api/history/sessions`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error('Failed to fetch sessions');
        const data = await res.json();
        chatSessions = data.sessions || [];
    } catch (err) {
        console.warn('Could not load history from server, using empty list.', err);
        chatSessions = [];
    }
    renderHistoryList();
}

async function saveCurrentSession() {
    if (!currentSessionId || currentMessages.length === 0) return;
    const firstUserMsg = currentMessages.find(m => m.role === 'user');
    const title = firstUserMsg ? firstUserMsg.content.substring(0, 60) : 'New Chat';

    try {
        await fetch(`${API_URL}/api/history/sessions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
            body: JSON.stringify({
                session_id: currentSessionId,
                title: title,
                messages: currentMessages
            })
        });
        await fetchSessionList();
    } catch (err) {
        console.warn('Could not save session to server:', err);
    }
}

async function loadSessionFromServer(sessionId) {
    try {
        const res = await fetch(`${API_URL}/api/history/sessions/${sessionId}`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error('Session not found');
        return await res.json();
    } catch (err) {
        console.warn('Could not load session:', err);
        return null;
    }
}

// ===== RENDER HISTORY =====
function renderHistoryList() {
    historyList.querySelectorAll('.history-item').forEach(el => el.remove());

    if (chatSessions.length === 0) {
        historyEmpty.style.display = 'block';
        return;
    }
    historyEmpty.style.display = 'none';

    chatSessions.forEach(session => {
        const li = document.createElement('li');
        li.className = 'history-item' + (session.id === currentSessionId ? ' active' : '');
        li.innerHTML = `
                    <i class="fa-regular fa-message"></i>
                    <span class="history-text">${session.title}</span>
                    <span class="history-time">${getTimeLabel(session.timestamp)}</span>
                `;
        li.addEventListener('click', () => loadSession(session.id));
        historyList.appendChild(li);
    });
}

async function loadSession(sessionId) {
    await saveCurrentSession();

    const session = await loadSessionFromServer(sessionId);
    if (!session) return;

    currentSessionId = session.id;
    currentMessages = [...session.messages];

    messagesList.innerHTML = '';
    welcomeScreen.style.display = 'none';
    messagesList.style.display = 'block';

    currentMessages.forEach(msg => {
        renderMessageToUI(msg.role, msg.content, msg.sources || []);
    });

    await fetchSessionList();
    scrollToBottom();
}

async function startNewChat() {
    await saveCurrentSession();

    currentSessionId = generateId();
    currentMessages = [];
    messagesList.innerHTML = '';
    messagesList.style.display = 'none';
    welcomeScreen.style.display = 'flex';

    renderHistoryList();
}

newChatBtn.addEventListener('click', startNewChat);

// ===== CHAT LOGIC =====
function askQuestion(q) {
    chatInput.value = q;
    chatForm.dispatchEvent(new Event('submit'));
}

// ===== FEEDBACK API =====
async function submitFeedback(btnElement, messageId, isPositive) {
    // UI Update
    const container = btnElement.parentElement;
    container.querySelectorAll('.feedback-btn').forEach(b => b.classList.remove('active-positive', 'active-negative'));
    if (isPositive) btnElement.classList.add('active-positive');
    else btnElement.classList.add('active-negative');

    try {
        await fetch(`${API_URL}/api/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
            body: JSON.stringify({ message_id: messageId, is_positive: isPositive })
        });
    } catch (e) {
        console.error("Feedback failed", e);
    }
}

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = chatInput.value.trim();
    if (!message) return;

    if (!currentSessionId) currentSessionId = generateId();

    welcomeScreen.style.display = 'none';
    messagesList.style.display = 'block';

    // 1. Add User Message
    const userMsgId = generateId();
    addMessage('user', message, [], userMsgId);

    chatInput.value = '';
    chatInput.disabled = true;
    sendBtn.disabled = true;
    typingIndicator.style.display = 'block';
    scrollToBottom();

    // 2. Prepare Bot Message container for Streaming
    const botMsgId = generateId();
    const botMessageObj = { role: 'bot', content: '', sources: [], id: botMsgId };
    currentMessages.push(botMessageObj); // Track it but don't save to server until done

    // Create the UI bubble empty
    const row = document.createElement('div');
    row.className = 'message-row bot';
    row.innerHTML = `
                <div class="msg-avatar bot-avatar"><i class="fa-solid fa-robot"></i></div>
                <div class="msg-bubble bot-bubble">
                    <div class="msg-content" id="stream-content-${botMsgId}">...</div>
                    <div id="stream-citations-${botMsgId}"></div>
                </div>
            `;
    messagesList.appendChild(row);
    const contentDiv = document.getElementById(`stream-content-${botMsgId}`);
    const citationsDiv = document.getElementById(`stream-citations-${botMsgId}`);

    try {
        const res = await fetch(`${API_URL}/api/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
            body: JSON.stringify({ message })
        });

        if (!res.ok) throw new Error('Backend error');

        typingIndicator.style.display = 'none';
        contentDiv.innerHTML = ''; // clear loading dots

        const reader = res.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let fullText = "";
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // keep the last incomplete line in the buffer

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.substring(6).trim();
                    if (dataStr === '[DONE]') continue;
                    if (!dataStr) continue;

                    try {
                        const payload = JSON.parse(dataStr);
                        if (payload.type === 'citations') {
                            botMessageObj.sources = payload.citations;

                            // Build citation chips HTML
                            if (payload.citations && payload.citations.length > 0) {
                                const chips = payload.citations.map(s => {
                                    const safeSource = (s.source || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                                    const snippetKey = `${botMsgId}_${s.ref_id || 0}_${Date.now()}`;
                                    snippetStore.set(snippetKey, s.text_snippet || '');
                                    return `
                                            <div class="citation-chip" data-source="${safeSource}" data-page="${s.page}" data-refid="${s.ref_id || 0}" data-snippetkey="${snippetKey}">
                                                <span class="ref-badge">${s.ref_id || '?'}</span>
                                                <span>${s.source} \u00b7 p.${s.page}</span>
                                            </div>`;
                                }).join('');

                                citationsDiv.innerHTML = `
                                            <div class="citations-panel">
                                                <div class="citations-label">\ud83d\udcc4 Source References</div>
                                                <div class="citation-chips">${chips}</div>
                                            </div>
                                        `;
                            }
                        } else if (payload.type === 'token') {
                            fullText += payload.content;
                            contentDiv.innerHTML = marked.parse(fullText);
                            scrollToBottom();
                        }
                    } catch (e) {
                        console.warn('Stream parse error:', e, dataStr);
                    }
                }
            }
        }

        botMessageObj.content = fullText;

        // Add feedback UI
        const feedbackDiv = document.createElement('div');
        feedbackDiv.className = 'feedback-actions';
        feedbackDiv.innerHTML = `
                    <button class="feedback-btn" onclick="submitFeedback(this, '${botMsgId}', true)"><i class="fa-regular fa-thumbs-up"></i> Helpful</button>
                    <button class="feedback-btn" onclick="submitFeedback(this, '${botMsgId}', false)"><i class="fa-regular fa-thumbs-down"></i> Unhelpful</button>
                `;
        citationsDiv.parentElement.appendChild(feedbackDiv);

        saveCurrentSession(); // Save everything finally

    } catch (err) {
        console.error(err);
        contentDiv.innerHTML = '<span style="color:red">\u274c Error communicating with backend.</span>';
        typingIndicator.style.display = 'none';
    } finally {
        chatInput.disabled = false;
        sendBtn.disabled = false;
        chatInput.focus();
        scrollToBottom();
    }
});

// ===== ROLE UI TOGGLE =====
const roleSelector = document.getElementById('role-selector');
const roleLabelHTML = document.getElementById('role-label-text');

function updateRoleUI() {
    const role = roleSelector.value;
    if (role === 'User') {
        document.body.classList.add('theme-user');
    } else {
        document.body.classList.remove('theme-user');
    }
}
roleSelector.addEventListener('change', updateRoleUI);
updateRoleUI(); // Run once on load

// ===== MODAL LOGIC =====
const modalOverlay = document.getElementById('modal-overlay');
const modalClose = document.getElementById('modal-close');
const modalClose2 = document.getElementById('modal-close-2');
const modalTitle = document.getElementById('modal-title');
const modalSource = document.getElementById('modal-source');
const modalPage = document.getElementById('modal-page');
const modalRef = document.getElementById('modal-ref');
const modalBodyText = document.getElementById('modal-body-text');
const modalViewer = document.getElementById('modal-viewer');
const viewerLoading = document.getElementById('viewer-loading');
const modalOpenDoc = document.getElementById('modal-open-doc');

let currentDocUrl = '';

function openCitationModal(source, page, refId, snippet) {
    try {
        console.log("Opening modal for:", source, page, refId);

        modalTitle.textContent = `Reference ${refId} \u2014 ${source}`;
        modalSource.textContent = source;
        modalPage.textContent = page;
        modalRef.textContent = refId;

        // Display snippet text
        if (snippet && snippet.trim().length > 0) {
            modalBodyText.textContent = snippet;
            modalBodyText.parentElement.style.display = 'block';
        } else {
            modalBodyText.parentElement.style.display = 'none';
        }

        modalOverlay.classList.add('active');

        // Build document URL
        const encodedName = encodeURIComponent(source);
        const ext = source.split('.').pop().toLowerCase();

        if (ext === 'pdf') {
            // Use the local PDF.js viewer for proper search highlighting
            const pdfUrl = `${API_URL}/api/documents/view/${encodedName}`;
            currentDocUrl = pdfUrl;

            // Show a search tip banner just in case
            const searchHint = snippet ? snippet.substring(0, 50).trim() : '';

            // Build local PDF.js viewer URL with search term for exact highlighting
            let viewerUrl = `${API_URL}/static/pdfjs/web/viewer.html?file=${encodeURIComponent(pdfUrl)}#page=${page}`;
            if (searchHint) {
                viewerUrl += `&search=${encodeURIComponent(searchHint)}&phrase=true`;
            }

            let hintHTML = '';
            if (searchHint) {
                hintHTML = `<div style="background:#eff6ff;border-bottom:1px solid #bfdbfe;padding:8px 16px;font-size:12px;color:#1e40af;display:flex;align-items:center;gap:8px;">
                        <i class="fa-solid fa-magnifying-glass"></i> 
                        <span><strong>Tip:</strong> If not highlighted, press <kbd style="background:#dbeafe;padding:2px 6px;border-radius:4px;font-size:11px">Ctrl+F</kbd> and search: "<em>${escapeHtml(searchHint)}</em>"</span>
                    </div>`;
            }
            modalViewer.innerHTML = `${hintHTML}<iframe src="${viewerUrl}" title="Document Viewer" style="height:calc(100% - ${searchHint ? '38px' : '0px'})"></iframe>`;
        } else {
            // Text files: fetch content and highlight the snippet
            currentDocUrl = `${API_URL}/api/documents/view/${encodedName}`;
            modalViewer.innerHTML = '<div class="modal-viewer-loading"><i class="fa-solid fa-spinner fa-spin"></i> Loading document...</div>';

            fetch(currentDocUrl)
                .then(res => res.text())
                .then(text => {
                    let displayText = '';
                    if (snippet && snippet.length > 10) {
                        const searchStr = snippet.substring(0, 80);
                        const idx = text.indexOf(searchStr);
                        if (idx >= 0) {
                            const ctxStart = Math.max(0, idx - 300);
                            const ctxEnd = Math.min(text.length, idx + searchStr.length + 500);
                            const before = escapeHtml(text.substring(ctxStart, idx));
                            const match = escapeHtml(text.substring(idx, idx + searchStr.length));
                            const after = escapeHtml(text.substring(idx + searchStr.length, ctxEnd));
                            displayText = `${ctxStart > 0 ? '... ' : ''}${before}<mark>${match}</mark>${after}${ctxEnd < text.length ? ' ...' : ''}`;
                        } else {
                            displayText = escapeHtml(text.substring(0, 3000));
                            if (text.length > 3000) displayText += '\n\n... (showing first 3000 characters)';
                        }
                    } else {
                        displayText = escapeHtml(text.substring(0, 3000));
                        if (text.length > 3000) displayText += '\n\n... (showing first 3000 characters)';
                    }
                    modalViewer.innerHTML = `<div class="modal-viewer-text">${displayText}</div>`;
                })
                .catch(() => {
                    modalViewer.innerHTML = '<div class="modal-viewer-loading"><i class="fa-solid fa-triangle-exclamation"></i> Could not load document. Please re-upload.</div>';
                });
        }
    } catch (error) {
        alert("Error rendering citation modal: " + error.message);
        console.error(error);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

modalOpenDoc.addEventListener('click', () => {
    if (currentDocUrl) window.open(currentDocUrl, '_blank');
});

const closeModal = () => {
    modalOverlay.classList.remove('active');
    modalViewer.innerHTML = '';
};
modalClose.addEventListener('click', closeModal);
modalClose2.addEventListener('click', closeModal);
modalOverlay.addEventListener('click', (e) => { if (e.target === modalOverlay) closeModal(); });
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });

// Event delegation for citation chips
document.getElementById('messages-list').addEventListener('click', (e) => {
    const chip = e.target.closest('.citation-chip');
    if (!chip) return;
    const snippetKey = chip.dataset.snippetkey;
    const snippet = snippetStore.get(snippetKey) || '';
    openCitationModal(
        chip.dataset.source,
        chip.dataset.page,
        chip.dataset.refid,
        snippet
    );
});

// ===== FILE UPLOAD =====
const SUPPORTED_EXTENSIONS = ['.pdf', '.txt', '.md', '.csv', '.doc', '.docx', '.json'];

fileUpload.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!SUPPORTED_EXTENSIONS.includes(ext)) {
        alert(`Unsupported file format. Supported: ${SUPPORTED_EXTENSIONS.join(', ')}`);
        return;
    }

    if (!currentSessionId) currentSessionId = generateId();
    welcomeScreen.style.display = 'none';
    messagesList.style.display = 'block';

    uploadZone.classList.add('uploading');
    uploadTitle.textContent = 'Processing...';
    uploadSubtitle.textContent = file.name;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch(`${API_URL}/api/documents/upload`, {
            method: 'POST',
            body: formData,
            headers: getAuthHeaders()
        });

        if (res.status === 403) {
            addMessage('system', '\u274c Upload blocked: Only **Admins** have permission to upload Standard Operating Procedures. Please select Admin role to test uploads.');
            return;
        }

        if (!res.ok) throw new Error('Upload failed');
        addMessage('system', `\u2705 Successfully uploaded "${file.name}". Background parsing is now in progress. You can start asking questions in a few seconds.`);
    } catch (err) {
        addMessage('system', '\u274c Upload failed. Please ensure the backend is running.');
    } finally {
        uploadZone.classList.remove('uploading');
        uploadTitle.textContent = 'Upload Document';
        uploadSubtitle.textContent = 'PDF, TXT, MD, CSV, DOC, DOCX, JSON';
        e.target.value = '';
        scrollToBottom();
    }
});

// ===== MESSAGE RENDERING =====
function addMessage(role, content, sources = [], msgId = null) {
    msgId = msgId || generateId();
    currentMessages.push({ role, content, sources, id: msgId });
    saveCurrentSession(); // async save to server

    renderMessageToUI(role, content, sources, msgId);
}

function renderMessageToUI(role, content, sources = [], msgId = null) {
    msgId = msgId || generateId();
    const row = document.createElement('div');
    row.className = `message-row ${role}`;

    let avatarHTML = '';
    let bubbleClass = '';

    if (role === 'user') {
        bubbleClass = 'user-bubble';
    } else if (role === 'bot') {
        bubbleClass = 'bot-bubble';
        avatarHTML = `<div class="msg-avatar bot-avatar"><i class="fa-solid fa-robot"></i></div>`;
    } else {
        bubbleClass = 'system-bubble';
        avatarHTML = `<div class="msg-avatar system-avatar"><i class="fa-solid fa-circle-info"></i></div>`;
    }

    const renderedContent = role === 'bot' ? marked.parse(content) : content;

    let citationsHTML = '';
    if (sources && sources.length > 0) {
        const chips = sources.map(s => {
            const safeSource = (s.source || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            // Store snippet in JS Map to avoid data-attribute issues
            const snippetKey = `${s.ref_id || 0}_${Date.now()}_${Math.random()}`;
            snippetStore.set(snippetKey, s.text_snippet || '');
            return `
                    <div class="citation-chip" data-source="${safeSource}" data-page="${s.page}" data-refid="${s.ref_id || 0}" data-snippetkey="${snippetKey}">
                        <span class="ref-badge">${s.ref_id || '?'}</span>
                        <span>${s.source} \u00b7 p.${s.page}</span>
                    </div>`;
        }).join('');

        citationsHTML = `
                    <div class="citations-panel">
                        <div class="citations-label">\ud83d\udcc4 Source References (click to view)</div>
                        <div class="citation-chips">${chips}</div>
                    </div>
                `;
    }

    let feedbackHTML = '';
    if (role === 'bot') {
        feedbackHTML = `
                    <div class="feedback-actions">
                        <button class="feedback-btn" onclick="submitFeedback(this, '${msgId}', true)"><i class="fa-regular fa-thumbs-up"></i> Helpful</button>
                        <button class="feedback-btn" onclick="submitFeedback(this, '${msgId}', false)"><i class="fa-regular fa-thumbs-down"></i> Unhelpful</button>
                    </div>
                `;
    }

    row.innerHTML = `
                ${role !== 'user' ? avatarHTML : ''}
                <div class="msg-bubble ${bubbleClass}">
                    <div class="msg-content">${renderedContent}</div>
                    ${citationsHTML}
                    ${feedbackHTML}
                </div>
                ${role === 'user' ? '<div class="msg-avatar user-avatar"><i class="fa-solid fa-user"></i></div>' : ''}
            `;

    messagesList.appendChild(row);
}

function scrollToBottom() {
    setTimeout(() => {
        chatFeed.scrollTo({ top: chatFeed.scrollHeight, behavior: 'smooth' });
    }, 100);
}

// ===== INIT — Load history from server =====
fetchSessionList();
