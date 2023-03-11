import os
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials


SERVICE_ACCOUNT_FILE = "service-account-key.json"
CREDENTIAL_FILE = "credentials.json"
TOKEN_FILE = "token.json"
API_ACCOUNT_TYPE = os.environ.get("GOOGLE_API_ACCOUNT_TYPE")


class GoogleSheetOperator():
    DEFAULT_API_TYPE = "service-account"
    def __init__(self):
        self._sheet_obj = None
        self._spreadsheet_id = None
        self._api_type = API_ACCOUNT_TYPE or self.DEFAULT_API_TYPE
        print(f"current api type: {self._api_type}")

    @property
    def spreadsheet(self):
        return self._spreadsheet_id

    @spreadsheet.setter
    def spreadsheet(self, value):
        self._spreadsheet_id = value

    def _prepare_credential(self):

        if self._api_type == "service-account":
            cred = service_account.Credentials.from_service_account_file(
                        filename = SERVICE_ACCOUNT_FILE)
        elif self._api_type == "user-account":
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            if os.path.exists(TOKEN_FILE):
                cred = Credentials.from_authorized_user_file(
                    TOKEN_FILE, scopes
                )

            if cred and cred.valid and cred.expired and cred.refresh_token:
                cred.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIAL_FILE, scopes
                )
            cred = flow.run_local_server(port=0)

            with open(TOKEN_FILE, 'w') as token_fp:
                token_fp.write(cred.to_json())
        else:
            raise SystemError(
                    f"Unsupported API account type: {self._api_type}")

        return cred

    def prepare_sheet_obj(self):
        credential = self._prepare_credential()
        service = build('sheets', 'v4', credentials=credential)
        self._sheet_obj = service.spreadsheets()

    def _check_service(self):
        return all([self._sheet_obj, self.spreadsheet])

    def get_range_data(self, data_range: str, major_dimension: str="ROWS"):
        if self._check_service():
            result = self._sheet_obj.values().get(
                        spreadsheetId=self.spreadsheet,
                        range=data_range,
                        majorDimension=major_dimension).execute()
            return result.get("values", [])

    def update_range_data(self, data_range: str, values: list,
                          input_option: str="USER_ENTERED"):
        if self._check_service():
            req_body = {
                "valueInputOption": input_option,
                "data": [{"range": data_range, "values": values}]
            }
            result = self._sheet_obj.values().batchUpdate(
                spreadsheetId=self.spreadsheet,
                body=req_body).execute()
            print(result)

    def insert_empty_rows(self,
                          sheet_id: int,
                          start_index: int,
                          num: int=1):
        if self._check_service():
            req_body = {
                "requests": [
                    {
                        "insertDimension": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "ROWS",
                                "startIndex": start_index,
                                "endIndex": start_index + num
                            }
                        }
                    }
                ]
            }
            result = self._sheet_obj.batchUpdate(
                spreadsheetId=self.spreadsheet,
                body=req_body).execute()
            print(result)

    def insert_empty_columns(self, sheet_id: int,
                             start_index: int, num: int=1):
        if self._check_service():
            req_body = {
                "requests": [
                    {
                        "insertDimension": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": start_index,
                                "endIndex": start_index + num
                            }
                        }
                    }
                ]
            }
            result = self._sheet_obj.batchUpdate(
                spreadsheetId=self.spreadsheet,
                body=req_body).execute()
            print(result)
