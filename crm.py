import requests
from requests_ntlm import HttpNtlmAuth
import json
import yaml
from log import logger

with open("config.yaml", 'r') as stream:
    data_loaded = yaml.safe_load(stream)
    email_login = data_loaded['crm_login']
    email_password = data_loaded['crm_password']
    systemuser_id = data_loaded['systemuser_id_crm']
    contact_id = data_loaded['contact_id_crm']
    base_url = data_loaded['base_url']


class CrmClient(object):

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

    def get_contact_account(self, rn_number):
        logger.info('get_contact_account')
        result = requests.get(self.baseurl + f"accounts?$filter=rn_number eq  + '{rn_number}'",
                              auth=self.get_auth())
        logger.info(f'Connect to CRM get_contact_account {result}')
        file = result.json()
        return file

    def get_contact_opportunity(self, name):
        logger.info('get_contact_opportunity')
        result = requests.get(
            self.baseurl + f"opportunities?$filter=name eq '{name}'",
            auth=self.get_auth())
        logger.info(f'Connect to CRM get_contact_opportunity {result}')
        file = result.json()
        return file

    def update_contact_post_account(self, rn_number, value):
        logger.info('update_contact_put_account')
        account_id = self.get_contact_account(rn_number)['value'][0]['accountid']
        payload = {"subject": value['subject'], "description": value["text"],
                   "regardingobjectid_account@odata.bind": f"/accounts({account_id})",
                   "email_activity_parties": [
                       {"partyid_systemuser@odata.bind": f"/systemusers({self.systemuser_id})",
                        "participationtypemask": 1},
                       {"partyid_contact@odata.bind": f"/contacts({self.contact_id})",
                        "participationtypemask": 2}]}

        answer = requests.post(self.baseurl + "emails", auth=self.get_auth(), headers=self.headers,
                               data=json.dumps(payload))
        logger.info(f'Update to CRM update_contact_put_id {answer}')
        return answer

    def update_contact_post_opportunity(self, name, value):
        logger.info('update_contact_put_opportunity')
        opportunity_id = self.get_contact_opportunity(name)['value'][0]['opportunityid']
        payload = {"subject": value['subject'], "description": value["text"],
                   "regardingobjectid_opportunity@odata.bind": f"/opportunities({opportunity_id})",
                   "email_activity_parties": [
                       {"partyid_systemuser@odata.bind": f"/systemusers({self.systemuser_id})",
                        "participationtypemask": 1},
                       {"partyid_contact@odata.bind": f"/contacts({self.contact_id})",
                        "participationtypemask": 2}]}
        answer = requests.post(self.baseurl + "emails", auth=self.get_auth(), headers=self.headers,
                               data=json.dumps(payload))
        logger.info(f'Update to CRM update_contact_put_name {answer}')
        return answer
