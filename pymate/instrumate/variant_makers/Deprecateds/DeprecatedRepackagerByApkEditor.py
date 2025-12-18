import os
from pymate import App
from pymate.common import app_variant as av
from pymate.common.app_variant import AppVariant
from pymate.instrumate.variant_maker import MakerContext
from pymate.instrumate.variant_makers.Deprecateds.DeprecatedGenericRepackager import DeprecatedGenericRepackager
from pymate.utils import fs_utils
from pymate.common.tools.ToolApkEditor import ToolApkEditorUnpack, ToolApkEditorRepack, ToolApkEditorMerge
from pymate.common.tools.ToolZipalign import ToolZipalign
from pymate.common.tools.ToolApkSigner import ToolApkSigner
from pymate.common.tools.ToolManifestEditor import ToolManifestEditor
from pymate.common.tools.ToolDex2Jar import ToolDex2JarMakeJar
from pymate.common.tools.ToolD8 import ToolD8


class RepackagerByApkEditor(DeprecatedGenericRepackager):
    def __init__(self, name=None, tag='by-apkeditor'):
        if name is None:
            super().__init__(name=self.__class__.__name__, tag=tag)
        else:
            super().__init__(name=name, tag=tag)
        self.use_d8_for_jar2dex = True

    def get_known_features(self):
        return [av.FEATURE_REPACKAGED,
                av.FEATURE_DEBUGGABLE,
                av.FEATURE_ALLOW_PRIVATE_DATA_BKP,
                av.FEATURE_TRUST_USER_INSTALLED_CERTS,
                # av.FEATURE_REVEAL_PASSWORD_FIELDS,
                # av.FEATURE_MONITOR_SENSITIVE_APIS_SMALI,
                # av.FEATURE_MONITOR_SENSITIVE_APIS_JAVA_AOP,
                av.FEATURE_MONITOR_METHOD_CALLS_WITH_DROIDFAX,
                av.FEATURE_MERGED_APP
                ]

    def can_make(self, app: App, variant: AppVariant):
        knows_features = super().can_make(app, variant)
        if not knows_features:
            return False
        if variant.is_at_least_one_feature_active([av.FEATURE_DEBUGGABLE, av.FEATURE_TRUST_USER_INSTALLED_CERTS,
                                                   av.FEATURE_ALLOW_PRIVATE_DATA_BKP]) and not variant.is_at_level(
            av.VARIANT_LEVEL_MODIFY_RESOURCES):
            return False
        return True

    def merge(self, context: MakerContext):
        app = context.input_app
        if not app.has_split_pkgs():
            raise RuntimeError("Merge is not possible to single apk based apps")
        merge_dir = self.get_tmp_dir()
        base_name = fs_utils.get_file_without_parent(app.get_base_pkg())
        dest_file = os.path.join(merge_dir, base_name)
        fs_utils.copy_file(source=app.get_base_pkg(), destination=dest_file)
        for split in app.get_split_pkgs():
            base_name = fs_utils.get_file_without_parent(split)
            dest_file = os.path.join(merge_dir, base_name)
            fs_utils.copy_file(source=split, destination=dest_file)
        merged_file = self.get_tmp_file()
        self.execute_tool(
            ToolApkEditorMerge(tool_path=self.apkeditor_tool_path, input_dir=merge_dir, output_file=merged_file))
        context.merged_apk = merged_file

    def unpack_single_apk(self, input_file, is_base: bool, context: MakerContext):
        unpack_dir_path = self.get_tmp_dir()
        variant = context.spec
        if os.path.exists(unpack_dir_path):
            fs_utils.destroy_dir_files(unpack_dir_path)

        skip_resources_decoding = True
        if context.spec.is_level_set(av.VARIANT_LEVEL_MODIFY_RESOURCES):
            skip_resources_decoding = False
        skip_smali_decoding = True
        self.execute_tool(
            ToolApkEditorUnpack(self.apkeditor_tool_path, input_file, unpack_dir_path, skip_smali_decoding,
                                skip_resources_decoding))

        if context.spec.is_level_set(av.VARIANT_LEVEL_MODIFY_MANIFEST) and skip_resources_decoding:
            manifest_file = os.path.join(unpack_dir_path, "AndroidManifest.xml.bin")
            if os.path.exists(manifest_file):
                # unpack_only_for_manifest = self.get_tmp_dir()
                # self.execute_tool(
                #     ToolApkEditorUnpack(self.apkeditor_tool_path, input_file, unpack_only_for_manifest, True,
                #                         False))
                # decoded_manifest = os.path.join(unpack_only_for_manifest, "AndroidManifest.xml")
                # if os.path.exists(decoded_manifest):
                #     os.remove(manifest_file)
                #     fs_utils.copy_file(decoded_manifest, unpack_dir_path, True)
                # fs_utils.destroy_dir_files(unpack_only_for_manifest)
                raise NotImplementedError('ApkEditor must decode resources too. This is not implemented yet.')

        # dex2jar
        if variant.is_feature_set(av.FEATURE_MONITOR_CRYPTO_API_MISUSE) \
                or variant.is_feature_set(av.FEATURE_MONITOR_METHOD_CALLS_WITH_COSMO):
            jar_file = self.get_tmp_file()
            self.execute_tool(ToolDex2JarMakeJar(dextool_dir=self.dex2jar_path, input_file=input_file,
                                                 output_file=jar_file))
            if "dex_2_jar" not in context.context_data:
                context.context_data["dex_2_jar"] = {}
            context.context_data["dex_2_jar"][unpack_dir_path] = jar_file
        return unpack_dir_path

    def modify_single_apk(self, unpacked_dir, is_base: bool, context: MakerContext):
        variant = context.spec
        debuggable = variant.is_feature_set(av.FEATURE_DEBUGGABLE)
        trust_user_installed_certs = variant.is_feature_set(av.FEATURE_TRUST_USER_INSTALLED_CERTS)
        allow_data_backup = variant.is_feature_set(av.FEATURE_ALLOW_PRIVATE_DATA_BKP)
        if debuggable or trust_user_installed_certs or allow_data_backup:
            manifest_file = os.path.join(unpacked_dir, "AndroidManifest.xml")
            if os.path.exists(manifest_file):
                self.execute_tool(ToolManifestEditor(input_file=manifest_file, allows_private_backups=allow_data_backup,
                                                     flag_add_debuggable=debuggable,
                                                     accept_user_installed_ca_certs=trust_user_installed_certs))

    def repack_single_apk(self, unpack_dir_path, is_base: bool, context: MakerContext):
        variant = context.spec
        # jar2dex
        if variant.is_feature_set(av.FEATURE_MONITOR_CRYPTO_API_MISUSE) \
                or variant.is_feature_set(av.FEATURE_MONITOR_METHOD_CALLS_WITH_COSMO):
            if unpack_dir_path in context.context_data["dex_2_jar"]:
                jar_file = context.context_data["dex_2_jar"][unpack_dir_path]
                if self.use_d8_for_jar2dex:
                    result_dir = self.get_tmp_dir()
                    if not os.path.exists(result_dir):
                        os.makedirs(result_dir)
                    self.execute_tool(
                        ToolD8(jdk17_home=self.jdk17_path, tool_path=self.tool_d8_path, input_file=jar_file,
                               output_dir=result_dir,
                               android_sdk_jar=self.get_target_sdk_jar(context.input_app),
                               min_sdk_api=context.input_app.get_min_sdk_version()
                               ))
                    os.remove(jar_file)
                    unpack_dex_dir_path = None
                    for file in fs_utils.list_files(directory_path=unpack_dir_path, extension='dex'):
                        if unpack_dex_dir_path is None:
                            unpack_dex_dir_path = fs_utils.get_immediate_parent_folder(file)
                        os.remove(file)
                    for file in fs_utils.list_files(directory_path=result_dir, extension='dex'):
                        fs_utils.copy_file(source=file, destination=unpack_dex_dir_path, force=True)
                    fs_utils.destroy_dir_files(result_dir)
                else:
                    raise NotImplementedError(
                        "Dex2Jar seems to have problems to convert back to dex if not individually")
                    # jar_file_output_dir = fs_utils.get_immediate_parent_folder(jar_file)
                    # jar_file_output = f"{fs_utils.get_file_name_without_extension(jar_file)}.dex"
                    # full_output_path = os.path.join(jar_file_output_dir, jar_file_output)
                    # self.execute_tool(ToolDex2JarMakeDex(dextool_dir=self.dex2jar_path, input_file=jar_file,
                    #                                      output_file=full_output_path))
                    # if not os.path.exists(full_output_path):
                    #     raise RuntimeError(f"DEX file {full_output_path} does not exists. Dex2Jar failed.")
                    # else:
                    #     os.remove(jar_file)
        tmp_file = self.get_tmp_file()
        self.execute_tool(ToolApkEditorRepack(self.apkeditor_tool_path, unpack_dir_path, tmp_file))
        if not os.path.exists(tmp_file):
            raise RuntimeError(f"Repackager failed. Packaged file is missing {tmp_file}")
        tmp_file2 = self.get_tmp_file()
        self.execute_tool(ToolZipalign(self.tool_zipalign, tmp_file, tmp_file2))
        if not os.path.exists(tmp_file2):
            raise RuntimeError(f"Repackager failed. Aligned file is missing {tmp_file2}")
        output_file = self.get_tmp_file()
        self.execute_tool(
            ToolApkSigner(self.tool_apksigner, self.apk_signer_key, self.apk_signer_cert, tmp_file2, output_file))
        if not os.path.exists(output_file):
            raise RuntimeError(f"Repackager failed. Signed file is missing {tmp_file}")
        fs_utils.destroy_dir_files(unpack_dir_path)
        if os.path.exists(tmp_file2):
            os.remove(tmp_file2)
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
        return output_file
