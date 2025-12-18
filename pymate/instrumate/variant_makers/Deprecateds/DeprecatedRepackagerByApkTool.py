import os
from pymate.common import app_variant as av
from pymate.instrumate.variant_makers.Deprecateds.DeprecatedGenericRepackager import DeprecatedGenericRepackager
from pymate.instrumate.variant_maker import MakerContext
from pymate.utils import fs_utils
from pymate.common.tools.ToolManifestEditor import ToolManifestEditor
from pymate.common.tools.ToolZipalign import ToolZipalign
from pymate.common.tools.ToolApkSigner import ToolApkSigner
from pymate.common.tools.ToolApkTool import ToolApkToolUnpackSkipSmaliNoResources, \
    ToolApkToolUnpackSkipSmaliDecodeResources, ToolApkToolUnpackSmaliMainClassesNoResources, \
    ToolApkToolUnpackSmaliMainClassesDecodeResources, ToolApkToolUnpackSmaliAllNoResources, \
    ToolApkToolUnpackSmaliAllDecodeResources, ToolApkToolRepack
from pymate.common.tools.ToolDex2Jar import ToolDex2JarMakeDex, ToolDex2JarMakeJar


class RepackagerByApkTool(DeprecatedGenericRepackager):
    def __init__(self):
        super().__init__(name=self.__class__.__name__, tag='by-apktool')
        self.smali_only_main_classes = False

    def get_known_features(self):
        return [av.FEATURE_REPACKAGED,
                av.FEATURE_DEBUGGABLE,
                av.FEATURE_ALLOW_PRIVATE_DATA_BKP,
                av.FEATURE_TRUST_USER_INSTALLED_CERTS,
                av.FEATURE_REVEAL_PASSWORD_FIELDS,
                av.FEATURE_MONITOR_METHOD_CALLS_WITH_ACVTOOL,
                av.FEATURE_MONITOR_CRYPTO_API_MISUSE,
                av.FEATURE_MONITOR_METHOD_CALLS_WITH_DROIDFAX
                ]

    def unpack_single_apk(self, input_file, is_base: bool, context: MakerContext):
        variant = context.spec
        unpack_dir_path = self.get_tmp_dir()
        if os.path.exists(unpack_dir_path):
            fs_utils.destroy_dir_files(unpack_dir_path)
        decode_resources = variant.is_at_least_one_feature_active([av.FEATURE_DEBUGGABLE, av.FEATURE_ALLOW_PRIVATE_DATA_BKP, av.FEATURE_TRUST_USER_INSTALLED_CERTS,
                                                                   av.FEATURE_REVEAL_PASSWORD_FIELDS])
        decode_smali = variant.is_feature_set(av.FEATURE_MONITOR_METHOD_CALLS_WITH_ACVTOOL)
        if decode_smali:
            if decode_resources:
                if self.smali_only_main_classes:
                    self.execute_tool(
                        ToolApkToolUnpackSmaliMainClassesDecodeResources(self.apktool_path, input_file,
                                                                         unpack_dir_path))
                else:
                    self.execute_tool(
                        ToolApkToolUnpackSmaliAllDecodeResources(self.apktool_path, input_file, unpack_dir_path))
            else:
                if self.smali_only_main_classes:
                    self.execute_tool(
                        ToolApkToolUnpackSmaliMainClassesNoResources(self.apktool_path, input_file,
                                                                     unpack_dir_path))
                else:
                    self.execute_tool(
                        ToolApkToolUnpackSmaliAllNoResources(self.apktool_path, input_file, unpack_dir_path))
        else:
            if decode_resources:
                self.execute_tool(
                    ToolApkToolUnpackSkipSmaliDecodeResources(self.apktool_path, input_file, unpack_dir_path))
            else:
                self.execute_tool(
                    ToolApkToolUnpackSkipSmaliNoResources(self.apktool_path, input_file, unpack_dir_path))
        # dex2jar
        if variant.is_feature_set(av.FEATURE_MONITOR_CRYPTO_API_MISUSE):
            file_list = fs_utils.list_files(unpack_dir_path)
            dex_files = [file for file in file_list if file.endswith('.dex')]
            self.logger.debug(f"Converting {len(dex_files)} DEX files to JAR")
            for dex_file in dex_files:
                dex_file_output_dir = fs_utils.get_immediate_parent_folder(dex_file)
                dex_file_output = f"{fs_utils.get_file_name_without_extension(dex_file)}.jar"
                full_output_path = os.path.join(dex_file_output_dir, dex_file_output)
                self.execute_tool(ToolDex2JarMakeJar(dextool_dir=self.dex2jar_path, input_file=dex_file,
                                                     output_file=full_output_path))
                if not os.path.exists(full_output_path):
                    raise RuntimeError(f"JAR file {full_output_path} does not exists. Dex2Jar failed.")
                else:
                    os.remove(dex_file)
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
        if variant.is_feature_set(av.FEATURE_MONITOR_CRYPTO_API_MISUSE):
            file_list = fs_utils.list_files(unpack_dir_path)
            jar_files = [file for file in file_list if file.endswith('.jar')]
            self.logger.debug(f"Converting {len(jar_files)} JAR files to DEX")
            for jar_file in jar_files:
                jar_file_output_dir = fs_utils.get_immediate_parent_folder(jar_file)
                jar_file_output = f"{fs_utils.get_file_name_without_extension(jar_file)}.dex"
                full_output_path = os.path.join(jar_file_output_dir, jar_file_output)
                self.execute_tool(ToolDex2JarMakeDex(dextool_dir=self.dex2jar_path, input_file=jar_file,
                                                     output_file=full_output_path))
                if not os.path.exists(full_output_path):
                    raise RuntimeError(f"DEX file {full_output_path} does not exists. Dex2Jar failed.")
                else:
                    os.remove(jar_file)
        tmp_file = self.get_tmp_file()
        self.execute_tool(ToolApkToolRepack(self.apktool_path, unpack_dir_path, tmp_file))
        if not os.path.exists(tmp_file):
            raise RuntimeError(f"Repackager failed. Packaged file is missing {tmp_file}")
        tmp_file2 = self.get_tmp_file()
        self.execute_tool(ToolZipalign(self.tool_zipalign, tmp_file, tmp_file2))
        if not os.path.exists(tmp_file2):
            raise RuntimeError(f"Repackager failed. Aligned file is missing {tmp_file}")
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
