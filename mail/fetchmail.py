import subprocess
import sys
from functools import cached_property, cache
from typing import NamedTuple
from typing import Tuple
from dataclasses import dataclass
from os.path import isfile


def shell_output(*args: str, **kwargv) -> str:
    output = subprocess.check_output(args, **kwargv)
    output = output.decode(sys.stdout.encoding)
    return output


def run_py_code(py_code, return_var):
    _locals = {}
    _globals = {}
    exec(py_code, _globals, _locals)
    return _locals.get(return_var)


def arr_append(arr: list, item):
    # No uso set() porque no quiero
    # alterar el orden de los elementos
    if item not in arr:
        arr.append(item)


def arr_none_if_empty(arr: list):
    if len(arr) == 0:
        arr = [None]
    return tuple(arr)


class FetchMailItem(NamedTuple):
    localname: str = None
    mailbox: str = None
    protocol: str = None
    host: str = None
    port: int = None
    user: str = None
    password: str = None

    @cache
    def fields_filled(self):
        kys = (k for k in self._fields if getattr(self, k) is not None)
        return tuple(kys)

    def subset(self, fields: Tuple[str]):
        fields = set(fields).intersection(self.fields_filled())
        dct = {k: getattr(self, k) for k in fields}
        return FetchMailItem(**dct)


class FetchCredentials(NamedTuple):
    protocol: str
    host: str
    port: int
    user: str
    password: str


@dataclass(frozen=True)
class FetchMail:
    fetchmailrc: str = None

    def __post_init__(self):
        if self.fetchmailrc is not None and not isfile(self.fetchmailrc):
            raise FileNotFoundError("%s is not a file" % self.fetchmailrc)

    @cached_property
    def config(self):
        cmd = ["fetchmail", "--configdump"]
        if self.fetchmailrc:
            cmd.extend(["--fetchmailrc", self.fetchmailrc])
        py_code = shell_output(*cmd)
        fetchmailrc = run_py_code(py_code, 'fetchmailrc')
        return fetchmailrc

    @cached_property
    def items(self) -> Tuple[FetchMailItem]:
        pls = []
        for servers in self.config['servers']:
            service = servers['service']
            for user in servers['users']:
                ssl = user['ssl']
                port = self.get_port(service, servers['protocol'], ssl)
                localnames = arr_none_if_empty(user['localnames'])
                mailboxes = arr_none_if_empty(user['mailboxes'])
                for localname in localnames:
                    for mailbox in mailboxes:
                        arr_append(
                            pls,
                            FetchMailItem(
                                protocol=servers['protocol'],
                                localname=localname,
                                host=servers['pollname'],
                                port=port,
                                user=user['remote'],
                                password=user['password'],
                                mailbox=mailbox
                            )
                        )
        return tuple(pls)

    def search_credentials(
            self,
            match: FetchMailItem = None) -> Tuple[FetchCredentials]:
        crd = []
        for item in self.items:
            if match is None or match == item.subset(match.fields_filled()):
                arr_append(
                    crd,
                    FetchCredentials(
                        protocol=item.protocol,
                        host=item.host,
                        port=item.port,
                        user=item.user,
                        password=item.password,
                    )
                )
        return tuple(crd)

    def get_credential(self, match: FetchMailItem = None) -> FetchCredentials:
        crd = self.search_credentials(match)
        if len(crd) == 0:
            raise Exception("Credential not found")
        if len(crd) > 1:
            raise Exception("Credential ambiguous")
        return crd[0]

    def get_port(self, service, protocol, ssl):
        if isinstance(service, int):
            return service
        if isinstance(service, str) and service.isdigit():
            return int(service)
        prot = {
            "IMAP": (143, 993),
            "POP3": (110, 995),
        }.get(protocol)
        if prot is None:
            return None
        return prot[int(ssl)]


if __name__ == "__main__":
    import os
    f = FetchMail()
    print(f.get_credential(FetchMailItem(
        protocol="IMAP",
        localname=os.environ['USER']
    )))
