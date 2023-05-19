import imaplib
import email
from email.header import decode_header
import base64
import yaml
from datetime import datetime
from email.utils import parsedate_to_datetime
from crm import CrmClient
from tinydb import TinyDB, Query
import re
from log import logger


class LocalDB:
    def id_in_local_db(self, massage_id):
        logger.info('Connect DATABASE')
        with TinyDB('mail_id.json') as db:
            if db.search(Query().id == massage_id):
                return True
            return False

    def append_localdb(self, massage_id, date):
        with TinyDB('mail_id.json') as db:
            db.insert(
                {'id': massage_id, 'Date': date})
            logger.info(f"Write email id = {massage_id} in DATABASE")





def check_email(email):
    pat = "^[a-zA-Z0-9-_.]+@[a-zA-Z0-9]+\.[a-z]{1,3}$"
    if re.match(pat, email):
        return True
    return False


class Mail:
    def __init__(self, emai_user, password_user):
        self.server = 'imap.mail.ru'
        self.mail_login = emai_user
        self.mail_password = password_user

    def connect_email(self):
        imap = imaplib.IMAP4_SSL(self.server)
        imap.login(self.mail_login, self.mail_password)
        logger.info('Connect Email Inbox')
        imap.select("INBOX", readonly=True)
        self.mail_read(imap)
        logger.info('Connect Email Send')
        imap.select("&BB4EQgQ,BEAEMAQyBDsENQQ9BD0ESwQ1-", readonly=True)
        self.mail_read(imap)
        imap.close()
        imap.logout()

    def mail_read(self, imap):
        count = 0
        for post in imap.search(None, 'ALL')[1][0].split():
            res, msg = imap.fetch(post, '(RFC822)')
            msg = email.message_from_bytes(msg[0][1])
            massage_id = msg['message-ID'].strip('<>')
            if LocalDB().id_in_local_db(massage_id):
                continue
            date = datetime.fromtimestamp(parsedate_to_datetime(msg['DATE']).timestamp()).strftime('%Y-%m-%d %H:%M:%S')
            title = decode_header(msg['SUBJECT'])[0][0] if msg["Subject"] else 'По умолчанию'
            if type(title) != str:
                title = title.decode()
            text = None

            LocalDB().append_localdb(massage_id, date)

            for i in msg.walk():
                if i.get_content_maintype() == 'text' and i.get_content_subtype() == 'plain':
                    text = base64.b64decode(i.get_payload()).decode()

            if len(title.split('#')) == 2:
                title_end = title.split('#')
                if self.mail_write(title_end[1], text):
                    count += 1
        if count == 0:
            logger.info('Don`t new massages')
        else:
            logger.info(f"Write {count} massages successful")

    def mail_write(self, title, text):
        value = {
            'text': text,
            'subject': title
        }
        if title.strip()[0] == 'K' or title.strip()[0] == 'К':
            CrmClient().update_contact_post_account(title, value)
            logger.info('Write email_account')
            return True
        elif title.strip()[0] == 'П':
            CrmClient().update_contact_post_opportunity(title, value)
            logger.info('Write email_account')
            return True
        else:
            logger.info('Не найден #номер_проекта и #номер_контрагента')
            return False
