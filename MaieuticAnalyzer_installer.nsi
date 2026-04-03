; ============================================================
;  MaieuticAnalyzer - Script d'installation NSIS
; ============================================================

Unicode True

; ---------- Metadonnees ----------
!define APP_NAME        "MaieuticAnalyzer"
!ifndef APP_VERSION
  !define APP_VERSION "dev"
!endif
!define APP_PUBLISHER   "Cabinet de sages-femmes"
!define APP_URL         "https://localhost:8443"
!define EXE_NAME        "MaieuticAnalyzer.exe"
!define INSTALL_DIR     "$PROGRAMFILES64\${APP_NAME}"
!define TASK_NAME       "MaieuticAnalyzerAutostart"
!define FW_RULE_NAME    "MaieuticAnalyzer HTTPS 8443"
!define UNINSTALL_KEY   "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"

; ---------- Parametres generaux ----------
Name              "${APP_NAME} ${APP_VERSION}"
OutFile "MaieuticAnalyzer_${APP_VERSION}.exe"
InstallDir        "${INSTALL_DIR}"
InstallDirRegKey  HKLM "${UNINSTALL_KEY}" "InstallLocation"
RequestExecutionLevel admin
SetCompressor     lzma

; ---------- Pages ----------
!include "MUI2.nsh"
!include "LogicLib.nsh"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_TEXT "Lancer ${APP_NAME}"
!define MUI_FINISHPAGE_RUN_FUNCTION LaunchApp
!define MUI_FINISHPAGE_SHOWREADME
!define MUI_FINISHPAGE_SHOWREADME_TEXT "Ouvrir https://localhost:8443"
!define MUI_FINISHPAGE_SHOWREADME_FUNCTION OpenBrowser
!define MUI_FINISHPAGE_RUN_CHECKED
!define MUI_FINISHPAGE_SHOWREADME_CHECKED
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "French"

; ============================================================
;  INSTALLATION
; ============================================================
Function .onInit
  ReadRegStr $R0 HKLM "${UNINSTALL_KEY}" "UninstallString"
  StrCmp $R0 "" done

  MessageBox MB_YESNO|MB_ICONQUESTION \
    "${APP_NAME} est déjà installé. Voulez-vous le réinstaller ?" \
    IDYES do_uninstall IDNO done

  do_uninstall:
    ExecWait '$R0 /S'
  done:
FunctionEnd

Function LaunchApp
  Exec "$INSTDIR\${EXE_NAME}"
FunctionEnd

Function OpenBrowser
  ExecShell "open" "https://localhost:8443"
FunctionEnd

Section "Installation principale" SecMain

  SetOutPath "$INSTDIR"

  DetailPrint "Arret de l'application si en cours..."

  nsExec::ExecToLog 'taskkill /IM "${EXE_NAME}" /F'
  Pop $0
  nsExec::ExecToLog 'schtasks /End /TN "${TASK_NAME}"'
  
  ; --- Copie des fichiers applicatifs ---
  File "dist\${EXE_NAME}"
  File "bin\mkcert.exe"
  ; Le XML de tache est copie ici pour etre patche au runtime
  File "MaieuticAnalyzer_task.xml"

  ; --------------------------------------------------------
  ;  Generation des certificats TLS avec mkcert
  ; --------------------------------------------------------
  Delete "$INSTDIR\cert.pem"
  Delete "$INSTDIR\key.pem"

  DetailPrint "Installation de la CA locale mkcert..."
  nsExec::ExecToLog '"$INSTDIR\mkcert.exe" -install'
  Pop $0
  ${If} $0 != 0
    MessageBox MB_ICONEXCLAMATION "Attention : installation CA mkcert echouee (code $0)."
  ${EndIf}

  DetailPrint "Generation des certificats pour localhost..."
  nsExec::ExecToLog '"$INSTDIR\mkcert.exe" -cert-file "$INSTDIR\cert.pem" -key-file "$INSTDIR\key.pem" localhost 127.0.0.1'
  Pop $0
  ${If} $0 != 0
    MessageBox MB_ICONSTOP "Erreur : impossible de generer les certificats (code $0)."
    Abort
  ${EndIf}

  ; --------------------------------------------------------
  ;  Regle de pare-feu (port 8443, localhost uniquement)
  ; --------------------------------------------------------
  DetailPrint "Configuration du pare-feu Windows..."
  nsExec::ExecToLog 'netsh advfirewall firewall delete rule name="${FW_RULE_NAME}"'
  nsExec::ExecToLog 'netsh advfirewall firewall add rule name="${FW_RULE_NAME}" dir=in action=allow protocol=TCP localport=8443 localip=127.0.0.1 profile=any'
  Pop $0
  ${If} $0 != 0
    MessageBox MB_ICONEXCLAMATION "Attention : regle pare-feu non creee (code $0)."
  ${EndIf}

  ; --------------------------------------------------------
  ;  Tache planifiee via XML patche par PowerShell
  ;  On remplace le placeholder MAIEUTIC_EXE_PATH par le
  ;  chemin reel, puis on encode en UTF-16 LE (requis par
  ;  schtasks /XML) et on importe la tache.
  ; --------------------------------------------------------
  DetailPrint "Creation de la tache planifiee..."

  ; Suppression d'une tache existante eventuelle (ignore si absente)
  nsExec::ExecToLog 'schtasks /Delete /TN "${TASK_NAME}" /F'

  ; Patch du XML + encodage UTF-16 via PowerShell
  nsExec::ExecToLog 'powershell -NoProfile -NonInteractive -Command "\
    $src  = [System.IO.File]::ReadAllText(\"$INSTDIR\MaieuticAnalyzer_task.xml\");\
    $src  = $src -replace \"MAIEUTIC_EXE_PATH\", \"$INSTDIR\\${EXE_NAME}\";\
    [System.IO.File]::WriteAllText(\
      \"$INSTDIR\task_final.xml\",\
      $src,\
      [System.Text.Encoding]::Unicode\
    )"'
  Pop $0
  ${If} $0 != 0
    MessageBox MB_ICONSTOP "Erreur : generation du XML de tache echouee (code $0)."
    Abort
  ${EndIf}

  ; Import de la tache planifiee
  nsExec::ExecToLog 'schtasks /Create /TN "${TASK_NAME}" /XML "$INSTDIR\task_final.xml" /F'
  Pop $0
  ${If} $0 != 0
    MessageBox MB_ICONSTOP "Erreur : creation de la tache planifiee echouee (code $0).$\r$\n\
Relancez l'installeur en tant qu'administrateur."
  ${EndIf}

  ; Nettoyage du XML temporaire patche
  Delete "$INSTDIR\task_final.xml"

  ; --------------------------------------------------------
  ;  Raccourci bureau
  ; --------------------------------------------------------
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${EXE_NAME}"

  ; --------------------------------------------------------
  ;  Entree Ajout/Suppression de programmes
  ; --------------------------------------------------------
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayName"      "${APP_NAME}"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayVersion"   "${APP_VERSION}"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "Publisher"        "${APP_PUBLISHER}"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "InstallLocation"  "$INSTDIR"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "UninstallString"  '"$INSTDIR\Uninstall.exe"'
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "URLInfoAbout"     "${APP_URL}"
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoModify"         1
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoRepair"         1

  WriteUninstaller "$INSTDIR\Uninstall.exe"

  DetailPrint "Installation terminée !"

SectionEnd

; ============================================================
;  DESINSTALLATION
; ============================================================
Section "Uninstall"

  DetailPrint "Arret de l'application..."

  nsExec::ExecToLog 'schtasks /End /TN "${TASK_NAME}"'
  nsExec::ExecToLog 'taskkill /IM "${EXE_NAME}" /F'
  Sleep 1000

  nsExec::ExecToLog 'schtasks /Delete /TN "${TASK_NAME}" /F'
  nsExec::ExecToLog 'netsh advfirewall firewall delete rule name="${FW_RULE_NAME}"'

  ; ${If} ${FileExists} "$INSTDIR\mkcert.exe"
  ;   nsExec::ExecToLog '"$INSTDIR\mkcert.exe" -uninstall'
  ; ${EndIf}

  Delete "$INSTDIR\${EXE_NAME}"
  Delete "$INSTDIR\mkcert.exe"
  Delete "$INSTDIR\cert.pem"
  Delete "$INSTDIR\key.pem"
  Delete "$INSTDIR\MaieuticAnalyzer_task.xml"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir  "$INSTDIR"

  Delete "$DESKTOP\${APP_NAME}.lnk"
  DeleteRegKey HKLM "${UNINSTALL_KEY}"

SectionEnd