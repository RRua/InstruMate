import os
import logging
from pymate.common.app import App
from pymate.instrumate.instrumate_log import InstruMateLog
from abc import abstractmethod


class StaticAnalyzer:

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.name = None
        self.tmp_dir = None
        self.output_dir = None
        self.tools_dir = None
        self.apktool_path = None
        self.instrumate_log: InstruMateLog = None

    def configure(self, tmp_dir: str = None, output_dir: str = None, tools_dir: str = None, name: str = None,
                  instrumate_log: InstruMateLog = None):
        if name is not None:
            self.name = name
        else:
            self.name = self.__class__.__name__
        self.tmp_dir = tmp_dir
        self.output_dir = output_dir
        self.tools_dir = tools_dir
        self.instrumate_log = instrumate_log
        self.apktool_path = os.path.join(self.tools_dir, 'misc', "apktool.jar")

    def register_log(self, log_name, log_columns):
        self.instrumate_log.register_generic_logger(log_name,
                                                    ["app_id", "package_name", "original", "features_flag",
                                                     "features_str",
                                                     "level_flag", "levels_str", "maker_tag"] + log_columns)

    def record_log(self, log_name, app: App, log_data):
        if app.is_variant():
            original = False
            features_flag = app.get_variant_bin_features()
            features_labels = "-".join(app.get_variant_feature_labels())
            levels_flag = app.get_variant_bin_levels()
            levels_flag_str = app.get_variant_level_labels()
            maker_tag = app.get_variant_maker_tag()
        else:
            original = True
            features_flag = None
            features_labels = None
            levels_flag = None
            levels_flag_str = None
            maker_tag = None
        app_id = app.get_app_id()
        package_id = app.get_package_name()
        self.instrumate_log.record_generic_log(log_name, [app_id, package_id, original, features_flag, features_labels, levels_flag,
                                                          levels_flag_str, maker_tag] + log_data)

    def get_name(self):
        return self.name

    @abstractmethod
    def analyze_app(self, app: App):
        raise NotImplementedError('This method should be implemented by subclasses')

    def save_analysis(self, app: App):
        pass
