from pathlib import Path
from os import access, R_OK
from subprocess import run
import re


class File(Path):

    @staticmethod
    def __rstrip(s: str | None):
        if s is None:
            return None
        s = s.rstrip()
        if len(s) == 0:
            return None
        return s
    
    def __read(self):
        if not self.is_file():
            return None
        if access(self, R_OK):
            with open(self, 'r') as f:
                return File.__rstrip(f.read())
        r = run(
            ['sudo', '-n', 'cat', str(self)],
            capture_output=True,
            text=True
        )
        if r.returncode == 0:
            return File.__rstrip(r.stdout)
        return None
    
    def read(
        self,
        comment='#',
        trim=True
    ):
        content = self.__read()
        if content is None:
            return None
        if comment:
            content = re.sub(re.escape(comment)+".*", "", content)
        if trim:
            content = "\n".join(ln.strip() for ln in content.split("\n") if ln.strip())
            content = content.strip()
        if len(content) == 0:
            return None
        return content
    
    def iterdict(
        self,
        rgx: re.Pattern,
        comment='#',
        trim=True,
    ):
        content = self.read(comment=comment, trim=trim)
        if content:
            for m in rgx.finditer(content):
                yield m.groupdict()