import hashlib
import os
import logging
from os import close

from yaml import serialize

from pymate.device_observer.device_observer import DeviceObserver, DeviceState
from pymate.utils import uiautomator_utils, utils
from pymate.common import ui_actions, UIActionUnit
from com.dtmilano.android.viewclient import ViewClient, View
from datetime import datetime
from pymate.device_link.device_link import DeviceViews


class DeviceViewObserver(DeviceObserver):
    def __init__(self):
        super().__init__("view_observer")

    def do_observe(self):
        self.device_link.wait_to_be_ready(max_wait_cycles=10)
        activity_history = self.device_link.get_activity_history()
        device_view = None
        if self.device_link.update_current_view(max_attempts=3):
            device_view = self.device_link.get_current_view()
        snapshot = self.device_link.capture_snapshot()
        observed_state = DeviceViewState(device_view, snapshot, activity_history)
        self.last_state = self.current_state
        self.current_state = observed_state
        return observed_state


class DeviceViewState(DeviceState):
    def __init__(self, device_view: DeviceViews, image_snapshot, activity_history):
        super().__init__()
        self.device_view = device_view
        views = []
        if device_view is not None:
            views = device_view.views
        self.logger = logging.getLogger(self.__class__.__name__)
        self.state_dict["view_components"] = {}
        self.state_dict["action_units"] = {}
        self.state_dict["unmapped_views"] = []
        self.state_dict["activity_history"] = activity_history
        self.image_snapshot = image_snapshot
        self.include_changeable_texts_in_signature = False
        for view in views:
            self._collect_uiautomator_components_in_view(view)
        signature_set = set()
        for key in self.state_dict["view_components"]:
            signature_set.add(key)
        if len(views) == 0:
            signature_set.add(datetime.now().strftime("%Y-%m-%d_%H%M%S"))
        self.state_dict["signature"] = hashlib.md5("\n".join(sorted(signature_set)).encode()).hexdigest()

    def _add_view_component(self, view_data: dict):
        uniqueId = view_data["uniqueId"]
        signature = view_data["signature"]
        already_exists = signature in self.state_dict["view_components"]
        existing_unique_id = self.state_dict["view_components"][signature]["uniqueId"] if already_exists else None
        if existing_unique_id is not None and existing_unique_id != uniqueId:
            raise RuntimeError(
                f"Possible ViewState signature colision with views with IDs {uniqueId} and {existing_unique_id}")
        action_unit = self._get_action_unit(view_data)
        if action_unit is not None:
            self.state_dict["action_units"][signature] = action_unit.to_dict()
        if not already_exists:
            self.state_dict["view_components"][signature] = view_data

    def _collect_uiautomator_components_in_view(self, view: View):
        view_component = {}
        view_component["android_class"] = view.getClass()
        view_component["package"] = view.getPackage()
        view_component["uniqueId"] = view.getUniqueId()
        view_component["parentUniqueId"] = view.getParent().getUniqueId() if view.getParent() is not None else None
        view_component["resourceID"] = view.getResourceId()
        view_component["contentDesc"] = view.getContentDescription()
        view_component["text"] = view.getText()
        view_component["checkable"] = view.getCheckable()
        view_component["checked"] = view.getChecked()
        view_component["clickable"] = view.getClickable()
        view_component["enabled"] = view.getEnabled()
        view_component["focusable"] = view.getFocusable()
        view_component["focused"] = view.getFocused()
        view_component["scrollable"] = view.getScrollable()
        view_component["visibility"] = view.getVisibility()
        view_component["password"] = view.getPassword()
        view_component["selected"] = view.getSelected()
        signature = (
            f'{view.getClass()};{view.getUniqueId()};{view.getContentDescription()};{view.getResourceId()};'
            f'{view.getText() if self.include_changeable_texts_in_signature else ""};{view.getCheckable()};{view.getChecked()};{view.getClickable()};'
            f'{view.getEnabled()};{view.getFocusable()};{view.getFocused()};{view.getScrollable()};'
            f'{view.getVisibility()};{view.getPassword()};{view.getSelected()};'
        )
        signature = utils.get_md5_hash_for_str(signature)
        view_component["signature"] = signature
        self._add_view_component(view_component)
        for child in view.getChildren():
            self._collect_uiautomator_components_in_view(child)

    def _get_action_unit(self, view_dict):
        view_id = view_dict["uniqueId"]
        resourceID = view_dict["resourceID"]
        view_signature = view_dict["signature"]
        cls = view_dict["android_class"]
        pkg = view_dict["package"]
        text = view_dict["text"]
        content_desc = view_dict["contentDesc"]
        is_scrollable = view_dict["scrollable"]
        if is_scrollable:
            action_type = ui_actions.ACTION_TYPE_SCROLL
            action_unit = UIActionUnit(view_id, resourceID, view_signature, cls, pkg, "scroll panel", action_type, text,
                                       content_desc)
            return action_unit
        if len(text) == 0 and len(content_desc) == 0:
            # self.logger.warning(f"Missing user text hint (label) for view id {view_id} with class {cls}")
            label = "unknown label"
        else:
            if len(text) == 0 and len(content_desc) > 0:
                label = content_desc
            elif len(text) > 0 and len(content_desc) == 0:
                label = text
            else:
                label = "%s (%s)" % (text, content_desc)
        if cls in ui_actions.ACTION_CLS_MAP:
            action_type = ui_actions.ACTION_CLS_MAP[cls]
            action_unit = UIActionUnit(view_id, resourceID, view_signature, cls, pkg, label, action_type, text,
                                       content_desc)
            return action_unit
        else:
            # self.logger.debug(f"Unmapped class/view. Label: {label}, id: {view_id}, class: {cls}")
            if cls not in self.state_dict["unmapped_views"]:
                self.state_dict["unmapped_views"].append(cls)
            return None

    def contains_action_units(self):
        if self.state_dict["action_units"] is not None:
            return len(self.state_dict["action_units"]) > 0
        return False

    def contains_view_components(self):
        if self.state_dict["view_components"] is not None:
            return len(self.state_dict["view_components"]) > 0
        return False

    def is_on_launcher_window(self):
        for item in self.state_dict["view_components"]:
            item_dict = self.state_dict["view_components"][item]
            if item_dict["package"] is not None and item_dict["package"] == "com.google.android.apps.nexuslauncher":
                return True
        return None

    def is_on_agree_window(self):
        agree_btn = self.find_action_unit_by_text(search_text="Agree", exact_search=True)
        agree_btn2 = self.find_action_unit_by_text(search_text="agree", exact_search=True)
        agree_btn3 = self.find_action_unit_by_text(search_text="accept", exact_search=True)
        agree_btn4 = self.find_action_unit_by_text(search_text="ACCEPT", exact_search=True)
        agree_btn5 = self.find_action_unit_by_text(search_text="Accept", exact_search=True)
        if agree_btn is not None or agree_btn2 is not None or agree_btn3 is not None or agree_btn4 is not None or agree_btn5 is not None:
            return True
        return False

    def close_agree_window(self):
        agree_btn = self.find_action_unit_by_text(search_text="Agree", exact_search=True)
        agree_btn2 = self.find_action_unit_by_text(search_text="agree", exact_search=True)
        agree_btn3 = self.find_action_unit_by_text(search_text="accept", exact_search=True)
        agree_btn4 = self.find_action_unit_by_text(search_text="ACCEPT", exact_search=True)
        agree_btn5 = self.find_action_unit_by_text(search_text="Accept", exact_search=True)
        if agree_btn is not None:
            self.device_view.execute_action(agree_btn)
        if agree_btn2 is not None:
            self.device_view.execute_action(agree_btn2)
        if agree_btn3 is not None:
            self.device_view.execute_action(agree_btn3)
        if agree_btn4 is not None:
            self.device_view.execute_action(agree_btn4)
        if agree_btn5 is not None:
            self.device_view.execute_action(agree_btn5)

    def is_on_app_not_responding_view(self):
        app_not_responding_msg = self.find_view_component_by_text("isn't responding")
        close_app_btn = self.find_btn_action_unit_by_text(search_text="Close app", exact_search=True)
        if app_not_responding_msg is not None and close_app_btn is not None:
            return True
        return False

    def close_not_responding_app(self):
        close_app_btn = self.find_btn_action_unit_by_text(search_text="Close app", exact_search=True)
        if close_app_btn is not None:
            self.device_view.execute_action(close_app_btn)

    def is_on_full_screen_alert_view(self):
        app_not_responding_msg = self.find_view_component_by_text("Viewing full screen")
        got_it_btn = self.find_btn_action_unit_by_text(search_text="Got it", exact_search=True)
        if app_not_responding_msg is not None and got_it_btn is not None:
            return True
        return False

    def accept_full_screen(self):
        got_it_btn = self.find_btn_action_unit_by_text(search_text="Got it", exact_search=True)
        if got_it_btn is not None:
            self.device_view.execute_action(got_it_btn)

    def is_on_permissions_settings_view(self):
        btn_allow = self.find_action_unit_by_text("Allow", exact_search=True)
        btn_not_allow = self.find_action_unit_by_text(search_text="Don\u2019t allow", exact_search=True)
        btn_while_using_app = self.find_action_unit_by_text("While using the app", exact_search=True)
        btn_only_this_time = self.find_action_unit_by_text("Only this time", exact_search=True)
        if btn_allow is not None and btn_not_allow is not None:
            return True
        if btn_while_using_app is not None and btn_only_this_time is not None:
            return True
        return False

    def allow_permission_settings(self):
        btn_allow = self.find_action_unit_by_text("Allow", exact_search=True)
        btn_while_using_app = self.find_action_unit_by_text("While using the app", exact_search=True)
        if btn_allow is not None:
            self.device_view.execute_action(btn_allow)
        if btn_while_using_app is not None:
            self.device_view.execute_action(btn_while_using_app)

    def find_btn_action_unit_by_text(self, search_text, exact_search=False):
        return self.find_action_unit_by_text_and_class(search_text=search_text,
                                                       cls_name=ui_actions.CLS_ANDROID_WIDGET_BUTTON,
                                                       exact_text_search=exact_search)

    def find_action_unit_by_text(self, search_text, exact_search=False):
        return self.find_action_unit_by_text_and_class(search_text, None, exact_search)

    def find_action_unit_by_text_and_class(self, search_text, cls_name, exact_text_search=False):
        for item in self.state_dict["action_units"]:
            item_dict = self.state_dict["action_units"][item]
            if cls_name is not None and item_dict['cls'] != cls_name:
                continue
            if exact_text_search:
                if search_text == item_dict["text"]:
                    return UIActionUnit.from_dict(item_dict)
            else:
                if search_text in item_dict["text"]:
                    return UIActionUnit.from_dict(item_dict)
        return None

    def find_view_component_by_text(self, search_text):
        for item in self.state_dict["view_components"]:
            if self.state_dict["view_components"][item]["text"] is not None and search_text in \
                    self.state_dict["view_components"][item]["text"]:
                return self.state_dict["view_components"][item]
        return None

    def find_view_component_by_id(self, component_id):
        for item in self.state_dict["view_components"]:
            item_dict = self.state_dict["view_components"][item]
            if item_dict["resourceID"] is not None and item_dict["resourceID"] == component_id:
                return item_dict
        return None

    def save(self, dest_dir):
        super().save(dest_dir=dest_dir)
        image_body = self.image_snapshot
        final_path = os.path.join(dest_dir, f"{self.get_signature()}_snapshot.png")
        with open(final_path, 'wb') as file:
            file.write(image_body)
        # image.save(final_path, "PNG")
