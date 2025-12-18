import logging

CLS_ANDROID_WIDGET_BUTTON = "android.widget.Button"
ACTION_TYPE_TAP = "tap"
ACTION_TYPE_INPUT = "input"
ACTION_TYPE_SCROLL = "scroll"
ACTION_TYPE_ANDROID_BACK = "android-back"
ACTION_TYPE_NONE = "no-action"
ACTION_CLS_MAP = {
    "android.widget.ScrollView": ACTION_TYPE_SCROLL,
    "android.widget.TextView": ACTION_TYPE_TAP,
    "android.widget.EditText": ACTION_TYPE_INPUT,
    "android.view.View": ACTION_TYPE_TAP,
    CLS_ANDROID_WIDGET_BUTTON: ACTION_TYPE_TAP,
    "android.widget.ImageView": ACTION_TYPE_TAP,
    "android.widget.FrameLayout": ACTION_TYPE_TAP,
    "android.widget.ImageButton": ACTION_TYPE_TAP,
    "android.widget.CheckBox": ACTION_TYPE_TAP,
    "android.widget.RadioButton": ACTION_TYPE_TAP,
    "android.widget.LinearLayout": ACTION_TYPE_NONE,
    "android.widget.RadioGroup": ACTION_TYPE_NONE
}
ACTION_SCROLL_FLING_FORWARD = "flingForward"
ACTION_SCROLL_FLING_BACKWARD = "flingBackward"
ACTION_SCROLL_FLING_TO_END = "flingToBeginning"
ACTION_SCROLL_FLING_TO_START = "flingToEnd"


class UIActionUnit:
    def __init__(self, view_id, resourceID, view_signature, cls, pkg, label, action_type, text, content_desc):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.view_id = view_id
        self.resourceID = resourceID
        self.view_signature = view_signature
        self.cls = cls
        self.pkg = pkg
        self.label = label
        self.text = text
        self.content_desc = content_desc
        self.action_type = action_type

    def to_dict(self):
        return {
            "view_id": self.view_id,
            "resourceID": self.resourceID,
            "view_signature": self.view_signature,
            "cls": self.cls,
            "pkg": self.pkg,
            "label": self.label,
            "type": self.action_type,
            "text": self.text,
            "content_desc": self.content_desc
        }

    @staticmethod
    def from_dict(data):
        assert data is not None
        ui_action_unit = UIActionUnit(data["view_id"], data["resourceID"], data["view_signature"], data["cls"], data["pkg"], data["label"],
                                      data["type"], data["text"], data["content_desc"])
        return ui_action_unit
