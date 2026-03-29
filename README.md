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

Sur Windows, commencez par télécharger [NSIS](https://nsis.sourceforge.io/Main_Page) :
```ps1
scoop install main/uv
uv sync
```

> Allez récupérer la [dernière version du build de mkcert](https://github.com/FiloSottile/mkcert/releases) pour Windows amd64, et placez la à la racine de ce dépôt dans un répertoire `.\bin\` que vous aurez créé.

### Builder l'applicatif

Pour un quickstart : 
```
python app.py
```

Pour générer un build (Linux & Windows) :
```
pyinstaller MaieuticAnalyzer.spec
```

Pour générer un installateur Windows :
```
makensis MaieuticAnalyzer_installer.nsi
```
