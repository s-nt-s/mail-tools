from .credentials import LOGIN as LG
from mail.imap import Imap
from mail.smtp import Smtp, Mail as SMail

import random
import string


def randomword(length):
    letters = string.ascii_lowercase
    word = ''.join(random.choice(letters) for i in range(length))
    return word


def send_ramdom():
    sMail = SMail(
        to=LG.user,
        subject="unit-test-" + randomword(50),
        body="unit-test-" + randomword(50),
        attachments=dict(file=dict(a=randomword(50)))
    )
    with Smtp(host=LG.smtp, user=LG.user, password=LG.password) as smtp:
        smtp.send(sMail)
    return sMail


def get_unread(imap):
    arr = list(imap.unread(f'ON "{Imap.dt_search()}"'))
    if len(arr) > 0:
        return arr[-1]


def assertMail(iMail, sMail):
    if isinstance(iMail, list):
        assert len(iMail) == 1
        iMail = iMail[0]
    assert iMail.body == sMail.body
    assert len(iMail.attachments) == 1
    att = iMail.attachments[0]
    sAt = list(sMail.attachments.keys())[0]
    assert att.name == sAt + ".json"
    assert att.content == sMail.attachments[sAt]


def test_search():
    sMail = send_ramdom()
    with Imap(host=LG.imap, user=LG.user, password=LG.password) as imap:
        imap.select('INBOX')
        result = list(imap.search(f'HEADER Subject "{sMail.subject}"'))
    assertMail(result, sMail)


def test_unread():
    sMail = send_ramdom()

    with Imap(host=LG.imap, user=LG.user, password=LG.password) as imap:
        imap.select('INBOX')

        iUnread = get_unread(imap)
        assertMail(iUnread, sMail)
        id = iUnread.id

        iUnread = get_unread(imap)
        assert iUnread is None or iUnread.id != id

        imap.unseen(id)
        iUnread = get_unread(imap)
        assertMail(iUnread, sMail)

        imap.unseen(id)
        imap.seen(id)
        iUnread = get_unread(imap)
        assert iUnread is None or iUnread.id != id


def test_unread_readonly():
    sMail = send_ramdom()

    with Imap(host=LG.imap, user=LG.user, password=LG.password) as imap:
        imap.select('INBOX', readonly=True)
        iUnread = get_unread(imap)
        assertMail(iUnread, sMail)
        iUnread = get_unread(imap)
        assertMail(iUnread, sMail)
