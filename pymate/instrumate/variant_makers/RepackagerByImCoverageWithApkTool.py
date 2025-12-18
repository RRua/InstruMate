import os
from pymate.instrumate.variant_makers.GenericApkToolRepackager import GenericApkToolRepackager
from pymate.common import app_variant as av
from pymate.common.tools.ToolSmaliCoveragePatcher import ToolSmaliCoveragePatcher
from pymate.instrumate.variant_maker import MakerContext


def list_smali_subdirectories(directory: str):
    smali_dirs = []
    for entry in os.scandir(directory):
        if entry.is_dir() and 'smali' in entry.name:
            smali_dirs.append(entry.path)
    return smali_dirs


class RepackagerByImCoverageWithApkTool(GenericApkToolRepackager):

    def __init__(self, tag='by-imcoverageapktool'):
        super().__init__(tag=tag)

    def get_known_features(self):
        return [av.FEATURE_MONITOR_METHOD_CALLS_WITH_IMCOVERAGE]

    def convert_to_instrumentation_representation(self, apk_file, unpacked_dir, is_base, context: MakerContext) -> str:
        smali_dirs = list_smali_subdirectories(unpacked_dir)
        if len(smali_dirs) > 0:
            return smali_dirs
        return None

    def instrument(self, apk_file: str, unpacked_dir: str, instrumentable_version: str, is_base,
                   context: MakerContext) -> str:
        smali_dirs = instrumentable_version
        qtd_injections = 0
        for smali_dir in smali_dirs:
            smali_patcher = ToolSmaliCoveragePatcher(smali_dir=smali_dir)
            self.execute_tool(smali_patcher, context)
            qtd_injections = qtd_injections + smali_patcher.qtd_injections
        if is_base and qtd_injections == 0:
            raise RuntimeError("Injection failed")
        self.logger.debug(f"Successfully injected IMCOVERAGE")
        return instrumentable_version
