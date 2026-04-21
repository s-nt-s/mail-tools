import os
from dotenv import load_dotenv
from mail.config import Config, LocalConfig
from typing import NamedTuple

load_dotenv()

def get_credentials():
    imap=os.environ.get("IMAP_HOST")
    smtp=os.environ.get("SMTP_HOST")
    user=os.environ.get("MAIL_USER")
    pssw=os.environ.get("MAIL_PASS")
    if None in (imap, smtp, user, pssw):
        users: set[str] = set()
        pssws: set[str] = set()
        local = LocalConfig.load_from_system()
        if local.smtp:
            smtp = local.smtp.host
            users.add(local.smtp.user)
            pssws.add(local.smtp.pssw)
        if local.imap:
            imap = local.imap.host
            users.add(local.imap.user)
            pssws.add(local.imap.pssw)
        if len(users) == 1:
            user = users.pop()
        if len(pssws) == 1:
            pssw = pssws.pop()
    if None in (imap, smtp, user, pssw):
        raise ValueError("Missing environment variables")
    return Loging(
        imap=imap,
        smtp=smtp,
        user=user,
        pssw=pssw
    )

class Loging(NamedTuple):
    imap: str
    smtp: str
    user: str
    pssw: str

    def to_imap(self):
        return Config(
            host=self.imap,
            user=self.user,
            pssw=self.pssw,
            port=None
        )

    def to_smtp(self):
        return Config(
            host=self.smtp,
            user=self.user,
            pssw=self.pssw,
            port=None
        )


LOGIN = get_credentials()
