from dataclasses import dataclass, fields, replace
from typing import Optional
from mail.file import File
import re


_HOST_PORT = {
   'imap.gmail.com': 993,
   'smtp.gmail.com': 465
}
SMTP_IMAP = {
    'smtp.gmail.com': 'imap.gmail.com'
}


def _mk_obj(dct: dict | None, *keys: str):
    if dct is None:
        return {k: None for k in keys}
    if not isinstance(dct, dict):
        raise ValueError(dct)
    obj = {}
    for k in keys:
        v = dct.get(k)
        if isinstance(v, str):
            v = v.strip()
            if len(v) == 0:
                v = None
        obj[k] = v
    return obj


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    user: str
    pssw: str

    def __post_init__(self):
        port =  _HOST_PORT.get(self.host)
        if port is not None:
            object.__setattr__(self, 'port', port)
        elif isinstance(self.port, str) and self.port.isdecimal():
            object.__setattr__(self, 'port', int(self.port))
        ko: list[str] = []
        for f in fields(self):
            v = getattr(self, f.name)
            if v is None or not isinstance(v, f.type):
                ko.append(f.name)
        if ko:
            raise ValueError(", ".join(ko))

    @classmethod
    def build(cls, obj: dict | None):
        obj = _mk_obj(obj, *(f.name for f in fields(cls)))
        if all(v is None for v in obj.values()):
            return None
        return cls(**obj)

    def _replace(self, **kwargs):
        return replace(self, **kwargs)


@dataclass(frozen=True)
class LocalConfig:
    smtp: Optional[Config] = None
    imap: Optional[Config] = None

    def __post_init__(self):
        for f in fields(self):
            v = getattr(self, f.name)
            if isinstance(v, dict):
                object.__setattr__(self, f.name, Config.build(v))
        if self.smtp is not None and self.imap is None:
            imap = SMTP_IMAP.get(self.smtp.host)
            if imap:
                object.__setattr__(self, 'imap', replace(self.smtp, host=imap, port=None))
        ko: list[str] = []
        for f in fields(self):
            v = getattr(self, f.name)
            if v is not None and not isinstance(v, Config):
                ko.append(f.name)
        if ko:
            raise ValueError(", ".join(ko))

    @classmethod
    def build(cls, obj: dict | None):
        return cls(**_mk_obj(obj, *(f.name for f in fields(cls))))
    
    @classmethod
    def load_from_system(cls):
        config = {'smtp': {}, 'imap': {}}
        for file, rgx in {
            '/etc/postfix/sasl_passwd': r"^\s*\[(?P<host>.*?)\]:(?P<port>\d+)\s+(?P<user>.+):(?P<pssw>.+)\s*$",
            '/etc/exim4/passwd.client': r"^\s*(?P<host>.*?):(?P<user>.+):(?P<pssw>.+)\s*$",
        }.items():
            for m in File(file).iterdict(
                re.compile(rgx, re.MULTILINE),
                comment="#",
                trim=True,
            ):
                config['smtp'].update(m)
        return cls.build(config)


if __name__ == "__main__":
    print(LocalConfig.load_from_system())