import os
from pymate.common import app_variant as av
from pymate.common.app import App, AppVariant
from pymate.instrumate.variant_maker import MakerContext
from pymate.instrumate.variant_makers.Deprecateds.DeprecatedGenericRepackager import DeprecatedGenericRepackager
from pymate.utils import fs_utils
from pymate.common.tools.ToolApkEditor import ToolApkEditorMerge
from pymate.common.tools.ToolACVTool import ToolACVTool
from pymate.common.tools.ToolZipalign import ToolZipalign
from pymate.common.tools.ToolApkSigner import ToolApkSigner


class RepackagerByACVTool(DeprecatedGenericRepackager):

    def __init__(self, name=None, tag='by-acvtool'):
        if name is None:
            super().__init__(name=self.__class__.__name__, tag=tag)
        else:
            super().__init__(name=name, tag=tag)

    def get_known_features(self):
        return [
            av.FEATURE_REPACKAGED,
            # av.FEATURE_DEBUGGABLE,
            # av.FEATURE_ALLOW_PRIVATE_DATA_BKP,
            # av.FEATURE_TRUST_USER_INSTALLED_CERTS,
            # av.FEATURE_REVEAL_PASSWORD_FIELDS,
            # av.FEATURE_MONITOR_SENSITIVE_APIS_SMALI,
            # av.FEATURE_MONITOR_SENSITIVE_APIS_JAVA_AOP,
            av.FEATURE_MONITOR_METHOD_CALLS_WITH_ACVTOOL,
            av.FEATURE_MERGED_APP
        ]

    def can_make(self, app: App, variant: AppVariant):
        knows_features = super().can_make(app, variant)
        if not knows_features:
            return False
        if not variant.is_feature_set(av.FEATURE_MONITOR_METHOD_CALLS_WITH_ACVTOOL):
            return False
        if variant.is_feature_set(av.FEATURE_MERGED_APP) and not app.has_split_pkgs():
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

    def unpack_single_apk(self, file_path, is_base: bool, context: MakerContext):
        return None

    def modify_single_apk(self, unpacked_dir, is_base: bool, context: MakerContext):
        output_dir = self.get_tmp_dir()
        if context.merged_apk is not None:
            self.execute_tool(
                ToolACVTool(tool_path=self.tool_acvtool, input_file=context.merged_apk))
        else:
            if context.input_app.has_split_pkgs():
                raise RuntimeError("If it has splits, it should be merged before")
            else:
                input_app = context.input_app.get_base_pkg()
                self.execute_tool(
                    ToolACVTool(tool_path=self.tool_acvtool, input_file=input_app, output_dir=output_dir,
                                aapt_path=self.tool_aapt2, zipalign_path=self.tool_zipalign,
                                adb_path=self.tool_adb, apksigner_path=self.tool_apksigner_bat, acvpatcher_path=self.tool_acvpatcher
                                ))
        created_app = fs_utils.list_files(output_dir)
        created_app = [item for item in created_app if fs_utils.get_file_extension(item) == '.apk']
        assert len(created_app) == 1
        context.context_data["acvtool"] = created_app.pop()

    def repack_single_apk(self, unpack_dir_path, is_base: bool, context: MakerContext):
        droidfax_file = context.context_data["acvtool"]
        if not os.path.exists(droidfax_file):
            raise RuntimeError("Missing acvtool instrumented file")
        tmp_file2 = self.get_tmp_file()
        self.execute_tool(ToolZipalign(self.tool_zipalign, droidfax_file, tmp_file2))
        if not os.path.exists(tmp_file2):
            raise RuntimeError(f"Repackager failed. Aligned file is missing {tmp_file2}")
        output_file = self.get_tmp_file()
        self.execute_tool(
            ToolApkSigner(self.tool_apksigner, self.apk_signer_key, self.apk_signer_cert, tmp_file2, output_file))
        if not os.path.exists(output_file):
            raise RuntimeError(f"Repackager failed. Signed file is missing {droidfax_file}")
        # context.output_app = App(apk_base_path=droidfax_file, extra_split_pkgs=[], variant_info=context.spec)
        return output_file

    def post_process(self, context: MakerContext):
        pass