import csv
import yaml
from log import logger
from mail import Mail, check_email


def write_crm():
    with open("config.yaml", 'r') as stream:
        data_loaded = yaml.safe_load(stream)
        file_name = data_loaded['file_name']
    with open(file_name, 'r') as csvfile:
        users = csv.reader(csvfile)
        for row in users:
            email_user, password = row[0].split(':')
            if not check_email(email_user):
                logger.info(f'Wrong email {email_user}')
                continue
            Mail(email_user, password).connect_email()


write_crm()
