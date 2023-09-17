import imaplib
import email
import os.path
import string
from email.header import decode_header
import datetime
import charset_normalizer as cn
from bs4 import BeautifulSoup
from crm import CrmClient
from tinydb import TinyDB, Query
import re
from log import logger
from dateutil.parser import parse
from multiprocessing import Lock


class LocalDB:
    def __init__(self, name=None):
        if name is not None:
            self.file_name = self.find(name)
            self.lock = Lock()
            with self.lock:
                self.id_list = [i['id'] for i in TinyDB(self.file_name).all()]

    @staticmethod
    def find(name):
        name = name + '.json'
        path = 'email_users/'
        for root, dirs, files in os.walk(path):
            if not files:
                with open(path + name, 'a') as f:
                    return f.name
            if name in files:
                return path + name
            else:
                with open(path + name, 'a') as f:
                    return f.name

    def append_local_db(self, list_date_title, flag_select):
        for i in list_date_title:
            if len(i) == 2:
                massage_id, date = i
                with TinyDB(self.file_name) as db:
                    if not db.contains(Query().id == massage_id):
                        with self.lock:
                            db.insert(
                                {'id': massage_id, 'Date': date, 'Box': flag_select})
                logger.info(f"Write email id = {massage_id} in DATABASE")

    def delete_by_date(self):
        for root, dirs, files in os.walk('email_users/'):
            for name in files:
                with TinyDB(root + name) as db:
                    date = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
                    logger.info('Delete last date')
                    query = Query()
                    db.remove(query.Date < date)


def del_charset(text):
    try:
        soup = BeautifulSoup(text, 'html.parser')
        charset = soup.find('meta')
        if charset and charset.get('content') is not None and 'charset' in charset.get('content').lower():
            charset.extract()
            return soup.prettify()
        return text
    except RecursionError:
        return text


def change_charset(text, char):
    try:
        soup = BeautifulSoup(text, 'html.parser')
        charset = soup.find('meta')
        if charset and charset.get('content') is not None and 'charset' in charset.get('content').lower():
            tag = charset.attrs
            tag['content'] = tag['content'].split(';')[0] + ';charset=' + char
            return soup.prettify()
        return text
    except RecursionError:
        return text


def check_email(email_user):
    pat = "^[a-zA-Z0-9-_.]+@[a-zA-Z0-9]+\.[a-z]{1,3}$"
    if re.match(pat, email_user):
        return True
    return False


class Mail:
    def __init__(self):
        self.list_table = None
        self.server = 'imap.mail.ru'
        self.today = datetime.datetime.now()
        self.yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        self.date_format = "%d-%b-%Y"
        self.request_date_today = f'(SINCE "{self.today.strftime(self.date_format)}")'
        self.request_date_yesterday = f'(SINCE "{self.yesterday.strftime(self.date_format)}") (BEFORE "{self.today.strftime(self.date_format)}")'

    def connect_email(self, mail_login, mail_password):
        try:
            imap = imaplib.IMAP4_SSL(self.server)
            imap.login(mail_login, mail_password)
        except Exception:
            logger.info(f'No connection {mail_login} wrong password or login')
            return
        self.list_table = LocalDB(mail_login).id_list
        INBOX, SENT = self.get_inbox_sent(imap.list())
        logger.info('Connect Email Inbox')
        imap.select(INBOX, readonly=True)
        if self.mail_read(user=mail_login, imap=imap, date=self.request_date_today, flag_select='INBOX'):
            self.mail_read(user=mail_login, imap=imap, date=self.request_date_yesterday, flag_select='INBOX')
        logger.info('Connect Email Send')
        imap.select(SENT, readonly=True)
        if self.mail_read(user=mail_login, imap=imap, date=self.request_date_today, flag_select='SEND'):
            self.mail_read(user=mail_login, imap=imap, date=self.request_date_yesterday, flag_select='SEND')
        imap.close()
        imap.logout()

    def mail_read(self, user, imap, date, flag_select=None):
        flag = False
        count = 0
        list_date_title = []
        for post in sorted(imap.search(None, date)[1][0].split(), reverse=True):
            res, msg = imap.fetch(post, '(RFC822)')
            try:
                msg = email.message_from_bytes(msg[0][1])
            except Exception as ex:
                logger.info('error read massage ', str(ex))
                try:
                    msg = self.for_massage(msg)
                except Exception as exx:
                    logger.info(f'{msg} error {exx}')
                    continue

            massage_id, date = self.get_message_id_date(msg)
            if massage_id in self.list_table:
                break

            sender, recipients = self.get_sender_recipients(msg)
            title, text = self.get_message_title_text_file(msg)
            list_date_title.append((massage_id, date))
            if self.mail_write(title, text, recipients, sender, flag_select, user=user):
                count += 1
        else:
            flag = True

        LocalDB(user).append_local_db(list_date_title, flag_select=flag_select)
        self.list_table = LocalDB(user).id_list
        if count == 0:
            logger.info('Don`t new massages')
        else:
            logger.info(f"Write {count} massages successful")
        return flag

    def mail_write(self, title, text, recipients, sender, flag, user=None):
        logger.info(f'{user} (title: {title})')
        title_end = title.split('#')
        if len(title_end) > 1:
            value = {
                'text': text,
                'subject': title,
                'recipients': recipients,
                'sender': sender,
                'flag': flag
            }
            for tit in title_end[1:]:
                res = '-'.join(self.find_pattern(tit))
                if not res:
                    continue
                logger.info(f'{user} write crm {res}')
                if res[0] == 'K' or res[0] == 'К':
                    if CrmClient().update_contact_post_account(res, value, user=user):
                        return True
                elif res[0] == 'П':
                    if CrmClient().update_contact_post_opportunity(res, value, user=user):
                        return True
            else:
                logger.info('Не найден #номер_проекта и #номер_контрагента')
        return False

    def for_massage(self, massage):
        logger.info('error massage')
        for n, m in enumerate(massage):
            try:
                msg = email.message_from_bytes(massage[n][1])
                return msg
            except Exception:
                continue

    def get_message_id_date(self, msg):
        logger.info('get_message_id_date')
        massage_id = msg['message-ID'].strip('<>') if msg['message-ID'] else None
        date = self.get_date(msg['DATE'])
        return massage_id, date

    def get_message_title_text_file(self, msg):
        logger.info('get_message_title_text_file')
        try:
            title = self.get_title(decode_header(msg['SUBJECT'])[0]) if msg["Subject"] else 'По умолчанию'
        except Exception as ex:
            logger.info(f"{ex} Ошибка заголовка")
            title = 'По умолчанию'
        text = ''
        for i in msg.walk():
            if i.get_content_maintype() == 'text' and i.get_content_subtype() == 'html':
                html = f"{self.get_text(i)}"
                text = html.replace("b'", "")
        return title, text

    def get_title(self, title):
        logger.info('get_title')
        if type(title) == bytes:
            try:
                return str(title, 'utf-8')
            except UnicodeDecodeError:
                return title
        if len(title) == 2:
            subject, encoding = title
            if encoding is None:
                if type(subject) == bytes:
                    try:
                        return subject.decode('utf-8')
                    except Exception as ex:
                        return 'По умолчанию'
                return subject
            else:
                try:
                    return subject.decode(encoding)
                except LookupError:
                    subject = ' '.join(list(subject))
                    return subject

    def get_text(self, msg):
        logger.info('get_text')
        text = msg.get_payload(decode=True)
        detect = cn.detect(text)
        try:
            text_result = text.decode(detect['encoding'])
            result = change_charset(text_result, 'utf-8')
        except AttributeError:
            result = change_charset(text, 'utf-8')

        return result

    def get_date(self, date):
        logger.info('get_date')
        try:
            date = parse(date).strftime('%Y-%m-%d')
            return date
        except Exception:
            date = date.split(',')[1].replace('(', '').replace(')', '')[:-10]
            date_obj = parse(date)
            date_str = date_obj.strftime('%Y-%m-%d')
            return date_str

    def get_file(self, msg):
        logger.info('get_file')
        try:
            file_name = decode_header(msg.get_filename())[0][0].decode()
        except Exception:
            file_name = msg.get_filename()
        if bool(file_name):
            file_path = os.path.join(f'/home/uventus/PycharmProjects/New_Proect/Integration_crm/{file_name}')
            if not os.path.isfile(file_path):
                with open(file_path, 'wb') as f:
                    f.write(msg.get_payload(decode=True))

    def get_sender_recipients(self, msg):
        ADDR_PATTERN = re.compile('<(.*?)>')
        try:
            sender = msg['From'].split('=')[-1].replace('<', '').replace('>', '').strip() if not msg[
                'Return-path'].strip(
                '<>') else \
                msg['Return-path'].strip('<>')
        except Exception:
            sender = msg['From'].split('<')[1].replace('>', '')
        recipients = []
        addr_fields = ['To', 'Cc', 'Bcc']

        for f in addr_fields:
            rfield = msg.get(f, "")  # Empty string if field not present
            rlist = re.findall(ADDR_PATTERN, rfield)
            recipients.extend(rlist)

        return sender, recipients

    def header_decode(self, header):
        hdr = ""
        try:
            for text, encoding in email.header.decode_header(header):
                if isinstance(text, bytes):
                    text = text.decode(encoding or "utf-8")
                hdr += text
            return hdr
        except Exception as ex:
            logger.info(f"Ошибка {ex}")
            return hdr

    def get_inbox_sent(self, lst):
        try:
            for i in lst[1]:
                msg = i.decode().split('/')
                if 'Inbox' in msg[0]:
                    inbox = ''.join([i for i in msg[1] if i.isalnum()])
                elif 'Sent' in msg[0]:
                    sent = msg[1].replace('"', '').replace("'", '')

            return inbox, sent
        except Exception as ex:
            logger.info(f"Ошибка {ex}")
            inbox,sent = 'INBOX','SENT'
            return inbox,sent

    def find_pattern(self, string):
        import re
        pattern = r"([А-ЯA-Z])-([А-ЯA-Zа-яa-z]+)-(\d+)"
        matches = re.findall(pattern, string)
        return matches[0] if len(matches) >= 1 else ''
