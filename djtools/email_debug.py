"""
Email backend that writes messages to console instead of sending them.
"""
import json
from django.core.mail.backends.base import BaseEmailBackend


class EmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        lista = []
        for message in email_messages:
            lista.append(dict(from_email=message.from_email, to=', '.join(message.to), message=message.body))
        with open('deploy/emails.json', 'w') as f:
            f.write(json.dumps(lista))
        return len(lista)
