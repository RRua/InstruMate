import os
from pymate.common import app_variant as av
from pymate.instrumate.variant_maker import MakerContext
from pymate.instrumate.variant_makers.Deprecateds.DeprecatedGenericRepackager import DeprecatedGenericRepackager
from pymate.utils import fs_utils
from pymate.common.tools.ToolZip import ToolZipUnpack, ToolZipRepack
from pymate.common.tools.ToolZipalign import ToolZipalign
from pymate.common.tools.ToolApkSigner import ToolApkSigner
from pymate.common.tools.ToolDex2Jar import ToolDex2JarMakeDex, ToolDex2JarMakeJar


class RepackagerZipToolBased(DeprecatedGenericRepackager):
    def __init__(self):
        super().__init__(name=self.__class__.__name__, tag='by-ziptool')

    def get_known_features(self):
        return [av.FLAG_TRANSITION_NONE ] #, av.FLAG_TRANSITION_JAVA]

    def get_levels_of_operation(self):
        return {}

    def unpack_single_apk(self, input_file, is_base: bool, context: MakerContext):
        unpack_dir_path = self.get_tmp_dir()
        variant = context.input_spec
        if os.path.exists(unpack_dir_path):
            fs_utils.destroy_dir_files(unpack_dir_path)
        if variant.is_flag_set(av.FLAG_TRANSITION_NONE) or variant.is_flag_set(av.FLAG_TRANSITION_JAVA):
            tool_result = self.execute_tool(ToolZipUnpack(input_file, unpack_dir_path))
            if not tool_result["success"]:
                raise RuntimeError("Failed to Unpack with zip tool. Maybe on Windows with conflicting files?")
        else:
            raise RuntimeError("Cant create variant for the flags selected")
        # dex2jar
        if variant.is_flag_set(av.FLAG_TRANSITION_JAVA):
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
        pass

    def repack_single_apk(self, unpack_dir_path, is_base: bool, context: MakerContext):
        variant = context.input_spec
        # jar2dex
        if variant.is_flag_set(av.FLAG_TRANSITION_JAVA):
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
        fs_utils.destroy_dir_files(os.path.join(unpack_dir_path, "META-INF"))
        self.execute_tool(ToolZipRepack(unpack_dir_path, tmp_file, not_compress_files=['resources.arsc']))
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