; ============================================================
;  MaieuticAnalyzer — Script d'installation NSIS
;  Prérequis : NSIS >= 3.09, plugin ExecDos (voir README)
; ============================================================

Unicode True

; ---------- Métadonnées ----------
!define APP_NAME        "MaieuticAnalyzer"
!define APP_VERSION     "1.0.0"
!define APP_PUBLISHER   "Cabinet de sages-femmes"
!define APP_URL         "https://localhost:8443"
!define EXE_NAME        "MaieuticAnalyzer.exe"
!define INSTALL_DIR     "$PROGRAMFILES64\${APP_NAME}"
!define TASK_NAME       "MaieuticAnalyzerAutostart"
!define FW_RULE_NAME    "MaieuticAnalyzer HTTPS 8443"
!define UNINSTALL_KEY   "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"

; ---------- Paramètres généraux ----------
Name              "${APP_NAME} ${APP_VERSION}"
OutFile           "MaieuticAnalyzer_Setup.exe"
InstallDir        "${INSTALL_DIR}"
InstallDirRegKey  HKLM "${UNINSTALL_KEY}" "InstallLocation"
RequestExecutionLevel admin
SetCompressor     lzma

; ---------- Pages ----------
!include "MUI2.nsh"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "French"

; ============================================================
;  INSTALLATION
; ============================================================
Section "Installation principale" SecMain

  SetOutPath "$INSTDIR"

  ; --- Copie des fichiers applicatifs ---
  File "dist\${EXE_NAME}"

  ; --- Copie de mkcert (doit être à côté du .nsi au moment du build) ---
  File "bin\mkcert.exe"

  ; --------------------------------------------------------
  ;  Génération des certificats TLS avec mkcert
  ;  1) installe la CA locale dans le store Windows
  ;  2) génère cert.pem + key.pem pour localhost
  ; --------------------------------------------------------
  DetailPrint "Installation de la CA locale mkcert..."
  nsExec::ExecToLog '"$INSTDIR\mkcert.exe" -install'
  Pop $0
  ${If} $0 != 0
    MessageBox MB_ICONEXCLAMATION "Attention : l'installation de la CA mkcert a échoué (code $0). \
      Les navigateurs pourraient afficher un avertissement de sécurité."
  ${EndIf}

  DetailPrint "Génération des certificats pour localhost..."
  ; On génère les certs directement dans le dossier d'install
  SetOutPath "$INSTDIR"
  nsExec::ExecToLog '"$INSTDIR\mkcert.exe" -cert-file "$INSTDIR\cert.pem" -key-file "$INSTDIR\key.pem" localhost 127.0.0.1'
  Pop $0
  ${If} $0 != 0
    MessageBox MB_ICONSTOP "Erreur : impossible de générer les certificats (code $0). \
      Vérifiez que mkcert.exe est présent dans le dossier d'installation."
    Abort
  ${EndIf}

  ; --------------------------------------------------------
  ;  Règle de pare-feu (port 8443 entrant, localhost only)
  ;  On supprime d'abord une règle éventuelle, puis on recrée
  ; --------------------------------------------------------
  DetailPrint "Configuration du pare-feu Windows..."
  nsExec::ExecToLog 'netsh advfirewall firewall delete rule name="${FW_RULE_NAME}"'
  nsExec::ExecToLog 'netsh advfirewall firewall add rule \
    name="${FW_RULE_NAME}" \
    dir=in \
    action=allow \
    protocol=TCP \
    localport=8443 \
    localip=127.0.0.1 \
    profile=any \
    description="MaieuticAnalyzer - acces local HTTPS"'
  Pop $0
  ${If} $0 != 0
    MessageBox MB_ICONEXCLAMATION "Attention : la règle de pare-feu n'a pas pu être créée (code $0). \
      L'application fonctionnera probablement quand même en accès local."
  ${EndIf}

  ; --------------------------------------------------------
  ;  Planificateur de tâches — démarre l'exe à chaque
  ;  ouverture de session, pour n'importe quel utilisateur
  ;  /RL HIGHEST = niveau d'exécution élevé (pas UAC mais
  ;  droits complets de l'utilisateur connecté)
  ; --------------------------------------------------------
  DetailPrint "Création de la tâche planifiée de démarrage..."
  ; Suppression d'une tâche existante éventuelle
  nsExec::ExecToLog 'schtasks /Delete /TN "${TASK_NAME}" /F'

  nsExec::ExecToLog 'schtasks /Create \
    /TN "${TASK_NAME}" \
    /TR "\"$INSTDIR\${EXE_NAME}\"" \
    /SC ONLOGON \
    /RU "BUILTIN\Users" \
    /RL HIGHEST \
    /DELAY 0000:10 \
    /F'
  Pop $0
  ${If} $0 != 0
    MessageBox MB_ICONEXCLAMATION "Attention : la tâche planifiée n'a pas pu être créée (code $0). \
      L'application ne démarrera pas automatiquement. \
      Vous pouvez la lancer manuellement depuis $INSTDIR\${EXE_NAME}."
  ${EndIf}

  ; --------------------------------------------------------
  ;  Raccourci bureau (optionnel, pratique pour tester)
  ; --------------------------------------------------------
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${EXE_NAME}"

  ; --------------------------------------------------------
  ;  Entrée dans Ajout/Suppression de programmes
  ; --------------------------------------------------------
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayName"      "${APP_NAME}"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayVersion"   "${APP_VERSION}"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "Publisher"        "${APP_PUBLISHER}"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "InstallLocation"  "$INSTDIR"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "UninstallString"  '"$INSTDIR\Uninstall.exe"'
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "URLInfoAbout"     "${APP_URL}"
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoModify"         1
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoRepair"         1

  ; Désinstalleur
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  DetailPrint "Installation terminée !"
  DetailPrint "L'application démarrera automatiquement à la prochaine ouverture de session."
  DetailPrint "Accès : https://localhost:8443"

SectionEnd

; ============================================================
;  DÉSINSTALLATION
; ============================================================
Section "Uninstall"

  ; Supprimer la tâche planifiée
  nsExec::ExecToLog 'schtasks /Delete /TN "${TASK_NAME}" /F'

  ; Supprimer la règle de pare-feu
  nsExec::ExecToLog 'netsh advfirewall firewall delete rule name="${FW_RULE_NAME}"'

  ; Révoquer/supprimer la CA mkcert du store Windows
  ; (mkcert -uninstall supprime la CA du trust store)
  ${If} ${FileExists} "$INSTDIR\mkcert.exe"
    nsExec::ExecToLog '"$INSTDIR\mkcert.exe" -uninstall'
  ${EndIf}

  ; Supprimer les fichiers
  Delete "$INSTDIR\${EXE_NAME}"
  Delete "$INSTDIR\mkcert.exe"
  Delete "$INSTDIR\cert.pem"
  Delete "$INSTDIR\key.pem"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir  "$INSTDIR"

  ; Supprimer le raccourci bureau
  Delete "$DESKTOP\${APP_NAME}.lnk"

  ; Supprimer l'entrée Ajout/Suppression de programmes
  DeleteRegKey HKLM "${UNINSTALL_KEY}"

SectionEnd
