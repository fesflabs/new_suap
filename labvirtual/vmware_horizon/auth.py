import requests
import logging
import json
import urllib
from simplejson.scanner import JSONDecodeError
from .exception import vmware_horizon_check_error


logger = logging.getLogger(__name__)


class Auth:
    def __init__(self, hostname: str, username: str, password: str, domain: str, url: str = "rest", method: str = "https", verify: bool = False) -> None:
        if method.lower() not in ["https", "http"]:
            raise ValueError("Only http and https methods are valid.")
        #
        self.REST_API = f"{method}://{hostname}.{domain}/{url}"
        self.username = username
        self.password = password
        self.verify = verify
        self.domain = domain
        self.access_token = None
        self.refresh_token = None

    def connect(self):
        """
        Used to authenticate to the VMware Horizon REST API's
        """
        headers = {
            'accept': '*/*',
            'Content-Type': 'application/json',
        }

        data = {"domain": self.domain, "password": self.password, "username": self.username}
        json_data = json.dumps(data)
        response = requests.post(f'{self.REST_API}/login', verify=self.verify, headers=headers, data=json_data)
        vmware_horizon_check_error(response)
        data = response.json()
        self.access_token = {
            'accept': '*/*',
            'Authorization': 'Bearer ' + data['access_token']
        }
        self.refresh_token = data['refresh_token']
        return self

    def disconnect(self):
        """"
        Used to close close the connection with the VMware Horizon REST API's
        """
        headers = {
            'accept': '*/*',
            'Content-Type': 'application/json',
        }
        data = {'refresh_token': self.refresh_token}
        json_data = json.dumps(data)
        url = f'{self.REST_API}/logout'
        response = requests.post(url, verify=self.verify, headers=headers, data=json_data)
        return vmware_horizon_check_error(response)

    def request(self, method: str, endpoint: str, headers: dict = None, payload: dict = None, expected_codes: list = [200], json_response: bool = True):
        #
        headers = self.access_token
        headers["Content-Type"] = 'application/json'

        logger.debug(f"{method} {endpoint} - Headers: {headers} - Payload: {payload}")
        url = f'{self.REST_API}{endpoint}'
        response = requests.request(method=method, url=url, data=payload, verify=self.verify, headers=headers)
        vmware_horizon_check_error(response, expected_codes)
        #
        if json_response:
            try:
                return response.json()
            except JSONDecodeError as e:
                logger.error(f"[Error] {method} {endpoint}  - Headers: {headers} - Payload: {payload}: Could not decode JSON response: {str(e)}")
                return response
        else:
            return response

    def paginated_request_by_page(self, endpoint, page: int, maxpagesize: int, filter: dict = None, extra_filter: str = None) -> list:
        url = endpoint
        if filter:
            filter_url = urllib.parse.quote(json.dumps(filter, separators=(', ', ':')))
            add_filter = f"{filter_url}"
            url = f'{url}?filter={add_filter}&{extra_filter}' if extra_filter else f'{url}?filter={add_filter}'
        #
        url = f'{url}?page={page}&size={maxpagesize}'
        response = self.request("GET", url, json_response=False)
        has_more_records = 'HAS_MORE_RECORDS' in response.headers
        return response.json(), has_more_records

    def paginated_request(self, endpoint, filter: dict = None, maxpagesize: int = 100, extra_filter=None) -> list:
        if maxpagesize > 1000:
            maxpagesize = 1000
        page = 1
        results, has_more = self.paginated_request_by_page(endpoint, page=page, maxpagesize=maxpagesize, filter=filter, extra_filter=extra_filter)
        while has_more:
            page += 1
            result, has_more = self.paginated_request_by_page(endpoint, page=page, maxpagesize=maxpagesize, filter=filter, extra_filter=extra_filter)
            results += result
        return results
