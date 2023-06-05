from mail.fetchmail import FetchMail, FetchMailItem, FetchCredentials


def test_fetchmail():
    f = FetchMail("tests/fetchmailrc.txt")
    c = f.get_credential(FetchMailItem(
        protocol="IMAP",
        localname='USER'
    ))
    assert c == FetchCredentials(
        host="imap.example.com",
        protocol="IMAP",
        port=993,
        user='examplel@domain.com',
        password="password"
    )
