import logging
import os
import re
import time

from pymate.common.app_variant import AppVariant
from pymate.utils import fs_utils, utils
from pymate.utils.utils import get_md5_sha1_sha256_hashes, get_md5_hash_for_str


def _get_ctrl_file(dest_dir):
    ctrl_file = os.path.join(dest_dir, 'ctrl.fm')
    return ctrl_file


class App:
    def __init__(self, apk_base_path: str = None, extra_split_pkgs=None, variant_info: AppVariant = None,
                 initial_properties=None, pkg_name: str = None):
        self.app_properties = initial_properties
        if extra_split_pkgs is None:
            extra_split_pkgs = []
        if self.app_properties is None:
            self.app_properties = {}
        self.call_graph = None
        self.dex_static_analysis = None
        self.native_static_analysis = None
        self.content_type_analysis = None
        self.possible_modifications_analysis = None
        self.set_split_pkgs([])
        self.logger = logging.getLogger(self.__class__.__name__)
        if apk_base_path is not None:
            self.set_base_pkg(apk_base_path)
            if extra_split_pkgs is not None and len(extra_split_pkgs) > 0:
                self.set_split_pkgs(extra_split_pkgs)
        else:
            if pkg_name is None:
                raise RuntimeError("Must provide either a pkg_name or apk_paths.")
            else:
                self.set_package_name(pkg_name)
        app_id_str = ""
        if self.get_base_pkg() is not None:
            if not os.path.exists(self.get_base_pkg()):
                raise RuntimeError(f"Base pkg file does not exists {self.get_base_pkg()}")
            else:
                hashes = get_md5_sha1_sha256_hashes(self.get_base_pkg())
                self.set_base_pkg_hashes(hashes)
                self.set_base_pkg_hash(hashes[0])
                self.set_base_file_name(os.path.basename(self.get_base_pkg()))
                app_id_str = app_id_str + ":" + hashes[0]
            splits_data = {}
            for item in self.get_split_pkgs():
                if not os.path.exists(item):
                    raise RuntimeError(f"Split pkg file does not exists {item}")
                else:
                    hashes = get_md5_sha1_sha256_hashes(self.get_base_pkg())
                    splits_data[item] = {
                        "hashes": hashes,
                        "hash": hashes[0],
                        "file_name": os.path.basename(item)
                    }
                    app_id_str = app_id_str + ":" + hashes[0]
            self.set_splits_data(splits_data)
            self.set_app_id(get_md5_hash_for_str(app_id_str))
        if variant_info is not None:
            self.app_properties["variant_info"] = variant_info.to_dict()
        else:
            if "variant_info" not in self.app_properties:
                self.app_properties["variant_info"] = None

    def exists_at_dir(self, dest_dir: str):
        if os.path.exists(_get_ctrl_file(dest_dir)):
            return True
        return False

    def save_to_dir(self, dest_dir: str, force_overwrite=True, move=False):
        self.logger.info(f"saving app {self.get_package_name()} to dir {dest_dir}")
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        else:
            if not force_overwrite:
                raise RuntimeError(f"Dest dir does already exists {dest_dir}")
        installers_dir = os.path.join(dest_dir, "installers")
        dest_base_pkg = os.path.join(installers_dir, fs_utils.get_file_without_parent(self.get_base_pkg()))
        if move:
            fs_utils.move_file(self.get_base_pkg(), dest_base_pkg)
        else:
            fs_utils.copy_file(self.get_base_pkg(), dest_base_pkg, force=force_overwrite)
        self.set_base_pkg(dest_base_pkg)
        new_split_dests = []
        for split in self.get_split_pkgs():
            dest_split_pkg = os.path.join(installers_dir, fs_utils.get_file_without_parent(split))
            if move:
                fs_utils.move_file(split, dest_split_pkg)
            else:
                fs_utils.copy_file(split, dest_split_pkg, force=force_overwrite)
            new_split_dests.append(dest_split_pkg)
        self.set_split_pkgs(new_split_dests)
        utils.write_dict_as_json(self.app_properties, dest_dir, "app.json", overwrite_existing=force_overwrite)
        if self.call_graph is not None:
            utils.write_dict_as_json(self.call_graph, dest_dir, "call_graph.json", overwrite_existing=force_overwrite)
        if self.dex_static_analysis is not None:
            for analysis_item in self.dex_static_analysis:
                src_relative_path = analysis_item["relative_path"]
                src_ra2_analysis_path = analysis_item["rabin2_analysis"]
                if src_ra2_analysis_path is not None:
                    dst_file_name = utils.replace_path_separators_cross_platform(src_relative_path)
                    analysis_dest_file = os.path.join(dest_dir, f"rabin2_{dst_file_name}.json")
                    fs_utils.move_file(src_ra2_analysis_path, analysis_dest_file)
                    analysis_item["rabin2_analysis"] = analysis_dest_file
            utils.write_dict_as_json(self.dex_static_analysis, dest_dir, "dex_static_analysis.json",
                                     overwrite_existing=force_overwrite)
        if self.native_static_analysis is not None:
            for analysis_item in self.native_static_analysis:
                src_relative_path = analysis_item["relative_path"]
                src_ra2_analysis_path = analysis_item["rabin2_analysis"]
                if src_ra2_analysis_path is not None:
                    dst_file_name = utils.replace_path_separators_cross_platform(src_relative_path)
                    analysis_dest_file = os.path.join(dest_dir, f"rabin2_{dst_file_name}.json")
                    fs_utils.move_file(src_ra2_analysis_path, analysis_dest_file)
                    analysis_item["rabin2_analysis"] = analysis_dest_file
            utils.write_dict_as_json(self.native_static_analysis, dest_dir, "native_static_analysis.json",
                                     overwrite_existing=force_overwrite)
        if self.content_type_analysis is not None:
            utils.write_dict_array_as_csv(self.content_type_analysis, dest_dir, "content_type_analysis.csv", True)
        if self.possible_modifications_analysis is not None:
            utils.write_dict_as_json(self.possible_modifications_analysis, dest_dir,
                                     "possible_modifications_analysis.json", overwrite_existing=force_overwrite)
        with open(_get_ctrl_file(dest_dir), 'w') as file:
            file.write(str(int(time.time() * 1000)))

    @staticmethod
    def load_from_dir(base_dir: str, json_file: str = None, installers_dir: str = None):
        if json_file is None:
            json_file = os.path.join(base_dir, 'app.json')
        if installers_dir is None:
            installers_dir = os.path.join(base_dir, 'installers')
        if not os.path.exists(base_dir) or not os.path.exists(installers_dir) or not os.path.exists(json_file):
            raise RuntimeError(
                f"Missing dirs. Assert that all the paths exists: {base_dir}, {json_file}, {installers_dir}")

        app_properties = utils.read_json_as_dict(file_name=json_file)
        apk_files = fs_utils.list_files(directory_path=installers_dir, extension="apk")
        pattern = r'\bbase\b'
        base_files = [item for item in apk_files if re.search(pattern, item, re.IGNORECASE)]
        if len(base_files) != 1:
            raise RuntimeError(f"Base installation packages not found: {base_dir}")
        split_files = [item for item in apk_files if item != base_files[0]]
        app = App(apk_base_path=base_files[0], extra_split_pkgs=split_files, initial_properties=app_properties)
        return app

    def free_memory(self):
        self.content_type_analysis = None
        self.possible_modifications_analysis = None

    def set_app_id(self, app_id: str):
        self.app_properties["app_id"] = app_id

    def get_app_id(self):
        return self.app_properties.get("app_id", None)

    def set_base_pkg_hashes(self, hashes):
        self.app_properties["base_pkg_hashes"] = hashes

    def get_base_pkg_hashes(self):
        return self.app_properties.get("base_pkg_hashes", None)

    def set_base_pkg_hash(self, hash):
        self.app_properties["base_pkg_hash"] = hash

    def get_base_pkg_hash(self):
        return self.app_properties.get("base_pkg_hash", None)

    def get_base_pkg(self):
        return self.app_properties.get("base_pkg", None)

    def set_base_file_name(self, file_name):
        self.app_properties["base_file_name"] = file_name

    def get_base_file_name(self):
        return self.app_properties.get("base_file_name", None)

    def set_base_pkg(self, apk_base_pkg):
        self.app_properties["base_pkg"] = apk_base_pkg

    def set_splits_data(self, splits_data):
        self.app_properties["splits_data"] = splits_data

    def get_splits_data(self):
        return self.app_properties.get("splits_data", None)

    def get_split_pkgs(self):
        return self.app_properties.get("split_pkgs", None)

    def has_split_pkgs(self):
        return "split_pkgs" in self.app_properties and len(self.app_properties["split_pkgs"]) > 0

    def set_split_pkgs(self, split_pkgs):
        self.app_properties["split_pkgs"] = split_pkgs

    def get_package_name(self):
        return self.app_properties.get("package_name", None)

    def set_package_name(self, package_name):
        self.app_properties["package_name"] = package_name

    def get_min_sdk_version(self):
        return self.app_properties.get("min_sdk_version", None)

    def set_min_sdk_version(self, min_sdk_version):
        self.app_properties["min_sdk_version"] = min_sdk_version

    def get_max_sdk_version(self):
        return self.app_properties.get("max_sdk_version", None)

    def set_max_sdk_version(self, max_sdk_version):
        self.app_properties["max_sdk_version"] = max_sdk_version

    def get_target_sdk_version(self):
        return self.app_properties.get("target_sdk_version", None)

    def set_target_sdk_version(self, target_sdk_version):
        self.app_properties["target_sdk_version"] = target_sdk_version

    def get_app_version_name(self):
        return self.app_properties.get("app_version_name", None)

    def set_app_version_name(self, app_version_name):
        self.app_properties["app_version_name"] = app_version_name

    def get_app_version_code(self):
        return self.app_properties.get("app_version_code", None)

    def set_app_version_code(self, app_version_code):
        self.app_properties["app_version_code"] = app_version_code

    def get_app_implied_permissions(self):
        return self.app_properties.get("app_implied_permissions", None)

    def set_app_implied_permissions(self, app_implied_permissions):
        self.app_properties["app_implied_permissions"] = app_implied_permissions

    def get_services(self):
        return self.app_properties.get("services", None)

    def set_services(self, services):
        self.app_properties["services"] = services

    def get_main_activity(self):
        return self.app_properties.get("main_activity", None)

    def set_main_activity(self, main_activity):
        self.app_properties["main_activity"] = main_activity

    def get_permissions(self):
        return self.app_properties.get("permissions", None)

    def set_permissions(self, permissions):
        self.app_properties["permissions"] = permissions

    def get_activities(self):
        return self.app_properties.get("activities", None)

    def set_activities(self, activities):
        self.app_properties["activities"] = activities

    def get_features(self):
        return self.app_properties.get("features", None)

    def set_features(self, features):
        self.app_properties["features"] = features

    def get_possible_broadcasts(self):
        return self.app_properties.get("possible_broadcasts", None)

    def set_possible_broadcasts(self, possible_broadcasts):
        self.app_properties["possible_broadcasts"] = possible_broadcasts

    def get_app_name(self):
        return self.app_properties.get("app_name", None)

    def set_app_name(self, app_name):
        self.app_properties["app_name"] = app_name

    def set_app_icon(self, app_icon):
        self.app_properties["app_icon"] = app_icon

    def get_app_icon(self):
        return self.app_properties.get("app_icon", None)

    def set_call_graph(self, call_graph):
        self.call_graph = call_graph

    def get_call_graph(self):
        return self.call_graph

    def set_dex_static_analysis(self, dex_static_analysis):
        self.dex_static_analysis = dex_static_analysis

    def get_dex_static_analysis(self):
        return self.dex_static_analysis

    def set_native_static_analysis(self, native_static_analysis):
        self.native_static_analysis = native_static_analysis

    def get_native_static_analysis(self):
        return self.native_static_analysis

    def set_content_type_analysis(self, content_type_analysis):
        self.content_type_analysis = content_type_analysis

    def get_content_type_analysis(self):
        return self.content_type_analysis

    def set_possible_modifications_analysis(self, possible_modifications_analysis):
        self.possible_modifications_analysis = possible_modifications_analysis

    def get_possible_modifications_analysis(self):
        return self.possible_modifications_analysis

    def set_variant_info(self, variant_info):
        self.app_properties["variant_info"] = variant_info

    def get_variant_info(self):
        return self.app_properties.get("variant_info", None)

    def is_variant(self):
        return self.get_variant_info() is not None

    def get_variant_maker_tag(self):
        variant_info_dict = self.get_variant_info()
        if variant_info_dict is not None:
            return variant_info_dict["variant_tag"]
        return None

    def get_variant_bin_features(self):
        variant_info_dict = self.get_variant_info()
        if variant_info_dict is not None:
            return variant_info_dict["variant_features_bin"]
        return None

    def get_variant_bin_levels(self):
        variant_info_dict = self.get_variant_info()
        if variant_info_dict is not None:
            return variant_info_dict["variant_levels_bin"]
        return None

    def get_variant_feature_labels(self):
        variant_info_dict = self.get_variant_info()
        if variant_info_dict is not None:
            return variant_info_dict["variant_feature_labels"]
        return None

    def get_variant_level_labels(self):
        variant_info_dict = self.get_variant_info()
        if variant_info_dict is not None:
            return variant_info_dict["variant_level_labels"]
        return None

    def get_variant_tag(self):
        variant_info_dict = self.get_variant_info()
        if variant_info_dict is not None:
            return variant_info_dict["variant_tag"]
        return None

    def get_dex_files_in_base(self):
        return self.app_properties.get("dex_files_in_base", [])

    def add_dex_file_in_base(self, file_name):
        if "dex_files_in_base" not in self.app_properties:
            self.app_properties["dex_files_in_base"] = []
        self.app_properties["dex_files_in_base"].append(file_name)

    def add_native_file_in_base(self, file_name):
        if "native_files_in_base" not in self.app_properties:
            self.app_properties["native_files_in_base"] = []
        self.app_properties["native_files_in_base"].append(file_name)

    def get_dex_files_in_splits(self):
        dict_obj = self.app_properties.get("dex_file_in_splits", {})
        result = []
        for key in dict_obj:
            result.extend(dict_obj[key]["dex_files"])
        return result

    def add_dex_file_in_split(self, split_name, file_name):
        if "dex_file_in_splits" not in self.app_properties:
            self.app_properties["dex_file_in_splits"] = {}
        dex_file_in_splits = self.app_properties["dex_file_in_splits"]
        if split_name not in dex_file_in_splits:
            dex_file_in_splits[split_name] = {
                "split_name": split_name,
                "dex_files": [file_name]
            }
        else:
            dex_file_in_splits[split_name]["dex_files"].append(file_name)

    def add_native_file_in_split(self, split_name, file_name):
        if "native_file_in_splits" not in self.app_properties:
            self.app_properties["native_file_in_splits"] = {}
        native_file_in_splits = self.app_properties["native_file_in_splits"]
        if split_name not in native_file_in_splits:
            native_file_in_splits[split_name] = {
                "split_name": split_name,
                "native_files": [file_name]
            }
        else:
            native_file_in_splits[split_name]["native_files"].append(file_name)

if __name__ == "__main__":
    # main()
    apps1 = App.load_from_dir(base_dir="I:\\git\\forensicmate-results\\iterations\\5_instrumate-mime-type\\"
                                       "com.dsi.ant.service.socket\\"
                                       "com.dsi.ant.service.socket-4.18.00_chgstringres-signature-resources_by-apkeditor")
