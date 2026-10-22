/**
 * Geraldo Desktop — Controlador de Interface Gráfica & Cliente WebSocket
 */

class GeraldoDesktopClient {
    constructor(host = "127.0.0.1", port = 8765) {
        this.host = host;
        this.port = port;
        this.ws = null;
        this.connected = false;
        this.isMuted = false;
        this.assistantState = "idle";
        this.pomodoroState = "idle";

        this.dom = {
            connPill: document.getElementById("conn-pill"),
            connText: document.getElementById("conn-text"),
            stateBadge: document.getElementById("state-badge"),
            audioWave: document.getElementById("audio-wave"),
            btnMicToggle: document.getElementById("btn-mic-toggle"),
            micIcon: document.getElementById("mic-icon"),
            micText: document.getElementById("mic-text"),
            chatStream: document.getElementById("chat-stream"),
            promptInput: document.getElementById("prompt-input"),
            btnSend: document.getElementById("btn-send"),
            btnCancel: document.getElementById("btn-cancel"),
            btnClearChat: document.getElementById("btn-clear-chat"),
            // Pomodoro
            pomoCountdown: document.getElementById("pomo-countdown"),
            pomoPhaseBadge: document.getElementById("pomo-phase-badge"),
            pomoCycleText: document.getElementById("pomo-cycle-text"),
            pomoEmpty: document.getElementById("pomo-empty"),
            pomoActiveDisplay: document.getElementById("pomo-active-display"),
            pomoActions: document.getElementById("pomo-actions"),
            btnPomoToggle: document.getElementById("btn-pomo-toggle"),
            btnPomoSkip: document.getElementById("btn-pomo-skip"),
            btnPomoReset: document.getElementById("btn-pomo-reset"),
            btnTogglePlanPomo: document.getElementById("btn-toggle-plan-pomo"),
            pomoPlanForm: document.getElementById("pomo-plan-form"),
            pomoInputWork: document.getElementById("pomo-input-work"),
            pomoInputBreak: document.getElementById("pomo-input-break"),
            pomoInputLongBreak: document.getElementById("pomo-input-long-break"),
            pomoInputLongInterval: document.getElementById("pomo-input-long-interval"),
            pomoInputCycles: document.getElementById("pomo-input-cycles"),
            btnSavePlanPomo: document.getElementById("btn-save-plan-pomo"),
            // Timers & Alarms
            timersList: document.getElementById("timers-list"),
            alarmsList: document.getElementById("alarms-list"),
            btnToggleNewTimer: document.getElementById("btn-toggle-new-timer"),
            newTimerForm: document.getElementById("new-timer-form"),
            btnAddTimerSubmit: document.getElementById("btn-add-timer-submit"),
            newTimerLabel: document.getElementById("new-timer-label"),
            newTimerHours: document.getElementById("new-timer-hours"),
            newTimerMin: document.getElementById("new-timer-min"),
            newTimerSec: document.getElementById("new-timer-sec"),
            btnCancelAllTimers: document.getElementById("btn-cancel-all-timers"),
            // Tabs & Temporizadores
            tabBtnTimers: document.getElementById("tab-btn-timers"),
            tabBtnAlarms: document.getElementById("tab-btn-alarms"),
            tabContentTimers: document.getElementById("tab-content-timers"),
            tabContentAlarms: document.getElementById("tab-content-alarms"),
            timersBadgeCount: document.getElementById("timers-badge-count"),
            alarmsBadgeCount: document.getElementById("alarms-badge-count"),
            // Alarmes
            btnToggleNewAlarm: document.getElementById("btn-toggle-new-alarm"),
            newAlarmForm: document.getElementById("new-alarm-form"),
            btnAddAlarmSubmit: document.getElementById("btn-add-alarm-submit"),
            newAlarmLabel: document.getElementById("new-alarm-label"),
            newAlarmTime: document.getElementById("new-alarm-time"),
            btnCancelAllAlarms: document.getElementById("btn-cancel-all-alarms"),
            // Configurações do Ollama
            btnOpenSettings: document.getElementById("btn-open-settings"),
            settingsModal: document.getElementById("settings-modal"),
            btnCloseSettings: document.getElementById("btn-close-settings"),
            btnCancelSettings: document.getElementById("btn-cancel-settings"),
            btnSaveSettings: document.getElementById("btn-save-settings"),
            btnTestOllama: document.getElementById("btn-test-ollama"),
            cfgOllamaHost: document.getElementById("cfg-ollama-host"),
            cfgLlmModel: document.getElementById("cfg-llm-model"),
            cfgModelDropdown: document.getElementById("cfg-model-dropdown"),
            testResultBox: document.getElementById("test-result-box"),
            testStatusBadge: document.getElementById("test-status-badge"),
            testStatusMsg: document.getElementById("test-status-msg"),
            testModelsContainer: document.getElementById("test-models-container"),
            specsLlmText: document.getElementById("specs-llm-text"),
            providerTabs: document.getElementById("provider-tabs"),
            cfgProviderSelect: document.getElementById("cfg-provider-select"),
            sectionOllama: document.getElementById("section-ollama"),
            sectionExternal: document.getElementById("section-external"),
            cfgApiKey: document.getElementById("cfg-api-key"),
            btnToggleKeyVisibility: document.getElementById("btn-toggle-key-visibility"),
            cfgApiBase: document.getElementById("cfg-api-base"),
            apiKeyLink: document.getElementById("api-key-link"),
            apiKeyHelp: document.getElementById("api-key-help"),
            modelPresetsContainer: document.getElementById("model-presets-container"),
            btnDetectContainer: document.getElementById("btn-detect-container"),
            // Google Calendar & Auto-Update
            btnHeaderCalendar: document.getElementById("btn-header-calendar"),
            btnOpenCalendar: document.getElementById("btn-open-calendar"),
            btnAuthCalendar: document.getElementById("btn-auth-calendar"),
            calStatusBadge: document.getElementById("cal-status-badge"),
            calStatusDesc: document.getElementById("cal-status-desc"),
            btnCheckUpdates: document.getElementById("btn-check-updates"),
            updaterStatusBadge: document.getElementById("updater-status-badge"),
            // Áudio & Atalho TUI
            cfgAudioInput: document.getElementById("cfg-audio-input"),
            cfgAudioOutput: document.getElementById("cfg-audio-output"),
            btnRefreshAudio: document.getElementById("btn-refresh-audio"),
            btnTestAudioBeep: document.getElementById("btn-test-audio-beep"),
            specsAudioInText: document.getElementById("specs-audio-in-text"),
            specsAudioOutText: document.getElementById("specs-audio-out-text"),
            tuiPathStatusBadge: document.getElementById("tui-path-status-badge"),
            btnExportTuiPath: document.getElementById("btn-export-tui-path"),
            // Elementos de Navegação de Abas
            mainNavTabs: document.querySelectorAll(".main-nav-tab"),
            mainViewPanels: document.querySelectorAll(".main-view-panel"),
            btnJumpToCalendarTab: document.getElementById("btn-jump-to-calendar-tab"),
            navCalendarBadge: document.getElementById("nav-calendar-badge"),
            navPomodoroStatus: document.getElementById("nav-pomodoro-status"),
            navTimersBadge: document.getElementById("nav-timers-badge"),
            // Elementos da Aba de Agenda
            calendarMonthYearLabel: document.getElementById("calendar-month-year-label"),
            calendarDaysGrid: document.getElementById("calendar-days-grid"),
            selectedDayFullLabel: document.getElementById("selected-day-full-label"),
            selectedDayEventsCount: document.getElementById("selected-day-events-count"),
            selectedDayEventsList: document.getElementById("selected-day-events-list"),
            calendarCreateForm: document.getElementById("calendar-create-event-form"),
            btnCalToggleNew: document.getElementById("btn-cal-toggle-new"),
            btnCalRefresh: document.getElementById("btn-cal-refresh"),
            btnCalPrevMonth: document.getElementById("btn-cal-prev-month"),
            btnCalNextMonth: document.getElementById("btn-cal-next-month"),
            btnCalToday: document.getElementById("btn-cal-today"),
            btnCalWebLink: document.getElementById("btn-cal-web-link"),
            btnCalManageAuth: document.getElementById("btn-cal-manage-auth"),
            calAuthBtnLabel: document.getElementById("cal-auth-btn-label"),
            calViewStatusPill: document.getElementById("cal-view-status-pill"),
            eventInputSummary: document.getElementById("event-input-summary"),
            eventInputDate: document.getElementById("event-input-date"),
            eventInputTime: document.getElementById("event-input-time"),
            eventInputDuration: document.getElementById("event-input-duration"),
            eventInputAllDay: document.getElementById("event-input-allday"),
            btnSubmitCreateEvent: document.getElementById("btn-submit-create-event"),
            btnCancelCreateEvent: document.getElementById("btn-cancel-create-event"),
            // Pomodoro Expandido
            pomoHeroCountdown: document.getElementById("pomo-hero-countdown"),
            pomoHeroBadge: document.getElementById("pomo-hero-badge"),
            pomoHeroCycle: document.getElementById("pomo-hero-cycle"),
            btnPomoHeroToggle: document.getElementById("btn-pomo-hero-toggle"),
            btnPomoHeroSkip: document.getElementById("btn-pomo-hero-skip"),
            btnPomoHeroReset: document.getElementById("btn-pomo-hero-reset"),
            // Timers & Alarmes Expandidos
            timersFullCountBadge: document.getElementById("timers-full-count-badge"),
            alarmsFullCountBadge: document.getElementById("alarms-full-count-badge"),
            fullTimersStream: document.getElementById("full-timers-stream"),
            fullAlarmsStream: document.getElementById("full-alarms-stream"),
            btnFullTimerSubmit: document.getElementById("btn-full-timer-submit"),
            btnFullAlarmSubmit: document.getElementById("btn-full-alarm-submit"),
            fullTimerLabel: document.getElementById("full-timer-label"),
            fullTimerH: document.getElementById("full-timer-h"),
            fullTimerM: document.getElementById("full-timer-m"),
            fullTimerS: document.getElementById("full-timer-s"),
            fullAlarmLabel: document.getElementById("full-alarm-label"),
            fullAlarmTime: document.getElementById("full-alarm-time"),
            btnQuickOpenSettingsModal: document.getElementById("btn-quick-open-settings-modal"),
            settingsViewCalBadge: document.getElementById("settings-view-cal-badge")
        };

        const now = new Date();
        this.currentCalendarYear = now.getFullYear();
        this.currentCalendarMonth = now.getMonth();
        // Formato ISO YYYY-MM-DD com fuso local
        const localYear = now.getFullYear();
        const localMonth = String(now.getMonth() + 1).padStart(2, '0');
        const localDay = String(now.getDate()).padStart(2, '0');
        this.selectedCalendarDate = `${localYear}-${localMonth}-${localDay}`;
        this.calendarEvents = [];

        this.audioConfig = {
            input_device: null,
            output_device: null,
            devices: { inputs: [], outputs: [] }
        };

        this.llmConfig = {
            provider: "ollama",
            ollama_host: "http://localhost:11434",
            llm_model: "qwen2.5:3b",
            api_key: "",
            api_key_masked: "",
            has_api_key: false,
            api_base: ""
        };
        // Alias de retrocompatibilidade
        this.ollamaConfig = this.llmConfig;
        this.currentProvider = "ollama";
        this._pendingRequests = new Map();

        this.loadLocalConfig();
        this.initEventListeners();
        this.connect();
    }

    connect() {
        const url = `ws://${this.host}:${this.port}`;
        this.updateConnectionStatus(false, "Conectando...");

        try {
            this.ws = new WebSocket(url);

            this.ws.onopen = () => {
                this.updateConnectionStatus(true, "Conectado");
                this.sendAction("get_config");
                this.sendAction("check_calendar");
                this.loadCalendarEvents();
                this.loadAudioDevices();
            };

            this.ws.onmessage = (event) => {
                this.handleMessage(event.data);
            };

            this.ws.onclose = () => {
                this.updateConnectionStatus(false, "Desconectado");
                setTimeout(() => this.connect(), 2000);
            };

            this.ws.onerror = () => {
                this.updateConnectionStatus(false, "Erro");
            };
        } catch (e) {
            this.updateConnectionStatus(false, "Falha");
            setTimeout(() => this.connect(), 2000);
        }
    }

    loadLocalConfig() {
        try {
            const cached = localStorage.getItem("geraldo_llm_config");
            if (cached) {
                const parsed = JSON.parse(cached);
                this.updateConfigDisplay(parsed);
            }
        } catch (e) {}
    }

    async openExternalUrl(url) {
        if (!url) return;
        try {
            if (window.__TAURI__ && window.__TAURI__.core && typeof window.__TAURI__.core.invoke === "function") {
                await window.__TAURI__.core.invoke("open_external_url", { url });
                return;
            }
            if (window.__TAURI_INTERNALS__ && typeof window.__TAURI_INTERNALS__.invoke === "function") {
                await window.__TAURI_INTERNALS__.invoke("open_external_url", { url });
                return;
            }
        } catch (e) {
            console.warn("Tauri open_external_url warning:", e);
        }
        window.open(url, "_blank", "noopener,noreferrer");
    }

    updateConnectionStatus(connected, text) {
        this.connected = connected;
        if (!this.dom.connPill) return;

        if (connected) {
            this.dom.connPill.classList.add("connected");
            this.dom.connPill.classList.remove("disconnected");
        } else {
            this.dom.connPill.classList.remove("connected");
            this.dom.connPill.classList.add("disconnected");
        }
        if (this.dom.connText) {
            this.dom.connText.textContent = text;
        }
    }

    handleMessage(rawData) {
        let msg;
        try {
            msg = JSON.parse(rawData);
        } catch (e) {
            return;
        }

        if (msg.type === "event") {
            this.handleEvent(msg.event, msg.data || {});
        } else if (msg.type === "response") {
            this.handleResponse(msg);
        }
    }

    handleEvent(eventName, data) {
        switch (eventName) {
            case "connected":
                this.updateStateBadge(data.assistant_state || "idle");
                this.updateMicBadge(data.is_muted || false);
                if (data.config) {
                    this.updateConfigDisplay(data.config);
                }
                break;

            case "config_changed":
                if (data) {
                    this.updateConfigDisplay(data);
                    this.appendSystemMessage(`Configuração atualizada: Ollama em ${data.ollama_host} (${data.llm_model})`);
                }
                break;

            case "state_changed":
                this.updateStateBadge(data.state || "idle");
                break;

            case "mute_changed":
                this.updateMicBadge(data.muted || false);
                break;

            case "transcription":
                if (data.text) {
                    this.appendChatMessage("user", data.text, "Voz");
                }
                break;

            case "reply":
            case "reply_generated":
                const replyText = data.reply || data.text;
                if (replyText) {
                    if (this._lastDisplayedReply !== replyText) {
                        this._lastDisplayedReply = replyText;
                        setTimeout(() => {
                            if (this._lastDisplayedReply === replyText) {
                                this._lastDisplayedReply = null;
                            }
                        }, 3000);
                        this.appendChatMessage("assistant", replyText, "Geraldo");
                    }
                }
                break;

            case "status_update":
                this.updateDashboardStatus(data);
                break;

            case "cancelled":
                this.appendSystemMessage("Ação ou som interrompido.");
                break;

            case "calendar_status":
                this.updateCalendarStatus(data);
                this.loadCalendarEvents();
                break;

            case "calendar_updated":
                this.loadCalendarEvents();
                break;

            case "audio_config_changed":
                this.updateAudioDevicesDisplay(data);
                break;
        }
    }

    handleResponse(msg) {
        if (msg.id && this._pendingRequests.has(msg.id)) {
            const cb = this._pendingRequests.get(msg.id);
            this._pendingRequests.delete(msg.id);
            cb(msg.status === "ok", msg.data, msg.error);
        }

        if (msg.status === "error") {
            this.appendSystemMessage(`Erro: ${msg.error || "Operação falhou"}`);
        } else if (msg.id) {
            if (msg.id.startsWith("get_config")) {
                this.updateConfigDisplay(msg.data);
            } else if (msg.id.startsWith("set_config")) {
                this.updateConfigDisplay(msg.data);
                this.closeSettingsModal();
                this.appendSystemMessage("Configurações de IA salvas com sucesso!");
            } else if (msg.id.startsWith("check_ollama") || msg.id.startsWith("check_llm")) {
                this.displayTestResults(msg.data);
            } else if (msg.id.startsWith("check_calendar")) {
                this.updateCalendarStatus(msg.data);
            } else if (msg.id.startsWith("get_calendar_events")) {
                this.calendarEvents = (msg.data && msg.data.events) || [];
                this.renderCalendarMonthGrid();
                this.renderSelectedDayEvents(this.selectedCalendarDate);
                this.updateCalendarBadge();
            } else if (msg.id.startsWith("get_audio_config")) {
                this.updateAudioDevicesDisplay(msg.data);
            } else if (msg.id.startsWith("get_tui_path_status")) {
                this.updateTuiPathBadge(msg.data);
            }
        }
    }

    sendAction(action, params = {}, callback = null) {
        if (!this.connected || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
            this.appendSystemMessage("⚠️ Não conectado ao serviço do Geraldo. Inicie o serviço com: systemctl --user start geraldo.service");
            if (callback) callback(false, null, "Não conectado");
            return;
        }

        const reqId = `${action}-${Date.now()}`;
        if (callback) {
            this._pendingRequests.set(reqId, callback);
        }

        const payload = {
            id: reqId,
            action: action,
            params: params
        };

        this.ws.send(JSON.stringify(payload));
    }

    updateStateBadge(state) {
        this.assistantState = state;
        if (!this.dom.stateBadge) return;

        this.dom.stateBadge.className = "state-badge";
        if (this.dom.audioWave) {
            this.dom.audioWave.className = "audio-wave";
        }

        const stateLabels = {
            idle: "PRONTO",
            listening: "OUVINDO...",
            transcribing: "PROCESSANDO...",
            thinking: "PENSANDO...",
            speaking: "FALANDO...",
            starting: "INICIANDO..."
        };

        this.dom.stateBadge.textContent = stateLabels[state] || state.toUpperCase();
        this.dom.stateBadge.classList.add(`state-${state}`);

        if (state === "listening" && this.dom.audioWave) {
            this.dom.audioWave.classList.add("listening");
        } else if (state === "speaking" && this.dom.audioWave) {
            this.dom.audioWave.classList.add("speaking");
        } else if (this.dom.audioWave) {
            this.dom.audioWave.classList.add("idle");
        }
    }

    updateMicBadge(isMuted) {
        this.isMuted = isMuted;
        if (!this.dom.btnMicToggle) return;

        if (isMuted) {
            this.dom.btnMicToggle.classList.add("muted");
            if (this.dom.micIcon) this.dom.micIcon.textContent = "🔇";
            if (this.dom.micText) this.dom.micText.textContent = "Mudo";
        } else {
            this.dom.btnMicToggle.classList.remove("muted");
            if (this.dom.micIcon) this.dom.micIcon.textContent = "🎤";
            if (this.dom.micText) this.dom.micText.textContent = "Ativo";
        }
    }

    updateDashboardStatus(data) {
        // 1. Pomodoro
        if (data.pomodoro) {
            const p = data.pomodoro;
            const pState = p.state || "idle";
            const isActive = p.active !== undefined 
                ? Boolean(p.active) 
                : ["work", "break", "long_break", "paused", "work_finished", "break_finished", "long_break_finished"].includes(pState);
            this.pomodoroState = pState;

            if (!isActive || pState === "idle") {
                if (this.dom.pomoEmpty) this.dom.pomoEmpty.classList.remove("hidden");
                if (this.dom.pomoActiveDisplay) this.dom.pomoActiveDisplay.classList.add("hidden");
                if (this.dom.pomoPhaseBadge) this.dom.pomoPhaseBadge.classList.add("hidden");
                if (this.dom.pomoActions) this.dom.pomoActions.classList.add("idle");
                if (this.dom.btnPomoSkip) this.dom.btnPomoSkip.classList.add("hidden");
                if (this.dom.btnPomoReset) this.dom.btnPomoReset.classList.add("hidden");
                if (this.dom.btnPomoToggle) {
                    this.dom.btnPomoToggle.textContent = "▶ Iniciar";
                    this.dom.btnPomoToggle.className = "btn-action primary";
                }
            } else {
                if (this.dom.pomoPlanForm) this.dom.pomoPlanForm.classList.add("hidden");
                if (this.dom.pomoEmpty) this.dom.pomoEmpty.classList.add("hidden");
                if (this.dom.pomoActiveDisplay) this.dom.pomoActiveDisplay.classList.remove("hidden");
                if (this.dom.pomoPhaseBadge) this.dom.pomoPhaseBadge.classList.remove("hidden");
                if (this.dom.pomoActions) this.dom.pomoActions.classList.remove("idle");
                if (this.dom.btnPomoSkip) this.dom.btnPomoSkip.classList.remove("hidden");
                if (this.dom.btnPomoReset) this.dom.btnPomoReset.classList.remove("hidden");

                const left = p.left || 0;
                const m = Math.floor(left / 60);
                const s = left % 60;
                const timeStr = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;

                if (this.dom.pomoCountdown) {
                    this.dom.pomoCountdown.textContent = (p.state === "work_finished" || p.state === "break_finished" || p.state === "long_break_finished") ? "00:00" : timeStr;
                }
                const maxCycle = p.long_break_interval || 4;
                if (this.dom.pomoCycleText) this.dom.pomoCycleText.textContent = `Ciclo ${p.cycle || 1} de ${maxCycle}`;

                const phaseLabels = {
                    work: "Foco",
                    break: "Pausa",
                    long_break: "Pausa Longa",
                    idle: "Inativo",
                    paused: "Pausado",
                    work_finished: "Foco Concluído!",
                    break_finished: "Pausa Concluída!",
                    long_break_finished: "Pausa Longa Concluída!"
                };

                if (this.dom.pomoPhaseBadge) {
                    this.dom.pomoPhaseBadge.textContent = phaseLabels[p.state] || p.state;
                    this.dom.pomoPhaseBadge.className = `badge-phase ${p.state}`;
                }

                if (this.dom.btnPomoToggle) {
                    if (p.state === "work" || p.state === "break" || p.state === "long_break") {
                        this.dom.btnPomoToggle.textContent = "⏸ Pausar";
                        this.dom.btnPomoToggle.className = "btn-action";
                    } else if (p.state === "paused") {
                        this.dom.btnPomoToggle.textContent = "▶ Retomar";
                        this.dom.btnPomoToggle.className = "btn-action primary";
                    } else if (p.state === "work_finished") {
                        this.dom.btnPomoToggle.textContent = "▶ Iniciar Pausa";
                        this.dom.btnPomoToggle.className = "btn-action primary";
                    } else if (p.state === "break_finished" || p.state === "long_break_finished") {
                        this.dom.btnPomoToggle.textContent = "▶ Próximo Ciclo";
                        this.dom.btnPomoToggle.className = "btn-action primary";
                    } else {
                        this.dom.btnPomoToggle.textContent = "▶ Iniciar";
                        this.dom.btnPomoToggle.className = "btn-action primary";
                    }
                }
            }
        }

        // 2. Timers
        if (this.dom.timersBadgeCount) this.dom.timersBadgeCount.textContent = (data.timers || []).length;
        if (this.dom.alarmsBadgeCount) this.dom.alarmsBadgeCount.textContent = (data.alarms || []).length;

        if (data.timers && this.dom.timersList) {
            if (this.dom.btnCancelAllTimers) {
                if (data.timers.length > 0) {
                    this.dom.btnCancelAllTimers.classList.remove("hidden");
                } else {
                    this.dom.btnCancelAllTimers.classList.add("hidden");
                }
            }

            if (data.timers.length === 0) {
                this.dom.timersList.innerHTML = '<div class="empty-state">Nenhum timer ativo</div>';
            } else {
                this.dom.timersList.innerHTML = data.timers.map(t => {
                    const totalSecs = Math.max(0, Math.floor(t.left || 0));
                    const h = Math.floor(totalSecs / 3600);
                    const m = Math.floor((totalSecs % 3600) / 60);
                    const s = totalSecs % 60;
                    const timeFormatted = h > 0
                        ? `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
                        : `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
                    const isPaused = !!t.paused;
                    const toggleAction = isPaused ? "resume" : "pause";
                    const toggleIcon = isPaused ? "▶" : "⏸";
                    const toggleTitle = isPaused ? "Retomar timer" : "Pausar timer";
                    const timerId = this.escapeHtml(t.id || "");
                    const countdownHtml = isPaused
                        ? `<span class="timer-countdown paused">Pausado (${timeFormatted})</span>`
                        : `<span class="timer-countdown">${timeFormatted}</span>`;

                    return `
                        <div class="timer-item" data-id="${timerId}">
                            <span class="timer-label" title="${this.escapeHtml(t.label || 'Timer')}">⏱ ${this.escapeHtml(t.label || "Timer")}</span>
                            <div class="timer-item-right">
                                ${countdownHtml}
                                <button type="button" class="btn-timer-action btn-timer-toggle" data-id="${timerId}" data-action="${toggleAction}" title="${toggleTitle}">${toggleIcon}</button>
                                <button type="button" class="btn-timer-action danger btn-timer-cancel" data-id="${timerId}" title="Cancelar timer">✕</button>
                            </div>
                        </div>
                    `;
                }).join("");
            }
        }

        // 3. Alarmes
        if (data.alarms && this.dom.alarmsList) {
            if (this.dom.btnCancelAllAlarms) {
                if (data.alarms.length > 0) {
                    this.dom.btnCancelAllAlarms.classList.remove("hidden");
                } else {
                    this.dom.btnCancelAllAlarms.classList.add("hidden");
                }
            }

            if (data.alarms.length === 0) {
                this.dom.alarmsList.innerHTML = '<div class="empty-state">Nenhum alarme programado</div>';
            } else {
                this.dom.alarmsList.innerHTML = data.alarms.map(a => {
                    const isEnabled = a.enabled !== false;
                    const statusClass = isEnabled ? "enabled" : "disabled";
                    const statusText = isEnabled ? "Ativo" : "Desativado";
                    const toggleIcon = isEnabled ? "🔔" : "🔕";
                    const toggleTitle = isEnabled ? "Desativar alarme" : "Ativar alarme";
                    const alarmId = this.escapeHtml(a.id || "");
                    const alarmTime = this.escapeHtml(a.time || "--:--");
                    const alarmLabel = this.escapeHtml(a.label || "Alarme");

                    return `
                        <div class="alarm-item ${statusClass}" data-id="${alarmId}">
                            <span class="alarm-label" title="${alarmLabel}">⏰ ${alarmLabel}</span>
                            <div class="alarm-item-right">
                                <span class="alarm-time">${alarmTime}</span>
                                <span class="alarm-status-tag ${statusClass}">${statusText}</span>
                                <button type="button" class="btn-timer-action btn-alarm-toggle" data-id="${alarmId}" title="${toggleTitle}">${toggleIcon}</button>
                                <button type="button" class="btn-timer-action danger btn-alarm-cancel" data-id="${alarmId}" title="Excluir alarme">✕</button>
                            </div>
                        </div>
                    `;
                }).join("");
            }
        }
    }

    scrollToBottom() {
        if (!this.dom.chatStream) return;
        requestAnimationFrame(() => {
            this.dom.chatStream.scrollTop = this.dom.chatStream.scrollHeight;
        });
    }

    appendChatMessage(sender, text, label) {
        if (!this.dom.chatStream) return;

        const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const bubble = document.createElement("div");
        bubble.className = `message-bubble ${sender}`;

        bubble.innerHTML = `
            <div class="meta-info">${label} • ${timeStr}</div>
            <div class="text-body">${this.escapeHtml(text)}</div>
        `;

        this.dom.chatStream.appendChild(bubble);
        this.scrollToBottom();
    }

    appendSystemMessage(text) {
        if (!this.dom.chatStream) return;

        const msg = document.createElement("div");
        msg.className = "system-message";
        msg.textContent = text;

        this.dom.chatStream.appendChild(msg);
        this.scrollToBottom();
    }

    initEventListeners() {
        // Envio de prompt
        if (this.dom.btnSend) {
            this.dom.btnSend.addEventListener("click", () => this.submitPrompt());
        }

        if (this.dom.promptInput) {
            this.dom.promptInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    this.submitPrompt();
                }
            });
        }

        // Botão Mudo
        if (this.dom.btnMicToggle) {
            this.dom.btnMicToggle.addEventListener("click", () => {
                this.sendAction("toggle_mute");
            });
        }

        // Botão Cancelar
        if (this.dom.btnCancel) {
            this.dom.btnCancel.addEventListener("click", () => {
                this.sendAction("cancel");
            });
        }

        // Limpar chat
        if (this.dom.btnClearChat) {
            this.dom.btnClearChat.addEventListener("click", () => {
                if (this.dom.chatStream) {
                    this.dom.chatStream.innerHTML = "";
                    this.appendSystemMessage("Histórico de mensagens limpo.");
                }
            });
        }

        // Chips de sugestão
        document.querySelectorAll(".chip-suggestion").forEach(chip => {
            chip.addEventListener("click", () => {
                const prompt = chip.getAttribute("data-prompt");
                if (prompt && this.dom.promptInput) {
                    this.dom.promptInput.value = prompt;
                    this.submitPrompt();
                }
            });
        });

        // Planejamento do Pomodoro
        if (this.dom.btnTogglePlanPomo && this.dom.pomoPlanForm) {
            this.dom.btnTogglePlanPomo.addEventListener("click", () => {
                this.dom.pomoPlanForm.classList.toggle("hidden");
            });
        }

        // Chips de Presets de Pomodoro
        document.querySelectorAll(".plan-presets-row .preset-chip").forEach(chip => {
            chip.addEventListener("click", () => {
                document.querySelectorAll(".plan-presets-row .preset-chip").forEach(c => c.classList.remove("active"));
                chip.classList.add("active");
                const work = chip.getAttribute("data-work");
                const brk = chip.getAttribute("data-break");
                const longBreak = chip.getAttribute("data-long-break");
                const longInterval = chip.getAttribute("data-long-interval");
                if (this.dom.pomoInputWork && work) this.dom.pomoInputWork.value = work;
                if (this.dom.pomoInputBreak && brk) this.dom.pomoInputBreak.value = brk;
                if (this.dom.pomoInputLongBreak && longBreak) this.dom.pomoInputLongBreak.value = longBreak;
                if (this.dom.pomoInputLongInterval && longInterval) this.dom.pomoInputLongInterval.value = longInterval;
            });
        });

        // Iniciar Pomodoro Planejado
        if (this.dom.btnSavePlanPomo) {
            this.dom.btnSavePlanPomo.addEventListener("click", () => {
                const work = parseInt(this.dom.pomoInputWork?.value || "25", 10) || 25;
                const brk = parseInt(this.dom.pomoInputBreak?.value || "5", 10) || 5;
                const longBrk = parseInt(this.dom.pomoInputLongBreak?.value || "15", 10) || 15;
                const longInterval = parseInt(this.dom.pomoInputLongInterval?.value || "4", 10) || 4;
                const cycle = parseInt(this.dom.pomoInputCycles?.value || "1", 10) || 1;
                this.sendAction("pomodoro", {
                    sub_action: "start",
                    work_minutes: work,
                    break_minutes: brk,
                    long_break_minutes: longBrk,
                    long_break_interval: longInterval,
                    cycle: cycle
                });
                if (this.dom.pomoPlanForm) this.dom.pomoPlanForm.classList.add("hidden");
            });
        }

        // Controles de Pomodoro
        if (this.dom.btnPomoToggle) {
            this.dom.btnPomoToggle.addEventListener("click", () => {
                if (this.pomodoroState === "work" || this.pomodoroState === "break" || this.pomodoroState === "long_break") {
                    this.sendAction("pomodoro", { sub_action: "pause" });
                } else if (this.pomodoroState === "paused") {
                    this.sendAction("pomodoro", { sub_action: "resume" });
                } else if (this.pomodoroState === "work_finished" || this.pomodoroState === "break_finished" || this.pomodoroState === "long_break_finished") {
                    this.sendAction("pomodoro", { sub_action: "advance" });
                } else {
                    const work = parseInt(this.dom.pomoInputWork?.value || "25", 10) || 25;
                    const brk = parseInt(this.dom.pomoInputBreak?.value || "5", 10) || 5;
                    const longBrk = parseInt(this.dom.pomoInputLongBreak?.value || "15", 10) || 15;
                    const longInterval = parseInt(this.dom.pomoInputLongInterval?.value || "4", 10) || 4;
                    const cycle = parseInt(this.dom.pomoInputCycles?.value || "1", 10) || 1;
                    this.sendAction("pomodoro", {
                        sub_action: "start",
                        work_minutes: work,
                        break_minutes: brk,
                        long_break_minutes: longBrk,
                        long_break_interval: longInterval,
                        cycle: cycle
                    });
                }
            });
        }

        if (this.dom.btnPomoSkip) {
            this.dom.btnPomoSkip.addEventListener("click", () => {
                this.sendAction("pomodoro", { sub_action: "skip" });
            });
        }

        if (this.dom.btnPomoReset) {
            this.dom.btnPomoReset.addEventListener("click", () => {
                this.sendAction("pomodoro", { sub_action: "reset" });
            });
        }

        // Formulário de Novo Timer & Presets
        const timerPresetChips = document.querySelectorAll(".timer-preset");
        timerPresetChips.forEach(chip => {
            chip.addEventListener("click", () => {
                timerPresetChips.forEach(c => c.classList.remove("active"));
                chip.classList.add("active");
                const h = chip.dataset.h || "0";
                const m = chip.dataset.m || "0";
                const s = chip.dataset.s || "0";
                if (this.dom.newTimerHours) this.dom.newTimerHours.value = h;
                if (this.dom.newTimerMin) this.dom.newTimerMin.value = m;
                if (this.dom.newTimerSec) this.dom.newTimerSec.value = s;
            });
        });

        if (this.dom.btnToggleNewTimer && this.dom.newTimerForm) {
            this.dom.btnToggleNewTimer.addEventListener("click", () => {
                this.dom.newTimerForm.classList.toggle("hidden");
            });
        }

        if (this.dom.btnAddTimerSubmit) {
            this.dom.btnAddTimerSubmit.addEventListener("click", () => {
                const label = (this.dom.newTimerLabel && this.dom.newTimerLabel.value.trim()) || "Timer";
                const hours = parseInt(this.dom.newTimerHours ? this.dom.newTimerHours.value : 0, 10) || 0;
                const mins = parseInt(this.dom.newTimerMin ? this.dom.newTimerMin.value : 0, 10) || 0;
                const secs = parseInt(this.dom.newTimerSec ? this.dom.newTimerSec.value : 0, 10) || 0;

                this.sendAction("timer_add", {
                    hours: hours,
                    minutes: mins,
                    seconds: secs,
                    label: label
                });

                if (this.dom.newTimerForm) this.dom.newTimerForm.classList.add("hidden");
            });
        }

        // Ações de timers individuais e em lote
        if (this.dom.timersList) {
            this.dom.timersList.addEventListener("click", (e) => {
                const toggleBtn = e.target.closest(".btn-timer-toggle");
                if (toggleBtn) {
                    const id = toggleBtn.dataset.id;
                    const action = toggleBtn.dataset.action;
                    if (action === "pause") {
                        this.sendAction("timer_pause", { id });
                    } else {
                        this.sendAction("timer_resume", { id });
                    }
                    return;
                }

                const cancelBtn = e.target.closest(".btn-timer-cancel");
                if (cancelBtn) {
                    const id = cancelBtn.dataset.id;
                    this.sendAction("timer_cancel", { id });
                    return;
                }
            });
        }

        if (this.dom.btnCancelAllTimers) {
            this.dom.btnCancelAllTimers.addEventListener("click", () => {
                this.sendAction("timer_cancel", { query: "todos" });
            });
        }

        // Alternância de Abas (Timers vs Alarmes)
        if (this.dom.tabBtnTimers && this.dom.tabBtnAlarms) {
            this.dom.tabBtnTimers.addEventListener("click", () => {
                this.dom.tabBtnTimers.classList.add("active");
                this.dom.tabBtnAlarms.classList.remove("active");
                if (this.dom.tabContentTimers) this.dom.tabContentTimers.classList.remove("hidden");
                if (this.dom.tabContentAlarms) this.dom.tabContentAlarms.classList.add("hidden");
            });

            this.dom.tabBtnAlarms.addEventListener("click", () => {
                this.dom.tabBtnAlarms.classList.add("active");
                this.dom.tabBtnTimers.classList.remove("active");
                if (this.dom.tabContentAlarms) this.dom.tabContentAlarms.classList.remove("hidden");
                if (this.dom.tabContentTimers) this.dom.tabContentTimers.classList.add("hidden");
            });
        }

        // Formulário de Novo Alarme & Presets
        const alarmPresetChips = document.querySelectorAll(".alarm-preset");
        alarmPresetChips.forEach(chip => {
            chip.addEventListener("click", () => {
                alarmPresetChips.forEach(c => c.classList.remove("active"));
                chip.classList.add("active");
                const timeVal = chip.dataset.time;
                if (timeVal && this.dom.newAlarmTime) {
                    this.dom.newAlarmTime.value = timeVal;
                }
            });
        });

        if (this.dom.btnToggleNewAlarm && this.dom.newAlarmForm) {
            this.dom.btnToggleNewAlarm.addEventListener("click", () => {
                this.dom.newAlarmForm.classList.toggle("hidden");
            });
        }

        if (this.dom.btnAddAlarmSubmit) {
            this.dom.btnAddAlarmSubmit.addEventListener("click", () => {
                const label = (this.dom.newAlarmLabel && this.dom.newAlarmLabel.value.trim()) || "Alarme";
                const timeVal = (this.dom.newAlarmTime && this.dom.newAlarmTime.value) || "08:00";

                this.sendAction("alarm_add", {
                    time: timeVal,
                    label: label
                });

                if (this.dom.newAlarmForm) this.dom.newAlarmForm.classList.add("hidden");
            });
        }

        // Ações de alarmes individuais e em lote
        if (this.dom.alarmsList) {
            this.dom.alarmsList.addEventListener("click", (e) => {
                const toggleBtn = e.target.closest(".btn-alarm-toggle");
                if (toggleBtn) {
                    const id = toggleBtn.dataset.id;
                    this.sendAction("alarm_toggle", { id });
                    return;
                }

                const cancelBtn = e.target.closest(".btn-alarm-cancel");
                if (cancelBtn) {
                    const id = cancelBtn.dataset.id;
                    this.sendAction("alarm_cancel", { id });
                    return;
                }
            });
        }

        if (this.dom.btnCancelAllAlarms) {
            this.dom.btnCancelAllAlarms.addEventListener("click", () => {
                this.sendAction("alarm_clear_all", {});
            });
        }

        // Configurações do Ollama / Modal
        if (this.dom.btnOpenSettings) {
            this.dom.btnOpenSettings.addEventListener("click", () => this.openSettingsModal());
        }

        if (this.dom.btnCloseSettings) {
            this.dom.btnCloseSettings.addEventListener("click", () => this.closeSettingsModal());
        }

        if (this.dom.btnCancelSettings) {
            this.dom.btnCancelSettings.addEventListener("click", () => this.closeSettingsModal());
        }

        if (this.dom.settingsModal) {
            this.dom.settingsModal.addEventListener("click", (e) => {
                if (e.target === this.dom.settingsModal) {
                    this.closeSettingsModal();
                }
            });
        }

        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && this.dom.settingsModal && !this.dom.settingsModal.classList.contains("hidden")) {
                this.closeSettingsModal();
            }
        });

        // Presets de host Ollama
        document.querySelectorAll(".preset-chip").forEach(chip => {
            chip.addEventListener("click", () => {
                const host = chip.getAttribute("data-host");
                if (host && this.dom.cfgOllamaHost) {
                    this.dom.cfgOllamaHost.value = host;
                }
            });
        });

        // Abas de seleção de provedor
        if (this.dom.providerTabs) {
            this.dom.providerTabs.querySelectorAll(".provider-tab").forEach(tab => {
                tab.addEventListener("click", () => {
                    const prov = tab.getAttribute("data-provider");
                    if (prov) this.selectProvider(prov);
                });
            });
        }

        // Toggle de visibilidade da API key
        if (this.dom.btnToggleKeyVisibility && this.dom.cfgApiKey) {
            this.dom.btnToggleKeyVisibility.addEventListener("click", () => {
                const isPassword = this.dom.cfgApiKey.type === "password";
                this.dom.cfgApiKey.type = isPassword ? "text" : "password";
                this.dom.btnToggleKeyVisibility.textContent = isPassword ? "🙈" : "👁️";
            });
        }

        // Dropdown de modelos detectados
        if (this.dom.cfgModelDropdown) {
            this.dom.cfgModelDropdown.addEventListener("change", (e) => {
                if (e.target.value && this.dom.cfgLlmModel) {
                    this.dom.cfgLlmModel.value = e.target.value;
                }
            });
        }

        // Testar conexão
        if (this.dom.btnTestOllama) {
            this.dom.btnTestOllama.addEventListener("click", () => this.testOllamaConnection());
        }

        // Salvar configurações
        if (this.dom.btnSaveSettings) {
            this.dom.btnSaveSettings.addEventListener("click", () => this.saveOllamaSettings());
        }

        // Detectar container Docker do Ollama
        if (this.dom.btnDetectContainer) {
            this.dom.btnDetectContainer.addEventListener("click", () => this.detectOllamaContainer());
        }

        // Link de obter API Key
        if (this.dom.apiKeyLink) {
            this.dom.apiKeyLink.addEventListener("click", (e) => {
                e.preventDefault();
                const url = this.dom.apiKeyLink.getAttribute("href") || this.dom.apiKeyLink.href;
                if (url && url !== "#") {
                    this.openExternalUrl(url);
                }
            });
        }

        // Google Calendar - Abrir agenda no navegador
        if (this.dom.btnHeaderCalendar) {
            this.dom.btnHeaderCalendar.addEventListener("click", () => this.openCalendar());
        }
        if (this.dom.btnOpenCalendar) {
            this.dom.btnOpenCalendar.addEventListener("click", () => this.openCalendar());
        }

        // Google Calendar - Autorizar ou Desconectar conta
        if (this.dom.btnAuthCalendar) {
            this.dom.btnAuthCalendar.addEventListener("click", () => {
                const isConfigured = this.calendarInfo && (this.calendarInfo.status === "configured" || this.calendarInfo.token_exists);
                if (isConfigured) {
                    if (confirm("Deseja realmente desvincular sua conta Google deste computador?")) {
                        this.sendAction("disconnect_calendar", {}, (ok) => {
                            if (ok) {
                                this.appendSystemMessage("Conta Google desvinculada com sucesso.");
                                this.sendAction("check_calendar");
                            }
                        });
                    }
                    return;
                }

                const canAuth = this.calendarInfo && (this.calendarInfo.credentials_exists || this.calendarInfo.ready_to_auth);
                if (!canAuth) {
                    const clientId = prompt("Insira seu Google Client ID para ativar a sincronização em 1 clique:");
                    if (!clientId || !clientId.trim()) return;
                    const clientSecret = prompt("Insira seu Google Client Secret (opcional):") || "";
                    this.sendAction("save_google_creds", { client_id: clientId.trim(), client_secret: clientSecret.trim() }, (ok) => {
                        if (ok) {
                            this.appendSystemMessage("Client ID salvo! Abrindo navegador para autorizar...");
                            this.startCalendarAuth();
                        }
                    });
                    return;
                }

                this.startCalendarAuth();
            });
        }

        // Auto-Update - Verificar atualizações
        if (this.dom.btnCheckUpdates) {
            this.dom.btnCheckUpdates.addEventListener("click", () => {
                const originalText = this.dom.btnCheckUpdates.textContent;
                this.dom.btnCheckUpdates.textContent = "Verificando...";
                setTimeout(() => {
                    this.dom.btnCheckUpdates.textContent = originalText;
                }, 2000);
                this.appendSystemMessage("Verificando atualizações automáticas via GitHub Releases...");
                this.openExternalUrl("https://github.com/correavitor4/geraldo/releases");
            });
        }

        // Dispositivos de Áudio
        if (this.dom.btnRefreshAudio) {
            this.dom.btnRefreshAudio.addEventListener("click", () => this.loadAudioDevices());
        }
        if (this.dom.btnTestAudioBeep) {
            this.dom.btnTestAudioBeep.addEventListener("click", () => this.testAudioOutput());
        }
        if (this.dom.cfgAudioInput) {
            this.dom.cfgAudioInput.addEventListener("change", () => {
                const opt = this.dom.cfgAudioInput.selectedOptions[0];
                const lbl = (opt && opt.value) ? opt.textContent.replace(/^\[\d+\]\s*/, "") : "Padrão";
                if (this.dom.specsAudioInText) this.dom.specsAudioInText.textContent = lbl;
            });
        }
        if (this.dom.cfgAudioOutput) {
            this.dom.cfgAudioOutput.addEventListener("change", () => {
                const opt = this.dom.cfgAudioOutput.selectedOptions[0];
                const lbl = (opt && opt.value) ? opt.textContent.replace(/^\[\d+\]\s*/, "") : "Padrão";
                if (this.dom.specsAudioOutText) this.dom.specsAudioOutText.textContent = lbl;
            });
        }

        // Atalho TUI (Terminal)
        if (this.dom.btnExportTuiPath) {
            this.dom.btnExportTuiPath.addEventListener("click", () => this.exportTuiPath());
        }

        // Navegação de Abas Principais
        if (this.dom.mainNavTabs) {
            this.dom.mainNavTabs.forEach(tab => {
                tab.addEventListener("click", () => {
                    const view = tab.getAttribute("data-view");
                    if (view) this.switchMainTab(view);
                });
            });
        }
        if (this.dom.btnJumpToCalendarTab) {
            this.dom.btnJumpToCalendarTab.addEventListener("click", () => {
                this.switchMainTab("view-calendar");
            });
        }

        // Calendário Interativo: Navegação de Mês & Ações
        if (this.dom.btnCalPrevMonth) {
            this.dom.btnCalPrevMonth.addEventListener("click", () => {
                this.currentCalendarMonth--;
                if (this.currentCalendarMonth < 0) {
                    this.currentCalendarMonth = 11;
                    this.currentCalendarYear--;
                }
                this.renderCalendarMonthGrid();
            });
        }
        if (this.dom.btnCalNextMonth) {
            this.dom.btnCalNextMonth.addEventListener("click", () => {
                this.currentCalendarMonth++;
                if (this.currentCalendarMonth > 11) {
                    this.currentCalendarMonth = 0;
                    this.currentCalendarYear++;
                }
                this.renderCalendarMonthGrid();
            });
        }
        if (this.dom.btnCalToday) {
            this.dom.btnCalToday.addEventListener("click", () => {
                const now = new Date();
                this.currentCalendarYear = now.getFullYear();
                this.currentCalendarMonth = now.getMonth();
                const m = String(now.getMonth() + 1).padStart(2, '0');
                const d = String(now.getDate()).padStart(2, '0');
                this.selectCalendarDate(`${now.getFullYear()}-${m}-${d}`);
                this.renderCalendarMonthGrid();
            });
        }
        if (this.dom.btnCalRefresh) {
            this.dom.btnCalRefresh.addEventListener("click", () => {
                this.loadCalendarEvents();
            });
        }
        if (this.dom.btnCalToggleNew) {
            this.dom.btnCalToggleNew.addEventListener("click", () => {
                if (this.dom.calendarCreateForm) {
                    this.dom.calendarCreateForm.classList.toggle("hidden");
                }
            });
        }
        if (this.dom.btnCancelCreateEvent) {
            this.dom.btnCancelCreateEvent.addEventListener("click", () => {
                if (this.dom.calendarCreateForm) {
                    this.dom.calendarCreateForm.classList.add("hidden");
                }
            });
        }
        if (this.dom.btnSubmitCreateEvent) {
            this.dom.btnSubmitCreateEvent.addEventListener("click", () => {
                this.createCalendarEvent();
            });
        }
        if (this.dom.btnCalWebLink) {
            this.dom.btnCalWebLink.addEventListener("click", () => {
                this.openCalendar();
            });
        }
        if (this.dom.btnCalManageAuth && this.dom.btnAuthCalendar) {
            this.dom.btnCalManageAuth.addEventListener("click", () => {
                this.dom.btnAuthCalendar.click();
            });
        }

        // Pomodoro Expandido (Hero Controls)
        if (this.dom.btnPomoHeroToggle && this.dom.btnPomoToggle) {
            this.dom.btnPomoHeroToggle.addEventListener("click", () => {
                this.dom.btnPomoToggle.click();
            });
        }
        if (this.dom.btnPomoHeroSkip && this.dom.btnPomoSkip) {
            this.dom.btnPomoHeroSkip.addEventListener("click", () => {
                this.dom.btnPomoSkip.click();
            });
        }
        if (this.dom.btnPomoHeroReset && this.dom.btnPomoReset) {
            this.dom.btnPomoHeroReset.addEventListener("click", () => {
                this.dom.btnPomoReset.click();
            });
        }
        document.querySelectorAll(".pomo-mode-card").forEach(card => {
            card.addEventListener("click", () => {
                document.querySelectorAll(".pomo-mode-card").forEach(c => c.classList.remove("active"));
                card.classList.add("active");
                const work = card.getAttribute("data-work");
                const brk = card.getAttribute("data-break");
                const longBreak = card.getAttribute("data-long-break");
                const longInterval = card.getAttribute("data-long-interval");
                if (work) {
                    this.sendAction("pomodoro", {
                        sub_action: "start",
                        work_minutes: parseInt(work, 10),
                        break_minutes: parseInt(brk, 10),
                        long_break_minutes: parseInt(longBreak, 10),
                        long_break_interval: parseInt(longInterval, 10)
                    });
                }
            });
        });

        // Temporizadores Expandidos
        if (this.dom.btnFullTimerSubmit) {
            this.dom.btnFullTimerSubmit.addEventListener("click", () => {
                const label = this.dom.fullTimerLabel?.value.trim() || "Timer";
                const h = parseInt(this.dom.fullTimerH?.value || "0", 10) || 0;
                const m = parseInt(this.dom.fullTimerM?.value || "5", 10) || 5;
                const s = parseInt(this.dom.fullTimerS?.value || "0", 10) || 0;
                this.sendAction("timer_add", { hours: h, minutes: m, seconds: s, label });
            });
        }
        document.querySelectorAll(".timer-preset-full").forEach(chip => {
            chip.addEventListener("click", () => {
                document.querySelectorAll(".timer-preset-full").forEach(c => c.classList.remove("active"));
                chip.classList.add("active");
                const h = chip.getAttribute("data-h") || "0";
                const m = chip.getAttribute("data-m") || "5";
                const s = chip.getAttribute("data-s") || "0";
                if (this.dom.fullTimerH) this.dom.fullTimerH.value = h;
                if (this.dom.fullTimerM) this.dom.fullTimerM.value = m;
                if (this.dom.fullTimerS) this.dom.fullTimerS.value = s;
            });
        });

        if (this.dom.btnFullAlarmSubmit) {
            this.dom.btnFullAlarmSubmit.addEventListener("click", () => {
                const label = this.dom.fullAlarmLabel?.value.trim() || "Alarme";
                const time = this.dom.fullAlarmTime?.value.trim() || "08:00";
                this.sendAction("alarm_add", { time, label });
            });
        }
        document.querySelectorAll(".alarm-preset-full").forEach(chip => {
            chip.addEventListener("click", () => {
                document.querySelectorAll(".alarm-preset-full").forEach(c => c.classList.remove("active"));
                chip.classList.add("active");
                const time = chip.getAttribute("data-time") || "08:00";
                if (this.dom.fullAlarmTime) this.dom.fullAlarmTime.value = time;
            });
        });

        if (this.dom.btnQuickOpenSettingsModal) {
            this.dom.btnQuickOpenSettingsModal.addEventListener("click", () => {
                this.openSettingsModal();
            });
        }

        // Intercepta qualquer outro link externo no documento para abrir confiavelmente no navegador
        document.addEventListener("click", (e) => {
            const target = e.target.closest("a[target='_blank'], a.field-link");
            if (target && target.href && !target.href.startsWith("javascript:")) {
                e.preventDefault();
                this.openExternalUrl(target.href);
            }
        });
    }

    startCalendarAuth() {
        if (this.dom.btnAuthCalendar) {
            this.dom.btnAuthCalendar.textContent = "Aguardando navegador...";
            this.dom.btnAuthCalendar.disabled = true;
        }
        this.appendSystemMessage("Abrindo o navegador para autorizar o Geraldo no Google Calendar. Conclua o login na janela que se abriu...");

        this.sendAction("auth_calendar", {}, (ok, data, err) => {
            if (this.dom.btnAuthCalendar) {
                this.dom.btnAuthCalendar.disabled = false;
            }
            if (ok && data && data.success) {
                this.appendSystemMessage("Conta Google vinculada com sucesso! Você já pode consultar ou agendar compromissos.");
                this.sendAction("check_calendar");
            } else if (data && data.status === "missing_credentials") {
                this.appendSystemMessage(data.message || "Credenciais não configuradas.");
            } else {
                this.appendSystemMessage(`Falha na autorização: ${err || (data && data.message) || "Cancelado pelo usuário."}`);
                this.sendAction("check_calendar");
            }
        });
    }

    openCalendar() {
        this.openExternalUrl("https://calendar.google.com");
        this.sendAction("open_calendar");
        this.appendSystemMessage("Abrindo o Google Calendar no navegador...");
    }

    updateCalendarStatus(info) {
        if (!this.dom.calStatusBadge && !this.dom.calViewStatusPill) return;
        this.calendarInfo = info || {};
        const status = info ? info.status : "not_configured";
        const isConnected = (status === "configured" || (info && info.token_exists));

        if (isConnected) {
            if (this.dom.calStatusBadge) {
                this.dom.calStatusBadge.textContent = "Conectada";
                this.dom.calStatusBadge.className = "badge-tag status-ok";
            }
            if (this.dom.calViewStatusPill) {
                this.dom.calViewStatusPill.textContent = "Conectado";
                this.dom.calViewStatusPill.className = "status-pill-badge connected";
            }
            if (this.dom.settingsViewCalBadge) {
                this.dom.settingsViewCalBadge.textContent = "Conectado";
                this.dom.settingsViewCalBadge.className = "badge-tag status-ok";
            }
            if (this.dom.calAuthBtnLabel) {
                this.dom.calAuthBtnLabel.textContent = "Desconectar Conta";
            }
            if (this.dom.calStatusDesc) {
                this.dom.calStatusDesc.textContent = "Conta Google sincronizada. Comandos de voz ativos.";
            }
            if (this.dom.btnAuthCalendar) {
                this.dom.btnAuthCalendar.textContent = "Desconectar";
                this.dom.btnAuthCalendar.className = "btn-action";
                this.dom.btnAuthCalendar.title = "Clique para desvincular sua conta Google";
            }
        } else if (status === "partial" || (info && info.credentials_exists) || (info && info.ready_to_auth)) {
            if (this.dom.calStatusBadge) {
                this.dom.calStatusBadge.textContent = "1 Clique Pronto";
                this.dom.calStatusBadge.className = "badge-tag status-warn";
            }
            if (this.dom.calViewStatusPill) {
                this.dom.calViewStatusPill.textContent = "Pronto para Conectar";
                this.dom.calViewStatusPill.className = "status-pill-badge";
            }
            if (this.dom.settingsViewCalBadge) {
                this.dom.settingsViewCalBadge.textContent = "Pronto para Conectar";
                this.dom.settingsViewCalBadge.className = "badge-tag status-warn";
            }
            if (this.dom.calAuthBtnLabel) {
                this.dom.calAuthBtnLabel.textContent = "Conectar Google";
            }
            if (this.dom.calStatusDesc) {
                this.dom.calStatusDesc.textContent = "Tudo pronto! Clique em Conectar para autorizar no navegador.";
            }
            if (this.dom.btnAuthCalendar) {
                this.dom.btnAuthCalendar.textContent = "🔗 Conectar com Google";
                this.dom.btnAuthCalendar.className = "btn-action primary";
                this.dom.btnAuthCalendar.title = "Autorizar Google Calendar em 1 clique";
            }
        } else {
            if (this.dom.calStatusBadge) {
                this.dom.calStatusBadge.textContent = "Não Configurado";
                this.dom.calStatusBadge.className = "badge-tag status-offline";
            }
            if (this.dom.calViewStatusPill) {
                this.dom.calViewStatusPill.textContent = "Não Vinculado";
                this.dom.calViewStatusPill.className = "status-pill-badge disconnected";
            }
            if (this.dom.settingsViewCalBadge) {
                this.dom.settingsViewCalBadge.textContent = "Não Vinculado";
                this.dom.settingsViewCalBadge.className = "badge-tag status-offline";
            }
            if (this.dom.calAuthBtnLabel) {
                this.dom.calAuthBtnLabel.textContent = "Configurar Chave Google";
            }
            if (this.dom.calStatusDesc) {
                this.dom.calStatusDesc.textContent = "Clique para configurar seu Client ID do Google.";
            }
            if (this.dom.btnAuthCalendar) {
                this.dom.btnAuthCalendar.textContent = "⚙ Configurar Google";
                this.dom.btnAuthCalendar.className = "btn-action";
                this.dom.btnAuthCalendar.title = "Inserir chaves do Google";
            }
        }
    }

    // ==========================================
    // NAVEGAÇÃO DE ABAS PRINCIPAIS
    // ==========================================
    switchMainTab(viewId) {
        if (this.dom.mainNavTabs) {
            this.dom.mainNavTabs.forEach(tab => {
                const isTarget = tab.getAttribute("data-view") === viewId;
                tab.classList.toggle("active", isTarget);
                tab.setAttribute("aria-selected", isTarget ? "true" : "false");
            });
        }
        if (this.dom.mainViewPanels) {
            this.dom.mainViewPanels.forEach(panel => {
                const isTarget = panel.id === viewId;
                panel.classList.toggle("active", isTarget);
                panel.classList.toggle("hidden", !isTarget);
            });
        }

        if (viewId === "view-calendar") {
            this.loadCalendarEvents();
        }
    }

    // ==========================================
    // MÓDULO COMPLETO DE GOOGLE CALENDAR
    // ==========================================
    loadCalendarEvents() {
        this.sendAction("get_calendar_events", { days_ahead: 60, days_behind: 30 }, (ok, data) => {
            if (ok && data && Array.isArray(data.events)) {
                this.calendarEvents = data.events;
                this.renderCalendarMonthGrid();
                this.renderSelectedDayEvents(this.selectedCalendarDate);
                this.updateCalendarBadge();
            }
        });
    }

    updateCalendarBadge() {
        if (!this.dom.navCalendarBadge) return;
        const total = (this.calendarEvents || []).length;
        if (total > 0) {
            this.dom.navCalendarBadge.textContent = total;
            this.dom.navCalendarBadge.classList.remove("hidden");
        } else {
            this.dom.navCalendarBadge.classList.add("hidden");
        }
    }

    renderCalendarMonthGrid() {
        if (!this.dom.calendarDaysGrid || !this.dom.calendarMonthYearLabel) return;

        const monthNames = [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
        ];
        this.dom.calendarMonthYearLabel.textContent = `${monthNames[this.currentCalendarMonth]} ${this.currentCalendarYear}`;

        const firstDayOfMonth = new Date(this.currentCalendarYear, this.currentCalendarMonth, 1).getDay();
        const daysInCurrentMonth = new Date(this.currentCalendarYear, this.currentCalendarMonth + 1, 0).getDate();
        const daysInPrevMonth = new Date(this.currentCalendarYear, this.currentCalendarMonth, 0).getDate();

        const todayObj = new Date();
        const todayStr = `${todayObj.getFullYear()}-${String(todayObj.getMonth() + 1).padStart(2, '0')}-${String(todayObj.getDate()).padStart(2, '0')}`;

        let html = "";

        // 1. Dias do mês anterior para preencher a primeira semana
        for (let i = firstDayOfMonth - 1; i >= 0; i--) {
            const dayNum = daysInPrevMonth - i;
            const prevMonth = this.currentCalendarMonth === 0 ? 12 : this.currentCalendarMonth;
            const prevYear = this.currentCalendarMonth === 0 ? this.currentCalendarYear - 1 : this.currentCalendarYear;
            const dateStr = `${prevYear}-${String(prevMonth).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`;
            html += `
                <div class="cal-day-cell other-month" data-date="${dateStr}">
                    <span class="day-number">${dayNum}</span>
                </div>
            `;
        }

        // 2. Dias do mês corrente
        for (let dayNum = 1; dayNum <= daysInCurrentMonth; dayNum++) {
            const mStr = String(this.currentCalendarMonth + 1).padStart(2, '0');
            const dStr = String(dayNum).padStart(2, '0');
            const dateStr = `${this.currentCalendarYear}-${mStr}-${dStr}`;

            const isToday = dateStr === todayStr;
            const isSelected = dateStr === this.selectedCalendarDate;

            // Filtra eventos do dia
            const dayEvents = (this.calendarEvents || []).filter(ev => {
                if (!ev.start) return false;
                return ev.start.startsWith(dateStr);
            });

            const hasEvents = dayEvents.length > 0;
            let dotsHtml = "";
            if (hasEvents) {
                const countDots = Math.min(dayEvents.length, 3);
                dotsHtml = '<div class="day-events-dots">';
                for (let k = 0; k < countDots; k++) {
                    dotsHtml += '<span class="event-dot"></span>';
                }
                dotsHtml += '</div>';
            }

            const classes = [
                "cal-day-cell",
                isToday ? "today" : "",
                isSelected ? "selected" : "",
                hasEvents ? "has-events" : ""
            ].filter(Boolean).join(" ");

            html += `
                <div class="${classes}" data-date="${dateStr}">
                    <span class="day-number">${dayNum}</span>
                    ${dotsHtml}
                </div>
            `;
        }

        // 3. Dias do mês seguinte para completar até múltiplo de 7 (35 ou 42 células)
        const totalCellsSoFar = firstDayOfMonth + daysInCurrentMonth;
        const totalRows = Math.ceil(totalCellsSoFar / 7);
        const nextMonthDays = (totalRows * 7) - totalCellsSoFar;
        for (let dayNum = 1; dayNum <= nextMonthDays; dayNum++) {
            const nextMonth = this.currentCalendarMonth === 11 ? 1 : this.currentCalendarMonth + 2;
            const nextYear = this.currentCalendarMonth === 11 ? this.currentCalendarYear + 1 : this.currentCalendarYear;
            const dateStr = `${nextYear}-${String(nextMonth).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`;
            html += `
                <div class="cal-day-cell other-month" data-date="${dateStr}">
                    <span class="day-number">${dayNum}</span>
                </div>
            `;
        }

        this.dom.calendarDaysGrid.innerHTML = html;

        // Adiciona evento de clique nas células dos dias
        this.dom.calendarDaysGrid.querySelectorAll(".cal-day-cell").forEach(cell => {
            cell.addEventListener("click", () => {
                const dateStr = cell.getAttribute("data-date");
                if (dateStr) {
                    this.selectCalendarDate(dateStr);
                }
            });
        });
    }

    selectCalendarDate(dateStr) {
        this.selectedCalendarDate = dateStr;

        // Atualiza campos do formulário de novo evento
        if (this.dom.eventInputDate) {
            this.dom.eventInputDate.value = dateStr;
        }

        // Formata data por extenso em português
        try {
            const parts = dateStr.split("-");
            const y = parseInt(parts[0], 10);
            const m = parseInt(parts[1], 10) - 1;
            const d = parseInt(parts[2], 10);
            const dt = new Date(y, m, d);

            const dayNames = [
                "Domingo", "Segunda-feira", "Terça-feira", "Quarta-feira",
                "Quinta-feira", "Sexta-feira", "Sábado"
            ];
            const monthNames = [
                "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
            ];

            if (this.dom.selectedDayFullLabel) {
                this.dom.selectedDayFullLabel.textContent = `${dayNames[dt.getDay()]}, ${d} de ${monthNames[m]} de ${y}`;
            }
        } catch (e) {
            if (this.dom.selectedDayFullLabel) {
                this.dom.selectedDayFullLabel.textContent = dateStr;
            }
        }

        // Destaque visual da célula selecionada
        if (this.dom.calendarDaysGrid) {
            this.dom.calendarDaysGrid.querySelectorAll(".cal-day-cell").forEach(c => {
                const cellDate = c.getAttribute("data-date");
                c.classList.toggle("selected", cellDate === dateStr);
            });
        }

        this.renderSelectedDayEvents(dateStr);
    }

    renderSelectedDayEvents(dateStr) {
        if (!this.dom.selectedDayEventsList) return;

        const events = (this.calendarEvents || []).filter(ev => {
            if (!ev.start) return false;
            return ev.start.startsWith(dateStr);
        });

        if (this.dom.selectedDayEventsCount) {
            if (events.length === 0) {
                this.dom.selectedDayEventsCount.textContent = "Nenhum compromisso para este dia";
            } else if (events.length === 1) {
                this.dom.selectedDayEventsCount.textContent = "1 compromisso agendado";
            } else {
                this.dom.selectedDayEventsCount.textContent = `${events.length} compromissos agendados`;
            }
        }

        if (events.length === 0) {
            this.dom.selectedDayEventsList.innerHTML = `
                <div class="empty-state" style="padding: 30px 10px;">
                    <div style="font-size: 32px; margin-bottom: 8px;">✨</div>
                    <p style="color: var(--text-secondary); font-size: 13.5px; margin-bottom: 12px;">Sua agenda está livre neste dia.</p>
                    <button type="button" class="btn-action primary mini" onclick="window.geraldoApp.openCreateEventForm('${dateStr}')">
                        ➕ Agendar Compromisso
                    </button>
                </div>
            `;
            return;
        }

        this.dom.selectedDayEventsList.innerHTML = events.map(ev => {
            const summary = this.escapeHtml(ev.summary || "Sem título");
            const location = ev.location ? this.escapeHtml(ev.location) : "";
            const desc = ev.description ? this.escapeHtml(ev.description) : "";
            const isAllDay = !!ev.all_day;

            let timeBadge = "Dia Inteiro";
            if (!isAllDay && ev.start && ev.start.includes("T")) {
                const startH = ev.start.split("T")[1].substring(0, 5);
                const endH = ev.end && ev.end.includes("T") ? ev.end.split("T")[1].substring(0, 5) : "";
                timeBadge = endH ? `🕒 ${startH} - ${endH}` : `🕒 às ${startH}`;
            }

            const locHtml = location ? `<div class="cal-event-location">📍 ${location}</div>` : "";
            const descHtml = desc ? `<div class="cal-event-desc">${desc}</div>` : "";
            const evId = this.escapeHtml(ev.id || "");
            const webLink = ev.htmlLink ? `<a href="${this.escapeHtml(ev.htmlLink)}" target="_blank" class="field-link" style="font-size: 11.5px;">Google Agenda ↗</a>` : "";

            return `
                <div class="cal-event-card ${isAllDay ? 'all-day' : ''}" data-event-id="${evId}">
                    <div class="cal-event-time-badge">${timeBadge}</div>
                    <div class="cal-event-title">${summary}</div>
                    ${locHtml}
                    ${descHtml}
                    <div class="cal-event-footer">
                        <div>${webLink}</div>
                        <button type="button" class="btn-delete-event" onclick="window.geraldoApp.deleteCalendarEvent('${evId}', '${summary.replace(/'/g, "\\'")}')">
                            🗑️ Excluir
                        </button>
                    </div>
                </div>
            `;
        }).join("");
    }

    openCreateEventForm(dateStr) {
        if (this.dom.calendarCreateForm) {
            this.dom.calendarCreateForm.classList.remove("hidden");
            if (this.dom.eventInputDate) this.dom.eventInputDate.value = dateStr || this.selectedCalendarDate;
            if (this.dom.eventInputSummary) this.dom.eventInputSummary.focus();
        }
    }

    createCalendarEvent() {
        const summary = this.dom.eventInputSummary?.value.trim();
        if (!summary) {
            alert("Por favor, digite o título do compromisso.");
            this.dom.eventInputSummary?.focus();
            return;
        }

        const date = this.dom.eventInputDate?.value || this.selectedCalendarDate;
        const time = this.dom.eventInputTime?.value || "09:00";
        const duration = parseInt(this.dom.eventInputDuration?.value || "60", 10);
        const allDay = !!(this.dom.eventInputAllDay && this.dom.eventInputAllDay.checked);

        if (this.dom.btnSubmitCreateEvent) {
            this.dom.btnSubmitCreateEvent.textContent = "Salvando...";
            this.dom.btnSubmitCreateEvent.disabled = true;
        }

        this.sendAction("create_calendar_event", {
            summary: summary,
            date_query: date,
            time_str: time,
            duration_minutes: duration,
            all_day: allDay
        }, (ok, data, err) => {
            if (this.dom.btnSubmitCreateEvent) {
                this.dom.btnSubmitCreateEvent.textContent = "Salvar no Google Agenda";
                this.dom.btnSubmitCreateEvent.disabled = false;
            }

            if (ok && data) {
                this.appendSystemMessage(`📅 ${data.message || 'Compromisso agendado com sucesso!'}`);
                if (this.dom.eventInputSummary) this.dom.eventInputSummary.value = "";
                if (this.dom.calendarCreateForm) this.dom.calendarCreateForm.classList.add("hidden");
                this.loadCalendarEvents();
            } else {
                alert(`Erro ao criar compromisso: ${err || (data && data.message) || 'Falha na comunicação.'}`);
            }
        });
    }

    deleteCalendarEvent(eventId, summary) {
        if (!confirm(`Deseja realmente excluir o compromisso "${summary || 'Compromisso'}" da sua Agenda do Google?`)) {
            return;
        }

        this.sendAction("delete_calendar_event", { event_id: eventId, summary }, (ok, data, err) => {
            if (ok && data) {
                this.appendSystemMessage(`🗑️ ${data.message || 'Compromisso excluído da agenda.'}`);
                this.loadCalendarEvents();
            } else {
                alert(`Erro ao excluir compromisso: ${err || (data && data.message) || 'Falha.'}`);
            }
        });
    }

    selectProvider(prov) {
        this.currentProvider = prov;

        // Atualiza abas visuais
        if (this.dom.providerTabs) {
            this.dom.providerTabs.querySelectorAll(".provider-tab").forEach(tab => {
                if (tab.getAttribute("data-provider") === prov) {
                    tab.classList.add("active");
                } else {
                    tab.classList.remove("active");
                }
            });
        }

        const presets = {
            ollama: {
                defaultBase: "http://localhost:11434",
                defaultModel: "qwen2.5:3b",
                models: ["qwen2.5:3b", "llama3.2:3b", "mistral:latest"],
                link: "https://ollama.com",
                linkLabel: "Site oficial Ollama ↗"
            },
            groq: {
                defaultBase: "https://api.groq.com/openai/v1",
                defaultModel: "llama-3.3-70b-versatile",
                models: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
                link: "https://console.groq.com/keys",
                linkLabel: "Obter chave Groq (grátis) ↗"
            },
            openai: {
                defaultBase: "https://api.openai.com/v1",
                defaultModel: "gpt-4o-mini",
                models: ["gpt-4o-mini", "gpt-4o"],
                link: "https://platform.openai.com/api-keys",
                linkLabel: "Obter chave OpenAI ↗"
            },
            openrouter: {
                defaultBase: "https://openrouter.ai/api/v1",
                defaultModel: "meta-llama/llama-3.3-70b-instruct",
                models: ["meta-llama/llama-3.3-70b-instruct", "deepseek/deepseek-chat"],
                link: "https://openrouter.ai/keys",
                linkLabel: "Obter chave OpenRouter ↗"
            },
            gemini: {
                defaultBase: "https://generativelanguage.googleapis.com/v1beta/openai",
                defaultModel: "gemini-2.0-flash",
                models: ["gemini-2.0-flash", "gemini-1.5-flash"],
                link: "https://aistudio.google.com/apikey",
                linkLabel: "Obter chave Google AI Studio (grátis) ↗"
            },
            custom: {
                defaultBase: "http://localhost:8000/v1",
                defaultModel: "default",
                models: [],
                link: "",
                linkLabel: ""
            }
        };

        const meta = presets[prov] || presets.custom;

        // Alterna visibilidade das seções
        if (prov === "ollama") {
            if (this.dom.sectionOllama) this.dom.sectionOllama.classList.remove("hidden");
            if (this.dom.sectionExternal) this.dom.sectionExternal.classList.add("hidden");
        } else {
            if (this.dom.sectionOllama) this.dom.sectionOllama.classList.add("hidden");
            if (this.dom.sectionExternal) this.dom.sectionExternal.classList.remove("hidden");

            // Atualiza link de ajuda
            if (this.dom.apiKeyLink) {
                if (meta.link) {
                    this.dom.apiKeyLink.href = meta.link;
                    this.dom.apiKeyLink.textContent = meta.linkLabel || "Obter chave ↗";
                    this.dom.apiKeyLink.classList.remove("hidden");
                } else {
                    this.dom.apiKeyLink.classList.add("hidden");
                }
            }

            // Preenche endpoint base padrão se vazio ou se pertencia ao preset anterior
            if (this.dom.cfgApiBase) {
                if (!this.dom.cfgApiBase.value || this.dom.cfgApiBase.value.startsWith("https://api.") || this.dom.cfgApiBase.value.startsWith("https://openrouter")) {
                    this.dom.cfgApiBase.value = meta.defaultBase;
                }
            }
        }

        // Atualiza chips de sugestão de modelos para o provedor escolhido
        if (this.dom.modelPresetsContainer) {
            if (meta.models && meta.models.length > 0) {
                this.dom.modelPresetsContainer.innerHTML = meta.models.map(m =>
                    `<button type="button" class="model-preset-chip" data-model="${this.escapeHtml(m)}">${this.escapeHtml(m)}</button>`
                ).join("");

                this.dom.modelPresetsContainer.querySelectorAll(".model-preset-chip").forEach(chip => {
                    chip.addEventListener("click", () => {
                        const m = chip.getAttribute("data-model");
                        if (m && this.dom.cfgLlmModel) {
                            this.dom.cfgLlmModel.value = m;
                        }
                    });
                });
            } else {
                this.dom.modelPresetsContainer.innerHTML = "";
            }
        }
    }

    openSettingsModal() {
        if (!this.dom.settingsModal) return;

        const prov = this.llmConfig.provider || "ollama";
        this.selectProvider(prov);

        if (this.dom.cfgOllamaHost) {
            this.dom.cfgOllamaHost.value = this.llmConfig.ollama_host || "http://localhost:11434";
        }
        if (this.dom.cfgLlmModel) {
            this.dom.cfgLlmModel.value = this.llmConfig.llm_model || "qwen2.5:3b";
        }
        if (this.dom.cfgApiBase) {
            this.dom.cfgApiBase.value = this.llmConfig.api_base || "";
        }
        if (this.dom.cfgApiKey) {
            this.dom.cfgApiKey.value = "";
            this.dom.cfgApiKey.placeholder = this.llmConfig.has_api_key
                ? (this.llmConfig.api_key_masked || "Chave configurada (oculta)")
                : "Insira sua API Key (ex: gsk_... ou sk-...)";
        }

        if (this.dom.testResultBox) {
            this.dom.testResultBox.classList.add("hidden");
        }
        this.dom.settingsModal.classList.remove("hidden");
        if (this.connected) {
            this.sendAction("get_config");
            this.loadAudioDevices();
            this.checkTuiPathStatus();
        }
    }

    closeSettingsModal() {
        if (!this.dom.settingsModal) return;
        this.dom.settingsModal.classList.add("hidden");
    }

    detectOllamaContainer() {
        if (this.dom.testResultBox) {
            this.dom.testResultBox.classList.remove("hidden");
        }
        if (this.dom.testModelsContainer) {
            this.dom.testModelsContainer.innerHTML = "";
        }

        if (!this.connected) {
            if (this.dom.cfgOllamaHost) {
                this.dom.cfgOllamaHost.value = "http://localhost:11434";
            }
            if (this.dom.testStatusBadge) {
                this.dom.testStatusBadge.className = "badge-status warning";
                this.dom.testStatusBadge.textContent = "DAEMON DESCONECTADO";
            }
            if (this.dom.testStatusMsg) {
                this.dom.testStatusMsg.textContent = "Host configurado para http://localhost:11434 (porta padrão do container Docker). Inicie o Geraldo para testar o container.";
            }
            return;
        }

        if (this.dom.testStatusBadge) {
            this.dom.testStatusBadge.className = "badge-status testing";
            this.dom.testStatusBadge.textContent = "Buscando...";
        }
        if (this.dom.testStatusMsg) {
            this.dom.testStatusMsg.textContent = "Procurando container Docker do Ollama no sistema...";
        }

        this.sendAction("detect_container", {}, (ok, data) => {
            if (ok && data && data.detected && data.container) {
                const c = data.container;
                if (this.dom.cfgOllamaHost) {
                    this.dom.cfgOllamaHost.value = c.host_url;
                }
                this.testOllamaConnection();
            } else {
                if (this.dom.cfgOllamaHost) {
                    this.dom.cfgOllamaHost.value = "http://localhost:11434";
                }
                this.testOllamaConnection();
            }
        });
    }

    testOllamaConnection() {
        const prov = this.currentProvider || "ollama";
        if (this.dom.testResultBox) {
            this.dom.testResultBox.classList.remove("hidden");
        }
        if (this.dom.testModelsContainer) {
            this.dom.testModelsContainer.innerHTML = "";
        }

        if (!this.connected) {
            if (this.dom.testStatusBadge) {
                this.dom.testStatusBadge.className = "badge-status error";
                this.dom.testStatusBadge.textContent = "DAEMON INATIVO";
            }
            if (this.dom.testStatusMsg) {
                this.dom.testStatusMsg.textContent = "O daemon do Geraldo não está rodando na porta 8765. Inicie o Geraldo ('python main.py' ou app desktop) para testar a conexão com o Ollama.";
            }
            if (this.dom.testModelsContainer) {
                this.dom.testModelsContainer.innerHTML = '<span class="field-hint">Dica: se o container Docker já estiver rodando, o Geraldo irá detectá-lo automaticamente ao iniciar.</span>';
            }
            return;
        }

        if (this.dom.testStatusBadge) {
            this.dom.testStatusBadge.className = "badge-status testing";
            this.dom.testStatusBadge.textContent = "Testando...";
        }

        if (prov === "ollama") {
            const host = (this.dom.cfgOllamaHost && this.dom.cfgOllamaHost.value.trim()) || "http://localhost:11434";
            if (this.dom.testStatusMsg) {
                this.dom.testStatusMsg.textContent = `Consultando Ollama em ${host}...`;
            }
            this.sendAction("check_ollama", { host: host });
        } else {
            const apiKey = (this.dom.cfgApiKey && this.dom.cfgApiKey.value.trim()) || "";
            const apiBase = (this.dom.cfgApiBase && this.dom.cfgApiBase.value.trim()) || "";
            const model = (this.dom.cfgLlmModel && this.dom.cfgLlmModel.value.trim()) || "";
            if (this.dom.testStatusMsg) {
                this.dom.testStatusMsg.textContent = `Verificando credenciais no ${prov.toUpperCase()}...`;
            }
            this.sendAction("check_llm", {
                provider: prov,
                api_key: apiKey,
                api_base: apiBase,
                model: model,
            });
        }
    }

    displayTestResults(data) {
        if (!this.dom.testResultBox) return;
        this.dom.testResultBox.classList.remove("hidden");

        const isOk = data && (data.status === "ok" || data.connected === true);
        if (isOk) {
            // Se o backend detectou o container e sugeriu uma URL efetiva diferente da atual, atualiza o input
            if (data.suggested_host && this.dom.cfgOllamaHost) {
                this.dom.cfgOllamaHost.value = data.suggested_host;
            }

            if (this.dom.testStatusBadge) {
                this.dom.testStatusBadge.className = "badge-status success";
                this.dom.testStatusBadge.textContent = "CONECTADO";
            }
            if (this.dom.testStatusMsg) {
                this.dom.testStatusMsg.textContent = data.message || `Provedor ativo e respondendo!`;
            }

            // Exibe tags de modelos disponíveis e popula dropdown se disponível
            if (this.dom.testModelsContainer && data.available_models && data.available_models.length > 0) {
                const currentModel = (this.dom.cfgLlmModel && this.dom.cfgLlmModel.value.trim()) || "";
                this.dom.testModelsContainer.innerHTML = data.available_models.map(m => {
                    const isSelected = currentModel && m.includes(currentModel);
                    return `<span class="model-tag ${isSelected ? 'selected' : ''}" data-model="${this.escapeHtml(m)}">${this.escapeHtml(m)}</span>`;
                }).join("");

                this.dom.testModelsContainer.querySelectorAll(".model-tag").forEach(tag => {
                    tag.addEventListener("click", () => {
                        const m = tag.getAttribute("data-model");
                        if (this.dom.cfgLlmModel) {
                            this.dom.cfgLlmModel.value = m;
                        }
                        this.dom.testModelsContainer.querySelectorAll(".model-tag").forEach(t => t.classList.remove("selected"));
                        tag.classList.add("selected");
                    });
                });
            }

            if (this.dom.cfgModelDropdown && data.available_models && data.available_models.length > 0) {
                this.dom.cfgModelDropdown.classList.remove("hidden");
                this.dom.cfgModelDropdown.innerHTML = '<option value="">Modelos detectados...</option>' +
                    data.available_models.map(m => `<option value="${this.escapeHtml(m)}">${this.escapeHtml(m)}</option>`).join("");
            }
        } else {
            if (this.dom.testStatusBadge) {
                this.dom.testStatusBadge.className = "badge-status error";
                this.dom.testStatusBadge.textContent = "INACESSÍVEL";
            }
            if (this.dom.testStatusMsg) {
                this.dom.testStatusMsg.textContent = (data && (data.message || data.error)) || "Não foi possível conectar ao endpoint.";
            }
            if (this.dom.testModelsContainer) {
                const hint = this.currentProvider === "ollama"
                    ? "Dica: certifique-se de que o container do Ollama está rodando com a porta 11434 exposta ('docker run -d -p 11434:11434 ollama/ollama')."
                    : "Dica: verifique se sua API Key é válida e se há saldo ou cota disponível.";
                this.dom.testModelsContainer.innerHTML = `<span class="field-hint">${hint}</span>`;
            }
        }
    }

    saveOllamaSettings() {
        const prov = this.currentProvider || "ollama";
        const host = (this.dom.cfgOllamaHost && this.dom.cfgOllamaHost.value.trim()) || "http://localhost:11434";
        const model = (this.dom.cfgLlmModel && this.dom.cfgLlmModel.value.trim()) || "qwen2.5:3b";
        const apiKey = (this.dom.cfgApiKey && this.dom.cfgApiKey.value.trim()) || "";
        const apiBase = (this.dom.cfgApiBase && this.dom.cfgApiBase.value.trim()) || "";

        const audioIn = this.dom.cfgAudioInput ? this.dom.cfgAudioInput.value : "";
        const audioOut = this.dom.cfgAudioOutput ? this.dom.cfgAudioOutput.value : "";

        const payload = {
            provider: prov,
            ollama_host: host,
            llm_model: model,
            audio_input_device: audioIn || null,
            audio_output_device: audioOut || null,
            persist: true
        };
        if (apiKey) payload.api_key = apiKey;
        if (apiBase) payload.api_base = apiBase;

        // Salva imediatamente no localStorage para garantir persistência mesmo sem daemon conectado
        try {
            localStorage.setItem("geraldo_llm_config", JSON.stringify(payload));
        } catch (e) {}

        this.updateConfigDisplay(payload);

        // Feedback visual imediato no botão
        const origBtnText = this.dom.btnSaveSettings ? this.dom.btnSaveSettings.innerHTML : "💾 Salvar Configurações";
        if (this.dom.btnSaveSettings) {
            this.dom.btnSaveSettings.innerHTML = "💾 Salvando...";
            this.dom.btnSaveSettings.disabled = true;
        }

        if (this.dom.testResultBox) {
            this.dom.testResultBox.classList.remove("hidden");
        }

        if (!this.connected) {
            if (this.dom.testStatusBadge) {
                this.dom.testStatusBadge.className = "badge-status success";
                this.dom.testStatusBadge.textContent = "SALVO NO APP";
            }
            if (this.dom.testStatusMsg) {
                this.dom.testStatusMsg.textContent = "Configurações salvas localmente! (Aviso: Daemon do Geraldo está desconectado. As alterações serão sincronizadas assim que o serviço iniciar).";
            }
            this.appendSystemMessage("Configurações salvas no cliente (Geraldo daemon desconectado).");
            setTimeout(() => {
                if (this.dom.btnSaveSettings) {
                    this.dom.btnSaveSettings.innerHTML = origBtnText;
                    this.dom.btnSaveSettings.disabled = false;
                }
                this.closeSettingsModal();
            }, 1200);
            return;
        }

        this.sendAction("set_config", payload, (ok, data, err) => {
            if (this.dom.btnSaveSettings) {
                this.dom.btnSaveSettings.innerHTML = origBtnText;
                this.dom.btnSaveSettings.disabled = false;
            }
            if (ok) {
                if (this.dom.testStatusBadge) {
                    this.dom.testStatusBadge.className = "badge-status success";
                    this.dom.testStatusBadge.textContent = "SALVO COM SUCESSO";
                }
                if (this.dom.testStatusMsg) {
                    this.dom.testStatusMsg.textContent = "Configurações sincronizadas e salvas com sucesso no Geraldo!";
                }
                this.appendSystemMessage("Configurações de IA salvas com sucesso!");
                setTimeout(() => {
                    this.closeSettingsModal();
                }, 1000);
            } else {
                if (this.dom.testStatusBadge) {
                    this.dom.testStatusBadge.className = "badge-status error";
                    this.dom.testStatusBadge.textContent = "ERRO AO SALVAR";
                }
                if (this.dom.testStatusMsg) {
                    this.dom.testStatusMsg.textContent = err || "Não foi possível salvar configurações no daemon.";
                }
            }
        });
    }

    updateConfigDisplay(config) {
        if (!config) return;
        this.llmConfig = Object.assign({}, this.llmConfig, config);
        this.ollamaConfig = this.llmConfig;

        if (config.audio) {
            this.updateAudioDevicesDisplay(config.audio);
        }

        if (config.provider) {
            this.currentProvider = config.provider;
        }

        if (this.dom.cfgOllamaHost && this.dom.settingsModal && !this.dom.settingsModal.classList.contains("hidden")) {
            this.dom.cfgOllamaHost.value = this.llmConfig.ollama_host || "http://localhost:11434";
        }
        if (this.dom.cfgLlmModel && this.dom.settingsModal && !this.dom.settingsModal.classList.contains("hidden")) {
            this.dom.cfgLlmModel.value = this.llmConfig.llm_model || "qwen2.5:3b";
        }
        if (this.dom.cfgApiBase && this.dom.settingsModal && !this.dom.settingsModal.classList.contains("hidden")) {
            this.dom.cfgApiBase.value = this.llmConfig.api_base || "";
        }
        if (this.dom.cfgApiKey && this.dom.settingsModal && !this.dom.settingsModal.classList.contains("hidden")) {
            if (this.llmConfig.has_api_key) {
                this.dom.cfgApiKey.placeholder = this.llmConfig.api_key_masked || "Chave configurada (oculta)";
            }
        }

        if (this.dom.specsLlmText) {
            const prov = (this.llmConfig.provider || "ollama").toLowerCase();
            const provName = prov === "ollama" ? "Ollama" : (prov.charAt(0).toUpperCase() + prov.slice(1));
            const modelName = this.llmConfig.llm_model || "qwen2.5:3b";
            this.dom.specsLlmText.textContent = `${provName} (${modelName})`;
            const titleHost = prov === "ollama"
                ? (this.llmConfig.ollama_host || "http://localhost:11434")
                : (this.llmConfig.api_base || "API Externa");
            this.dom.specsLlmText.title = `Provedor: ${provName} | Endpoint: ${titleHost}`;
        }
    }

    loadAudioDevices() {
        if (!this.connected) return;
        this.sendAction("get_audio_config", {}, (ok, data) => {
            if (ok && data) {
                this.updateAudioDevicesDisplay(data);
            }
        });
    }

    updateAudioDevicesDisplay(data) {
        if (!data) return;
        this.audioConfig = Object.assign({}, this.audioConfig, data);
        const inSelect = this.dom.cfgAudioInput;
        const outSelect = this.dom.cfgAudioOutput;
        const curIn = (data.input_device !== undefined && data.input_device !== null) ? String(data.input_device) : "";
        const curOut = (data.output_device !== undefined && data.output_device !== null) ? String(data.output_device) : "";

        const inputs = (data.devices && Array.isArray(data.devices.inputs))
            ? data.devices.inputs
            : (Array.isArray(data.available_inputs) ? data.available_inputs : (Array.isArray(data.inputs) ? data.inputs : null));
        const outputs = (data.devices && Array.isArray(data.devices.outputs))
            ? data.devices.outputs
            : (Array.isArray(data.available_outputs) ? data.available_outputs : (Array.isArray(data.outputs) ? data.outputs : null));

        let activeInLabel = "Padrão";
        let activeOutLabel = "Padrão";

        if (inSelect && inputs) {
            let html = '<option value="">Padrão do Sistema</option>';
            inputs.forEach(dev => {
                const isSelected = (curIn !== "" && (String(dev.id) === curIn || dev.name.toLowerCase().includes(curIn.toLowerCase())));
                if (isSelected) {
                    activeInLabel = dev.name;
                }
                const api = dev.hostapi_name ? ` (${dev.hostapi_name})` : '';
                html += `<option value="${dev.id}" ${isSelected ? 'selected' : ''}>[${dev.id}] ${this.escapeHtml(dev.name)}${api}</option>`;
            });
            inSelect.innerHTML = html;
        }

        if (outSelect && outputs) {
            let html = '<option value="">Padrão do Sistema</option>';
            outputs.forEach(dev => {
                const isSelected = (curOut !== "" && (String(dev.id) === curOut || dev.name.toLowerCase().includes(curOut.toLowerCase())));
                if (isSelected) {
                    activeOutLabel = dev.name;
                }
                const api = dev.hostapi_name ? ` (${dev.hostapi_name})` : '';
                html += `<option value="${dev.id}" ${isSelected ? 'selected' : ''}>[${dev.id}] ${this.escapeHtml(dev.name)}${api}</option>`;
            });
            outSelect.innerHTML = html;
        }

        if (this.dom.specsAudioInText) {
            this.dom.specsAudioInText.textContent = activeInLabel;
            this.dom.specsAudioInText.title = `Microfone ativo: ${activeInLabel}`;
        }
        if (this.dom.specsAudioOutText) {
            this.dom.specsAudioOutText.textContent = activeOutLabel;
            this.dom.specsAudioOutText.title = `Saída de áudio ativa: ${activeOutLabel}`;
        }
    }

    testAudioOutput() {
        const outSelect = this.dom.cfgAudioOutput;
        const selectedDev = outSelect ? outSelect.value : "";
        const origText = this.dom.btnTestAudioBeep ? this.dom.btnTestAudioBeep.innerHTML : "🔔 Testar Saída de Áudio";
        if (this.dom.btnTestAudioBeep) {
            this.dom.btnTestAudioBeep.innerHTML = "🔔 Reproduzindo...";
            this.dom.btnTestAudioBeep.disabled = true;
        }

        this.sendAction("test_audio_beep", { device: selectedDev || null }, (ok, data, err) => {
            setTimeout(() => {
                if (this.dom.btnTestAudioBeep) {
                    this.dom.btnTestAudioBeep.innerHTML = origText;
                    this.dom.btnTestAudioBeep.disabled = false;
                }
            }, 1000);
            if (ok) {
                this.appendSystemMessage("🔔 Som de teste reproduzido na saída de áudio.");
            } else {
                this.appendSystemMessage(`Erro ao reproduzir teste de som: ${err || (data && data.message) || "Falha"}`);
            }
        });
    }

    checkTuiPathStatus() {
        if (!this.connected) return;
        this.sendAction("get_tui_path_status", {}, (ok, data) => {
            if (ok && data) {
                this.updateTuiPathBadge(data);
            }
        });
    }

    updateTuiPathBadge(data) {
        const badge = this.dom.tuiPathStatusBadge;
        if (!badge || !data) return;
        if (data.in_path) {
            badge.textContent = "Configurado no PATH";
            badge.className = "badge-tag status-ok";
        } else if (data.installed) {
            badge.textContent = "Reabra o Terminal";
            badge.className = "badge-tag status-warn";
        } else {
            badge.textContent = "Não Configurado";
            badge.className = "badge-tag status-offline";
        }
    }

    exportTuiPath() {
        const origText = this.dom.btnExportTuiPath ? this.dom.btnExportTuiPath.innerHTML : "⚡ Configurar 'geraldo_tui' no PATH";
        if (this.dom.btnExportTuiPath) {
            this.dom.btnExportTuiPath.innerHTML = "⚡ Configurando...";
            this.dom.btnExportTuiPath.disabled = true;
        }

        this.sendAction("export_tui_path", {}, (ok, data, err) => {
            setTimeout(() => {
                if (this.dom.btnExportTuiPath) {
                    this.dom.btnExportTuiPath.innerHTML = origText;
                    this.dom.btnExportTuiPath.disabled = false;
                }
            }, 1200);

            if (ok && data) {
                this.appendSystemMessage(`Atalho TUI: ${data.message || 'Configurado com sucesso!'}`);
                this.checkTuiPathStatus();
            } else {
                this.appendSystemMessage(`Falha ao configurar atalho TUI: ${err || 'Erro'}`);
            }
        });
    }

    submitPrompt() {
        if (!this.dom.promptInput) return;
        const text = this.dom.promptInput.value.trim();
        if (!text) return;

        this.appendChatMessage("user", text, "Você");
        this.updateStateBadge("thinking");
        this.sendAction("send_prompt", { text: text }, (ok, data, err) => {
            if (ok && data && (data.reply || data.text)) {
                const rep = data.reply || data.text;
                if (this._lastDisplayedReply !== rep) {
                    this._lastDisplayedReply = rep;
                    setTimeout(() => {
                        if (this._lastDisplayedReply === rep) {
                            this._lastDisplayedReply = null;
                        }
                    }, 3000);
                    this.appendChatMessage("assistant", rep, "Geraldo");
                }
            } else if (!ok && err) {
                this.appendSystemMessage(`Erro ao processar prompt: ${err}`);
            }
        });
        this.dom.promptInput.value = "";
    }

    escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
}

// Inicializa a aplicação ao carregar a página
document.addEventListener("DOMContentLoaded", () => {
    window.geraldoApp = new GeraldoDesktopClient();
});

// Suporte para exportação em ambiente de testes Node/Jest se aplicável
if (typeof module !== "undefined" && module.exports) {
    module.exports = { GeraldoDesktopClient };
}
