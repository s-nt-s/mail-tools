import smtplib
from dataclasses import dataclass
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from functools import cached_property
from typing import Union, Any
import json
from os.path import isfile, basename


def to_addr(s):
    if isinstance(s, str):
        return s
    return COMMASPACE.join(s)


@dataclass(frozen=True)
class Mail:
    to: Union[str, list, tuple]
    frm: str = None
    dt: str = formatdate(localtime=True)
    subject: Union[str, None] = None
    body: Union[str, None] = None
    attachments: Union[tuple, dict] = tuple()

    def to_multipart(self):
        msg = MIMEMultipart()
        if self.frm:
            msg['From'] = self.frm
        msg['To'] = to_addr(self.to)
        msg['Date'] = self.dt
        if self.subject:
            msg['Subject'] = self.subject

        if self.body:
            msg.attach(MIMEText(self.body))

        for att in self.iter_attachments():
            msg.attach(att)
        return msg

    def iter_attachments(self):
        if isinstance(self.attachments, dict):
            for k, v in self.attachments.items():
                name = k + ".json"
                att = MIMEApplication(
                    json.dumps(v).encode(),
                    Name=name
                )
                att['Content-Disposition'] = 'attachment; filename="%s"' % name
                yield att
        if isinstance(self.attachments, tuple):
            for att in self.attachments:
                if isfile(att):
                    name = basename(att)
                    with open(att, "rb") as fil:
                        content = fil.read()
                    att = MIMEApplication(
                        content,
                        Name=name
                    )
                    att['Content-Disposition'] = 'attachment; filename="%s"' % name
                    yield att


@dataclass(frozen=True)
class Smtp:
    host: str
    user: str
    password: str
    port: int = 465

    def __post_init__(self):
        self.login()

    def login(self):
        self.session.login(self.user, self.password)

    @cached_property
    def session(self):
        return smtplib.SMTP_SSL(self.host, self.port)

    def close(self):
        self.session.close()

    def send(self, msg: Union[MIMEMultipart, Mail]):
        if isinstance(msg, Mail):
            msg = msg.to_multipart()
        if msg['From'] is None:
            msg['From'] = self.user
        self.session.sendmail(msg['From'], msg['To'], msg.as_string())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
