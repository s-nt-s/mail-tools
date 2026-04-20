from subprocess import run
from os.path import isfile
from os import access, R_OK
from typing import NamedTuple
import re

_HOST_PORT = {
   'imap.gmail.com': 993,
   'smtp.gmail.com': 587
}


class Config(NamedTuple):
    host: str = None
    port: int = None
    user: str = None
    pssw: str = None

    @classmethod
    def from_dict(cls, dct: dict):
        d = {k: v for k, v in dct.items() if k in cls._fields and v is not None}
        if d.get("port") is None:
           d["port"] = _HOST_PORT.get(d.get("host"))
        return cls(**d)


class SysConfig(NamedTuple):
    imap: Config = None
    smtp: Config = None

    @classmethod
    def from_dict(cls, dct: dict):
        d = {}
        for k, v in dct.items():
            if k in cls._fields and v is not None:
                if k in ('imap', 'smtp') and isinstance(v, dict):
                    v = Config.from_dict(v)
                d[k] = v
        if d.get('imap') is None and d.get('smtp') is not None:
            if d['smtp'].host == 'smtp.gmail.com':
                d['imap'] = Config.from_dict(
                    d['smtp']._replace(host='imap.gmail.com', port=None)._asdict()
                )
        return cls(**d)


def _read(path: str):
    if not isfile(path):
        return None
    if access(path, R_OK):
        with open(path, 'r') as f:
            return f.read().strip()
    r = run(
        ['sudo', '-n', 'cat', path],
        capture_output=True,
        text=True
    )
    if r.returncode == 0:
        return r.stdout.strip()
    return None


def _load(file: str):
    content = _read(file)
    if content is None:
        return None
    content = re.sub(r"#.*", "", content)
    content = re.sub(r"^\s+$", " ", content, flags=re.MULTILINE)
    content = content.strip()
    if len(content) == 0:
        return None
    return content


def _parse_postfix(content: str) -> dict[str]:
    for x in re.findall(
        r"^\s*\[(.*?)\]:(\d+)\s+(.+):(.+)\s*$",
        content,
        flags=re.MULTILINE
    ):
        host, port, user, pssw = x
        return {
            'smtp': Config.from_dict({
                'host': host,
                'port': int(port),
                'user': user,
                'pssw': pssw
            })
        }

def _parse_exim4(content: str) -> dict[str]:
    for x in re.findall(
        r"^\s*(.*?):(.+):(.+)\s*$",
        content,
        flags=re.MULTILINE
    ):
        host, user, pssw = x
        return {
            'smtp': Config.from_dict({
                'host': host,
                'user': user,
                'pssw': pssw
            })
        }


def get_config() -> SysConfig:
    config = {}
    for file, fnc in {
        '/etc/postfix/sasl_passwd': _parse_postfix,
        '/etc/exim4/passwd.client': _parse_exim4
    }.items():
        content = _load(file)
        if content is not None:
            cnf = fnc(content)
            if cnf:
                config.update(cnf)
    return SysConfig.from_dict(config)


if __name__ == "__main__":
    import sys
    print(get_config())
