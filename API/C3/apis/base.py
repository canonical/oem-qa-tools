import requests
import json
import os
import pathlib

from C3.utils.logging_utils import init_logger, get_logger
# logger
init_logger()
logger = get_logger(__name__)

C3_DIR_PATH = os.path.split(pathlib.Path(__file__).parent.resolve())[0]
CONF_DIR_PATH = os.path.join(C3_DIR_PATH, 'configs')


class C3API:
    def __init__(self):
        with open(os.path.join(CONF_DIR_PATH, 'c3_conf.json')) as f:
            self._base_url = json.load(f)['site_url']

        with open(os.path.join(CONF_DIR_PATH, 'api_token.json')) as f:
            self._api_token = json.load(f)

    @property
    def base_url(self):
        return self._base_url

    @property
    def api_token(self):
        return self._api_token

    def _request(self, http_method='GET', url='', payload={}):
        """ Wrapper for requests
        """

        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'ApiKey {}:{}'.format(
                self._api_token['launchpad_name'],
                self._api_token['api_token']
            )
        }

        try:
            payload = json.dumps(payload)
            response = requests.request(
                http_method,
                url,
                data=payload,
                headers=headers
            )
            if response.status_code < 200 or response.status_code > 299:
                response.raise_for_status()
        except Exception as e:
            logger.error(e)
            logger.error('*' * 50)
            logger.error(payload)
            logger.error('*' * 50)
        finally:
            return response

    def _update_dut(self, cid, payload):
        """ Update DUT information
        """
        api_endpoint = "{}/{}/inventory".format(
            self._base_url, cid)
        response = self._request("PATCH", url=api_endpoint, payload=payload)
        return response

    def get_dut_by_cid(self, cid, format='json'):
        """ Get one DUT information by CID
        """
        url_params = 'format={}&canonical_id={}'.format(
            format, cid
        )
        api_endpoint = '{}?{}'.format(
            self._base_url, url_params)
        response = self._request(url=api_endpoint)
        return response

    def update_dut_holder(self, cid, holder_launchpad_id):
        """ Update the holder of specific DUT by CID
        """
        payload = {
            'holder': holder_launchpad_id
        }
        response = self._update_dut(cid, payload=payload)
        return response
