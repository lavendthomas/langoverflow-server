# Langoverflow Backend

This repository contains the backend for the langoverflow frontend. This backend is written in Flask (Python) and allows to store videos and questions inside a SQLite database.

### Launch 🚀

Redis needs to be installed and running on the default port (6379).

```sh
sudo dnf install redis # On Fedora / RHEL
sudo systemctl start redis
```

The following commands install and launch the server which automatically reload when the file `sse.py` is modified.
```sh
pip install --user -r requirements.txt
gunicorn sse:app --worker-class gevent --bind 0.0.0.0:8000 --reload
```

The code in itself is contained in `sse.py` 🙃 (yeah we could have split the code properly 😅).
