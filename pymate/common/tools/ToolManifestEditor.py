import os
import shutil
import traceback
from pymate.common.tool import BaseTool
from pymate.utils import fs_utils
import xml.etree.ElementTree as ET


def is_debuggable(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        if 'debuggable="true"' in content:
            return True
        else:
            return False
    except FileNotFoundError:
        print(f"The file {file_path} does not exist.")
        return False


class ToolManifestEditor(BaseTool):

    def __init__(self, input_file=None, flag_add_debuggable=False, accept_user_installed_ca_certs=False,
                 allows_private_backups=False, add_cosmo_broadcast_receiver=False, create_backup=False,
                 add_permissions=None, toggle_extract_native_libs=False):
        super().__init__(name=self.__class__.__name__,
                         description="Manifest Editor",
                         cmd=None, options={
                "input_file": input_file,
                "flag_add_debuggable": flag_add_debuggable,
                "accept_user_installed_ca_certs": accept_user_installed_ca_certs,
                "allows_private_backups": allows_private_backups,
                "create_backup": create_backup,
                "add_permissions": add_permissions,
                "toggle_extract_native_libs": toggle_extract_native_libs,
            })
        self.input_file = input_file
        self.flag_add_debuggable = flag_add_debuggable
        self.accept_user_installed_ca_certs = accept_user_installed_ca_certs
        self.allows_private_backups = allows_private_backups
        self.create_backup = create_backup
        self.add_cosmo_broadcast_receiver = add_cosmo_broadcast_receiver
        self.add_permissions = add_permissions
        self.toggle_extract_native_libs = toggle_extract_native_libs

    def before_exec(self):
        if not os.path.exists(self.input_file):
            raise RuntimeError("XmlEditor: input file is missing")

    def after_exec(self):
        if not os.path.exists(self.input_file):
            raise RuntimeError("XmlEditor: input file is missing and could not be edited")
        if self.flag_add_debuggable and not is_debuggable(self.input_file):
            raise RuntimeError("XmlEditor: input file does not have the debuggable flag after edition")

    def exec_script(self) -> (str, str):
        self.edit_manifest()
        return "", ""

    def edit_manifest(self):
        parent_dir = fs_utils.get_immediate_parent_folder(self.input_file)
        if self.create_backup:
            backup_path = os.path.join(parent_dir, 'AndroidManifest_backup.xml')
            shutil.copy(self.input_file, backup_path)
        try:
            tree = ET.parse(self.input_file)
        except Exception as e:
            tb_exception = traceback.format_exc()
            self.logger.debug(tb_exception)
            raise
        namespaces = dict([node for _, node in
                           ET.iterparse(self.input_file,
                                        events=["start-ns"])])
        for ns in namespaces:
            ET.register_namespace(ns, namespaces[ns])

        if "android" not in namespaces:
            android_namespace = 'http://schemas.android.com/apk/res/android'
            ET.register_namespace('android', android_namespace)
            android_prefix = '{' + android_namespace + '}'
        else:
            android_prefix = "{" + namespaces["android"] + "}"

        if self.allows_private_backups:
            changed_pointer = False
            for el in tree.findall("application"):
                el.attrib[android_prefix + "allowBackup"] = "true"
                el.attrib[android_prefix + "fullBackupContent"] = "true"
                el.attrib[android_prefix + "fullBackupOnly"] = "true"
                el.attrib[android_prefix + "fullBackupContent"] = "@xml/backup_rules"
                changed_pointer = True
                break
            if changed_pointer:
                backup_rules_file = os.path.join(parent_dir, "res", "xml", "backup_rules.xml")
                if self.create_backup and os.path.exists(backup_rules_file):
                    backup_path = os.path.join(parent_dir, "res", "xml", "backup_rules_backup.xml")
                    shutil.copy(self.input_file, backup_path)
                os.makedirs(fs_utils.get_immediate_parent_folder(backup_rules_file), exist_ok=True)
                with open(backup_rules_file, "wb") as fh:
                    fh.write(
                        """<?xml version="1.0" encoding="utf-8"?>
                            <full-backup-content>
                                <include domain="root" path="."/>
                            </full-backup-content>""".encode(
                            "utf-8"))

        if self.flag_add_debuggable or self.toggle_extract_native_libs:
            if self.flag_add_debuggable:
                for el in tree.findall("application"):
                    el.attrib[android_prefix + "debuggable"] = "true"
                    break
            if self.toggle_extract_native_libs:
                for el in tree.findall("application"):
                    el.attrib[android_prefix + "extractNativeLibs"] = "true"
                    break

        if self.accept_user_installed_ca_certs:
            changed_pointer_cfg = False
            for el in tree.findall("application"):
                el.attrib[android_prefix + "networkSecurityConfig"] = "@xml/network_security_config"
                changed_pointer_cfg = True
                break
            if changed_pointer_cfg:
                network_security_config_file = os.path.join(parent_dir, "res", "xml", "network_security_config.xml")
                if self.create_backup and os.path.exists(network_security_config_file):
                    backup_path = os.path.join(parent_dir, "res", "xml", "network_security_config_backup.xml")
                    shutil.copy(self.input_file, backup_path)
                os.makedirs(fs_utils.get_immediate_parent_folder(network_security_config_file), exist_ok=True)
                with open(network_security_config_file, "wb") as fh:
                    fh.write(
                        "<?xml version=\"1.0\" encoding=\"utf-8\" ?>"
                        "<network-security-config><base-config><trust-anchors>"
                        "<certificates src=\"system\" /><certificates src=\"user\" />"
                        "</trust-anchors></base-config></network-security-config>".encode(
                            "utf-8"))
        if self.add_cosmo_broadcast_receiver:
            for el in tree.findall("application"):
                application = el
                receiver = ET.SubElement(application, 'receiver')
                receiver.set('android:name', 'cosmo.receiver.EndCoverageBroadcast')
                receiver.set('android:exported', 'true')
                intent_filter = ET.SubElement(receiver, 'intent-filter')
                action = ET.SubElement(intent_filter, 'action')
                action.set('android:name', 'intent.END_COVERAGE')
                break
        if self.add_permissions is not None and len(self.add_permissions) > 0:
            present_permissions = []
            for el in tree.findall("uses-permission"):
                perm_name = el.get(f'{android_prefix}name')
                present_permissions.append(perm_name)
            permissions_to_add = [perm_name for perm_name in self.add_permissions if
                                  perm_name not in present_permissions]
            for new_permission_str in permissions_to_add:
                new_permission = ET.Element('uses-permission')
                new_permission.set(f'{android_prefix}name', new_permission_str)
                tree.getroot().append(new_permission)

        tree.write(self.input_file, encoding='utf-8', xml_declaration=True)
        self.logger.debug(f'Changed manifest file {self.input_file}')


def main():
    input_file = ".\\input\\apk\\manifest-tests\\AndroidManifestWhatsApp.xml"
    output_file = ".\\tmp\\AndroidManifestWhatsAppEdited.xml"
    if os.path.exists(output_file):
        os.remove(output_file)
    fs_utils.copy_file(input_file, output_file)
    tool = ToolManifestEditor(input_file=output_file, flag_add_debuggable=True, accept_user_installed_ca_certs=True,
                              allows_private_backups=True, create_backup=True)
    tool.execute()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)
    main()
