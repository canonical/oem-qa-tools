import requests
import json
import os
import pathlib
from dataclasses import dataclass, asdict
from enum import Enum

from C3.utils.logging_utils import init_logger, get_logger
# logger
init_logger()
logger = get_logger(__name__)

C3_DIR_PATH = os.path.split(pathlib.Path(__file__).parent.resolve())[0]
CONF_DIR_PATH = os.path.join(C3_DIR_PATH, 'configs')


class TaipeiLocation(Enum):
    """ The location string from C3
    """
    TEL_L1 = 'Taipei Eongher - Lab-1'
    TEL_L2 = 'Taipei Eongher - Lab-2'
    TEL_L3 = 'Taipei Eongher - Lab-3'
    TEL_L4 = 'Taipei Eongher - Lab-4'
    TEL_L5 = 'Taipei Eongher - Lab-5'
    TEL_L6 = 'Taipei Eongher - Lab-6'
    TEL_L7 = 'Taipei Eongher - Lab-7'
    TEL_OFFICE = 'Taipei Eongher - Lab - Office'
    TAIPEI_OFFCIE = 'Taipei Office'


@dataclass
class DUTPayloadAttrs:
    """ As request payload and be used to update the DUT.

        e.g. DUTPayloadAttrs({'holder': '<launchpad_id>'})
    """
    holder: str = None
    location: TaipeiLocation = None
    holder: str = None
    location: str = None
    canonical_contact: str = None
    date_received: str = None
    hardware_build: str = None
    project_name: str = None
    serial_number: str = None
    status: str = None


class C3API:
    def __init__(self, base_url=''):
        with open(os.path.join(CONF_DIR_PATH, 'api_token.json')) as f:
            self._api_token = json.load(f)

        self._base_url = base_url if base_url else \
            'https://certification.canonical.com/api/v1/hardware'

    @property
    def base_url(self):
        return self._base_url

    @property
    def api_token(self):
        return self._api_token

    def _request(self, http_method='GET', url='', params={}, payload={}):
        """ Wrapper for requests
        """
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'ApiKey {}:{}'.format(
                self._api_token['launchpad_id'],
                self._api_token['api_token']
            )
        }

        try:
            payload = json.dumps(payload)
            response = requests.request(
                http_method,
                url,
                params=params,
                data=payload,
                headers=headers
            )
            if response.status_code < 200 or response.status_code > 299:
                response.raise_for_status()
        except Exception as e:
            logger.error(e)
            logger.error('*' * 50)
            logger.error('params: {}'.format(params))
            logger.error('payload: {}'.format(payload))
            logger.error('*' * 50)
        finally:
            return response

    def _update_dut(self, cid, payload):
        """ Update DUT information
        """
        api_endpoint = '{}/{}/inventory/'.format(
            self._base_url, cid)
        response = self._request(
            http_method='PATCH', url=api_endpoint, payload=payload)
        return response

    def get_dut_by_cid(self, cid, format='json'):
        """ Get one DUT information by CID
        """
        params = {'format': format, 'canonical_id': cid}
        response = self._request(url=self._base_url, params=params)
        return response

    def update_dut(self, cid, payload):
        """ Update the information of specific DUT by CID
        """
        # To dictionary and filter None attrs
        f_payload = asdict(
            DUTPayloadAttrs(**payload),
            dict_factory=lambda x: {k: v for (k, v) in x if v is not None}
        )
        response = self._update_dut(cid, payload=f_payload)
        return response
