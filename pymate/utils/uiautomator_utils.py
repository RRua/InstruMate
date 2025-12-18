import io
import os

from com.dtmilano.android.viewclient import ViewClient, View

FORCE_CLICKABLE_CLASSES = ['android.widget.TextView', 'android.widget.Button', 'android.widget.ImageButton']


def collect_components_in_view(view: View, components_dict: dict = None, by_class_catalog: dict = None, clickables=None,
                               checkables=None, scrollables=None, include_variable_text=True, include_view_ref=True):
    parent = view.getParent()
    if parent is not None:
        parent_unique_id = parent.getUniqueId()
    else:
        parent_unique_id = None

    if include_variable_text:
        text_value = view.getText()
    else:
        text_value = None
    if include_view_ref:
        view_ref = view
    else:
        view_ref = None
    if view.getUniqueId() not in components_dict:
        view_dict = {
            "android_class": view.getClass(),
            "uniqueId": view.getUniqueId(),
            "resourceID": view.getResourceId(),
            "contentDesc": view.getContentDescription(),
            "text": text_value,
            "checkable": view.getCheckable(),
            "checked": view.getChecked(),
            "clickable": view.getClickable(),
            "enabled": view.getEnabled(),
            "focusable": view.getFocusable(),
            "focused": view.getFocused(),
            "scrollable": view.getScrollable(),
            "visibility": view.getVisibility(),
            "password": view.getPassword(),
            "selected": view.getSelected(),
            "parentUniqueId": parent_unique_id,
            "package": view.getPackage(),
            "view_reference": view_ref
        }
        signature = (
            f'{view.getClass()};{view.getUniqueId()};{view.getContentDescription()};{view.getResourceId()};'
            f'{text_value};{view.getCheckable()};{view.getChecked()};{view.getClickable()};'
            f'{view.getEnabled()};{view.getFocusable()};{view.getFocused()};{view.getScrollable()};'
            f'{view.getVisibility()};{view.getPassword()};{view.getSelected()};{parent_unique_id}'
        )
        view_dict["signature"] = signature
        components_dict[view.getUniqueId()] = view_dict
        if view.getClass() not in by_class_catalog:
            by_class_catalog[view.getClass()] = []
        by_class_catalog[view.getClass()].append(view_dict)
        if view.getClickable() or view.getClass() in FORCE_CLICKABLE_CLASSES:
            clickables.append(view_dict)
        if view.getCheckable():
            checkables.append(view_dict)
        if view.getScrollable():
            scrollables.append(view_dict)

    for child in view.getChildren():
        collect_components_in_view(child, components_dict, by_class_catalog, clickables, checkables,
                                   scrollables)


def collect_components(views, include_variable_text=True, include_view_ref=True):
    view_components = {}
    by_class_catalog = {}
    clickables = []
    checkables = []
    scrollables = []
    for view in views:
        collect_components_in_view(view, view_components, by_class_catalog, clickables, checkables,
                                   scrollables, include_variable_text, include_view_ref)
    return view_components, by_class_catalog, clickables, checkables, scrollables


def take_snapshot_and_save(view_client: ViewClient, base_dir, file_name, overwrite_existing=False):
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    image = view_client.device.takeSnapshot(reconnect=True)
    final_path = os.path.join(base_dir, file_name)
    if not os.path.exists(final_path) or overwrite_existing:
        image.save(final_path, "PNG")
    return final_path


def take_snapshot(view_client: ViewClient):
    image = view_client.device.takeSnapshot(reconnect=True)
    return image


def print_android_view(views):
    buffer = io.StringIO()
    for view in views:
        android_view_to_string(view, buffer, 0)
    content = buffer.getvalue()
    buffer.close()
    print(content)


def android_view_to_string(view: View, buffer, level=0):
    level_str = "\t" * level
    print("--------", file=buffer)
    print(f"{level_str}class: {view.getClass()}", file=buffer)
    print(f"{level_str}uniqueId: {view.getUniqueId()}", file=buffer)
    print(f"{level_str}contentDesc: {view.getContentDescription()}", file=buffer)
    print(f"{level_str}text: {view.getText()}", file=buffer)
    print(f"{level_str}checkable: {view.getCheckable()}, checked: {view.getChecked()}", file=buffer)
    print(f"{level_str}clickable: {view.getClickable()}, enabled: {view.getEnabled()}", file=buffer)
    print(f"{level_str}focusable: {view.getFocusable()}, focused: {view.getFocused()}", file=buffer)
    print(f"{level_str}scrollable: {view.getScrollable()}", file=buffer)
    print(f"{level_str}visibility: {view.getVisibility()}", file=buffer)
    print(f"{level_str}password: {view.getPassword()}", file=buffer)
    print(f"{level_str}selected: {view.getSelected()}", file=buffer)
    if view.getParent() is not None:
        print(f"\t{level_str}parentId: {view.getParent().getUniqueId()}", file=buffer)
    for child in view.getChildren():
        android_view_to_string(child, buffer, level + 1)
