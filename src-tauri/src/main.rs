// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::TcpStream;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::Duration;

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

use tauri::{
    menu::{MenuBuilder, MenuItemBuilder},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Manager, WindowEvent,
};

static SIDECAR_PROCESS: Mutex<Option<Child>> = Mutex::new(None);

#[tauri::command]
fn get_desktop_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

#[tauri::command]
fn is_daemon_active() -> bool {
    is_daemon_running()
}

#[tauri::command]
fn open_external_url(url: String) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        Command::new("cmd")
            .args(["/C", "start", "", &url])
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .arg(&url)
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    #[cfg(target_os = "linux")]
    {
        Command::new("xdg-open")
            .arg(&url)
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}

fn is_daemon_running() -> bool {
    if let Ok(addr) = "127.0.0.1:8765".parse() {
        TcpStream::connect_timeout(&addr, Duration::from_millis(300)).is_ok()
    } else {
        false
    }
}

fn try_spawn_sidecar() {
    if is_daemon_running() {
        println!("[Tauri] Geraldo daemon já está em execução (porta 8765 ativa).");
        return;
    }

    println!("[Tauri] Geraldo daemon não detectado. Procurando executável sidecar...");

    // 1. Procura executável geraldo-core no mesmo diretório do executável (ex: /Applications/Geraldo.app/Contents/MacOS/geraldo-core)
    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(parent) = exe_path.parent() {
            for name in &["geraldo-core", "geraldo-core.exe"] {
                let adjacent = parent.join(name);
                if adjacent.exists() {
                    println!("[Tauri] Iniciando sidecar adjacente ao executável: {:?}", adjacent);
                    let mut cmd = Command::new(&adjacent);
                    cmd.current_dir(parent);
                    #[cfg(target_os = "windows")]
                    {
                        cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW
                    }
                    if let Ok(child) = cmd.spawn() {
                        if let Ok(mut lock) = SIDECAR_PROCESS.lock() {
                            *lock = Some(child);
                        }
                        println!("[Tauri] Processo sidecar iniciado com sucesso.");
                        return;
                    }
                }
            }
        }
    }

    let candidates = [
        "binaries/geraldo-core-x86_64-unknown-linux-gnu",
        "src-tauri/binaries/geraldo-core-x86_64-unknown-linux-gnu",
        "../src-tauri/binaries/geraldo-core-x86_64-unknown-linux-gnu",
        "binaries/geraldo-core.exe",
        "src-tauri/binaries/geraldo-core.exe",
        "../src-tauri/binaries/geraldo-core.exe",
        "binaries/geraldo-core-x86_64-pc-windows-msvc.exe",
        "src-tauri/binaries/geraldo-core-x86_64-pc-windows-msvc.exe",
        "geraldo-core.exe",
        "geraldo-core",
    ];

    for candidate in candidates {
        let path = std::path::Path::new(candidate);
        if path.exists() {
            println!("[Tauri] Iniciando sidecar em segundo plano: {:?}", path);
            let mut cmd = Command::new(path);
            if let Some(parent) = path.parent() {
                cmd.current_dir(parent);
            }
            #[cfg(target_os = "windows")]
            {
                cmd.creation_flags(0x08000000);
            }
            if let Ok(child) = cmd.spawn() {
                if let Ok(mut lock) = SIDECAR_PROCESS.lock() {
                    *lock = Some(child);
                }
                println!("[Tauri] Processo sidecar iniciado com sucesso.");
                return;
            }
        }
    }

    // Procura em diretórios padrão do Geraldo
    if let Ok(home) = std::env::var("HOME").or_else(|_| std::env::var("USERPROFILE")) {
        let home_p = std::path::PathBuf::from(home);
        for sub in &["projects/geraldo", "geraldo", ".local/share/geraldo"] {
            let dir = home_p.join(sub);
            let main_py = dir.join("main.py");
            if main_py.exists() {
                let venv_py = dir.join("venv/bin/python");
                let venv_py_win = dir.join("venv/Scripts/python.exe");
                let exec_candidate = if venv_py.exists() {
                    venv_py
                } else if venv_py_win.exists() {
                    venv_py_win
                } else {
                    std::path::PathBuf::from("python3")
                };
                let mut cmd = Command::new(&exec_candidate);
                cmd.arg(&main_py).current_dir(&dir);
                #[cfg(target_os = "windows")]
                {
                    cmd.creation_flags(0x08000000);
                }
                if let Ok(child) = cmd.spawn() {
                    if let Ok(mut lock) = SIDECAR_PROCESS.lock() {
                        *lock = Some(child);
                    }
                    println!("[Tauri] Processo daemon iniciado via '{:?} {:?}'.", exec_candidate, main_py);
                    return;
                }
            }
        }
    }

    // Se nenhum binário for encontrado, tenta iniciar main.py com o interpretador python disponível
    for py_cmd in &["python", "py", "python3"] {
        let mut cmd = Command::new(py_cmd);
        cmd.args(["main.py"]);
        #[cfg(target_os = "windows")]
        {
            cmd.creation_flags(0x08000000);
        }
        if let Ok(child) = cmd.spawn() {
            if let Ok(mut lock) = SIDECAR_PROCESS.lock() {
                *lock = Some(child);
            }
            println!("[Tauri] Processo daemon iniciado via '{} main.py'.", py_cmd);
            return;
        }
    }
}

fn open_tui() {
    let mut core_candidate: Option<std::path::PathBuf> = None;
    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(parent) = exe_path.parent() {
            for name in &["geraldo-core.exe", "geraldo-core"] {
                let p = parent.join(name);
                if p.exists() {
                    core_candidate = Some(p);
                    break;
                }
            }
        }
    }

    #[cfg(target_os = "windows")]
    {
        if let Some(core) = &core_candidate {
            let core_str = core.to_string_lossy().to_string();
            let _ = Command::new("cmd")
                .args(["/C", "start", "Geraldo TUI", &core_str, "--tui"])
                .spawn();
            return;
        }

        if let Ok(exe_path) = std::env::current_exe() {
            if let Some(parent) = exe_path.parent() {
                for rel in &["_up_/bin/geraldo-tui.cmd", "_up_/bin/geraldo_tui.cmd", "bin/geraldo-tui.cmd", "bin/geraldo_tui.cmd", "run_tui.bat"] {
                    let sp = parent.join(rel);
                    if sp.exists() {
                        let _ = Command::new("cmd")
                            .args(["/C", "start", "Geraldo TUI", &sp.to_string_lossy().to_string()])
                            .spawn();
                        return;
                    }
                }
            }
        }

        let _ = Command::new("cmd")
            .args(["/C", "start", "Geraldo TUI", "geraldo_tui"])
            .spawn();
    }

    #[cfg(target_os = "macos")]
    {
        if let Some(core) = &core_candidate {
            let core_str = core.to_string_lossy().to_string();
            let script = format!("tell application \"Terminal\" to do script \"\\\"{}\\\" --tui\"", core_str);
            let _ = Command::new("osascript").args(["-e", &script]).spawn();
            return;
        }
        let _ = Command::new("osascript").args(["-e", "tell application \"Terminal\" to do script \"geraldo_tui\""]).spawn();
    }

    #[cfg(target_os = "linux")]
    {
        let cmd_str = if let Some(core) = &core_candidate {
            format!("\"{}\" --tui", core.to_string_lossy())
        } else {
            "geraldo_tui".to_string()
        };

        for term in &["x-terminal-emulator", "gnome-terminal", "konsole", "xfce4-terminal", "alacritty", "kitty", "xterm"] {
            let res = if *term == "gnome-terminal" {
                Command::new(term).args(["--", "bash", "-c", &format!("{}; exec bash", cmd_str)]).spawn()
            } else {
                Command::new(term).args(["-e", "bash", "-c", &format!("{}; exec bash", cmd_str)]).spawn()
            };
            if res.is_ok() {
                return;
            }
        }
    }
}

#[tauri::command]
fn open_desktop_tui() {
    open_tui();
}

fn stop_sidecar() {
    if let Ok(mut lock) = SIDECAR_PROCESS.lock() {
        if let Some(mut child) = lock.take() {
            println!("[Tauri] Encerrando processo sidecar...");
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

fn ensure_cli_path() {
    #[cfg(any(target_os = "macos", target_os = "linux"))]
    {
        if let Ok(home) = std::env::var("HOME") {
            let local_bin = std::path::PathBuf::from(&home).join(".local").join("bin");
            let _ = std::fs::create_dir_all(&local_bin);

            let macos_target = "/Applications/Geraldo.app/Contents/MacOS/geraldo-core";

            for cmd_name in &["geraldo_tui", "geraldo-tui"] {
                let link_path = local_bin.join(cmd_name);
                if !link_path.exists() {
                    let script = format!(
                        "#!/usr/bin/env bash\n\
                        if [ -f \"{0}\" ]; then\n  exec \"{0}\" --tui \"$@\"\n\
                        elif [ -f \"/usr/bin/geraldo-desktop\" ]; then\n  exec \"/usr/bin/geraldo-desktop\" --tui \"$@\"\n\
                        elif [ -f \"/usr/bin/geraldo\" ]; then\n  exec \"/usr/bin/geraldo\" --tui \"$@\"\n\
                        elif [ -f \"$(dirname \"$0\")/geraldo-core\" ]; then\n  exec \"$(dirname \"$0\")/geraldo-core\" --tui \"$@\"\n\
                        fi\n\
                        CANDIDATES=(\"$HOME/projects/geraldo\" \"$HOME/geraldo\" \"$HOME/.local/share/geraldo\")\n\
                        for DIR in \"${{CANDIDATES[@]}}\"; do\n\
                            if [ -f \"$DIR/venv/bin/python\" ] && [ -f \"$DIR/main.py\" ]; then\n\
                                exec \"$DIR/venv/bin/python\" \"$DIR/main.py\" --tui \"$@\"\n\
                            fi\n\
                            if [ -f \"$DIR/venv/bin/python\" ] && [ -f \"$DIR/ui/tui.py\" ]; then\n\
                                PYTHONPATH=\"$DIR:${{PYTHONPATH}}\" exec \"$DIR/venv/bin/python\" -m ui.tui \"$@\"\n\
                            fi\n\
                        done\n\
                        if [ -f \"./venv/bin/python\" ]; then\n  exec \"./venv/bin/python\" -m ui.tui \"$@\"\n\
                        else\n  exec python3 -m ui.tui \"$@\"\nfi\n",
                        macos_target
                    );
                    let _ = std::fs::write(&link_path, script);
                    #[cfg(unix)]
                    {
                        use std::os::unix::fs::PermissionsExt;
                        let _ = std::fs::set_permissions(&link_path, std::fs::Permissions::from_mode(0o755));
                    }
                }
            }

            // Garante que ~/.local/bin esteja presente nos arquivos de perfil do shell
            for rc_name in &[".zshrc", ".bashrc", ".profile"] {
                let rc_path = std::path::PathBuf::from(&home).join(rc_name);
                if rc_path.exists() {
                    if let Ok(content) = std::fs::read_to_string(&rc_path) {
                        if !content.contains(".local/bin") && !content.contains("geraldo_tui") {
                            use std::io::Write;
                            if let Ok(mut file) = std::fs::OpenOptions::new().append(true).open(&rc_path) {
                                let _ = writeln!(file, "\n# Geraldo TUI CLI PATH\nexport PATH=\"$HOME/.local/bin:$PATH\"");
                            }
                        }
                    }
                }
            }
        }
    }

    #[cfg(target_os = "windows")]
    {
        if let Ok(exe_path) = std::env::current_exe() {
            if let Some(parent) = exe_path.parent() {
                let dir_str = parent.to_string_lossy().to_string();
                let _ = Command::new("cmd")
                    .args([
                        "/C",
                        &format!(
                            "powershell -NoProfile -Command \"$d='{0}'; $p=[Environment]::GetEnvironmentVariable('Path', 'User'); if ($p -notlike '*'+$d+'*') {{ [Environment]::SetEnvironmentVariable('Path', $p+';'+$d, 'User') }}\"",
                            dir_str.replace("'", "''")
                        ),
                    ])
                    .spawn();
            }
        }
    }
}

fn main() {
    // Corrige compatibilidade do WebKitGTK em ambientes Wayland (Hyprland, Sway, GNOME)
    #[cfg(target_os = "linux")]
    {
        if std::env::var("WEBKIT_DISABLE_DMABUF_RENDERER").is_err() {
            std::env::set_var("WEBKIT_DISABLE_DMABUF_RENDERER", "1");
        }
    }

    tauri::Builder::default()
        .plugin(tauri_plugin_updater::Builder::new().build())
        .setup(|app| {
            // Garante comando CLI geraldo_tui no PATH do sistema
            ensure_cli_path();

            // Tenta iniciar o daemon se não estiver em execução
            try_spawn_sidecar();

            // Cria menu de contexto da bandeja do sistema
            let open_item = MenuItemBuilder::with_id("open", "Abrir Geraldo").build(app)?;
            let tui_item = MenuItemBuilder::with_id("tui", "Abrir TUI").build(app)?;
            let mute_item = MenuItemBuilder::with_id("mute", "Mutar/Desmutar Microfone").build(app)?;
            let cancel_item = MenuItemBuilder::with_id("cancel", "Cancelar Sons e Ações").build(app)?;
            let quit_item = MenuItemBuilder::with_id("quit", "Sair do Geraldo").build(app)?;

            let tray_menu = MenuBuilder::new(app)
                .item(&open_item)
                .item(&tui_item)
                .separator()
                .item(&mute_item)
                .item(&cancel_item)
                .separator()
                .item(&quit_item)
                .build()?;

            let _tray = TrayIconBuilder::with_id("main-tray")
                .menu(&tray_menu)
                .show_menu_on_left_click(false)
                .tooltip("Geraldo - Assistente de Voz Local")
                .on_menu_event(|app, event| {
                    match event.id().as_ref() {
                        "open" => {
                            if let Some(window) = app.get_webview_window("main") {
                                let _ = window.show();
                                let _ = window.unminimize();
                                let _ = window.set_focus();
                            }
                        }
                        "tui" => {
                            open_tui();
                        }
                        "quit" => {
                            stop_sidecar();
                            app.exit(0);
                        }
                        _ => {}
                    }
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            let is_visible = window.is_visible().unwrap_or(false);
                            if is_visible {
                                let _ = window.hide();
                            } else {
                                let _ = window.show();
                                let _ = window.unminimize();
                                let _ = window.set_focus();
                            }
                        }
                    }
                })
                .build(app)?;

            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                // Ao clicar no 'X', minimiza para a bandeja em vez de encerrar o processo
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .invoke_handler(tauri::generate_handler![
            get_desktop_version,
            is_daemon_active,
            open_external_url,
            open_desktop_tui
        ])
        .run(tauri::generate_context!())
        .expect("error while running geraldo desktop application");
}
