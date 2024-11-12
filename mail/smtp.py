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
from os.path import isfile
import re

re_mail = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def to_mail_tuple(m: Union[None, str, tuple[str, ...], list[str]]):
    if m is None:
        return tuple()
    if isinstance(m, (tuple, list)):
        return tuple(m)
    if not isinstance(m, str):
        raise ValueError("Not a valid email: "+str(type(m))+" "+str(m))
    v = re_mail.findall(m)
    return tuple(sorted(set(v)))


@dataclass(frozen=True)
class Mail:
    to: tuple[str, ...]
    frm: str = None
    dt: str = formatdate(localtime=True)
    subject: Union[str, None] = None
    body: Union[str, None] = None
    attachments: Union[tuple[str, ...], dict[str, Any]] = tuple()
    cc: tuple[str, ...] = tuple()
    bcc: tuple[str, ...] = tuple()

    def __post_init__(self):
        object.__setattr__(self, 'to', to_mail_tuple(self.to))
        object.__setattr__(self, 'cc', to_mail_tuple(self.cc))
        object.__setattr__(self, 'bcc', to_mail_tuple(self.bcc))

    @property
    def to_addrs(self):
        return tuple(sorted(
            set(self.to).union(self.bcc).union(self.bcc)
        ))

    def to_multipart(self):
        msg = MIMEMultipart()
        if self.frm:
            msg['From'] = self.frm
        if self.to:
            msg['To'] = COMMASPACE.join(self.to)
        if self.cc:
            msg['CC'] = COMMASPACE.join(self.cc)
        msg['Date'] = self.dt
        if self.subject:
            msg['Subject'] = self.subject

        if self.body:
            msg.attach(MIMEText(self.body))

        for att in self.iter_attachments():
            msg.attach(att)
        return msg

    def iter_attachments(self):
        c_disposition = 'attachment; filename="{}"'
        if isinstance(self.attachments, dict):
            for k, v in self.attachments.items():
                name = k + ".json"
                att = MIMEApplication(
                    json.dumps(v).encode(),
                    Name=name
                )
                att['Content-Disposition'] = c_disposition.format(name)
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
                    att['Content-Disposition'] = c_disposition.format(name)
                    yield att


@dataclass(frozen=True)
class Smtp:
    host: str
    user: str
    password: str
    port: int = 465

    def login(self):
        self.session.login(self.user, self.password)

    @cached_property
    def session(self):
        return smtplib.SMTP_SSL(self.host, self.port)

    def close(self):
        self.session.close()

    def send(self, msg: Union[MIMEMultipart, Mail]):
        to_addrs, msg = self.__prepare_mail(msg)

        if len(to_addrs) == 0:
            raise ValueError("to_addrs is empty")

        if msg['From'] is None:
            msg['From'] = self.user

        self.session.sendmail(
            msg['From'],
            to_addrs,
            msg.as_string()
        )

    def __prepare_mail(self,  msg: Union[MIMEMultipart, Mail]) -> tuple[tuple[str, ...], MIMEMultipart]:
        if isinstance(msg, Mail):
            return msg.to_addrs, msg.to_multipart()
        to_addrs = set()
        for k in ('To', 'CC'):
            m = re_mail.findall(msg.get(k, ''))
            to_addrs = to_addrs.union(m)
        return tuple(sorted(to_addrs)), msg

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
