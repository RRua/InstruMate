import os
from pymate import App
from pymate.common import app_variant as av
from pymate.common.app_variant import AppVariant
from pymate.instrumate.variant_maker import MakerContext
from pymate.instrumate.variant_makers.GenericRepackager import GenericRepackager
from pymate.utils import fs_utils
from pymate.common.tools.ToolApkEditor import ToolApkEditorUnpack, ToolApkEditorRepack, ToolApkEditorMerge
from pymate.common.tools.ToolManifestEditor import ToolManifestEditor
from pymate.common.tools.ToolDex2Jar import ToolDex2JarMakeJar
from pymate.common.tools.ToolRevealPasswordFields import ToolRevealPasswordFields
from pymate.common.tools.ToolChangeStringResource import ToolChangeStringResource
from pymate.common.tools.ToolChangeIconResource import ToolChangeIconResource

class GenericApkEditorRepackager(GenericRepackager):

    def __init__(self, tag='by-apkeditor'):
        super().__init__(tag=tag)
        self.check_merge_levels = False

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
        if self.check_merge_levels:
            if variant.is_feature_set(av.FEATURE_MERGED_APP):
                has_all_levels = variant.is_level_set(av.VARIANT_LEVEL_MODIFY_MANIFEST) and variant.is_level_set(av.VARIANT_LEVEL_MODIFY_RESOURCES) and variant.is_level_set(av.VARIANT_LEVEL_MODIFY_SIGNATURE)
                if not has_all_levels:
                    return False
                #by now, we are interested only in checking if merging is necessary
                #if variant.is_other_feature_active([av.FEATURE_REPACKAGED]):
                #    return False
        return True

    def merge(self, context: MakerContext):
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
        if os.path.exists(unpack_dir_path):
            fs_utils.destroy_dir_files(unpack_dir_path)
        skip_smali_decoding = True
        skip_resources_decoding = True
        variant = context.spec
        debuggable = variant.is_feature_set(av.FEATURE_DEBUGGABLE)
        trust_user_installed_certs = variant.is_feature_set(av.FEATURE_TRUST_USER_INSTALLED_CERTS)
        allow_data_backup = variant.is_feature_set(av.FEATURE_ALLOW_PRIVATE_DATA_BKP)
        level_modify_res = variant.is_level_set(av.VARIANT_LEVEL_MODIFY_RESOURCES)
        if debuggable or trust_user_installed_certs or allow_data_backup or level_modify_res:
            skip_resources_decoding = False
        if context.spec.is_level_set(av.VARIANT_LEVEL_MODIFY_BEHAVIOUR):
            if context.spec.is_feature_set(av.FEATURE_MONITOR_METHOD_CALLS_WITH_FRIDA_GADGET):
                skip_resources_decoding = False
                skip_smali_decoding = False
            if context.spec.is_feature_set(av.FEATURE_MONITOR_METHOD_CALLS_WITH_IMCOVERAGE):
                skip_smali_decoding = False
        self.execute_tool(
            ToolApkEditorUnpack(self.apkeditor_tool_path, file_path, unpack_dir_path, skip_smali_decoding,
                                skip_resources_decoding), context)
        return unpack_dir_path

    def convert_to_instrumentation_representation(self, apk_file, unpacked_dir, is_base, context: MakerContext) -> str:
        variant = context.spec
        if variant.is_feature_set(av.FEATURE_MONITOR_CRYPTO_API_MISUSE) \
                or variant.is_feature_set(av.FEATURE_MONITOR_METHOD_CALLS_WITH_COSMO):
            jar_file = self.get_tmp_file()
            self.execute_tool(ToolDex2JarMakeJar(dextool_dir=self.dex2jar_path, input_file=apk_file,
                                                 output_file=jar_file), context)
            return jar_file
        return None

    def repack_single_apk(self, apk_file, unpacked_dir: str, instrumentable_version: str, instrumented_version: str,
                          is_base: bool, context: MakerContext):
        variant = context.spec
        tmp_file = self.get_tmp_file()
        self.execute_tool(ToolApkEditorRepack(self.apkeditor_tool_path, unpacked_dir, tmp_file), context)
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