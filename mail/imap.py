import imaplib
from dataclasses import dataclass
from functools import cached_property
from email import message_from_bytes
from email.header import decode_header
from email.message import Message
import json
from typing import Union, Any
from datetime import datetime, date


@dataclass(frozen=True)
class File:
    name: str
    bytes: Any

    @cached_property
    def content(self):
        ext = self.name.rsplit(".")[-1].lower()
        if ext == "json":
            content = self.bytes.decode('utf8')
            return json.loads(content)
        return self.bytes


@dataclass(frozen=True)
class Mail:
    msg: Message
    id: str = None

    @staticmethod
    def from_bytes(body, *args, **kwargs):
        mail = message_from_bytes(body)
        return Mail(mail, *args, **kwargs)

    @cached_property
    def attachments(self):
        atts: list[File] = []
        for part in self.msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
            file_name = part.get_filename()

            if bool(file_name):
                file_name = decode_header(file_name)[0][0]
                if not isinstance(file_name, str):
                    file_name = str(file_name, 'utf-8', 'ignore')
                body_bytes = part.get_payload(decode=True)
                atts.append(File(
                    name=file_name,
                    bytes=body_bytes
                ))
        return tuple(atts)

    @cached_property
    def body(self) -> Union[str, None]:
        if not self.msg.is_multipart():
            c_type = self.msg.get_content_type()
            if c_type == "text/plain":
                body = self.msg.get_payload(decode=True)
                deco = self.msg.get_content_charset()
                body = body.decode(deco)
                return body.rstrip()
            return

        for part in self.msg.walk():
            c_type = part.get_content_type()
            c_disp = str(part.get("Content-Disposition"))
            if not (c_type == "text/plain" and "attachment" not in c_disp):
                continue
            body = part.get_payload(decode=True)
            if body is None:
                continue
            deco = part.get_content_charset()
            body = body.decode(deco)
            return body.rstrip()


@dataclass(frozen=True)
class Imap:
    host: str
    user: str
    password: str
    port: int = 993

    def __post_init__(self):
        self.login()

    def login(self):
        typ, accountDetails = self.session.login(self.user, self.password)
        if typ != 'OK':
            raise Exception('Not able to sign in!')

    @cached_property
    def session(self):
        return imaplib.IMAP4_SSL(self.host, self.port)

    def select(self, folder, readonly=False):
        typ, data = self.session.select(folder, readonly=readonly)
        if typ != 'OK':
            raise Exception(str(data[0], 'utf-8'))

    def gmraw(self, search, **kwargs):
        return self.search('X-GM-RAW', '"' + search + '"', **kwargs)

    def search(self, *criteria: str, fetch='(RFC822)'):
        typ, data = self.session.search(None, *criteria)
        if typ != 'OK':
            raise Exception('Error searching')
        for msgId in data[0].split():
            typ, messageParts = self.session.fetch(msgId, fetch)
            if typ != 'OK':
                raise Exception('Error fetching mail ' + str(msgId))
            mail = Mail.from_bytes(messageParts[0][1], id=msgId)
            yield mail

    def store(self, *args, **kwargs):
        typ, data = self.session.store(*args, **kwargs)
        if typ != 'OK':
            raise Exception("Fail in store")

    def seen(self, *msgId: str):
        for id in msgId:
            self.store(id, '+FLAGS', '\\Seen')

    def unseen(self, *msgId: str):
        for id in msgId:
            self.store(id, '-FLAGS', '\\Seen')

    def unread(self, *args, **kwargs):
        return self.search(*args, 'UNSEEN', **kwargs)

    def close(self):
        self.session.close()
        self.session.logout()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @staticmethod
    def dt_search(dt: Union[date, datetime, None] = None):
        if dt is None:
            dt = date.today()
        if isinstance(dt, (datetime, date)):
            return dt.strftime("%d-%b-%Y")
