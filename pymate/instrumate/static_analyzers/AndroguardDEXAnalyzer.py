import os
import logging
import string
import base64
from loguru import logger
from androguard.core.apk import APK
from androguard.misc import AnalyzeAPK
from androguard.core.analysis.analysis import Analysis
from androguard.core.dex import DEX, ClassDefItem, MethodIdItem, EncodedMethod, EncodedField

from pymate.instrumate.static_analyzers.androguard_utils import get_method_signature, \
    get_field_signature, get_method_id_signature
from pymate.common.app import App
from pymate.instrumate.static_analyzer import StaticAnalyzer


class AndroguardDEXAnalyzer(StaticAnalyzer):
    def configure(self, tmp_dir: str = None, output_dir: str = None, tools_dir: str = None, name: str = None,
                  instrumate_log=None):
        super().configure(tmp_dir=tmp_dir, output_dir=output_dir, tools_dir=tools_dir,
                          name="Androguard DEX Analyzer", instrumate_log=instrumate_log)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.save_strings_to_global_log = False

    def analyze_app(self, app: App):
        # loguru
        logger.remove()
        if self.logger.isEnabledFor(logging.DEBUG):
            logger.add(sink=os.path.join(self.tmp_dir, "loguru.log"), level="DEBUG")
        else:
            logger.add(lambda _: None)
        # loguru
        analysis: Analysis
        androguard_apk: APK
        self.logger.debug("Opening dex file. Lazy Operation.")
        androguard_apk, dex_files, analysis = AnalyzeAPK(app.get_base_pkg())
        dex_file: DEX
        dex_analysis_result = {}
        for index, dex_file in enumerate(dex_files):
            dex_analysis = {}
            qtd_classes = 0
            dex_methods = []
            dex_class_defined_methods = []
            dex_class_free_methods = []
            fields = []
            clss: ClassDefItem
            for clss in dex_file.get_classes():
                qtd_classes = qtd_classes + 1
                field: EncodedField
                for field in clss.get_fields():
                    fields.append(get_field_signature(field))
                clss_m: EncodedMethod
                for clss_m in clss.get_methods():
                    dex_class_defined_methods.append(get_method_signature(clss_m))
            clss_m_id: MethodIdItem
            for clss_m_id in dex_file.get_methods():
                method_signature = get_method_id_signature(clss_m_id)
                dex_methods.append(method_signature)
                if method_signature not in dex_class_defined_methods and clss_m_id.get_name() != '<init>':
                    dex_class_free_methods.append(method_signature)
            dex_analysis["num_classes"] = qtd_classes
            dex_analysis["num_methods"] = len(dex_methods)
            dex_analysis["num_strings"] = len(dex_file.get_strings())
            dex_analysis["num_fields"] = len(fields)
            dex_analysis["num_class_free_methods"] = len(dex_class_free_methods)
            dex_analysis["dex_methods"] = sorted(dex_methods)
            dex_analysis["class_free_methods"] = sorted(dex_class_free_methods)
            dex_analysis["dex_fields"] = sorted(fields)
            dex_analysis["dex_strings"] = sorted(dex_file.get_strings())
            dex_analysis["dex_file"] = index
            dex_analysis_result[f"dex_{index}"] = dex_analysis
        app.set_dex_static_analysis(dex_analysis_result)

    def save_analysis(self, app: App):
        self.register_log(
            "apk_dex_summary",
            ["dex_item", "num_classes", "num_methods", "num_strings", "num_fields", "num_class_free_methods"]
        )
        self.register_log(
            "apk_dex_methods",
            ["dex_item", "method"]
        )
        self.register_log(
            "apk_dex_fields",
            ["dex_item", "field"]
        )
        self.register_log(
            "apk_dex_strings",
            ["dex_item", "printable_string_value", "raw_b64_string"]
        )
        self.register_log(
            "apk_dex_free_methods",
            ["dex_item", "method"]
        )
        dex_analysis_result = app.get_dex_static_analysis()
        if dex_analysis_result is not None:
            for key in dex_analysis_result:
                dex_analysis = dex_analysis_result[key]
                self.record_log("apk_dex_summary",
                                app,
                                [dex_analysis["dex_file"], dex_analysis["num_classes"], dex_analysis["num_methods"],
                                 dex_analysis["num_strings"], dex_analysis["num_fields"],
                                 dex_analysis["num_class_free_methods"]])
                methods = dex_analysis["dex_methods"]
                class_free_methods = dex_analysis["class_free_methods"]
                fields = dex_analysis["dex_fields"]
                strings = dex_analysis["dex_strings"]
                for m in methods:
                    self.record_log("apk_dex_methods",
                                    app,
                                    [dex_analysis["dex_file"], m])
                for m in class_free_methods:
                    self.record_log("apk_dex_free_methods",
                                    app,
                                    [dex_analysis["dex_file"], m])
                for f in fields:
                    self.record_log("apk_dex_fields",
                                    app,
                                    [dex_analysis["dex_file"], f])
                printable = set(string.printable)
                if self.save_strings_to_global_log:
                    for s in strings:
                        safe_str = 'failed'
                        b64_str = 'failed'
                        try:
                            safe_str = ''.join(filter(lambda x: x in printable, s))
                            b64_str = base64.b64encode(s.encode('utf-8'))
                        except:
                            pass
                        self.record_log("apk_dex_strings",
                                        app,
                                        [dex_analysis["dex_file"], safe_str, b64_str])
