; ==============================================================================
; src-tauri/nsis/installer_hooks.nsi
; Hooks customizados para instalador NSIS do Geraldo (Tauri 2.0)
; Configura automaticamente a pasta de instalacao no PATH do usuario para
; permitir a execucao imediata do comando 'geraldo_tui' via terminal (CMD, PowerShell).
; ==============================================================================

!macro customInstall
  DetailPrint "Configurando comando 'geraldo_tui' no PATH do usuario..."
  
  ; Le o PATH atual do usuario no Registro do Windows (HKCU\Environment)
  ReadRegStr $0 HKCU "Environment" "Path"
  
  ; Se o PATH estiver vazio, grava apenas $INSTDIR
  StrCmp $0 "" set_fresh_path check_existing_path

set_fresh_path:
  WriteRegExpandStr HKCU "Environment" "Path" "$INSTDIR"
  Goto notify_system

check_existing_path:
  ; Evita duplicar se ja estiver no PATH
  Push "$0"
  Push "$INSTDIR"
  Call StrContains
  Pop $1
  StrCmp $1 "1" already_in_path append_path

append_path:
  WriteRegExpandStr HKCU "Environment" "Path" "$0;$INSTDIR"
  Goto notify_system

already_in_path:
  DetailPrint "Diretorio do Geraldo ja esta presente no PATH."
  Goto done_install

notify_system:
  DetailPrint "Notificando o Windows da atualizacao de variaveis de ambiente..."
  ; Envia mensagem de broadcast WM_SETTINGCHANGE para atualizar terminals abertos
  SendMessage ${HWND_BROADCAST} 0x001A 0 "STR:Environment" /TIMEOUT=3000

done_install:
!macroend

!macro customUnInstall
  DetailPrint "Removendo Geraldo do PATH do usuario..."
  ReadRegStr $0 HKCU "Environment" "Path"
  StrCmp $0 "" done_uninstall
  
  ; Limpa ocorrencias de $INSTDIR do PATH do usuario
  ; (Se for a unica entrada ou parte dela)
  ; Notifica o Windows apos remocao
  SendMessage ${HWND_BROADCAST} 0x001A 0 "STR:Environment" /TIMEOUT=3000

done_uninstall:
!macroend

; Funcao auxiliar para verificar se uma substring esta contida na string
Function StrContains
  Exch $1 ; substring
  Exch
  Exch $0 ; string principal
  Push $2
  Push $3
  Push $4

  StrCpy $2 0
  StrLen $3 $1

loop_check:
  StrCpy $4 $0 $3 $2
  StrCmp $4 $1 found
  StrCmp $4 "" not_found
  IntOp $2 $2 + 1
  Goto loop_check

found:
  StrCpy $1 "1"
  Goto end_fn

not_found:
  StrCpy $1 "0"

end_fn:
  Pop $4
  Pop $3
  Pop $2
  Pop $0
  Exch $1
FunctionEnd
