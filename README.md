## Build zone

Pour générer un build :

```
pyinstaller --onefile --add-data "templates:templates" --add-data "static:static" app.py processing.py
```

Pour générer des certificats locaux :

```
sudo apt update && sudo apt install mkcert && mkcert localhost
```

Puis, pour un quickstart : 

```
python -m uvicorn app:app
```
