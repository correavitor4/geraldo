import json
import os
import struct
import pytest

TAURI_DIR = "/home/vitor/projects/geraldo/src-tauri"
TAURI_CONF_PATH = os.path.join(TAURI_DIR, "tauri.conf.json")
CARGO_TOML_PATH = os.path.join(TAURI_DIR, "Cargo.toml")
MAIN_RS_PATH = os.path.join(TAURI_DIR, "src", "main.rs")
ICONS_DIR = os.path.join(TAURI_DIR, "icons")


def test_tauri_conf_json_valid_syntax():
    """Valida se o tauri.conf.json existe e é um JSON válido."""
    assert os.path.exists(TAURI_CONF_PATH), "tauri.conf.json não encontrado"
    with open(TAURI_CONF_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)


def test_tauri_conf_schema_and_product_metadata():
    """Valida metadados do produto e conformidade com o schema Tauri 2.0."""
    with open(TAURI_CONF_PATH, "r", encoding="utf-8") as f:
        conf = json.load(f)

    assert conf.get("$schema") == "https://schema.tauri.app/config/2"
    assert conf.get("productName") == "Geraldo"
    assert conf.get("identifier") == "com.geraldo.desktop"
    assert conf.get("version"), "Versão não especificada"
    import re
    assert re.match(r"^\d+\.\d+\.\d+", conf.get("version"))


def test_tauri_build_frontend_dist():
    """Valida se o caminho de frontendDist existe no disco."""
    with open(TAURI_CONF_PATH, "r", encoding="utf-8") as f:
        conf = json.load(f)

    dist = conf.get("build", {}).get("frontendDist")
    assert dist == "../desktop-ui"

    abs_dist = os.path.normpath(os.path.join(TAURI_DIR, dist))
    assert os.path.isdir(abs_dist), f"Diretório frontend '{abs_dist}' não existe"
    assert os.path.exists(os.path.join(abs_dist, "index.html")), "index.html não encontrado no frontend"


def test_tauri_window_configuration():
    """Valida parâmetros da janela principal do desktop."""
    with open(TAURI_CONF_PATH, "r", encoding="utf-8") as f:
        conf = json.load(f)

    windows = conf.get("app", {}).get("windows", [])
    assert len(windows) >= 1, "Nenhuma janela configurada em tauri.conf.json"

    main_win = windows[0]
    assert main_win.get("label") == "main"
    assert "Geraldo" in main_win.get("title", "")
    assert main_win.get("width") == 1100
    assert main_win.get("height") == 750
    assert main_win.get("minWidth") == 800
    assert main_win.get("minHeight") == 600
    assert main_win.get("resizable") is True


def test_tauri_tray_icon_configuration():
    """Valida se a bandeja do sistema (System Tray) está configurada corretamente."""
    with open(TAURI_CONF_PATH, "r", encoding="utf-8") as f:
        conf = json.load(f)

    tray = conf.get("app", {}).get("trayIcon", {})
    assert tray.get("id") == "main-tray"
    assert "Geraldo" in tray.get("tooltip", "")

    icon_path = tray.get("iconPath")
    assert icon_path
    abs_icon = os.path.join(TAURI_DIR, icon_path)
    assert os.path.isfile(abs_icon), f"Ícone da bandeja '{abs_icon}' não existe"


def test_tauri_bundle_icons_exist_and_are_valid():
    """Valida se todos os ícones declarados existem e contêm cabeçalhos válidos (PNG, ICO, ICNS)."""
    with open(TAURI_CONF_PATH, "r", encoding="utf-8") as f:
        conf = json.load(f)

    icons = conf.get("bundle", {}).get("icon", [])
    assert len(icons) >= 2, "Poucos ícones configurados no bundle"

    png_header = b"\x89PNG\r\n\x1a\n"
    ico_header = b"\x00\x00\x01\x00"
    icns_header = b"icns"

    for rel_path in icons:
        abs_path = os.path.join(TAURI_DIR, rel_path)
        assert os.path.isfile(abs_path), f"Ícone '{abs_path}' não encontrado"

        with open(abs_path, "rb") as f:
            if rel_path.endswith(".png"):
                header = f.read(8)
                assert header == png_header, f"Arquivo '{abs_path}' não é um PNG válido"
                chunk_len, chunk_type = struct.unpack(">I4s", f.read(8))
                if chunk_type == b"IHDR":
                    w, h = struct.unpack(">II", f.read(8))
                    assert w > 0 and h > 0, "Dimensões inválidas no PNG"
            elif rel_path.endswith(".ico"):
                header = f.read(4)
                assert header == ico_header, f"Arquivo '{abs_path}' não é um ICO válido"
            elif rel_path.endswith(".icns"):
                header = f.read(4)
                assert header == icns_header, f"Arquivo '{abs_path}' não é um ICNS válido"


def test_tauri_cargo_toml_validity():
    """Valida o manifesto Cargo.toml do projeto Rust Tauri."""
    assert os.path.exists(CARGO_TOML_PATH)
    with open(CARGO_TOML_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert 'name = "geraldo-desktop"' in content
    assert 'edition = "2021"' in content
    assert 'tauri-build' in content
    assert 'features = ["tray-icon"]' in content
    assert 'serde' in content


def test_tauri_main_rs_source_components():
    """Valida componentes críticos implementados no src/main.rs do Tauri."""
    assert os.path.exists(MAIN_RS_PATH)
    with open(MAIN_RS_PATH, "r", encoding="utf-8") as f:
        code = f.read()

    # Janela oculta em release para Windows
    assert 'windows_subsystem = "windows"' in code

    # Itens do Menu da Bandeja
    assert 'MenuItemBuilder::with_id("open", "Abrir Geraldo")' in code
    assert 'MenuItemBuilder::with_id("mute", "Mutar/Desmutar Microfone")' in code
    assert 'MenuItemBuilder::with_id("cancel", "Cancelar Sons e Ações")' in code
    assert 'MenuItemBuilder::with_id("quit", "Sair do Geraldo")' in code

    # Eventos de clique na bandeja
    assert 'TrayIconBuilder::with_id("main-tray")' in code
    assert 'on_tray_icon_event' in code

    # Minimizar para bandeja ao fechar janela
    assert 'WindowEvent::CloseRequested' in code
    assert 'api.prevent_close()' in code
    assert 'window.hide()' in code

    # Comando exposto
    assert 'get_desktop_version' in code

    # Configuração de PATH CLI para geraldo_tui
    assert 'ensure_cli_path' in code
    assert 'geraldo_tui' in code


def test_tauri_nsis_installer_hooks_config():
    """Valida se o instalador NSIS do Windows aponta para o script de hooks com PATH export."""
    with open(TAURI_CONF_PATH, "r", encoding="utf-8") as f:
        conf = json.load(f)

    nsis = conf.get("bundle", {}).get("windows", {}).get("nsis", {})
    assert "installerHooks" in nsis
    assert "installer_hooks.nsi" in nsis.get("installerHooks", "")

    resources = conf.get("bundle", {}).get("resources", [])
    assert any("geraldo_tui.cmd" in r for r in resources)
    assert any("geraldo_tui" in r for r in resources)

