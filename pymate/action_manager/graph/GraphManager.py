import networkx as nx
import json
from pymate.utils import utils
from pymate.action_manager.graph.UIActionUnit import UIActionUnit
from pymate.action_manager.graph.Action import ActionBag
from pymate.forensic_state import MultipleStateItem, ViewStateObserver, SandboxedEnvironmentObserver, \
    FileSystemStateObserver
import os
import re

START_SNAPSHOT = "START.png"
END_SNAPSHOT = "END.png"
MISSING_SNAPSHOT = "MISSING.png"


class GraphManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(GraphManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, states_dir: str, graph_dir: str, flatten_dicts=False, load_graph_from_dir = True):
        if not hasattr(self, 'initialized'):
            import logging
            self.logger = logging.getLogger(self.__class__.__name__)
            self.initialized = True
            self.states_dir = states_dir
            self.graph = nx.DiGraph()
            self.add_state_node("None", {
                "snapshot": START_SNAPSHOT,
                "top_activity": '',
            })
            self.graph_dir = graph_dir
            self.flatten_dicts = flatten_dicts
            if not os.path.exists(self.graph_dir):
                os.makedirs(self.graph_dir)
            self.current_node_id = None
            self.last_node_id = None
            self.node_history = []
            if load_graph_from_dir:
                self.load_graph_from_states_dir()

    def add_state_node(self, node_id: str, node_properties: dict):
        self.graph.add_node(node_id, **node_properties)

    def add_state_node_dict(self, multiple_state: MultipleStateItem):
        signature = multiple_state.get_signature()
        if signature in self.graph.nodes:
            return
        node_props = {}
        view_state = multiple_state.get_state_by_class(ViewStateObserver)
        sandboxed_state = multiple_state.get_state_by_class(SandboxedEnvironmentObserver)
        fs_state = multiple_state.get_state_by_class(FileSystemStateObserver)
        if view_state is not None:
            self._load_view_state_props_from_dict(view_state.to_dict(), node_props)
        if sandboxed_state is not None:
            self._load_sandbox_state_props_from_dict(sandboxed_state.to_dict(), node_props)
        if fs_state is not None:
            self._load_fs_state_props_from_dict(fs_state.to_dict(), node_props)
        self.add_state_node(signature, node_props)

    def add_state_transition(self, from_id: str, to_id: str, edge_properties):
        self.graph.add_edge(from_id, to_id, **edge_properties)

    def add_state_transition_dict(self, transition_dict, policy_classifier, from_signature, to_signature):
        transition_props = {}
        if self.flatten_dicts:
            raise NotImplementedError()
        transition_props.update(transition_dict)
        transition_props["classifier"] = policy_classifier
        self.add_state_transition(from_signature, to_signature, transition_props)

    def load_graph_from_states_dir(self):
        self._load_graph_from_dir(self.states_dir)

    def save_graphml(self):
        if self.flatten_dicts:
            file_path = os.path.join(self.graph_dir, "graph.graphml")
            nx.write_graphml(self.graph, file_path)
        else:
            raise NotImplementedError("Graphml is not possible if the graph has dicts as properties. "
                                      "Use flatten_dicts=True")

    def load_graph(self):
        file_path = os.path.join(self.graph_dir, "graph.graphml")
        self.graph = nx.read_graphml(file_path)

    def save_graph_vis_json(self):
        graph_nodes = []
        graph_edges = []
        g_nodes = list(self.graph.nodes(data=True))
        g_edges = list(self.graph.edges(data=True))
        for node_id, data in g_nodes:
            new_dict = data.copy()
            new_dict["id"] = node_id
            base_states_dir = os.path.basename(self.states_dir)
            actual_snapshot_file = os.path.join(self.states_dir, data["snapshot"])
            if os.path.isfile(actual_snapshot_file):
                img_str = "./%s/%s" % (base_states_dir, data["snapshot"])
            else:
                img_str = "./%s/%s" % (base_states_dir, MISSING_SNAPSHOT)
            new_dict["image"] = img_str
            new_dict["label"] = node_id
            new_dict["shape"] = "image"
            graph_nodes.append(new_dict)
        for edge_from_id, edge_to_id, data in g_edges:
            new_dict = data.copy()
            new_dict["from"] = edge_from_id
            new_dict["to"] = edge_to_id
            graph_edges.append(new_dict)

        final_dict = {
            "nodes": graph_nodes,
            "edges": graph_edges,
        }
        utils.write_dict_as_json(final_dict, base_dir=self.graph_dir, file_name="graph-vis.json",
                                 overwrite_existing=True)

    def save_graph_vis_utg(self, overwrite_existing=True):
        utg_nodes = []
        utg_edges = []
        g_nodes = list(self.graph.nodes(data=True))
        g_edges = list(self.graph.edges(data=True))
        base_states_dir = os.path.basename(self.states_dir)
        for node_id, data in g_nodes:
            img_str = "%s/%s" % (base_states_dir, data["snapshot"])
            utg_node = {
                "id": node_id,
                "shape": "image",
                "image": img_str,
                "label": data["top_activity"],
                "package": "change to activity stack",
                "activity": data["top_activity"],
                "state_str": node_id,
                "structure_str": "remove ",
                "title": "<table class=\"table\">\n"
                         "<tr><th>package</th><td>com.sec.android.app.launcher</td></tr>\n"
                         "<tr><th>activity</th><td>.activities.LauncherActivity</td></tr>\n"
                         "<tr><th>state_str</th><td>1bfca49c3ffe6e53b50b999f7677b934ef4a12e6c0036153b4476021a01f9cd2</td></tr>\n"
                         "<tr><th>structure_str</th><td>5564041755f41ac95626ccae753b3333</td></tr>\n</table>",
                "content": "com.sec.android.app.launcher\n"
                           ".activities.LauncherActivity\n"
                           "1bfca49c3ffe6e53b50b999f7677b934ef4a12e6c0036153b4476021a01f9cd2\n"
                           "com.sec.android.app.launcher:id/iconview_titleView,com.google.android.googlequicksearchbox:id/search_widget_voice_btn,com.sec.android.widgetapp.samsungapps:id/title_text,com.sec.android.app.launcher:id/home_view,com.sec.android.widgetapp.samsungapps:id/description_text,com.sec.android.app.launcher:id/launcher,com.google.android.googlequicksearchbox:id/search_widget_background,com.sec.android.widgetapp.samsungapps:id/view_flipper,com.sec.android.app.launcher:id/home_page_indicator,com.google.android.googlequicksearchbox:id/search_widget_voice_hint,com.sec.android.widgetapp.samsungapps:id/app_display_icon2,com.sec.android.widgetapp.samsungapps:id/interim_essentials,com.sec.android.app.launcher:id/iconview_shadow,com.sec.android.daemonapp:id/widget_empty_icon,com.sec.android.app.launcher:id/swipe_affordance,com.google.android.googlequicksearchbox:id/search_widget_google_full,com.sec.android.app.launcher:id/iconview_image_preview,com.sec.android.app.launcher:id/hotseat,com.google.android.googlequicksearchbox:id/default_search_widget,com.sec.android.widgetapp.samsungapps:id/app_display_icon1,com.google.android.googlequicksearchbox:id/search_plate_container,com.sec.android.app.launcher:id/workspace,com.google.android.googlequicksearchbox:id/search_widget_background_protection,com.google.android.googlequicksearchbox:id/search_plate,com.sec.android.app.launcher:id/inactive,com.sec.android.app.launcher:id/iconview_imageView,android:id/content,com.sec.android.daemonapp:id/widget_background,com.google.android.googlequicksearchbox:id/search_widget_google_logo,com.sec.android.app.launcher:id/layout,com.sec.android.daemonapp:id/widget_empty_layout,com.sec.android.app.launcher:id/drag_layer,com.google.android.googlequicksearchbox:id/search_edit_frame,com.sec.android.app.launcher:id/swipe_affordance_arrow_frame,com.google.android.googlequicksearchbox:id/hint_text_alignment,com.sec.android.app.launcher:id/active\nGoogle,Samsung Pay,C\u00e2mera,Galaxy Apps,Pasta Segura,Aplicativos Microsoft,Play Store,Aplicativos que voc\u00ea precisa ter projetados para seu Galaxy.,Mensagens,Notas,Internet,Galeria,Telefone,Contatos,Word,Calend\u00e1rio,Galaxy Essentials,Rel\u00f3gio",
                "font": "14px Arial red"
            }
            utg_nodes.append(utg_node)

        for edge_from_id, edge_to_id, data in g_edges:
            utg_edge = {
                "from": edge_from_id,
                "to": edge_to_id,
                "id": f"{edge_from_id}-->{edge_to_id}",
                "title": "<table class=\"table\">\n"
                         "<tr><th>1</th><td>IntentEvent(intent='am start com.simplemobiletools.calendar.pro/com.simplemobiletools.calendar.pro.activities.SplashActivity.Orange')</td></tr>\n"
                         "</table>",
                "label": f"{edge_from_id}-->{edge_to_id}",
                "events": [
                    {
                        "event_str": "IntentEvent(intent='am start com.simplemobiletools.calendar.pro/com.simplemobiletools.calendar.pro.activities.SplashActivity.Orange')",
                        "event_id": 1,
                        "event_type": "intent",
                        "view_images": []
                    }
                ]
            }
            utg_edges.append(utg_edge)
        utg_str = utils.dict_as_formatted_json({
            "nodes": utg_nodes,
            "edges": utg_edges,
            "num_nodes": len(utg_nodes),
            "num_edges": len(utg_edges),
            "num_effective_events": 31,
            "num_reached_activities": 2,
            "test_date": "2024-02-24 10:43:44",
            "time_spent": 1028.384312,
            "num_transitions": 150,
            "device_serial": "fddedc49",
            "device_model_number": "SM-A910F",
            "device_sdk_version": 26,
            "app_sha256": "0bdbb72a704bce36737c721ce5b68f3e5b9338eac4988bd6a69403c15a9cff8b",
            "app_package": "com.simplemobiletools.calendar.pro",
            "app_main_activity": "com.simplemobiletools.calendar.pro.activities.SplashActivity.Orange",
            "app_num_total_activities": 18
        })
        file_path = os.path.join(self.graph_dir, "utg.js")
        if not os.path.exists(file_path) or overwrite_existing:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(f"var utg = \n{utg_str}")

    def _load_graph_from_dir(self, base_dir):
        if not os.path.isdir(base_dir):
            self.logger.info(f"Base dir {self.states_dir} does not exists.")
            return
        for file_name in os.listdir(base_dir):
            full_file_path = os.path.join(base_dir, file_name)
            if os.path.isdir(full_file_path):
                self._load_graph_from_dir(full_file_path)
            if file_name.startswith("MultipleState"):
                self._load_state_node_from_file(full_file_path)
            elif file_name.startswith("Transition"):
                self._load_transition_from_file(full_file_path)

    def _load_state_node_from_file(self, file_path):
        file_name = os.path.basename(file_path)
        pattern = r'MultipleState_(.*)\.json'
        match = re.match(pattern, file_name)
        if not match:
            return None
        signature = match.group(1)
        node_props = {
            "signature": signature,
            "snapshot": None,
            "top_activity": None,
        }
        multiple_state_dict = utils.read_json_as_dict(file_path)
        view_state_signature = multiple_state_dict[
            "ViewStateObserver"] if "ViewStateObserver" in multiple_state_dict else None
        self._load_view_state_props_from_file(view_state_signature, node_props)
        sandboxed_env_signature = multiple_state_dict[
            "SandboxedEnvironmentObserver"] if "SandboxedEnvironmentObserver" in multiple_state_dict else None
        self._load_sandbox_state_props_from_file(sandboxed_env_signature, node_props)
        fs_state_signature = multiple_state_dict[
            "FileSystemStateObserver"] if "FileSystemStateObserver" in multiple_state_dict else None
        self._load_fs_state_props_from_file(fs_state_signature, node_props)
        self.add_state_node(signature, node_props)

    def _load_view_state_props_from_file(self, view_state_signature, node_props):
        view_state_file = f"ViewState_{view_state_signature}.json"
        view_state = utils.read_json_as_dict(view_state_file, self.states_dir)
        self._load_view_state_props_from_dict(view_state, node_props)

    def _load_view_state_props_from_dict(self, view_state, node_props):
        signature = view_state["signature"]
        node_props["view_state_signature"] = signature
        action_units = UIActionUnit.get_action_units_in_view_dict(view_state)
        if self.flatten_dicts:
            for index, item in enumerate(action_units):
                node_props[f"action_unit_{index}"] = json.dumps(item.to_dict())
        else:
            node_props["action_units"] = [item.to_dict() for item in action_units]
        snapshot_file = f"ViewState_{signature}_Snapshot.png"
        actual_snapshot_file = os.path.join(self.states_dir, snapshot_file)
        if os.path.isfile(actual_snapshot_file):
            node_props["snapshot"] = snapshot_file
        else:
            node_props["snapshot"] = MISSING_SNAPSHOT

    def _load_sandbox_state_props_from_file(self, sandbox_state_signature, node_props):
        sandbox_state_file = f"SandboxedEnvState_{sandbox_state_signature}.json"
        sandbox_state = utils.read_json_as_dict(sandbox_state_file, self.states_dir)
        self._load_sandbox_state_props_from_dict(sandbox_state, node_props)

    def _load_sandbox_state_props_from_dict(self, sandbox_state, node_props):
        if sandbox_state is not None:
            node_props["top_activity"] = sandbox_state["env_state"]["top_activity"]
            if self.flatten_dicts:
                node_props["activity_stack"] = ",".join(sandbox_state["env_state"]["activity_stack"])
                node_props["sensitive_apis"] = ",".join(sandbox_state["frida_sandbox_state"]["sensitive_apis"])
                node_props["class_modules"] = ",".join(sandbox_state["frida_sandbox_state"]["modules"]["class_module"])
                node_props["native_modules"] = ",".join(
                    sandbox_state["frida_sandbox_state"]["modules"]["native_module"])
            else:
                node_props["activity_stack"] = sandbox_state["env_state"]["activity_stack"]
                node_props["sensitive_apis"] = sandbox_state["frida_sandbox_state"]["sensitive_apis"]
                node_props["class_modules"] = sandbox_state["frida_sandbox_state"]["modules"]["class_module"]
                node_props["native_modules"] = sandbox_state["frida_sandbox_state"]["modules"]["native_module"]

    def _load_fs_state_props_from_file(self, fs_state_signature, node_props):
        fs_state_file = f"FileSystemState_{fs_state_signature}.json"
        fs_state = utils.read_json_as_dict(fs_state_file, self.states_dir)
        self._load_fs_state_props_from_dict(fs_state, node_props)

    def _load_fs_state_props_from_dict(self, fs_state, node_props):
        if fs_state is not None:
            private_dir_list = fs_state["private_dir"]["list"]
            shared_dir_list = fs_state["shared_dir"]["list"]
            final_private_dir_list = [item["file"] for item in private_dir_list]
            final_shared_dir_list = [item["file"] for item in shared_dir_list]
            if self.flatten_dicts:
                node_props["private_dir_files"] = ",".join(final_private_dir_list)
                node_props["shared_dir_files"] = ",".join(final_shared_dir_list)
            else:
                node_props["private_dir_files"] = final_private_dir_list
                node_props["shared_dir_files"] = final_shared_dir_list

    def _load_transition_from_file(self, full_file_path):
        pattern = r'Transition_(With_Policy|Without_Policy)_from_(.*)_to_(.*)\.json'
        file_name = os.path.basename(full_file_path)
        match = re.match(pattern, file_name)
        if not match:
            return None
        policy_classifier = match.group(1)
        from_signature = match.group(2)
        to_signature = match.group(3)
        transition_dict = utils.read_json_as_dict(full_file_path)
        self.add_state_transition_dict(transition_dict, policy_classifier, from_signature, to_signature)

    def get_state_action_bag(self, signature=None, multiple_state: MultipleStateItem = None) -> ActionBag:
        if signature is None:
            signature = multiple_state.get_signature()
        if signature in self.graph.nodes:
            node = self.graph.nodes[signature]
            action_units = node["action_units"]
            action_bag = ActionBag.from_action_units_dict(action_units)
            return action_bag
        else:
            return None

    def get_current_state_id(self):
        return self.current_node_id

    def get_current_state_snapshot(self):
        return self.graph.nodes[self.current_node_id]["snapshot"]

    def get_current_state_action_bag(self) -> ActionBag:
        return self.get_state_action_bag(self.current_node_id)

    def get_last_state_action_bag(self) -> ActionBag:
        return self.get_state_action_bag(self.last_node_id)

    def _update_current_state_pointer(self, new_state_id):
        if new_state_id != self.current_node_id:
            self.node_history.append(self.current_node_id)
            self.last_node_id = self.current_node_id
            self.current_node_id = new_state_id

    def update_current_state(self, signature=None, multiple_state_item: MultipleStateItem = None):
        assert not(signature is None and multiple_state_item is None)
        if signature is not None:
            if signature not in self.graph.nodes:
                raise RuntimeError(f"Can't change current state since {signature} is of an unknown state")
            else:
                self._update_current_state_pointer(signature)
        if multiple_state_item is not None:
            signature = multiple_state_item.get_signature()
            self.add_state_node_dict(multiple_state=multiple_state_item)
            self._update_current_state_pointer(signature)


def main():
    from dotenv import load_dotenv
    load_dotenv()
    graph_manager = GraphManager(
        states_dir="I:\\git\\forensicmate-static-analysis\\output\\MONITOR\\com.whatsapp-2.24.4.76\\states",
        graph_dir="I:\\git\\forensicmate-static-analysis\\output\\MONITOR\\com.whatsapp-2.24.4.76\\")
    graph_manager.load_graph_from_states_dir()
    # graph_manager.save_graphml()
    graph_manager.save_graph_vis_utg()
    graph_manager.save_graph_vis_json()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)
    main()
