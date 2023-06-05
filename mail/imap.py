import imaplib
from dataclasses import dataclass
from functools import cached_property
from email import message_from_bytes
from email.header import decode_header
from email.message import Message
import json
from typing import Union, Any
from datetime import datetime, date
import functools
import re
from os.path import join, dirname, isdir
from os import makedirs


class SelectException(imaplib.IMAP4.error):
    pass


class LoginException(imaplib.IMAP4.error):
    pass


class SearchException(imaplib.IMAP4.error):
    pass


class FetchException(imaplib.IMAP4.error):
    pass


class StoreException(imaplib.IMAP4.error):
    pass


class ListException(imaplib.IMAP4.error):
    pass


class GMailFolderException(imaplib.IMAP4.error):
    pass


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

    def save(self, target):
        if target[-1] in ("/", "\\"):
            target = join(target, self.name)
        fdir = dirname(target)
        if fdir and not isdir(fdir):
            makedirs(fdir)
        with open(target, "wb") as f:
            f.write(self.bytes)
        return target


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


def raise_deco(func, exc):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            typ, data = func(*args, **kwargs)
        except imaplib.IMAP4.error as e:
            raise exc(e)
        if typ != 'OK':
            raise exc(str(data[0], 'utf-8'))
        return typ, data
    return wrapped


class IMAP4_SSL(imaplib.IMAP4_SSL):
    EXC = {
        "login": LoginException,
        "select": SelectException,
        "search": SearchException,
        "fetch": FetchException,
        "store": StoreException,
        "list": ListException
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, exc in IMAP4_SSL.EXC.items():
            mth = getattr(self, name)
            mth = raise_deco(mth, exc)
            setattr(self, name, mth)


@dataclass(frozen=True)
class Imap:
    user: str
    password: str
    host: str
    port: int = 993

    def login(self):
        return self.session.login(self.user, self.password)

    @cached_property
    def session(self):
        return IMAP4_SSL(self.host, self.port)

    def list(self):
        arr = []
        typ, data = self.session.list()
        for item in data:
            arr.append(item.decode())
        return tuple(arr)

    def select(self, folder, readonly=False):
        return self.session.select(folder, readonly=readonly)

    def search(self, *criteria: str, fetch='(RFC822)'):
        typ, data = self.session.search(None, *criteria)
        for msgId in data[0].split():
            typ, messageParts = self.session.fetch(msgId, fetch)
            mail = Mail.from_bytes(messageParts[0][1], id=msgId)
            yield mail

    def store(self, *args, **kwargs):
        return self.session.store(*args, **kwargs)

    def seen(self, *msgId: str):
        for id in msgId:
            self.store(id, '+FLAGS', '\\Seen')

    def unseen(self, *msgId: str):
        for id in msgId:
            self.store(id, '-FLAGS', '\\Seen')

    def close(self):
        if self.session.state == "SELECTED":
            self.session.close()
        if self.session.state == "AUTH":
            self.session.logout()

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @staticmethod
    def dt_search(dt: Union[date, datetime, None] = None):
        if dt is None:
            dt = date.today()
        if isinstance(dt, (datetime, date)):
            return dt.strftime("%d-%b-%Y")


@dataclass(frozen=True)
class GMail(Imap):
    host: str = 'imap.gmail.com'
    port: int = 993

    @cached_property
    def folder_all(self):
        flds = set()
        re_folder = re.compile(r'.*(?:\(| )\\All\b.*"/" "([^"]+)"$')
        for folder in self.list():
            m = re_folder.match(folder)
            if m:
                flds.add(m.group(1))
        if len(flds) == 0:
            raise GMailFolderException("No GMail All Folder")
        if len(flds) > 1:
            flds = ", ".join(sorted(flds))
            raise GMailFolderException("Ambiguous GMail All Folder: " + flds)
        return flds.pop()

    def search(self, search: str, fetch='(RFC822)'):
        search = search.replace('"', r'\"')
        return super().search('X-GM-RAW', '"' + search + '"', fetch=fetch)

    def select(self, folder, readonly=False):
        if folder == "ALL":
            folder = self.folder_all
        return super().select(folder, readonly=readonly)
