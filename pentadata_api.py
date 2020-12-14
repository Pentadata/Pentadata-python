from urllib.parse import urljoin
from datetime import datetime, timedelta

import requests


class PentaApi:
    """Provide utility functions to communicate more easily
    with the Pentadata API endpoints.

    This class is built on top of the `requests` package
    (https://requests.readthedocs.io/en/master/). It provides convenient
    wrappers around the HTTP verbs GET, POST, PUT and DELETE to ease the
    communication with the Pentadata Subscribers API.

    Example usage:
    ```
    >> from pentadata_api import PentaApi
    >> email = 'you@email.com'
    >> api_key = 'secret-key'
    >> penta = PentaApi(email, api_key)
    ```

    Once created, the `PentaApi` object supports `.get()`, `.post()`, `.put()`,
    and `.delete()` methods with same signature and return type of the
    corresponding function in the package `requests`. Internally, the
    connection to the Pentadata API is handled transparently.

    You do not need to use `_refresh()` nor `_is_expired()`; they are for
    internal usage only.

    Example (continued):
    ```
    >> url = ...
    >> payload = {...}
    >> headers = {...}
    # now use penta instead of requests
    >> response = penta.post(url, headers=headers, json=payload)
    ```

    """

    DOMAIN = 'https://api.pentadatainc.com'
    LOGIN = 'subscribers/login'
    REFRESH = 'subscribers/refresh'
    DELTA = 5

    def __init__(self, email: str, api_key: str):
        """Initialize a PentaApi object.

        :param email: (str) Verified subscriber email.
        :param api_key: (str) Api key for the subscriber.
        """
        self.email = email
        self.api_key = api_key
        self.token = None
        self.expires = None
        self.refresh_token = None
        self.refresh_expires = None
        self._login()

    def _login(self):
        headers = {'Content-type': 'application/json'}
        payload = {'email': self.email, 'api_key': self.api_key}
        url = urljoin(PentaApi.DOMAIN, PentaApi.LOGIN)
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            self.token = data['token']
            self.expires = data['expires']
            self.refresh_token = data['refresh_token']
            self.refresh_expires = data['refresh_expires']
        else:
            raise ValueError('Credentials not valid')

    def _refresh(self):
        if self._is_refresh_expired():
            # log in again
            self._login()
        else:
            # use /refresh endpoint
            url = urljoin(PentaApi.DOMAIN, PentaApi.REFRESH)
            tok = self.refresh_token
            headers = {'Authorization': f'Bearer {tok}'}
            response = requests.post(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                self.token = data['token']
                self.expires = data['expires']
            else:
                raise ValueError('Cannot refresh JWT')

    def _is_expired(self):
        expiration = datetime.strptime(self.expires, '%Y%m%d%H%M%S')
        now = datetime.utcnow()
        delta = timedelta(seconds=PentaApi.DELTA)
        if expiration < now:
            return True
        return expiration - now < delta

    def _is_refresh_expired(self):
        expiration = datetime.strptime(self.refresh_expires, '%Y%m%d%H%M%S')
        now = datetime.utcnow()
        delta = timedelta(seconds=PentaApi.DELTA)
        if expiration < now:
            return True
        return expiration - now < delta

    def _request(self, method, *args, **kwargs):
        if self._is_expired():
            self._refresh()
        if 'headers' in kwargs:
            kwargs['headers']['Authorization'] = f'Bearer {self.token}'
            kwargs['headers']['Content-type'] = 'application/json'
        else:
            kwargs['headers'] = {'Authorization': f'Bearer {self.token}'}
            kwargs['headers']['Content-type'] = 'application/json'
        return requests.request(method, *args, **kwargs)

    def get(self, *args, **kwargs):
        """GET method"""
        return self._request('GET', *args, **kwargs)

    def post(self, *args, **kwargs):
        """POST method"""
        return self._request('POST', *args, **kwargs)

    def put(self, *args, **kwargs):
        """PUT method"""
        return self._request('PUT', *args, **kwargs)

    def delete(self, *args, **kwargs):
        """DELETE method"""
        return self._request('DELETE', *args, **kwargs)
