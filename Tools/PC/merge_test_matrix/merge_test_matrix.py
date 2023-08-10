import os
import argparse
import copy
import operator
import json
import re
import tarfile
import xlsxwriter
from collections import OrderedDict


TEST_RESULT_PATTERN = r"^\S*-initial-test.json$"
TEST_MATRIX_MAPPING = OrderedDict(
    {
        "Platform Name": "Platform",
        "Configuration": "SKU",
        "BIOS": "BIOS",
        "CPU": "CPU",
        "Chipset": None,
        "Memory": "RAM",
        "Video (onboard)": "Video",
        "Video (add-on)": "Video",
        "Audio": "Audio",
        "NIC": "Ethernet",
        "Wireless": ["WiFi", "WiFi (subsystem)"],
        "Bluetooth": "BT",
        "WWAN": "WWAN",
        "Screen": "Touchscreen",
        "Touchpad": "Touchpad",
        "Webcam": "Webcam",
        "Fingerprint": "Fingerprint",
        "Disk": "Disk",
        "Other Special peipherals": None,
        "Test scope": None,
    }
)


class InitialResultParser:
    def __init__(self, data):
        self._data = data

    @property
    def platform_name(self):
        return self._data.get("Platform")

    @property
    def sku(self):
        return self._data.get("SKU")

    @property
    def bios(self):
        return self._data.get("BiosVersion")

    @property
    def cpu(self):
        return self._data.get("CPU")

    @property
    def memory(self):
        return self._data.get("RAM")

    @property
    def onboard_gpu(self):
        gpus = self._data.get("GPU")
        return gpus[0]["device"] if gpus else "N/A"

    @property
    def discrete_gpu(self):
        gpus = self._data.get("GPU")
        return gpus[1]["device"] if len(gpus) > 1 else "N/A"

    @property
    def audio(self):
        audios = self._data.get("Audio")
        if audios:
            return "\n".join(
                [f"{tmp['device']}, driver: {tmp['driver']}" for tmp in audios]
            ).strip("\n")
        else:
            return "N/A"

    @property
    def ethernet(self):
        networks = self._data.get("Ethernet")
        if networks:
            return "\n".join([f"{tmp['device']}"
                              for tmp in networks]).strip("\n")
        else:
            return "N/A"

    @property
    def wlan(self):
        wlans = self._data.get("WLAN")
        if wlans:
            return "\n".join(
                [f"{tmp['device']}\nsub_id: {tmp['sub_id']}" for tmp in wlans]
            ).strip("\n")
        else:
            return "N/A"

    @property
    def bluetooth(self):
        bts = self._data.get("Bluetooth")
        return "\n".join(tmp for tmp in bts).strip("\n") if bts else "N/A"

    @property
    def wwan(self):
        return self._data.get("WWAN")

    @property
    def fingerprint(self):
        return self._data.get("Fingerprint")

    @property
    def touchpad(self):
        touchpads = self._data.get("Touchpad")
        if touchpads:
            return "\n".join([f"{tmp['device']}"
                              for tmp in touchpads]).strip("\n")
        else:
            return "N/A"

    @property
    def touchscreen(self):
        touchscreens = self._data.get("Touchscreen")
        if touchscreens:
            return "\n".join([f"{tmp['device']}"
                              for tmp in touchscreens]).strip("\n")
        else:
            return "N/A"

    @property
    def webcam(self):
        webcams = self._data.get("Webcam")
        if webcams:
            return "\n".join(tmp for tmp in webcams).strip("\n")
        else:
            return "N/A"

    @property
    def disk(self):
        disks = self._data.get("Disk")
        if disks:
            return "\n".join(tmp for tmp in disks).strip("\n")
        else:
            return "N/A"


SUPT_BG_COLORS = [
    "cyan",
    "gray",
    "lime",
    "yellow",
    "pink",
    "orange",
    "purple",
    "silver",
    "navy",
    "blue",
    "brown",
]


class WorkbookFormater:
    def_font_name = "Arial"
    def_font_size = 10
    def_font_color = "black"
    def_bg_color = "white"
    def_bold = False
    def_border_type = 1

    def __init__(self, workbook):
        self._workbook = workbook
        # self._cell_format = None
        self._cell_format = self._get_default_format()

    def _get_default_format(self):
        # self._workbook = workbook
        cell_format = self._workbook.add_format(
            {
                "font_name": self.def_font_name,
                "font_size": self.def_font_size,
                "font_color": self.def_font_color,
                "bold": self.def_bold,
                "border": self.def_border_type,
            }
        )
        return cell_format

    def _generate_format(self, **kwargs):
        for key, value in kwargs.items():
            if key == "bold" and value:
                self._cell_format.set_bold()
            if key == "bolder":
                self._cell_format.set_border()
            if key == "font_size":
                self._cell_format.set_size(value)
            if key == "font_name":
                self._cell_format.set_font_name()
            if key == "font_color":
                self._cell_format.set_font_color(value)
            if key == "bg_color":
                self._cell_format.set_bg_color(value)
        return self._cell_format

    @classmethod
    def default_format(cls, workbook):
        return cls(workbook)._get_default_format()

    @classmethod
    def highlight_format(cls, workbook):
        return cls(workbook)._generate_format(fond_color="red")

    @classmethod
    def header_format(cls, workbook):
        return cls(workbook)._generate_format(font_size=12, bold=True)

    @classmethod
    def custom_format(
        cls,
        workbook,
        bold=def_bold,
        font_size=def_font_size,
        font_color=def_font_color,
        bg_color=def_bg_color,
    ):
        return cls(workbook)._generate_format(
            bold=bold, font_size=font_size,
            font_color=font_color, bg_color=bg_color
        )


def generate_test_matrix(test_results, filename, no_highlight):
    filename += ".xlsx"
    with xlsxwriter.Workbook(filename) as workbook:
        worksheet = workbook.add_worksheet("Platform")
        worksheet.set_column(0, 0, 25)
        worksheet.set_column(1, 10, 75)
        _maximum_height_mapping = {}

        for idx, key in enumerate(TEST_MATRIX_MAPPING.keys()):
            tmp_data_queue = {}
            tmp_color_quere = copy.deepcopy(SUPT_BG_COLORS)
            # Write row name
            row = 0
            if idx in [0, 1]:
                worksheet.write(
                    idx, row, key, WorkbookFormater.header_format(workbook)
                )
            else:
                worksheet.write(
                    idx, row, key, WorkbookFormater.default_format(workbook)
                )

            # Write data
            mapping_value = TEST_MATRIX_MAPPING.get(key)
            query_keys = (
                mapping_value if isinstance(mapping_value, list)
                else [mapping_value]
            )

            for data in test_results:
                row += 1
                values = ""
                for query_key in query_keys:
                    init_data = data.get(query_key)
                    if isinstance(init_data, str):
                        values += "\n{}".format(init_data.strip())
                    elif isinstance(init_data, list):
                        values += "\n{}".format(
                            "\n".join([_tmp.strip() for _tmp in init_data])
                        )

                values = values.strip("\n") if values else "N/A"

                if key in ["Video (onboard)", "Video (add-on)"]:
                    tmp_data = values.split("\n")
                    if key == "Video (onboard)":
                        values = tmp_data[0]
                    else:
                        values = (
                            "N/A" if len(tmp_data) == 1
                            else "\n".join(tmp_data[1:])
                        )

                if key == "Audio":
                    values = "\n".join(
                        [
                            "Audio device {}".format(i)
                            for i in values.split("Audio device")
                            if i
                        ]
                    )

                if key == "Disk":
                    # values = values.replace(" ", "\n")
                    values = "\n".join(
                        [
                            "Disk device {}".format(i)
                            for i in values.split("Disk device")
                            if i
                        ]
                    )

                # Modify cell height for multiple lines
                if values.count("\n") >= _maximum_height_mapping.get(idx, 1):
                    _maximum_height_mapping.update({idx: values.count("\n")})
                    worksheet.set_row(idx, 15 * (values.count("\n") + 1))

                if idx in [0, 1]:
                    worksheet.write(
                        idx, row, values,
                        WorkbookFormater.header_format(workbook)
                    )
                else:
                    if no_highlight:
                        worksheet.write(
                            idx, row, values,
                            WorkbookFormater.default_format(workbook)
                        )
                    else:
                        if key in [
                            "BIOS",
                            "Disk",
                            "Memory",
                            "Fingerprint",
                            "Other Special peipherals",
                            "Test scope",
                        ] or values in ["", "N/A"]:
                            bg_color = "white"
                        elif values in tmp_data_queue.keys():
                            bg_color = tmp_data_queue.get(values)
                        else:
                            if len(tmp_color_quere):
                                bg_color = tmp_color_quere.pop(0)
                            else:
                                bg_color = "white"
                            tmp_data_queue.update({values: bg_color})

                        worksheet.write(
                            idx, row, values,
                            WorkbookFormater.custom_format(workbook,
                                                           bg_color=bg_color),
                        )


def generate_test_matrix_v2(test_results, filename, no_highlight):
    filename += ".xlsx"
    with xlsxwriter.Workbook(filename) as workbook:
        worksheet = workbook.add_worksheet("Platform")
        worksheet.set_column(0, 0, 25)
        worksheet.set_column(1, 10, 50)

        titles = [
            "Platform Name",
            "Configuration",
            "BIOS",
            "CPU",
            "Chipset",
            "Memory",
            "Video (onboard)",
            "Video (add-on)",
            "Audio",
            "NIC",
            "WLAN",
            "Bluetooth",
            "WWAN",
            "Screen",
            "Touchpad",
            "Webcam",
            "Fingerprint",
            "Disk",
            "Other Special peipherals",
            "Test scope",
        ]

        for idx, key in enumerate(titles):
            # Write row name
            row = 0
            if idx in [0, 1]:
                worksheet.write(
                    idx, row, key,
                    WorkbookFormater.header_format(workbook))
                worksheet.set_row(idx, 20)
            else:
                worksheet.write(
                    idx, row, key,
                    WorkbookFormater.default_format(workbook)
                )
                worksheet.set_row(idx, 25)

        need_custom = {
            "cpu": 3,
            "onboard_gpu": 6,
            "discrete_gpu": 7,
            "audio": 8,
            "ethernet": 9,
            "wlan": 10,
            "bluetooth": 11,
            "wwan": 12,
            "touchscreen": 13,
            "touchpad": 14,
            "webcam": 15,
            "fingerprint": 16,
            "disk": 17,
        }
        tmp_data = {}

        for data in test_results:

            row += 1
            parser = InitialResultParser(data)

            worksheet.write(
                0, row, parser.platform_name,
                WorkbookFormater.header_format(workbook)
            )
            worksheet.write(
                1, row, parser.sku,
                WorkbookFormater.header_format(workbook)
            )
            worksheet.write(
                2, row, parser.bios,
                WorkbookFormater.default_format(workbook)
            )
            # Write empty data for chipset
            worksheet.write(
                4, row, "",
                WorkbookFormater.default_format(workbook))
            worksheet.write(
                5, row, parser.memory,
                WorkbookFormater.default_format(workbook)
            )
            # Write empty data for other
            worksheet.write(
                18, row, "",
                WorkbookFormater.default_format(workbook))
            # Write empty data for test scope
            worksheet.write(
                19, row, "",
                WorkbookFormater.default_format(workbook))

            if no_highlight:
                worksheet.write(
                    3, row, parser.cpu,
                    WorkbookFormater.default_format(workbook)
                )
                worksheet.write(
                    6, row, parser.onboard_gpu,
                    WorkbookFormater.default_format(workbook),
                )
                worksheet.write(
                    7, row, parser.discrete_gpu,
                    WorkbookFormater.default_format(workbook),
                )
                worksheet.write(
                    8, row, parser.audio,
                    WorkbookFormater.default_format(workbook)
                )
                worksheet.write(
                    9, row, parser.ethernet,
                    WorkbookFormater.default_format(workbook)
                )
                worksheet.write(
                    10, row, parser.wlan,
                    WorkbookFormater.default_format(workbook)
                )
                worksheet.write(
                    11, row, parser.bluetooth,
                    WorkbookFormater.default_format(workbook)
                )
                worksheet.write(
                    12, row, parser.wwan,
                    WorkbookFormater.default_format(workbook)
                )
                worksheet.write(
                    13, row, parser.touchscreen,
                    WorkbookFormater.default_format(workbook),
                )
                worksheet.write(
                    14, row, parser.touchpad,
                    WorkbookFormater.default_format(workbook)
                )
                worksheet.write(
                    15, row, parser.webcam,
                    WorkbookFormater.default_format(workbook)
                )
                worksheet.write(
                    16, row, parser.fingerprint,
                    WorkbookFormater.default_format(workbook),
                )
                worksheet.write(
                    17, row, parser.disk,
                    WorkbookFormater.default_format(workbook)
                )
            else:
                for key, index in need_custom.items():
                    value = getattr(parser, key)
                    if value == "N/A" or value == "":
                        worksheet.write(
                            index, row, value,
                            WorkbookFormater.default_format(workbook)
                        )
                    else:
                        if tmp_data.get(key) is None:
                            tmp_data.update(
                                {key: {
                                    "color_queue":
                                    copy.deepcopy(SUPT_BG_COLORS),
                                    "values": [],
                                }}
                            )
                        if value not in tmp_data[key]["values"]:
                            tmp_data[key]["values"].append(value)
                        color_index = tmp_data[key]["values"].index(value)
                        bg_color = tmp_data[key]["color_queue"][color_index]
                        worksheet.write(
                            index, row, value,
                            WorkbookFormater.custom_format(workbook,
                                                           bg_color=bg_color),
                        )


def _collect_test_results(folder_path, extension):
    compress_files = os.listdir(folder_path)
    initial_results = []
    for cfile in compress_files:
        if cfile.endswith(extension):
            with tarfile.open(
                os.path.sep.join([folder_path, cfile]), mode="r:gz"
            ) as so:
                print("\nChecking the content in {} tarball".format(cfile))
                for filename in so.getmembers():
                    expected_file = re.search(TEST_RESULT_PATTERN,
                                              filename.name)
                    if expected_file:
                        print("Loading initial test result from"
                              "{}".format(filename))
                        data = json.loads(so.extractfile(filename).read())
                        initial_results.append(data)
        else:
            print(
                "the extension file name is not expected. tarbal: "
                "{}".format(cfile)
            )

    return sorted(initial_results, key=operator.itemgetter("SKU"))


def _register_arguments():

    description = "This utiltiy is generate the test matrix \
                   from initial test results."
    parser = argparse.ArgumentParser(
        description=description, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("-p", "--path", type=str, default=os.getcwd())
    parser.add_argument("-fe", "--file-extension", type=str, default=".tar.gz")
    parser.add_argument("-o", "--output", type=str, default="test_matrix")
    parser.add_argument("--no-highlight", action="store_true", default=False)
    parser.add_argument("--old-format", action="store_true", default=False)

    return parser.parse_args()


def main():
    args = _register_arguments()
    path = (
        args.path
        if os.path.isabs(args.path)
        else os.path.sep.join([os.getcwd(), args.path])
    )
    print(path)
    test_results = _collect_test_results(path, args.file_extension)
    if args.old_format:
        generate_test_matrix(test_results, args.output, args.no_highlight)
    else:
        generate_test_matrix_v2(test_results, args.output, args.no_highlight)


if __name__ == "__main__":
    main()
