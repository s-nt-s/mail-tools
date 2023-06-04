from .credentials import LOGIN as LG
from mail.imap import Imap, SelectException, LoginException, StoreException, FetchException, SearchException
from mail.smtp import Smtp, Mail as SMail
import pytest

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
    arr = list(imap.search(f'ON "{Imap.dt_search()}"', 'UNSEEN'))
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


def test_ko_select():
    word = randomword(50)

    with Imap(host=LG.imap, user=LG.user, password=LG.password) as imap:
        with pytest.raises(SelectException):
            imap.select(word, readonly=True)


def test_ko_login():
    word = randomword(50)

    with pytest.raises(LoginException):
        with Imap(host=LG.imap, user=LG.user, password=word) as imap:
            imap.select('INBOX', readonly=True)


def test_ko_store():
    sMail = send_ramdom()
    with Imap(host=LG.imap, user=LG.user, password=LG.password) as imap:
        imap.select('INBOX', readonly=True)
        result = list(imap.search(f'HEADER Subject "{sMail.subject}"'))
        assert len(result) == 1
        iMail = result[0]
        with pytest.raises(StoreException):
            imap.seen(iMail.id)


def test_ko_search():
    with Imap(host=LG.imap, user=LG.user, password=LG.password) as imap:
        imap.select('INBOX', readonly=True)
        with pytest.raises(SearchException):
            list(imap.search("XXXX"))


def test_ko_fetch():
    sMail = send_ramdom()
    with Imap(host=LG.imap, user=LG.user, password=LG.password) as imap:
        imap.select('INBOX', readonly=True)
        with pytest.raises(FetchException):
            list(imap.search(
                f'HEADER Subject "{sMail.subject}"',
                fetch="XXXX"
            ))
