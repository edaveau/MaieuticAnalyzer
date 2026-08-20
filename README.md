# MaieuticApp Analyzer

## TLDR

Petite application permettant de calculer les rétrocessions issues d'un export MaieuticApp.

## User zone

Pour utiliser et lancer l'application, rien de plus simple. Téléchargez la [dernière release](https://github.com/edaveau/MaieuticAnalyzer/releases/latest), et lancez une première fois l'exécutable. Si c'est la première fois qu'il est lancé sur votre PC, une configuration aura lieu. Cliquez une deuxième fois sur l'exécutable pour relancer l'appli.

## Build zone

### Installer les prérequis pour les certificats

Sur Linux
```bash
sudo apt update && sudo apt install mkcert && mkcert *.home *.local localhost 127.0.0.1 ::1
```

Sur Windows, installez dans un premier temps [Scoop](https://scoop.sh/), puis 
```powershell
scoop bucket add extras
scoop install mkcert
mkdir certs
cd certs
mkcert -install
mkcert *.home *.local localhost 127.0.0.1 ::1
mv .\_wildcard.home+4.pem cert.pem
mv .\_wildcard.home+4-key.pem key.pem
```

### Installer les prérequis pour un build

Sur Linux :
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

Sur Windows, commencez par télécharger [NSIS](https://nsis.sourceforge.io/Main_Page), puis téléchargez les prérequis Python :
```ps1
scoop install main/uv
uv sync
```

> Allez récupérer la dernière version du build de mkcert pour [Windows AMD64](https://dl.filippo.io/mkcert/latest?for=windows/amd64) ou [Linux AMD64](https://dl.filippo.io/mkcert/latest?for=linux/amd64), et placez la à la racine de ce dépôt dans un répertoire `.\bin\` que vous aurez créé. Renommez le en mkcert.exe

### Builder l'applicatif

Pour un quickstart : 
```
python app.py
```

Pour lancer l'appli en local :
```
python -m uvicorn app:app
```

Pour générer un build (Linux & Windows) :
```
pyinstaller MaieuticAnalyzer.spec
```

