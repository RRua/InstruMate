import os
from pymate.common import app_variant as av
from pymate.common.app import App, AppVariant
from pymate.instrumate.variant_maker import MakerContext
from pymate.instrumate.variant_makers.Deprecateds.DeprecatedGenericRepackager import DeprecatedGenericRepackager
from pymate.utils import fs_utils
from pymate.common.tools.ToolApkEditor import ToolApkEditorMerge
from pymate.common.tools.ToolAndrologInstrumentation import ToolAndrologInstrumentation


class RepackagerByAndrolog(DeprecatedGenericRepackager):

    def __init__(self, name=None, tag='by-androlog'):
        if name is None:
            super().__init__(name=self.__class__.__name__, tag=tag)
        else:
            super().__init__(name=name, tag=tag)

    def get_known_features(self):
        return [
            av.FEATURE_REPACKAGED,
            av.FEATURE_MONITOR_METHOD_CALLS_WITH_ANDROLOG,
            av.FEATURE_MERGED_APP
        ]

    def can_make(self, app: App, variant: AppVariant):
        knows_features = super().can_make(app, variant)
        if not knows_features:
            return False
        if not variant.is_feature_set(av.FEATURE_MONITOR_METHOD_CALLS_WITH_ANDROLOG):
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
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        target_sdk_jar = self.get_target_sdk_jar(app=context.input_app)
        if os.path.exists(target_sdk_jar):
            target_sdk_dir = fs_utils.get_immediate_parent_folder(fs_utils.get_immediate_parent_folder(target_sdk_jar))
        else:
            raise NotImplementedError("Specific jar for the expected sdk is missing")
        if context.merged_apk is not None:
            self.execute_tool(
                ToolAndrologInstrumentation(androlog_jar=self.tool_androlog, platform_dir=target_sdk_dir,
                                            input_file=context.merged_apk,
                                            output_dir=output_dir))
        else:
            if context.input_app.has_split_pkgs():
                raise RuntimeError("If it has splits, it should be merged before")
            else:
                input_app = context.input_app.get_base_pkg()
                self.execute_tool(
                    ToolAndrologInstrumentation(androlog_jar=self.tool_androlog, platform_dir=target_sdk_dir,
                                                input_file=input_app,
                                                output_dir=output_dir))
        created_app = fs_utils.list_files(output_dir)
        assert len(created_app) == 1
        context.context_data["androlog"] = created_app.pop()

    def repack_single_apk(self, unpack_dir_path, is_base: bool, context: MakerContext):
        androlog_app = context.context_data["androlog"]
        if not os.path.exists(androlog_app):
            raise RuntimeError("Missing androlog instrumented file")
        return androlog_app

    def post_process(self, context: MakerContext):
        pass
