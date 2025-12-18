from abc import ABC, abstractmethod
from pymate.common.app import App, AppVariant
from pymate.instrumate.variant_maker import VariantMaker, MakerContext
from pymate.utils import fs_utils


class DeprecatedGenericRepackager(VariantMaker, ABC):
    def __init__(self, name: str = None, tag: str = None):
        super().__init__(name=self.__class__.__name__, tag=tag)

    @abstractmethod
    def unpack_single_apk(self, file_path, is_base: bool, context: MakerContext):
        raise NotImplementedError("Subclasses should implement this method")

    @abstractmethod
    def repack_single_apk(self, unpacked_dir, is_base: bool, context: MakerContext):
        raise NotImplementedError("Subclasses should implement this method")

    @abstractmethod
    def modify_single_apk(self, unpacked_dir, is_base: bool, context: MakerContext):
        raise NotImplementedError("Subclasses should implement this method")

    def unpack(self, context: MakerContext):
        unpacked_files = {}
        if context.merged_apk is not None:
            merged_unpacked = self.unpack_single_apk(context.merged_apk, True, context)
            context.context_data["base_file_pointer"] = context.merged_apk
            unpacked_files[context.merged_apk] = merged_unpacked
        else:
            base_pkg_file = context.input_app.get_base_pkg()
            base_pkg_file_unpacked = self.unpack_single_apk(base_pkg_file, True, context)
            context.context_data["base_file_pointer"] = base_pkg_file
            unpacked_files[base_pkg_file] = base_pkg_file_unpacked
            for index, split in enumerate(context.input_app.get_split_pkgs()):
                split_unpacked = self.unpack_single_apk(split, False, context)
                unpacked_files[split] = split_unpacked
        context.context_data["unpacked_files"] = unpacked_files

    def modify(self, context: MakerContext):
        if "unpacked_files" not in context.context_data:
            raise RuntimeError("No unpacked dirs for modification")
        unpacked_files = context.context_data["unpacked_files"]
        for key in unpacked_files:
            unpack_dir_path = unpacked_files[key]
            self.modify_single_apk(unpack_dir_path, context.context_data["base_file_pointer"] == key, context)

    def repack(self, context: MakerContext):
        if "unpacked_files" not in context.context_data:
            raise RuntimeError("No unpacked dirs to be repackaged")
        unpacked_files = context.context_data["unpacked_files"]
        variant = AppVariant(variant_features=context.spec.variant_features, variant_levels=context.spec.variant_levels,
                             tag=self.tag)
        #repack base apk
        base_pkg_file = context.input_app.get_base_pkg()
        if context.merged_apk is not None:
            unpacked_dir = unpacked_files[context.merged_apk]
        else:
            unpacked_dir = unpacked_files[base_pkg_file]
        tmp_file = self.repack_single_apk(unpacked_dir, True, context)
        final_base_file = self.get_final_variant_file(base_pkg_file, variant)
        fs_utils.move_file(tmp_file, final_base_file)

        #repack splits
        new_splits = []
        for index, split in enumerate(context.input_app.get_split_pkgs()):
            if split not in unpacked_files:
                continue
            split_unpacked = unpacked_files[split]
            final_split_file = self.get_final_variant_file(split, variant)
            tmp_file = self.repack_single_apk(split_unpacked, False, context)
            fs_utils.move_file(tmp_file, final_split_file)
            new_splits.append(final_split_file)
        context.output_app = App(apk_base_path=final_base_file, extra_split_pkgs=new_splits, variant_info=variant)
