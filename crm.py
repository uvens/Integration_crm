import requests
from requests_ntlm import HttpNtlmAuth
import json
import yaml
from log import logger

with open("config.yaml", 'r') as stream:
    """
    Получаем данные из файла config.yaml
    """
    data_loaded = yaml.safe_load(stream)
    email_login = data_loaded['crm_login']
    email_password = data_loaded['crm_password']
    systemuser_id = data_loaded['systemuser_id_crm']
    contact_id = data_loaded['contact_id_crm']
    base_url = data_loaded['base_url']


class CrmClient(object):
    """Класс CrmClient предназначени для подключения к crm: http://srvr-mscrm.first/Ruscon/api/data/v8.2/,
     получения данных и запись в crm результата
     Методы:
     baseurl - объект property для url адреса
     get_auth - Аутентификация при входе
     get_contact_account - Получение данных по контрагенту
     get_contact_opportunity - Получение данных по сделке
     update_contact_post_account - Запись сообщения из переписки к контрагенту
     update_contact_post_opportunity - Запись сообщения из переписки к сделке
     """

    def __init__(self):
        self.headers = {
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8"
        }
        self.systemuser_id = systemuser_id
        self.contact_id = contact_id
        self.login = email_login
        self.password = email_password
        self.base_url = base_url

    @property
    def baseurl(self):
        return self.base_url

    def get_auth(self):
        return HttpNtlmAuth(self.login, self.password)

    def get_contact_account(self, rn_number: str) -> dict:
        """
        Совершаем get запрос на получение данных из сервиса crm: http://srvr-mscrm.first/Ruscon/api/data/v8.2/ по сделке
        :param rn_number: Номер сделки
        :return: Информацию по сделке
        """
        logger.info('get_contact_account')
        result: requests = requests.get(self.baseurl + f"accounts?$filter=rn_number eq  + '{rn_number}'",
                                        auth=self.get_auth())
        logger.info(f'Connect to CRM get_contact_account {result}')
        file: dict = result.json()
        return file

    def get_contact_opportunity(self, name: str) -> dict:
        """
        Совершаем get запрос на получение данных из сервиса crm: http://srvr-mscrm.first/Ruscon/api/data/v8.2/ по коносаменту
        :param name: Номер коносамента
        :return: Информацию по коносаменту
        """
        logger.info('get_contact_opportunity')
        result: requests = requests.get(
            self.baseurl + f"opportunities?$filter=name eq '{name}'",
            auth=self.get_auth())
        logger.info(f'Connect to CRM get_contact_opportunity {result}')
        file: dict = result.json()
        return file

    def update_contact_post_account(self, rn_number: str, value: dict, user=None) -> requests:
        """
        При удачном получение данных по сделки мы записываем результат в crm при помощи метода post библиотеки requests.
        Создаём payload в который передаём все данные для записи
        :param rn_number: Номер сделки
        :param value: Словарь со значениями из сообщения(заголовок, текст, отправитель, получатели)
        :param user: email пользователя
        :return: Возвращается результат запроса
        """
        account: list = self.get_contact_account(rn_number)['value']
        flag: bool = value['flag'] != 'INBOX'
        if not account:
            return False
        logger.info(f'{user} update_contact_put_account')
        account_id: str = account[0]['accountid']
        payload: dict = {"subject": value['subject'],
                         "description": value['text'],
                         "regardingobjectid_account@odata.bind": f"/accounts({account_id})",
                         "email_activity_parties": [{
                             "addressused": value['sender'],
                             "participationtypemask": 1
                         },
                             *[{"addressused": i, "participationtypemask": 2} for i in value['recipients']]
                         ],
                         "directioncode": flag,
                         "statecode": 1,
                         }

        # answer: requests = requests.post(self.baseurl + "emails", auth=self.get_auth(), headers=self.headers,
        #                                  data=json.dumps(payload))
        # logger.info(f'Update to CRM user({user}) update_contact_put_id {answer}')
        # return answer

    def update_contact_post_opportunity(self, name: str, value: dict, user=None) -> requests:
        """
        При удачном получение данных по контрагенту мы записываем результат в crm при помощи метода post библиотеки requests.
        Создаём payload в который передаём все данные для записи
        :param name: Номер контрагента
        :param value: Словарь со значениями из сообщения(заголовок, текст, отправитель, получатели)
        :param user: email пользователя
        :return: Возвращается результат запроса
        """
        opportunity: list = self.get_contact_opportunity(name)['value']
        flag: bool = value['flag'] != 'INBOX'
        if not opportunity:
            return False
        logger.info(f'{user} update_contact_put_opportunity')
        opportunity_id: str = opportunity[0]['opportunityid']
        payload: dict = {"subject": value['subject'], "description": value["text"],
                         "regardingobjectid_opportunity@odata.bind": f"/opportunities({opportunity_id})",
                         "email_activity_parties": [{
                             "addressused": value['sender'],
                             "participationtypemask": 1
                         },
                             *[{"addressused": i, "participationtypemask": 2} for i in value['recipients']]
                         ],
                         "directioncode": flag,
                         "statecode": 1,
                         }

        # answer: requests = requests.post(self.baseurl + "emails", auth=self.get_auth(), headers=self.headers,
        #                                  data=json.dumps(payload))
        # logger.info(f'Update to CRM user({user})  update_contact_put_name {answer}')
        # return answer
