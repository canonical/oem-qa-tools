import re
import json
import logging
from datetime import datetime
from Google.google_sheet_api import GoogleSheetOperator


LP_BUG_URL = "https://bugs.launchpad.net/{}/+bugs?field.tag={}"
LOWER_KEYS = ["platform_tag", "status"]


class MD_PLATFORM_RECORD():

    def __init__(self):
        self._platform_name = ""
        self._platform_tag = ""
        self._status = ""
        self._pm = ""
        self._fe = ""
        self._swe = ""
        self._qa = ""
        self._bug_link = ""

    @property
    def platform_name(self):
        return self._platform_name

    @platform_name.setter
    def platform_name(self, value):
        self._platform_name = value

    @property
    def platform_tag(self):
        return self._platform_tag

    @platform_tag.setter
    def platform_tag(self, value):
        self._platform_tag = value

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value

    @property
    def pm(self):
        return self._pm

    @pm.setter
    def pm(self, value):
        self._pm = value

    @property
    def fe(self):
        return self._fe

    @fe.setter
    def fe(self, value):
        self._fe = value

    @property
    def swe(self):
        return self._swe

    @swe.setter
    def swe(self, value):
        self._swe = value

    @property
    def bug_link(self):
        return self._bug_link

    @bug_link.setter
    def bug_link(self, value):
        self._bug_link = value

    @property
    def request(self):
        return self._request

    @request.setter
    def request(self, value):
        self._request = value

    @property
    def start_date(self):
        return self._start_date

    @start_date.setter
    def start_date(self, value):
        self._start_date = value

    @property
    def end_date(self):
        return self._end_date

    @end_date.setter
    def end_date(self, value):
        self._end_date = value

    @staticmethod
    def _validate_time_format(value):
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return value
        except Exception as err:
            # logging.warning("Incorrect time format: %s", value)
            return ""

    @staticmethod
    def _expand_mapping(tmp_mapping):
        if isinstance(tmp_mapping, dict):
            mapping = [
                tmp for tmp in tmp_mapping.values() if isinstance(tmp, str)]
            [mapping.extend(tmp) for tmp in
                tmp_mapping.values() if isinstance(tmp, list)]
        else:
            raise ValueError("Unacceptable sheet mapping format!")
        return mapping

    @classmethod
    def _create_record_object(cls, data, mapping):
        obj = cls()
        for key, pattern in mapping.items():
            if isinstance(pattern, str):
                value = data.get(pattern)
            elif isinstance(pattern, list):
                value = []
                for tmp in pattern:
                    _value = data.get(tmp, "")
                    if key in ["start_date", "end_date"]:
                        _value = cls._validate_time_format(_value)
                    value.append(_value)
            else:
                raise ValueError("Unsupported pattern format")

            if key in LOWER_KEYS and value and isinstance(value, str):
                value = value.strip().lower()
            setattr(obj, key, value)
        return obj


class SOMERVILLE_PLATFORM_RECORD(MD_PLATFORM_RECORD):
    project_name = "somerville"

    @classmethod
    def rts_mapping(cls):
        mapping = {
            "platform_name": "Platform",
            "product_name": "Product Name\n(SMBIOS)",
            "platform_tag": "Launchpad\nTag",
            "status": "Stage",
            "pm": "Canonical\nPM",
            "swe": "Canonical\nEng",
            "fe": "Canonical \nFE",
            "qa": "IEV Full QA",
            "start_date": ["IEV Full to QA", "IEV Reg to QA", "FV Reg to QA"],
            "end_date": [
                "IEV Full Report", "IEV Reg\nReport", "FV Reg Report"
            ]
        }

        return mapping

    @classmethod
    def prts_mapping(cls):
        mapping = {
            "platform_name": "Platform",
            "request": "Request",
            "request_date": "Request\nDate",
            "platform_tag": "Launchpad\nTag",
            "status": "Stage",
            "pm": "Canonical\nPM",
            "swe": "Canonical\nEng",
            "fe": "Canonical \nFE",
            "qa": "IEV Full QA",
            "start_date": ["IEV Full to QA", "IEV Reg to QA", "FV Reg to QA"],
            "end_date": [
                "IEV Full Report", "IEV Reg\nReport", "FV Reg Report"
            ]
        }

        return mapping

    @classmethod
    def online_update_mapping(cls):
        return cls.prts_mapping()

    @classmethod
    def generate_record(cls, data, record_type):
        if record_type == "rts":
            mapping = cls.rts_mapping()
        elif record_type == "prts":
            mapping = cls.prts_mapping()
        elif record_type == "online udpate":
            mapping = cls.online_update_mapping()
        else:
            raise ValueError(f"Unexpected record type: {record_type}")

        obj = cls._create_record_object(data, mapping)
        check_data = [
            obj.platform_name,
            obj.platform_tag,
            obj.status
        ]
        if record_type in ["prts", "online update"]:
            check_data.append(obj.request)
        if obj.status == "canceled":
            return None
        elif obj.status in ["in-flight", "delivered"] and not all(check_data):
            raise ValueError(f"Primary values not available: {obj.__dict__}")

        bug_pattern = obj.platform_tag or "TBD"
        setattr(obj, "bug_link",
                LP_BUG_URL.format(obj.project_name, bug_pattern))

        return obj


class STELLA_PLATFORM_RECORD(MD_PLATFORM_RECORD):
    project_name = "stella"

    @classmethod
    def rts_mapping(cls):
        mapping = {
            "platform_name": "Code Name",
            "product_name": "Platform",
            "platform_tag": "Platform Code Name",
            "status": "Status",
            "pm": "Canonical PM",
            "swe": "Canonical Eng",
            "qa": "Canonical QA",
            "rts_stage": "Pre/Post-RTS?",
            "lp_tag": "LP tag",
            "start_date": ["M1 QA", "M2 QA", "M3 QA"],
        }

        return mapping

    @classmethod
    def generate_record(cls, data):
        mapping = cls.rts_mapping()
        obj = cls._create_record_object(data, mapping)
        check_data = [
            obj.platform_name,
            obj.platform_tag,
            obj.status
        ]
        if obj.status == "canceled":
            return None
        elif obj.status in ["in-flight", "delivered"] and not all(check_data):
            raise ValueError(f"Primary values not available: {obj.__dict__}")

        bug_pattern = obj.platform_tag or "TBD"
        setattr(obj, "bug_link",
                LP_BUG_URL.format(obj.project_name, bug_pattern))

        return obj


class SUTTON_PLATFORM_RECORD(MD_PLATFORM_RECORD):
    project_name = "sutton"

    @classmethod
    def rts_mapping(cls):
        mapping = {
            "platform_name": "Code Name",
            "product_name": "Platform",
            "platform_tag": "Canonical Platform Code name",
            "status": "Status",
            "swe": "Canonical Eng",
            "qa": "QA",
            "lp_tag": "Official Tag",
            "start_date": [
                "Alpha\n(Planned)", "Beta\n(Planned)", "GM (Planned)"
            ],
            "prts": "Refresh"
        }

        return mapping

    @classmethod
    def generate_record(cls, data):
        mapping = cls.rts_mapping()
        obj = cls._create_record_object(data, mapping)
        check_data = [
            obj.platform_name,
            obj.platform_tag,
            obj.status
        ]
        if obj.status == "canceled":
            return None
        elif obj.status in ["in-flight", "delivered"] and not all(check_data):
            raise ValueError(f"Primary values not available: {obj.__dict__}")

        # If refresh cell is 1, that means it's PRTS cycle
        obj.prts = True if str(obj.prts).strip() == "1" else False
        bug_pattern = obj.platform_tag or "TBD"
        setattr(obj, "bug_link",
                LP_BUG_URL.format(obj.project_name, bug_pattern))

        return obj


class MD_PC_PROJECT_BOOK():

    _allow_filter_keys = [
        "status", "platform_tag", "platform_name"
    ]

    def __init__(self):
        self.prts = []
        self.rts = []
        self.online_update = []

    def _handle_record(self, record):
        new_record = {}
        for key, value in record.__dict__.items():
            new_record.update({key.lstrip("_"): value})
        return new_record

    def _filter_record(self, record, pattern):
        """
            status.eq=in-flight
            platform.contains=fossa
            e.g.
            status.eq=in-flight&platform.contains=fossa
        """
        re_pattern = "(\w*).(\w*)=([\w -]*)"
        patterns = pattern.split("&")
        for validation in patterns:
            re_check = re.search(re_pattern, validation)
            if re_check:
                key, op, value = re_check.groups()
                if key not in self._allow_filter_keys:
                    raise KeyError("Unsupported filter keys: {key}")

                # No need to filter
                if record[key] is None:
                    return False

                if op not in ["eq", "contains"]:
                    raise KeyError("Unsupported filter operator: {op}")

                if op == "eq" and record[key] != value:
                    return False
                elif op == "contains" and record[key].find(value) == -1:
                    return False
            else:
                raise ValueError("Incorrect filter pattern format: {data}")

        return True

    def dump_to_dict(self, filters=None):

        dict_pj_book = {}
        for key, records in self.__dict__.items():
            new_records = []
            for record in records:
                if isinstance(record, MD_PLATFORM_RECORD):
                    dict_record = self._handle_record(record)
                    if filters:
                        wanted = self._filter_record(dict_record, filters)
                    else:
                        wanted = True

                    if wanted:
                        new_records.append(dict_record)
            dict_pj_book.update({key: new_records})
        return dict_pj_book

    def dump_to_json(self, filters=None):

        return json.dumps(self.dump_to_dict(filters), indent=4)


def get_somerville_platform_tracker(google_sheet_conf={}):
    somerville_project = MD_PC_PROJECT_BOOK()
    test_obj = GoogleSheetOperator()
    test_obj.prepare_sheet_obj()
    test_obj.spreadsheet = google_sheet_conf["sheet_link"]

    rts_range = google_sheet_conf["rts_range"]
    key_data = test_obj.get_range_data(rts_range, major_dimension="ROWS")
    mapping = SOMERVILLE_PLATFORM_RECORD._expand_mapping(
        SOMERVILLE_PLATFORM_RECORD.rts_mapping()
    )
    key_index = [key_data[0].index(key) for key in mapping]
    for data in key_data[2:]:
        tmp_dict = {}
        for idx, record_idx in enumerate(key_index):
            value = data[record_idx] if len(data) > record_idx else ""
            tmp_dict.update({mapping[idx]: value})
        try:
            record = SOMERVILLE_PLATFORM_RECORD.generate_record(
                                                    tmp_dict, "rts")
            somerville_project.rts.append(record)
        except ValueError as err:
            logging.warning(err)

    prts_range = google_sheet_conf["prts_range"]
    key_data = test_obj.get_range_data(prts_range, major_dimension="ROWS")
    mapping = SOMERVILLE_PLATFORM_RECORD._expand_mapping(
        SOMERVILLE_PLATFORM_RECORD.prts_mapping()
    )
    # To get online update field to identify task type
    str_online_update = "Online\nUpdate"
    mapping.append(str_online_update)

    key_index = [key_data[0].index(key) for key in mapping]
    for data in key_data[2:]:
        tmp_dict = {}
        for idx, record_idx in enumerate(key_index):
            value = data[record_idx] if len(data) > record_idx else ""
            tmp_dict.update({mapping[idx]: value})
        try:
            online_update = tmp_dict.pop(str_online_update)
            record = SOMERVILLE_PLATFORM_RECORD.generate_record(
                    tmp_dict, "prts")
            if online_update == "No":
                somerville_project.prts.append(record)
            else:
                somerville_project.online_update.append(record)
        except ValueError as err:
            logging.warning(err)

    return somerville_project


def get_stella_platform_tracker(google_sheet_conf={}):
    stella_project = MD_PC_PROJECT_BOOK()
    test_obj = GoogleSheetOperator()
    test_obj.prepare_sheet_obj()
    test_obj.spreadsheet = google_sheet_conf["sheet_link"]
    rts_range = google_sheet_conf["rts_range"]
    key_data = test_obj.get_range_data(rts_range, major_dimension="ROWS")
    mapping = STELLA_PLATFORM_RECORD._expand_mapping(
        STELLA_PLATFORM_RECORD.rts_mapping()
    )
    key_index = [key_data[0].index(key) for key in mapping]
    for data in key_data[2:]:
        tmp_dict = {}
        for idx, record_idx in enumerate(key_index):
            value = data[record_idx] if len(data) > record_idx else ""
            tmp_dict.update({mapping[idx]: value})
        try:
            record = STELLA_PLATFORM_RECORD.generate_record(tmp_dict)
            if record.rts_stage == "post":
                stella_project.prts.append(record)
            else:
                stella_project.rts.append(record)
        except ValueError as err:
            logging.warning(err)

    return stella_project


def get_sutton_platform_tracker(google_sheet_conf={}):
    sutton_project = MD_PC_PROJECT_BOOK()
    test_obj = GoogleSheetOperator()
    test_obj.prepare_sheet_obj()

    test_obj.spreadsheet = google_sheet_conf["sheet_link"]
    rts_range = google_sheet_conf["rts_range"]
    key_data = test_obj.get_range_data(rts_range, major_dimension="ROWS")
    mapping = SUTTON_PLATFORM_RECORD._expand_mapping(
        SUTTON_PLATFORM_RECORD.rts_mapping()
    )
    key_index = [key_data[0].index(key) for key in mapping]
    for data in key_data[2:]:
        tmp_dict = {}
        for idx, record_idx in enumerate(key_index):
            value = data[record_idx] if len(data) > record_idx else ""
            tmp_dict.update({mapping[idx]: value})
        try:
            record = SUTTON_PLATFORM_RECORD.generate_record(tmp_dict)
            if record.prts:
                sutton_project.prts.append(record)
            else:
                sutton_project.rts.append(record)
        except ValueError as err:
            logging.warning(err)

    return sutton_project


def read_config(config_name="google_sheet_link.json"):
    if not config_name.endswith(".json"):
        raise Exception(f"Expect JSON config file but got {config_name}")
    with open(f"./configs/{config_name}") as config_file:
        file_contents = config_file.read()
        return json.loads(file_contents)


def generate_platform_tracker(project_name):
    # Get google sheet info by reading config file
    conf = read_config()
    # Get the records by project
    if project_name == "somerville":
        obj_pj_book = get_somerville_platform_tracker(
            google_sheet_conf=conf[project_name]
        )
    elif project_name == "stella":
        obj_pj_book = get_stella_platform_tracker(
            google_sheet_conf=conf[project_name]
        )
    elif project_name == "sutton":
        obj_pj_book = get_sutton_platform_tracker(
            google_sheet_conf=conf[project_name]
        )
    else:
        raise KeyError("Unsupported project name")

    return obj_pj_book


if __name__ == "__main__":
    print(
        generate_platform_tracker(
            "sutton").dump_to_json("status.eq=in-flight")
    )
