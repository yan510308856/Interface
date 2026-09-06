# Session headers set to `None` should be omitted

Setting a default session header to `None`, such as `session.headers['Accept-Encoding'] = None`, should prevent that header from being sent. The merged session/request settings must omit `None` values rather than serializing them as the string `None`. The production change is in `requests/sessions.py`.
