// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::TcpStream;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::Duration;

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

    let candidates = [
        "binaries/geraldo-core-x86_64-unknown-linux-gnu",
        "src-tauri/binaries/geraldo-core-x86_64-unknown-linux-gnu",
        "../src-tauri/binaries/geraldo-core-x86_64-unknown-linux-gnu",
        "geraldo-core",
    ];

    for candidate in candidates {
        let path = std::path::Path::new(candidate);
        if path.exists() {
            println!("[Tauri] Iniciando sidecar em segundo plano: {:?}", path);
            if let Ok(child) = Command::new(path).spawn() {
                if let Ok(mut lock) = SIDECAR_PROCESS.lock() {
                    *lock = Some(child);
                }
                println!("[Tauri] Processo sidecar iniciado com sucesso.");
                return;
            }
        }
    }
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
    #[cfg(target_os = "macos")]
    {
        if let Ok(home) = std::env::var("HOME") {
            let local_bin = std::path::PathBuf::from(&home).join(".local").join("bin");
            let _ = std::fs::create_dir_all(&local_bin);

            let app_target = "/Applications/Geraldo.app/Contents/MacOS/geraldo-core";

            for cmd_name in &["geraldo_tui", "geraldo-tui"] {
                let link_path = local_bin.join(cmd_name);
                if !link_path.exists() {
                    let script = format!(
                        "#!/usr/bin/env bash\nif [ -f \"{0}\" ]; then\n  exec \"{0}\" --tui \"$@\"\nelif [ -f \"$(dirname \"$0\")/geraldo-core\" ]; then\n  exec \"$(dirname \"$0\")/geraldo-core\" --tui \"$@\"\nelse\n  exec python3 -m ui.tui \"$@\"\nfi\n",
                        app_target
                    );
                    let _ = std::fs::write(&link_path, script);
                    #[cfg(unix)]
                    {
                        use std::os::unix::fs::PermissionsExt;
                        let _ = std::fs::set_permissions(&link_path, std::fs::Permissions::from_mode(0o755));
                    }
                }
            }

            // Garante que ~/.local/bin esteja presente no ~/.zshrc se ausente
            let zshrc = std::path::PathBuf::from(&home).join(".zshrc");
            if zshrc.exists() {
                if let Ok(content) = std::fs::read_to_string(&zshrc) {
                    if !content.contains(".local/bin") && !content.contains("geraldo_tui") {
                        use std::io::Write;
                        if let Ok(mut file) = std::fs::OpenOptions::new().append(true).open(&zshrc) {
                            let _ = writeln!(file, "\n# Geraldo TUI CLI\nexport PATH=\"$HOME/.local/bin:$PATH\"");
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
        .setup(|app| {
            // Garante comando CLI geraldo_tui no PATH do sistema
            ensure_cli_path();

            // Tenta iniciar o daemon se não estiver em execução
            try_spawn_sidecar();

            // Cria menu de contexto da bandeja do sistema
            let open_item = MenuItemBuilder::with_id("open", "Abrir Geraldo").build(app)?;
            let mute_item = MenuItemBuilder::with_id("mute", "Mutar/Desmutar Microfone").build(app)?;
            let cancel_item = MenuItemBuilder::with_id("cancel", "Cancelar Sons e Ações").build(app)?;
            let quit_item = MenuItemBuilder::with_id("quit", "Sair do Geraldo").build(app)?;

            let tray_menu = MenuBuilder::new(app)
                .item(&open_item)
                .separator()
                .item(&mute_item)
                .item(&cancel_item)
                .separator()
                .item(&quit_item)
                .build()?;

            let _tray = TrayIconBuilder::with_id("main-tray")
                .menu(&tray_menu)
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
        .invoke_handler(tauri::generate_handler![get_desktop_version, is_daemon_active])
        .run(tauri::generate_context!())
        .expect("error while running geraldo desktop application");
}
