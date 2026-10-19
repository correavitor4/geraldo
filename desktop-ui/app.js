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
            btnPomoToggle: document.getElementById("btn-pomo-toggle"),
            btnPomoSkip: document.getElementById("btn-pomo-skip"),
            btnPomoReset: document.getElementById("btn-pomo-reset"),
            // Timers & Alarms
            timersList: document.getElementById("timers-list"),
            alarmsList: document.getElementById("alarms-list"),
            btnToggleNewTimer: document.getElementById("btn-toggle-new-timer"),
            newTimerForm: document.getElementById("new-timer-form"),
            btnAddTimerSubmit: document.getElementById("btn-add-timer-submit"),
            newTimerLabel: document.getElementById("new-timer-label"),
            newTimerMin: document.getElementById("new-timer-min"),
            newTimerSec: document.getElementById("new-timer-sec"),
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
            updaterStatusBadge: document.getElementById("updater-status-badge")
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
            }
        }
    }

    sendAction(action, params = {}, callback = null) {
        if (!this.connected || !this.ws) {
            this.appendSystemMessage("Não conectado ao daemon do Geraldo.");
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
            this.pomodoroState = p.state || "idle";
            const left = p.left || 0;
            const m = Math.floor(left / 60);
            const s = left % 60;
            const timeStr = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;

            if (this.dom.pomoCountdown) this.dom.pomoCountdown.textContent = timeStr;
            if (this.dom.pomoCycleText) this.dom.pomoCycleText.textContent = `Ciclo ${p.cycle || 1} de 4`;

            const phaseLabels = {
                work: "Foco",
                break: "Pausa",
                idle: "Inativo",
                paused: "Pausado",
                work_finished: "Foco Concluído!",
                break_finished: "Pausa Concluída!"
            };

            if (this.dom.pomoPhaseBadge) {
                this.dom.pomoPhaseBadge.textContent = phaseLabels[p.state] || p.state;
                this.dom.pomoPhaseBadge.className = `badge-phase ${p.state}`;
            }

            if (this.dom.btnPomoToggle) {
                if (p.state === "work" || p.state === "break") {
                    this.dom.btnPomoToggle.textContent = "⏸ Pausar";
                    this.dom.btnPomoToggle.className = "btn-action";
                } else {
                    this.dom.btnPomoToggle.textContent = "▶ Foco";
                    this.dom.btnPomoToggle.className = "btn-action primary";
                }
            }
        }

        // 2. Timers
        if (data.timers && this.dom.timersList) {
            if (data.timers.length === 0) {
                this.dom.timersList.innerHTML = '<div class="empty-state">Nenhum timer ativo</div>';
            } else {
                this.dom.timersList.innerHTML = data.timers.map(t => {
                    const m = Math.floor(t.left / 60);
                    const s = t.left % 60;
                    const timeStr = t.paused ? "Pausado" : `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
                    return `
                        <div class="timer-item">
                            <span class="timer-label">⏱ ${this.escapeHtml(t.label || "Timer")}</span>
                            <span class="timer-countdown">${timeStr}</span>
                        </div>
                    `;
                }).join("");
            }
        }

        // 3. Alarmes
        if (data.alarms && this.dom.alarmsList) {
            if (data.alarms.length === 0) {
                this.dom.alarmsList.innerHTML = '<div class="empty-state">Nenhum alarme programado</div>';
            } else {
                this.dom.alarmsList.innerHTML = data.alarms.map(a => {
                    const statusClass = a.enabled ? "enabled" : "disabled";
                    return `
                        <div class="alarm-item">
                            <span class="alarm-label">⏰ ${this.escapeHtml(a.label || "Alarme")}</span>
                            <span class="alarm-time ${statusClass}">${a.time || "--:--"}</span>
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

        // Controles de Pomodoro
        if (this.dom.btnPomoToggle) {
            this.dom.btnPomoToggle.addEventListener("click", () => {
                const action = (this.pomodoroState === "work" || this.pomodoroState === "break") ? "pause" : "start";
                this.sendAction("pomodoro", { sub_action: action });
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

        // Formulário de Novo Timer
        if (this.dom.btnToggleNewTimer && this.dom.newTimerForm) {
            this.dom.btnToggleNewTimer.addEventListener("click", () => {
                this.dom.newTimerForm.classList.toggle("hidden");
            });
        }

        if (this.dom.btnAddTimerSubmit) {
            this.dom.btnAddTimerSubmit.addEventListener("click", () => {
                const label = (this.dom.newTimerLabel && this.dom.newTimerLabel.value.trim()) || "Timer";
                const mins = parseInt(this.dom.newTimerMin ? this.dom.newTimerMin.value : 0, 10) || 0;
                const secs = parseInt(this.dom.newTimerSec ? this.dom.newTimerSec.value : 0, 10) || 0;

                this.sendAction("timer_add", {
                    minutes: mins,
                    seconds: secs,
                    label: label
                });

                if (this.dom.newTimerForm) this.dom.newTimerForm.classList.add("hidden");
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
        if (!this.dom.calStatusBadge) return;
        this.calendarInfo = info || {};
        const status = info ? info.status : "not_configured";

        if (status === "configured" || (info && info.token_exists)) {
            this.dom.calStatusBadge.textContent = "Conectada";
            this.dom.calStatusBadge.className = "badge-tag status-ok";
            if (this.dom.calStatusDesc) {
                this.dom.calStatusDesc.textContent = "Conta Google sincronizada. Comandos de voz ativos.";
            }
            if (this.dom.btnAuthCalendar) {
                this.dom.btnAuthCalendar.textContent = "Desconectar";
                this.dom.btnAuthCalendar.className = "btn-action";
                this.dom.btnAuthCalendar.title = "Clique para desvincular sua conta Google";
            }
        } else if (status === "partial" || (info && info.credentials_exists) || (info && info.ready_to_auth)) {
            this.dom.calStatusBadge.textContent = "1 Clique Pronto";
            this.dom.calStatusBadge.className = "badge-tag status-warn";
            if (this.dom.calStatusDesc) {
                this.dom.calStatusDesc.textContent = "Tudo pronto! Clique em Conectar para autorizar no navegador.";
            }
            if (this.dom.btnAuthCalendar) {
                this.dom.btnAuthCalendar.textContent = "🔗 Conectar com Google";
                this.dom.btnAuthCalendar.className = "btn-action primary";
                this.dom.btnAuthCalendar.title = "Autorizar Google Calendar em 1 clique";
            }
        } else {
            this.dom.calStatusBadge.textContent = "Não Configurado";
            this.dom.calStatusBadge.className = "badge-tag status-offline";
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

        const payload = {
            provider: prov,
            ollama_host: host,
            llm_model: model,
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
