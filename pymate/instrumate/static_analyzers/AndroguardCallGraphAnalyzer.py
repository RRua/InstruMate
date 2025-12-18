import os
import networkx as nx
import logging
from loguru import logger
from androguard.core.apk import APK
from androguard.misc import AnalyzeAPK
from androguard.core.analysis.analysis import Analysis, ClassAnalysis, MethodAnalysis
from androguard.core.dex import DEX, ClassDefItem, ClassManager, MethodIdItem
from pymate.utils import utils
from pymate.common.app import App
from pymate.instrumate.static_analyzer import StaticAnalyzer


def get_method_signature(method):
    method_name = method.get_name().replace(';', '')
    class_name = method.get_class_name().replace(';', '')
    descriptor = ",".join(method.get_descriptor().replace('(', '').split(')')[0].replace(' ', '').split(';'))
    method_signature = f"{class_name}.{method_name}({descriptor})"
    return method_signature.replace('/', '.')


class AndroguardCallGraphAnalyzer(StaticAnalyzer):
    def configure(self, tmp_dir: str = None, output_dir: str = None, tools_dir: str = None, name: str = None,
                  instrumate_log=None):
        super().configure(tmp_dir=tmp_dir, output_dir=output_dir, tools_dir=tools_dir,
                          name="Androguard Static Call Graph Analyzer", instrumate_log=instrumate_log)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.global_log_enabled = False

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
        androguard_apk, dex_files, analysis = AnalyzeAPK(app.get_base_pkg())
        call_graph: nx.DiGraph
        call_graph = analysis.get_call_graph()
        nodes = [get_method_signature(item) for item in call_graph.nodes]
        edges = [{"from": get_method_signature(edge_from), "to": get_method_signature(edge_to)} for edge_from, edge_to
                 in
                 call_graph.edges(data=False)]

        call_graph_result = {"nodes": nodes, "edges": edges}
        utils.write_dict_as_json(json_dict=call_graph_result, base_dir=self.output_dir,
                                 file_name="call_graph.json", overwrite_existing=True)
        app.set_call_graph(call_graph_result)

    def save_analysis(self, app: App):
        if not self.global_log_enabled:
            return
        self.register_log(
            "apk_call_graph_nodes",
            ["node_id"]
        )
        self.register_log(
            "apk_call_graph_edges",
            ["node_from", "node_to"]
        )
        call_graph_result = app.get_call_graph()
        if call_graph_result is not None:
            edges = call_graph_result["edges"]
            for e in edges:
                self.record_log("apk_call_graph_edges",
                                app,
                                [e["from"], e["to"]])
