import os
from pymate import App
from pymate.common import app_variant as av
from pymate.common.app_variant import AppVariant
from pymate.instrumate.variant_maker import MakerContext
from pymate.instrumate.variant_makers.GenericRepackager import GenericRepackager
from pymate.utils import fs_utils
from pymate.common.tools.ToolZip import ToolZipUnpack, ToolZipRepack

SIGNATURE_FILES = ["rsa", "dsa", "ec", "sf"]


def remove_signature_files(meta_inf_dir):
    for ext in SIGNATURE_FILES:
        sig_files = fs_utils.list_files(directory_path=meta_inf_dir, extension=ext) + fs_utils.list_files(
            directory_path=meta_inf_dir, extension=ext.upper())
        for file in sig_files:
            os.remove(file)


class GenericZipRepackager(GenericRepackager):

    def __init__(self, tag='by-zip'):
        super().__init__(tag=tag)

    def get_known_features(self):
        return [
            av.FEATURE_REPACKAGED
        ]

    def can_make(self, app: App, variant: AppVariant):
        knows_features = super().can_make(app, variant)
        if not knows_features:
            return False
        return True

    def merge(self, context: MakerContext):
        raise RuntimeError("Merge is not possible with zip-repackager")

    def unpack_single_apk(self, file_path, is_base: bool, context: MakerContext) -> str:
        unpack_dir_path = self.get_tmp_dir(label="unpack")
        self.execute_tool(ToolZipUnpack(input_file=file_path, output_dir=unpack_dir_path,
                                        fail_on_ms_windows_overwrite=True), context)
        meta_inf_dir = os.path.join(unpack_dir_path, "META-INF")
        if os.path.exists(meta_inf_dir):
            remove_signature_files(meta_inf_dir)
        return unpack_dir_path

    def convert_to_instrumentation_representation(self, apk_file, unpacked_dir, is_base, context: MakerContext) -> str:
        return None

    def repack_single_apk(self, apk_file, unpacked_dir: str, instrumentable_version: str, instrumented_version: str,
                          is_base: bool, context: MakerContext):
        variant = context.spec
        tmp_file = self.get_tmp_file()
        self.execute_tool(ToolZipRepack(unpacked_dir, tmp_file, not_compress_files=['resources.arsc', '.so']), context)
        fs_utils.destroy_dir_files(unpacked_dir)
        return tmp_file

    def modify_single_apk(self, apk_file: str, unpacked_dir: str, is_base: bool, context: MakerContext):
        return
