import os
from abc import ABC, abstractmethod

from pymate.common import app_variant as av
from pymate.common.app import App, AppVariant
from pymate.common.tools.ToolApkSigner import ToolApkSigner
from pymate.common.tools.ToolD8 import ToolD8
from pymate.common.tools.ToolDex2Jar import ToolDex2JarMakeJar
from pymate.common.tools.ToolZipalign import ToolZipalign
from pymate.instrumate.variant_maker import VariantMaker, MakerContext
from pymate.utils import fs_utils


class GenericRepackager(VariantMaker, ABC):
    def __init__(self, tag: str = None):
        super().__init__(name=self.__class__.__name__, tag=tag)

    @abstractmethod
    def unpack_single_apk(self, file_path, is_base: bool, context: MakerContext) -> str:
        raise NotImplementedError("Subclasses should implement this method")

    def convert_to_instrumentation_representation(self, apk_file, unpacked_dir, is_base, context: MakerContext) -> str:
        return None

    def convert_to_java_instrumentation_representation(self, apk_file, unpacked_dir, is_base,
                                                       context: MakerContext) -> str:
        dex_files = fs_utils.list_files(directory_path=unpacked_dir, extension='dex')
        if len(dex_files) == 0:
            return None
        variant = context.spec
        jar_file = self.get_tmp_file()
        self.execute_tool(ToolDex2JarMakeJar(dextool_dir=self.dex2jar_path, input_file=apk_file,
                                             output_file=jar_file), context)
        return jar_file

    def instrument(self, apk_file: str, unpacked_dir: str, instrumentable_version: str, is_base,
                   context: MakerContext) -> str:
        return None

    def convert_instrumented_java_to_dex(self, apk_file: str, unpacked_dir: str, instrumented_version: str, is_base,
                                         context: MakerContext) -> str:
        jar_file = instrumented_version
        result_dir = self.get_tmp_dir(label="java_2_dex")
        if not os.path.exists(result_dir):
            os.makedirs(result_dir)
        self.execute_tool(
            ToolD8(jdk17_home=self.jdk17_path, tool_path=self.tool_d8_path, input_file=jar_file,
                   output_dir=result_dir,
                   android_sdk_jar=self.get_target_sdk_jar(context.input_app),
                   min_sdk_api=context.input_app.get_min_sdk_version()
                   ), context)
        os.remove(jar_file)
        unpack_dex_dir_path = None
        for file in fs_utils.list_files(directory_path=unpacked_dir, extension='dex'):
            if unpack_dex_dir_path is None:
                unpack_dex_dir_path = fs_utils.get_immediate_parent_folder(file)
            os.remove(file)
        for file in fs_utils.list_files(directory_path=result_dir, extension='dex'):
            fs_utils.copy_file(source=file, destination=unpack_dex_dir_path, force=True)
        fs_utils.destroy_dir_files(result_dir)

    @abstractmethod
    def repack_single_apk(self, apk_file, unpacked_dir: str, instrumentable_version: str, instrumented_version: str,
                          is_base: bool,
                          context: MakerContext):
        raise NotImplementedError("Subclasses should implement this method")

    @abstractmethod
    def modify_single_apk(self, apk_file: str, unpacked_dir: str, is_base: bool,
                          context: MakerContext):
        raise NotImplementedError("Subclasses should implement this method")

    # @abstractmethod
    # def merge_splited_app(self, base_file: str, split_files, context: MakerContext):
    #     raise NotImplementedError("Subclasses should implement this method")

    def pre_process(self, context: MakerContext):
        # spec = context.spec
        # app = context.input_app
        # if spec.is_feature_set(av.FEATURE_MERGED_APP) and not app.has_split_pkgs():
        #     context.merged_apk = self.merge_splited_app(base_file=context.input_app.get_base_pkg(),
        #                                                 split_files=context.input_app.get_split_pkgs(), context=context)
        pass

    def unpack(self, context: MakerContext):
        if context.spec.is_feature_set(av.FEATURE_MERGED_APP):
            if context.merged_apk is not None:
                self._unpack(context.merged_apk, True, context)
            else:
                raise RuntimeError('Feature merged app was requested, but no merged version exists')
        else:
            self._unpack(context.input_app.get_base_pkg(), True, context)
            for index, split in enumerate(context.input_app.get_split_pkgs()):
                self._unpack(split, False, context)

    def _unpack(self, apk_file, is_base, context):
        unpacked_dir = self.unpack_single_apk(apk_file, is_base, context)
        instrumentable_version = self.convert_to_instrumentation_representation(apk_file, unpacked_dir, is_base,
                                                                                context)
        unpacked_files = context.context_data["unpacked_files"] if "unpacked_files" in context.context_data else {}
        instrumentable_versions = context.context_data[
            "instrumentable_versions"] if "instrumentable_versions" in context.context_data else {}
        unpacked_files[apk_file] = unpacked_dir
        instrumentable_versions[apk_file] = instrumentable_version
        context.context_data["unpacked_files"] = unpacked_files
        context.context_data["instrumentable_versions"] = instrumentable_versions

    def modify(self, context: MakerContext):
        if context.spec.is_feature_set(av.FEATURE_MERGED_APP):
            self._modify(apk_file=context.merged_apk, is_base=True, context=context)
        else:
            base_pkg_file = context.input_app.get_base_pkg()
            self._modify(base_pkg_file, True, context)
            for index, split in enumerate(context.input_app.get_split_pkgs()):
                self._modify(split, False, context)

    def _modify(self, apk_file: str, is_base: bool, context: MakerContext):
        unpacked_files = context.context_data["unpacked_files"]
        instrumentable_versions = context.context_data["instrumentable_versions"]
        instrumented_versions = context.context_data[
            "instrumented_versions"] if "instrumented_versions" in context.context_data else {}
        instrumentable_version = instrumentable_versions[apk_file]
        unpacked_dir = unpacked_files[apk_file]
        self.modify_single_apk(apk_file=apk_file, unpacked_dir=unpacked_dir, is_base=is_base, context=context)
        if instrumentable_version is not None:
            instrumented_version = self.instrument(apk_file=apk_file, unpacked_dir=unpacked_dir,
                                                   is_base=is_base,
                                                   instrumentable_version=instrumentable_version, context=context)
            instrumented_versions[apk_file] = instrumented_version
        else:
            self.logger.debug(f"Instrumentable version for file {apk_file} is None. Can't instrument.")
        context.context_data["instrumented_versions"] = instrumented_versions

    def repack(self, context: MakerContext):
        # pretty base name
        final_base_file = self.get_final_variant_file(context.input_app.get_base_pkg(), context.spec)
        new_splits = []
        if context.spec.is_feature_set(av.FEATURE_MERGED_APP):
            merged_repackaged = self._repack(apk_file=context.merged_apk, is_base=True, context=context)
            # rename merged to pretty name
            fs_utils.move_file(merged_repackaged, final_base_file)
        else:
            base_pkg_file = context.input_app.get_base_pkg()
            base_repackaged = self._repack(apk_file=base_pkg_file, is_base=True, context=context)
            # rename base repackaged to pretty name
            fs_utils.move_file(base_repackaged, final_base_file)
            for index, split in enumerate(context.input_app.get_split_pkgs()):
                split_repackaged = self._repack(apk_file=split, is_base=False, context=context)
                final_split_file = self.get_final_variant_file(split, context.spec)
                # rename split to final pretty name
                fs_utils.move_file(split_repackaged, final_split_file)
                new_splits.append(final_split_file)
        # make variant App
        variant = AppVariant(variant_features=context.spec.variant_features, variant_levels=context.spec.variant_levels,
                             tag=self.tag)
        context.output_app = App(apk_base_path=final_base_file, extra_split_pkgs=new_splits, variant_info=variant)

    def _repack(self, apk_file: str, is_base: bool, context: MakerContext):
        unpacked_files = context.context_data.get("unpacked_files", {})
        instrumentable_versions = context.context_data.get("instrumentable_versions", {})
        instrumented_versions = context.context_data.get("instrumented_versions", {})
        unpacked_dir = unpacked_files.get(apk_file, None)
        instrumentable_version = instrumentable_versions.get(apk_file, None)
        instrumented_version = instrumented_versions.get(apk_file, None)
        created_pkg = self.repack_single_apk(apk_file=apk_file, unpacked_dir=unpacked_dir,
                                             instrumentable_version=instrumentable_version,
                                             instrumented_version=instrumented_version,
                                             is_base=is_base,
                                             context=context)
        if unpacked_dir is not None and os.path.exists(unpacked_dir):
            fs_utils.destroy_dir_files(unpacked_dir)
        return self.sign(created_pkg, context)

    def sign(self, apk_file, context: MakerContext):
        if not os.path.exists(apk_file):
            raise RuntimeError(f"Repackager failed. Packaged file is missing {apk_file}")
        tmp_file2 = self.get_tmp_file()
        self.execute_tool(ToolZipalign(self.tool_zipalign, apk_file, tmp_file2), context)
        if not os.path.exists(tmp_file2):
            raise RuntimeError(f"Repackager failed. Aligned file is missing {tmp_file2}")
        output_file = self.get_tmp_file()
        self.execute_tool(
            ToolApkSigner(self.tool_apksigner, self.apk_signer_key, self.apk_signer_cert, tmp_file2, output_file),
            context)
        if not os.path.exists(output_file):
            raise RuntimeError(f"Repackager failed. Signed file is missing {output_file}")
        if os.path.exists(tmp_file2):
            os.remove(tmp_file2)
        if os.path.exists(apk_file):
            os.remove(apk_file)
        return output_file
