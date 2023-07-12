import csv
import os
import time
from functools import wraps
import yaml
from log import logger
from mail import Mail, check_email, LocalDB
from multiprocessing import Pool as ThreadPool
from ecrypt_user import encrypt_user, decrypt_user


def time_count(func):
    @wraps(func)
    def inner(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        print(f'Затрачено времени {total_time} ')
        return result

    return inner


@time_count
def write_crm():
    with open("config.yaml", 'r') as stream:
        data_loaded = yaml.safe_load(stream)
        file_name = data_loaded['file_name']
        processing = data_loaded['Processing']
        user = []
        if os.path.isfile(file_name):
            encrypt_user(file_name)
            users = decrypt_user(file_name)
        else:
             users = decrypt_user(file_name)
        for row in users:
            email_user, password = row[0].split(';')
            if not check_email(email_user):
                logger.info(f'Wrong email {email_user}')
                continue
            else:
                user.append((email_user, password))
    with ThreadPool(processing) as p:
        p.starmap(Mail().connect_email, user)



if __name__ == '__main__':
    write_crm()
    LocalDB().delete_by_date()
