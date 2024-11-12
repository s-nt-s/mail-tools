import os
from dotenv import load_dotenv
from typing import NamedTuple

load_dotenv()


class Loging(NamedTuple):
    imap: str
    smtp: str
    user: str
    password: str


LOGIN = Loging(
    imap=os.environ["IMAP_HOST"],
    smtp=os.environ["SMTP_HOST"],
    user=os.environ["MAIL_USER"],
    password=os.environ["MAIL_PASS"]
)
