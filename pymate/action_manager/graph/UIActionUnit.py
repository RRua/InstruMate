from pymate.forensic_state import ViewStateItem
import logging

ACTION_TYPE_TAP = "tap"
ACTION_TYPE_INPUT = "input"
ACTION_TYPE_SCROLL = "scroll"
ACTION_TYPE_ANDROID_BACK = ""
ACTION_CLS_MAP = {
    "android.widget.ScrollView": ACTION_TYPE_SCROLL,
    "android.widget.TextView": ACTION_TYPE_TAP,
    "android.widget.EditText": ACTION_TYPE_INPUT,
    "android.view.View": ACTION_TYPE_TAP,
    "android.widget.Button": ACTION_TYPE_TAP,
    "android.widget.ImageView": ACTION_TYPE_TAP,
    "android.widget.FrameLayout": ACTION_TYPE_TAP,
    "android.widget.ImageButton": ACTION_TYPE_TAP,
}
SUB_ACTION_SCROLL_FLING_FORWARD = "flingForward"
SUB_ACTION_SCROLL_FLING_BACKWARD = "flingBackward"
SUB_ACTION_SCROLL_FLING_TO_END = "flingToBeginning"
SUB_ACTION_SCROLL_FLING_TO_START = "flingToEnd"


class UIActionUnit:
    def __init__(self, view_id, cls, pkg, label, action_type):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.view_id = view_id
        self.cls = cls
        self.pkg = pkg
        self.label = label
        self.action_type = action_type

    def to_dict(self):
        return {
            "view_id": self.view_id,
            "cls": self.cls,
            "pkg": self.pkg,
            "label": self.label,
            "type": self.action_type
        }

    @staticmethod
    def from_dict(data):
        assert data is not None
        ui_action_unit = UIActionUnit(data["view_id"], data["cls"], data["pkg"], data["label"], data["type"])
        return ui_action_unit

    @staticmethod
    def get_action_units_in_view(view_state: ViewStateItem):
        action_units = []
        for item in view_state.clickables:
            action_unit = UIActionUnit._get_action_unit(item)
            if action_unit is not None:
                action_units.append(action_unit)
        for item in view_state.checkables:
            action_unit = UIActionUnit._get_action_unit(item)
            if action_unit is not None:
                action_units.append(action_unit)
        for item in view_state.scrollables:
            action_unit = UIActionUnit._get_action_unit(item)
            if action_unit is not None:
                action_units.append(action_unit)
        return action_units

    @staticmethod
    def get_action_units_in_view_dict(view_state: dict):
        action_units = []
        if view_state is not None:
            for item in view_state["clickables"]:
                action_unit = UIActionUnit._get_action_unit(item)
                if action_unit is not None:
                    action_units.append(action_unit)
            for item in view_state["checkables"]:
                action_unit = UIActionUnit._get_action_unit(item)
                if action_unit is not None:
                    action_units.append(action_unit)
            for item in view_state["scrollables"]:
                action_unit = UIActionUnit._get_action_unit(item)
                if action_unit is not None:
                    action_units.append(action_unit)
        return action_units

    @staticmethod
    def _get_action_unit(view_dict):
        view_id = view_dict["uniqueId"]
        cls = view_dict["android_class"]
        pkg = view_dict["package"]
        text = view_dict["text"]
        content_desc = view_dict["contentDesc"]
        is_scrollable = view_dict["scrollable"]
        if is_scrollable:
            action_type = ACTION_TYPE_SCROLL
            action_unit = UIActionUnit(view_id, cls, pkg, "scroll panel", action_type)
            return action_unit
        if len(text) == 0 and len(content_desc) == 0:
            print(f"Actions.py: Missing type for id {view_id} class {cls}")
            return None
        else:
            if len(text) == 0 and len(content_desc) > 0:
                label = content_desc
            elif len(text) > 0 and len(content_desc) == 0:
                label = text
            else:
                label = "%s (%s)" % (text, content_desc)
        if cls in ACTION_CLS_MAP:
            action_type = ACTION_CLS_MAP[cls]
            action_unit = UIActionUnit(view_id, cls, pkg, label, action_type)
            return action_unit
        else:
            print(f"Actions.py: Missing type for label {label} id {view_id} class {cls}")
            return None
