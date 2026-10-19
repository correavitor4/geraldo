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
            newTimerSec: document.getElementById("new-timer-sec")
        };

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
                    this.appendChatMessage("assistant", replyText, "Geraldo");
                }
                break;

            case "status_update":
                this.updateDashboardStatus(data);
                break;

            case "cancelled":
                this.appendSystemMessage("Ação ou som interrompido.");
                break;
        }
    }

    handleResponse(msg) {
        if (msg.status === "error") {
            this.appendSystemMessage(`Erro: ${msg.error || "Operação falhou"}`);
        }
    }

    sendAction(action, params = {}) {
        if (!this.connected || !this.ws) {
            this.appendSystemMessage("Não conectado ao daemon do Geraldo.");
            return;
        }

        const payload = {
            id: `gui-${Date.now()}`,
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
        this.dom.chatStream.scrollTop = this.dom.chatStream.scrollHeight;
    }

    appendSystemMessage(text) {
        if (!this.dom.chatStream) return;

        const msg = document.createElement("div");
        msg.className = "system-message";
        msg.textContent = text;

        this.dom.chatStream.appendChild(msg);
        this.dom.chatStream.scrollTop = this.dom.chatStream.scrollHeight;
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
    }

    submitPrompt() {
        if (!this.dom.promptInput) return;
        const text = this.dom.promptInput.value.trim();
        if (!text) return;

        this.appendChatMessage("user", text, "Você");
        this.sendAction("send_prompt", { text: text });
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
