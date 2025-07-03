#!/usr/bin/env python3

from configparser import ConfigParser
import os
import re
import glob
import json
import argparse
import yaml
import subprocess as subp
import warnings


def runcmd(cmd=str, timeout=5):
    ret = subp.run(cmd, shell=True, stdout=subp.PIPE,
                   stderr=subp.PIPE, encoding="utf-8",
                   timeout=timeout)
    return ret


def shellcheck_for_cmd_str(cmdstr=str, shellname="bash"):
    shellcheckexe = "/usr/bin/shellcheck"
    if not os.path.exists(shellcheckexe):
        warnings.warn("Can't find the shellcheck execute path under \
                      /usr/bin, Please install the shellcheck, \
                      if you want to do this check.", Warning)
        return False

    shell_list = ["sh", "bash", "dash", "ksh"]
    if shellname not in shell_list:
        raise ValueError(f"Invalid shell name. \
                         Expected one of: {shell_list}")
    tmp_file = "./tmp.sh"
    if os.path.exists(tmp_file):
        os.remove(tmp_file)
    with open(tmp_file, "w", encoding="utf-8") as tmp_f:
        tmp_f.write(cmdstr)
    cmd = f"{shellcheckexe} -s {shellname} {tmp_file}"
    ret = runcmd(cmd)
    out = ret.stdout
    if ret.returncode == 0:
        print("Shellcheck: Pass")
        os.remove(tmp_file)
        return True
    msg = f"Shellcheck: Fail\nPlease check the file: {tmp_file}\n\
Detail:\n{out}\n"
    warnings.warn(msg, Warning)
    return False


class ConfigOperation():
    def __init__(self, delimiters=("=",), optionform=str):
        self.config_object = ConfigParser(delimiters=delimiters)
        self.config_object.optionxform = optionform

    def merge_with_file(self, file_path, import_file_type="conf",
                        json_conf_section_name="manifest"):
        file_type_list = ["conf", "json", ".conf", ".json"]
        if import_file_type not in file_type_list:
            raise ValueError(f"Invalid file type. \
                             Expected one of: {file_type_list}")
        if os.path.exists(file_path):
            real_file_type = os.path.splitext(file_path)[1]
            if real_file_type == "":
                file_type = import_file_type
            else:
                if real_file_type not in file_type_list:
                    raise ValueError(f"Invalid file type. \
                                     Expected one of: {file_type_list}")
                file_type = real_file_type

            if file_type in ("conf", ".conf"):
                self.config_object.read(file_path)
            elif file_type in ("json", ".json"):
                with open(file_path, "r", encoding="utf-8") as file:
                    conf_dict = json.load(file)
                conf_dict = {json_conf_section_name: conf_dict}
                self.merge_with_dict(conf_dict)
            else:
                raise ValueError("It shouldn't be here ...")
        else:
            raise ValueError(f"File not exist: {file_path}")

    def merge_with_dict(self, dict_content):
        sections = dict_content.keys()
        for section in sections:
            if self.config_object.has_section(section) is False:
                self.config_object.add_section(section)
        for section in sections:
            inner_dict = dict_content[section]
            fields = inner_dict.keys()
            for field in fields:
                value = inner_dict[field]
                self.config_object.set(section, field, str(value))

    def remove_section_value(self, section_name, key):
        if self.config_object.has_section(section_name):
            self.config_object.remove_option(section_name, key)

    def update_section_value(self, section_name, key, value):
        self.config_object.set(section_name, key, str(value))

    def generate_config_file(self, file_path="./final_launcher",
                             execute_path="/usr/bin/env checkbox-cli"):
        if os.path.exists(file_path):
            os.remove(file_path)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(f"#!{execute_path}\n")
            self.config_object.write(file)
        with open(file_path, "r+", encoding="utf-8") as file:
            file.seek(0, os.SEEK_END)
            pos = file.tell() - 1
            while pos > 0 and file.read(1) != "\n":
                pos -= 1
                file.seek(pos, os.SEEK_SET)
            if pos > 0:
                file.seek(pos, os.SEEK_SET)
                file.truncate()


class YamlGenerator:
    def __init__(self, default_yaml_file_path="./template/template.yaml"):
        if os.path.exists(default_yaml_file_path):
            with open(default_yaml_file_path, "r", encoding="utf-8") as file:
                self.yaml_dict = yaml.load(file, Loader=yaml.SafeLoader)
        else:
            self.yaml_dict = {}

    def yaml_update_field(self, input_dict):
        self.yaml_dict.update(input_dict)

    def yaml_remove_field(self, field_name):
        if field_name in self.yaml_dict:
            self.yaml_dict.pop(field_name)

    def generate_yaml_file(self, file_path="./final_testflinger.yaml"):
        def str_presenter(dumper, data):
            if data.count('\n') > 0:
                return dumper.represent_scalar('tag:yaml.org,2002:str',
                                               data, style='|')
            return dumper.represent_scalar('tag:yaml.org,2002:str', data)
        yaml.representer.SafeRepresenter.add_representer(str, str_presenter)
        if os.path.exists(file_path):
            os.remove(file_path)
        with open(file_path, "w", encoding="utf-8") as file:
            yaml.safe_dump(data=self.yaml_dict, stream=file)


class CheckboxLauncherBuilder(ConfigOperation):
    def __init__(self, template_folder="./template/launcher_config"):
        super().__init__(delimiters=("=",), optionform=str)
        launcher_template_list = glob.glob(f"{template_folder}/*.conf")
        if len(launcher_template_list) == 0:
            raise ValueError(f"Couldn't find the .conf file under launcher \
                                template folder: {template_folder}")
        for file in launcher_template_list:
            self.merge_with_file(file, "conf")

    def merge_manifest_json(self, json_file_path):
        if os.path.exists(json_file_path):
            self.merge_with_file(json_file_path, "json", "manifest")

    def merge_checkbox_conf(self, conf_path):
        if os.path.exists(conf_path):
            self.merge_with_file(conf_path, "conf")

    def set_test_plan(self, test_plan_name="client-cert-desktop-20-04-auto"):
        if "com.canonical.certification" not in test_plan_name:
            test_plan_name = f"com.canonical.certification::{test_plan_name}"
        self.update_section_value("test plan", "unit", test_plan_name)

    def set_exclude_job(self, exclude_job_pattern_str=""):
        if not exclude_job_pattern_str:
            self.remove_section_value("test selection", "exclude")
            return
        self.update_section_value("test selection", "exclude",
                                  exclude_job_pattern_str)


class TestCommandGenerator(CheckboxLauncherBuilder):
    default_session_desc = "CE-QA-PC_Test"

    def __init__(self, template_bin_folder="./template/shell_scripts/",
                 launcher_temp_folder="./template/launcher_config"):
        super().__init__(template_folder=launcher_temp_folder)
        # self.shell_file_list = glob.glob(f"{template_bin_folder}/*")
        self.bin_folder = template_bin_folder
        self.shell_file_list = [f"{template_bin_folder}/{f}"
                                for f in os.listdir(f"{self.bin_folder}/")
                                if re.search(r'^(\d{2}).*', f)]
        self.shell_file_list.sort()

    def build_launcher(self, manifest_json_path, checkbox_conf_path,
                       test_plan_name, exclude_job_pattern_str,
                       file_path="./final_launcher",
                       execute_path="/usr/bin/env checkbox-cli",
                       need_manifest=True):
        self.set_test_plan(test_plan_name)
        self.set_exclude_job(exclude_job_pattern_str)
        if need_manifest:
            self.merge_manifest_json(json_file_path=manifest_json_path)
        self.merge_checkbox_conf(conf_path=checkbox_conf_path)
        self.generate_config_file(file_path=file_path,
                                  execute_path=execute_path)

    def generate_test_cmd(self, manifest_json_path, checkbox_conf_path,
                          test_plan_name, exclude_job_pattern_str,
                          is_distupgrade=False, checkbox_type="deb",
                          is_runtest=True, need_manifest=True,
                          session_desc=default_session_desc):
        if checkbox_type not in ["deb", "snap"]:
            raise ValueError(f"Checkbox type is not valid. \
                              Expected one of: {checkbox_type}")
        cmd_str = ""
        for file in self.shell_file_list:
            if "Install_checkbox" in os.path.basename(file):
                if checkbox_type not in os.path.basename(file):
                    continue
            if os.path.basename(file) == "90_start_test" and\
                    is_runtest is False:
                continue
            if os.path.basename(file) == "01_dist_upgrade" and\
                    is_distupgrade is False:
                continue

            if os.path.basename(file) == "90_start_test":
                launcher_file_path = "final_launcher"
                self.build_launcher(manifest_json_path,
                                    checkbox_conf_path,
                                    test_plan_name,
                                    exclude_job_pattern_str,
                                    launcher_file_path,
                                    "/usr/bin/env checkbox-cli",
                                    need_manifest)

                with open(launcher_file_path, "r", encoding="utf-8") as l_file:
                    lines = l_file.readlines()
                    cmd_str += "cat <<EOF > checkbox-launcher\n"
                    for line in lines:
                        cmd_str += line
                    cmd_str += "\n"
                    cmd_str += "EOF\n"
            with open(file, "r", encoding="utf-8") as f_file:
                content = f_file.read().strip()
                if content:
                    if (
                        self.default_session_desc != session_desc
                        and f'SESSION_DESC="{self.default_session_desc}"'
                        in content
                    ):
                        content = content.replace(
                            f'SESSION_DESC="{self.default_session_desc}"',
                            f'SESSION_DESC="{session_desc}"'
                        )
                    cmd_str += f"{content}\n"
        lines = cmd_str.split("\n")
        cmd_str = "\n".join([line for line in lines if line.strip("\n") != ""])
        ret_sc = shellcheck_for_cmd_str(cmd_str)
        if not ret_sc:
            msg = f"Shellcheck fail after combining the file under \
{self.bin_folder}"
            warnings.warn(msg, Warning)
        return cmd_str


class TFYamlBuilder(YamlGenerator, TestCommandGenerator):
    def __init__(self, cid, default_yaml_file_path="./template/template.yaml",
                 globaltimeout=43200, outputtimeout=3600,
                 template_bin_folder="./template/shell_scripts/",
                 launcher_temp_folder="./template/launcher_config/",
                 is_runtest=True, need_manifest=True, is_distupgrade=False):
        YamlGenerator.__init__(self,
                               default_yaml_file_path=default_yaml_file_path)
        TestCommandGenerator.__init__(self, template_bin_folder,
                                      launcher_temp_folder)
        self.yaml_update_field({"global_timeout": globaltimeout})
        self.yaml_update_field({"output_timeout": outputtimeout})
        self.yaml_update_field({"job_queue": cid})
        self.is_runtest = is_runtest
        self.need_manifest = need_manifest
        self.is_distupgrade = is_distupgrade

    def provision_setting(self, is_provision, image="desktop-22-04-2-uefi",
                          provision_type="distro", provision_token="",
                          provision_auth_keys="", provision_user_data=""):
        if not is_provision:
            self.yaml_remove_field("provision_data")
            return
        setting_dict = {'provision_data': {provision_type: image}}

        # additional parameters if use oem_autoinstall connector
        attachments = []
        if provision_user_data:
            setting_dict['provision_data']['user_data'] = provision_user_data
            attachments.append({'local': provision_user_data})
        if provision_token:
            setting_dict['provision_data']['token_file'] = provision_token
            attachments.append({'local': provision_token})
        if provision_auth_keys:
            setting_dict['provision_data'][
                'authorized_keys'] = provision_auth_keys
            attachments.append({'local': provision_auth_keys})
        if attachments:
            setting_dict['provision_data']['attachments'] = attachments

        self.yaml_update_field(setting_dict)

    def reserve_setting(self, is_reserve, lp_username, timeout=120):
        if not is_reserve:
            self.yaml_remove_field("reserve_data")
            return
        setting_dict = {'reserve_data': {'timeout': timeout,
                                         'ssh_keys': [f"lp:{lp_username}"]}}
        self.yaml_update_field(setting_dict)

    def test_cmd_setting(self, manifest_json_path="./template/manifest.json",
                         checkbox_conf_path="./template/checkbox.conf",
                         test_plan_name="client-cert-desktop-20-04-automated",
                         exclude_job_pattern_str="",
                         checkbox_type="deb", session_desc="CE-QA-PC_Test"):
        test_cmds_str = self.generate_test_cmd(manifest_json_path,
                                               checkbox_conf_path,
                                               test_plan_name,
                                               exclude_job_pattern_str,
                                               self.is_distupgrade,
                                               checkbox_type,
                                               self.is_runtest,
                                               self.need_manifest,
                                               session_desc)
        setting_dict = {'test_data': {'test_cmds': test_cmds_str}}
        self.yaml_update_field(setting_dict)


def parse_input_arg():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(
        description='Testflinger yaml file generator',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    req_args = parser.add_argument_group('Required', )
    req_args.add_argument('-c', '--CID', type=str, required=True,
                          help='CID')
    req_args.add_argument('-o', '--outputFileName', type=str, required=True,
                          help="Set the output yaml file Name")

    opt_args = parser.add_argument_group("general options")
    opt_args.add_argument('--outputFolder', type=str, default="./",
                          help='Set the output folder path')
    opt_args.add_argument('--dist-upgrade', action='store_true',
                          help="Set to allow the dist-upgrade before \
                          run checkbox test")
    opt_args.add_argument('--testplan', type=str, default="",
                          help="Set the checkbox test plan name. \
                          If didn\'t set this will not run checkbox test")
    opt_args.add_argument('--excludeJobs', type=str, default="",
                          help='Set the exclude jobs pattern. \
                          ie".*memory/memory_stress_ng".')
    opt_args.add_argument("--sessionDesc", type=str,
                          default="CE-QA-PC_Test",
                          help="Set the session description")
    opt_args.add_argument('--checkboxType', choices=["deb", "snap"],
                          default="deb",
                          help="Set which checkbox type you need to \
                          install and test.")
    opt_args.add_argument('--provisionType', choices=["distro", "url"],
                          default="distro", help='Set the provision type')
    opt_args.add_argument('--provisionImage', type=str, default="",
                          help='The provision image. \
                          ie, desktop-22-04-2-uefi. \
                          If didn\'t set this mean no provision')
    opt_args.add_argument('--provisionToken', default="", type=str,
                          help='Optional file with username and token \
                          when image URL requires authentication \
                          (i.e Jenkins artifact). This file must be \
                          in YAML format, i.e: \
                          \"username: $JENKINS_USERNAME \\n \
                          token: $JENKINS_API_TOKEN\"')
    opt_args.add_argument('--provisionUserData', default="", type=str,
                          help='user-data file for autoinstall and cloud-init \
                          provisioning. This argument is a MUST required \
                          if deploy the image using the autoinstall image \
                          (i.e. 24.04 image)')
    opt_args.add_argument('--provisionAuthKeys', default="", type=str,
                          help='ssh authorized_keys file to add in \
                          provisioned system')
    opt_args.add_argument('--provisionOnly', action='store_true',
                          help='Run only provisioning without tests. \
                          Removes test_data before generating the yaml.')
    opt_args.add_argument('--globalTimeout', type=int, default=43200,
                          help="Set the testflinger's global timeout. \
                          Max:43200")
    opt_args.add_argument('--outputTimeout', type=int, default=9000,
                          help='Set the output timeout if the DUT didn\'t \
                          response to server, it will be forced closed \
                          this job. It should be set under the global \
                          timeout.')

    opt_launcher = parser.add_argument_group("Launcher settion  options")
    opt_launcher.add_argument("--manifestJson", type=str,
                              default=f"{script_dir}/template/manifest.json",
                              help="Set the manifest json file to build \
                              the launcher.")
    opt_launcher.add_argument("--needManifest", action="store_true",
                              help="Set if need the Manifest.")
    opt_launcher.add_argument("--no-needManifest", dest="needManifest",
                              action="store_false")
    opt_launcher.set_defaults(needManifest=True)
    opt_launcher.add_argument("--checkboxConf", type=str,
                              default=f"{script_dir}/template/checkbox.conf",
                              help="Set the checkbox configuration file to \
                              build the launcher.")
    opt_launcher.add_argument("--LauncherTemplate", type=str,
                              default=(
                                f"{script_dir}/template/launcher_config/"
                              ),
                              help="Set the launcher template folder")
    opt_tfyaml = parser.add_argument_group("Testflinger yaml options")
    opt_tfyaml.add_argument("--LpID", type=str, default="",
                            help="If you want to reserve the DUT, please \
                            input your Launchpad ID")
    opt_tfyaml.add_argument("--reserveTime", type=int, default=1200,
                            help="Set the timeout (sec) for reserve.")
    opt_tfyaml.add_argument("--TFYamlTemplate", type=str,
                            default=f"{script_dir}/template/template.yaml",
                            help="Set the testflinger template yaml file")

    opt_shell = parser.add_argument_group("Test command in testflinger yaml")
    opt_shell.add_argument(
        "--binFolder", type=str,
        default=f"{script_dir}/template/shell_scripts/",
        help="Set the testflinger test command folder",
    )

    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_input_arg()
    reserve, provision, runtest, distupgrade = True, True, True, False
    if not args.LpID:
        reserve = False
    if not args.provisionImage:
        provision = False
    if not args.testplan:
        runtest = False
    if args.dist_upgrade:
        distupgrade = True

    if os.path.splitext(args.outputFileName)[-1] in [".yaml", ".yml"]:
        TF_yaml_file_path = f"{args.outputFolder}/{args.outputFileName}"
    else:
        TF_yaml_file_path = f"{args.outputFolder}/{args.outputFileName}.yaml"

    builder = TFYamlBuilder(cid=args.CID,
                            default_yaml_file_path=args.TFYamlTemplate,
                            globaltimeout=args.globalTimeout,
                            outputtimeout=args.outputTimeout,
                            template_bin_folder=args.binFolder,
                            launcher_temp_folder=args.LauncherTemplate,
                            is_runtest=runtest,
                            need_manifest=args.needManifest,
                            is_distupgrade=distupgrade)

    builder.provision_setting(is_provision=provision,
                              image=args.provisionImage,
                              provision_type=args.provisionType,
                              provision_token=args.provisionToken,
                              provision_user_data=args.provisionUserData,
                              provision_auth_keys=args.provisionAuthKeys)
    if args.provisionOnly:
        # remove test and reserve stages that were added by default
        builder.yaml_remove_field("test_data")
        builder.yaml_remove_field("reserve_data")
    else:
        builder.reserve_setting(is_reserve=reserve,
                                lp_username=args.LpID,
                                timeout=args.reserveTime)

        builder.test_cmd_setting(manifest_json_path=args.manifestJson,
                                 checkbox_conf_path=args.checkboxConf,
                                 test_plan_name=args.testplan,
                                 exclude_job_pattern_str=args.excludeJobs,
                                 checkbox_type=args.checkboxType,
                                 session_desc=args.sessionDesc)

    builder.generate_yaml_file(file_path=TF_yaml_file_path)
