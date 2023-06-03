import os
from dotenv import load_dotenv
from collections import namedtuple

Loging = namedtuple("Credentials", "imap smtp user password")

load_dotenv()

LOGIN = Loging(
    imap=os.environ["IMAP_HOST"],
    smtp=os.environ["SMTP_HOST"],
    user=os.environ["MAIL_USER"],
    password=os.environ["MAIL_PASS"]
)
