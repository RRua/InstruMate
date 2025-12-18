import os
from pymate import App
from pymate.common import app_variant as av
from pymate.common.app_variant import AppVariant
from pymate.instrumate.variant_maker import MakerContext
from pymate.instrumate.variant_makers.GenericRepackager import GenericRepackager
from pymate.utils import fs_utils
from pymate.common.tools.ToolApkTool import ToolApkToolUnpack, ToolApkToolRepack
from pymate.common.tools.ToolManifestEditor import ToolManifestEditor
from pymate.common.tools.ToolApkEditor import ToolApkEditorMerge
from pymate.common.tools.ToolRevealPasswordFields import ToolRevealPasswordFields
from pymate.common.tools.ToolChangeStringResource import ToolChangeStringResource
from pymate.common.tools.ToolChangeIconResource import ToolChangeIconResource


class GenericApkToolRepackager(GenericRepackager):

    def __init__(self, tag='by-apktool'):
        super().__init__(tag=tag)

    def get_known_features(self):
        return [
            av.FEATURE_REPACKAGED,
            av.FEATURE_DEBUGGABLE,
            av.FEATURE_ALLOW_PRIVATE_DATA_BKP,
            av.FEATURE_TRUST_USER_INSTALLED_CERTS,
            av.FEATURE_REVEAL_PASSWORD_FIELDS,
            av.FEATURE_CHANGE_STRING_RESOURCE,
            av.FEATURE_GRAYSCALE_IMAGES,
            av.FEATURE_MERGED_APP
        ]

    def can_make(self, app: App, variant: AppVariant):
        knows_features = super().can_make(app, variant)
        if not knows_features:
            return False
        if variant.is_feature_set(av.FEATURE_MERGED_APP) and not app.has_split_pkgs():
            return False
        return True

    def merge(self, context: MakerContext):
        #  raise RuntimeError("Merge is not possible with apktool")
        app = context.input_app
        if not app.has_split_pkgs():
            raise RuntimeError("Merge is not possible to single apk based apps")
        merge_dir = self.get_tmp_dir(label="merge")
        base_name = fs_utils.get_file_without_parent(app.get_base_pkg())
        dest_file = os.path.join(merge_dir, base_name)
        fs_utils.copy_file(source=app.get_base_pkg(), destination=dest_file)
        for split in app.get_split_pkgs():
            base_name = fs_utils.get_file_without_parent(split)
            dest_file = os.path.join(merge_dir, base_name)
            fs_utils.copy_file(source=split, destination=dest_file)
        merged_file = self.get_tmp_file()
        self.execute_tool(
            ToolApkEditorMerge(tool_path=self.apkeditor_tool_path, input_dir=merge_dir, output_file=merged_file), context)
        context.merged_apk = merged_file

    def unpack_single_apk(self, file_path, is_base: bool, context: MakerContext) -> str:
        unpack_dir_path = self.get_tmp_dir(label="unpack")
        if not os.path.exists(unpack_dir_path):
            os.makedirs(unpack_dir_path)
        decode_smali = False
        decode_smali_only_main_classes = False
        decode_resources = False
        decode_resources_only_manifest = False
        decode_assets = False
        if context.spec.is_level_set(av.VARIANT_LEVEL_MODIFY_RESOURCES):
            decode_resources = True
        else:
            if context.spec.is_level_set(av.VARIANT_LEVEL_MODIFY_MANIFEST):
                decode_resources = True
                decode_resources_only_manifest = True
        if context.spec.is_level_set(av.VARIANT_LEVEL_MODIFY_BEHAVIOUR):
            if context.spec.is_feature_set(av.FEATURE_MONITOR_METHOD_CALLS_WITH_FRIDA_GADGET):
                decode_smali = True
                decode_resources = True
                decode_resources_only_manifest = True
            if context.spec.is_feature_set(av.FEATURE_MONITOR_METHOD_CALLS_WITH_IMCOVERAGE):
                decode_smali = True
        self.execute_tool(
            ToolApkToolUnpack(tool_path=self.apktool_path, input_file=file_path, output_dir=unpack_dir_path,
                              decode_smali=decode_smali, decode_smali_only_main_classes=decode_smali_only_main_classes,
                              decode_resources=decode_resources,
                              decode_resources_only_manifest=decode_resources_only_manifest,
                              decode_assets=decode_assets), context=context)
        return unpack_dir_path

    def convert_to_instrumentation_representation(self, apk_file, unpacked_dir, is_base, context: MakerContext) -> str:
        return None

    def repack_single_apk(self, apk_file, unpacked_dir: str, instrumentable_version: str, instrumented_version: str,
                          is_base: bool, context: MakerContext):
        variant = context.spec
        tmp_file = self.get_tmp_file()
        self.execute_tool(ToolApkToolRepack(self.apktool_path, unpacked_dir, tmp_file), context)
        fs_utils.destroy_dir_files(unpacked_dir)
        return tmp_file

    def modify_single_apk(self, apk_file: str, unpacked_dir: str, is_base: bool, context: MakerContext):
        variant = context.spec
        debuggable = variant.is_feature_set(av.FEATURE_DEBUGGABLE)
        trust_user_installed_certs = variant.is_feature_set(av.FEATURE_TRUST_USER_INSTALLED_CERTS)
        allow_data_backup = variant.is_feature_set(av.FEATURE_ALLOW_PRIVATE_DATA_BKP)
        extract_native_libs = variant.is_feature_set(av.FEATURE_MONITOR_METHOD_CALLS_WITH_FRIDA_GADGET)
        if is_base:
            if debuggable or trust_user_installed_certs or allow_data_backup or extract_native_libs:
                manifest_file = os.path.join(unpacked_dir, "AndroidManifest.xml")
                permissions = ['android.permission.INTERNET'] if extract_native_libs else None
                if os.path.exists(manifest_file):
                    self.execute_tool(ToolManifestEditor(input_file=manifest_file, allows_private_backups=allow_data_backup,
                                                         flag_add_debuggable=debuggable,
                                                         accept_user_installed_ca_certs=trust_user_installed_certs,
                                                         add_permissions=permissions,
                                                         toggle_extract_native_libs=extract_native_libs), context)
                else:
                    raise RuntimeError(f"File should exist to satisfy features and be able to edit: {manifest_file}")
        change_app_name = variant.is_feature_set(av.FEATURE_CHANGE_STRING_RESOURCE)
        change_icons_to_gray = variant.is_feature_set(av.FEATURE_GRAYSCALE_IMAGES)
        reveal_password_fields = variant.is_feature_set(av.FEATURE_REVEAL_PASSWORD_FIELDS)

        if change_app_name:
            self.execute_tool(ToolChangeStringResource(input_dir=unpacked_dir), context, fail_on_error=is_base)
        if change_icons_to_gray:
            self.execute_tool(ToolChangeIconResource(input_dir=unpacked_dir), context, fail_on_error=is_base)
        if reveal_password_fields:
            self.execute_tool(ToolRevealPasswordFields(input_dir=unpacked_dir), context, fail_on_error=is_base)