/**
 * MCADV Web Interface – AdventureGame
 *
 * Handles all API communication and DOM updates for the play.html gameplay page.
 */

class AdventureGame {
    constructor() {
        this.sessionId = null;
        this.history = [];
        this.status = 'none';
        this._apiBase = '';   // same origin

        // Restore any in-progress session from localStorage
        this._restoreSession();
    }

    // -------------------------------------------------------------------------
    // API helpers
    // -------------------------------------------------------------------------

    async _post(path, body) {
        const resp = await fetch(this._apiBase + path, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await resp.json();
        if (!resp.ok) {
            throw new Error(data.error || `HTTP ${resp.status}`);
        }
        return data;
    }

    async _get(path) {
        const resp = await fetch(this._apiBase + path);
        const data = await resp.json();
        if (!resp.ok) {
            throw new Error(data.error || `HTTP ${resp.status}`);
        }
        return data;
    }

    // -------------------------------------------------------------------------
    // Public API
    // -------------------------------------------------------------------------

    async loadThemes() {
        try {
            const data = await this._get('/api/themes');
            return data.themes || [];
        } catch (e) {
            console.error('Failed to load themes:', e);
            return ['fantasy', 'scifi', 'horror'];
        }
    }

    async startAdventure(theme) {
        this._setLoading(true);
        try {
            const data = await this._post('/api/adventure/start', { theme });
            this.sessionId = data.session_id;
            this.history = [];
            this.status = data.status;
            this._persistSession();
            this._addToHistory(`⚔ New adventure began — theme: ${theme}`);
            this.displayStory(data.story, data.choices);
            this._updateStatus(data.status);
        } catch (e) {
            this._showError('Failed to start adventure: ' + e.message);
        } finally {
            this._setLoading(false);
        }
    }

    async makeChoice(choiceNumber) {
        if (!this.sessionId) return;
        this._setLoading(true);
        this._disableChoices(true);
        try {
            const data = await this._post('/api/adventure/choice', {
                session_id: this.sessionId,
                choice: String(choiceNumber),
            });
            const choiceLabel = document.querySelector(
                `.choice-btn[data-choice="${choiceNumber}"] .choice-text`
            );
            const choiceText = choiceLabel ? choiceLabel.textContent : `Choice ${choiceNumber}`;
            this._addToHistory(`➤ You chose: ${choiceText}`);
            this.status = data.status;
            this._persistSession();
            this.displayStory(data.story, data.choices);
            this._updateStatus(data.status);
            if (data.status === 'finished') {
                this.sessionId = null;
                this._clearPersistedSession();
            }
        } catch (e) {
            this._showError('Failed to make choice: ' + e.message);
            this._disableChoices(false);
        } finally {
            this._setLoading(false);
        }
    }

    async endAdventure() {
        if (!this.sessionId) return;
        this._setLoading(true);
        try {
            await this._post('/api/adventure/quit', { session_id: this.sessionId });
        } catch (e) {
            // Best-effort; clear locally even if server call fails
        } finally {
            this.sessionId = null;
            this.history = [];
            this.status = 'none';
            this._clearPersistedSession();
            this._clearDisplay();
            this._updateStatus('none');
            this._setLoading(false);
        }
    }

    // -------------------------------------------------------------------------
    // Display
    // -------------------------------------------------------------------------

    displayStory(story, choices) {
        const storyEl = document.getElementById('story-text');
        if (!storyEl) return;
        storyEl.textContent = story;
        storyEl.classList.remove('animate');
        // Trigger reflow to restart animation
        void storyEl.offsetWidth;
        storyEl.classList.add('animate');

        this._addToHistory(story);
        this._renderChoices(choices);
        storyEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    _renderChoices(choices) {
        const container = document.getElementById('choices-container');
        if (!container) return;
        container.innerHTML = '';
        if (!choices || choices.length === 0) return;
        choices.forEach((text, idx) => {
            const num = idx + 1;
            const btn = document.createElement('button');
            btn.className = 'choice-btn';
            btn.dataset.choice = num;
            btn.innerHTML = `<span class="choice-number">${num}</span><span class="choice-text">${this._escapeHtml(text)}</span>`;
            btn.addEventListener('click', () => this.makeChoice(num));
            container.appendChild(btn);
        });
    }

    _clearDisplay() {
        const storyEl = document.getElementById('story-text');
        if (storyEl) {
            storyEl.textContent = '';
            const placeholder = document.createElement('p');
            placeholder.className = 'story-placeholder';
            placeholder.textContent = 'Select a theme and press "Begin Adventure" to start your quest.';
            storyEl.appendChild(placeholder);
        }
        const container = document.getElementById('choices-container');
        if (container) container.innerHTML = '';
    }

    // -------------------------------------------------------------------------
    // History
    // -------------------------------------------------------------------------

    _addToHistory(text) {
        this.history.push(text);
        this._renderHistoryItem(text);
    }

    _renderHistoryItem(text) {
        const list = document.getElementById('history-list');
        if (!list) return;

        const empty = list.querySelector('.history-empty');
        if (empty) empty.remove();

        const entry = document.createElement('div');
        const isChoice = text.startsWith('➤') || text.startsWith('⚔');
        entry.className = 'history-entry' + (isChoice ? ' choice-marker' : '');
        entry.textContent = text;
        list.appendChild(entry);
        list.scrollTop = list.scrollHeight;
    }

    // -------------------------------------------------------------------------
    // Status
    // -------------------------------------------------------------------------

    _updateStatus(status) {
        this.status = status;
        const dot = document.getElementById('status-dot');
        const label = document.getElementById('status-label');
        if (!dot || !label) return;
        dot.className = 'status-dot ' + status;
        const labels = { active: 'Active', finished: 'Finished', none: 'No Adventure', loading: 'Loading…' };
        label.textContent = labels[status] || status;

        // Toggle button states
        const endBtn = document.getElementById('btn-end');
        if (endBtn) endBtn.disabled = status !== 'active';
    }

    // -------------------------------------------------------------------------
    // Loading state
    // -------------------------------------------------------------------------

    _setLoading(loading) {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.classList.toggle('visible', loading);
        if (loading) this._updateStatus('loading');
        const startBtn = document.getElementById('btn-start');
        if (startBtn) startBtn.disabled = loading;
    }

    _disableChoices(disabled) {
        document.querySelectorAll('.choice-btn').forEach(btn => {
            btn.disabled = disabled;
        });
    }

    // -------------------------------------------------------------------------
    // Error display
    // -------------------------------------------------------------------------

    _showError(msg) {
        const storyEl = document.getElementById('story-text');
        if (storyEl) {
            storyEl.textContent = '⚠ ' + msg;
            storyEl.classList.add('animate');
        }
    }

    // -------------------------------------------------------------------------
    // Persistence
    // -------------------------------------------------------------------------

    _persistSession() {
        try {
            localStorage.setItem('mcadv_session', JSON.stringify({
                sessionId: this.sessionId,
                status: this.status,
            }));
        } catch (_) { /* ignore */ }
    }

    _restoreSession() {
        try {
            const raw = localStorage.getItem('mcadv_session');
            if (!raw) return;
            const data = JSON.parse(raw);
            if (data && data.sessionId) {
                this.sessionId = data.sessionId;
                this.status = data.status || 'none';
            }
        } catch (_) { /* ignore */ }
    }

    _clearPersistedSession() {
        try { localStorage.removeItem('mcadv_session'); } catch (_) { /* ignore */ }
    }

    // -------------------------------------------------------------------------
    // Utilities
    // -------------------------------------------------------------------------

    _escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }
}

// -------------------------------------------------------------------------
// Page initialisation
// -------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', async () => {
    const game = new AdventureGame();

    // Populate theme selector
    const themeSelect = document.getElementById('theme-select');
    if (themeSelect) {
        const themes = await game.loadThemes();
        themes.forEach(theme => {
            const opt = document.createElement('option');
            opt.value = theme;
            opt.textContent = theme.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            if (theme === 'fantasy') opt.selected = true;
            themeSelect.appendChild(opt);
        });
    }

    // Start adventure button
    const startBtn = document.getElementById('btn-start');
    if (startBtn) {
        startBtn.addEventListener('click', () => {
            const theme = themeSelect ? themeSelect.value : 'fantasy';
            game.startAdventure(theme);
        });
    }

    // End adventure button
    const endBtn = document.getElementById('btn-end');
    if (endBtn) {
        endBtn.disabled = true;
        endBtn.addEventListener('click', () => game.endAdventure());
    }

    // History toggle
    const historyHeader = document.getElementById('history-header');
    const historyList = document.getElementById('history-list');
    const historyToggle = document.getElementById('history-toggle');
    if (historyHeader && historyList) {
        let historyVisible = true;
        historyHeader.addEventListener('click', () => {
            historyVisible = !historyVisible;
            historyList.style.display = historyVisible ? '' : 'none';
            if (historyToggle) historyToggle.classList.toggle('collapsed', !historyVisible);
        });
    }

    // Restore status if there's a saved session
    if (game.sessionId && game.status === 'active') {
        game._updateStatus('active');
        // Previous session found — user must start a new adventure
        const storyEl = document.getElementById('story-text');
        if (storyEl) {
            storyEl.textContent = 'A previous session was found, but its state cannot be resumed. Press "Begin Adventure" to start a new quest.';
        }
    }

    // Make game globally accessible for debugging
    window._mcadvGame = game;
});
