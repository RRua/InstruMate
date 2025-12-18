import os
import traceback
import xml.etree.ElementTree as ET
from PIL import Image
from pymate.common.tool import BaseTool
from pymate.utils import fs_utils


class ToolChangeIconResource(BaseTool):

    def __init__(self, input_dir=None, skip_modifications = False):
        super().__init__(name=self.__class__.__name__,
                         description="Icon Resources Editor",
                         cmd=None, options={
                "input_dir": input_dir,
            })
        self.input_dir = input_dir
        self.selected_id_to_change = None
        self.all_files = []
        self.edited_files = []
        self.qtd_files_edited = 0
        self.max_depth = 3
        self.skip_modifications = skip_modifications

    def before_exec(self):
        if not os.path.exists(self.input_dir):
            raise RuntimeError("Icon Resources Editor: input dir is missing")
        android_manifest = os.path.join(self.input_dir, "AndroidManifest.xml")
        if not os.path.exists(android_manifest):
            raise RuntimeError("Icon Resources Editor: can't change resources without AndroidManifest.xml present.")

    def after_exec(self):
        if self.qtd_files_edited == 0 and not self.skip_modifications:
            raise RuntimeError("Icon Resources Editor: no image was edited")

    def exec_script(self) -> (str, str):
        self.all_files = fs_utils.list_files(directory_path=self.input_dir)
        self._select_icon_id_to_be_changed()
        self._change_image_resources_by_id(self.selected_id_to_change, 0)
        return "", ""

    def _change_image_resources_by_id(self, id_to_change, recursion_count=0):
        if recursion_count > self.max_depth:
            return
        resources_to_change = [item for item in self.all_files if
                               id_to_change == fs_utils.get_file_name_without_extension(
                                   fs_utils.get_file_without_parent(item))]
        xml_files = [item for item in resources_to_change if item.endswith('.xml')]
        webp_files = [item for item in resources_to_change if item.endswith('.webp')]
        for item in webp_files:
            self._turn_webp_into_grayscale(item)
        for item in xml_files:
            referenced_drawables = self._find_referenced_drawables_in_xml(item)
            for drawable in referenced_drawables:
                self._change_image_resources_by_id(drawable, recursion_count=recursion_count+1)

    def _turn_webp_into_grayscale(self, webp_file):
        if webp_file in self.edited_files:
            return
        image = Image.open(webp_file)
        gray_image = image.convert('L')
        if not self.skip_modifications:
            gray_image.save(webp_file)
        self.qtd_files_edited = self.qtd_files_edited + 1
        self.edited_files.append(webp_file)

    def _find_referenced_drawables_in_xml(self, xml_path):
        tree = ET.parse(xml_path)
        namespaces = dict([node for _, node in
                           ET.iterparse(xml_path,
                                        events=["start-ns"])])
        for ns in namespaces:
            ET.register_namespace(ns, namespaces[ns])

        if "android" not in namespaces:
            android_namespace = 'http://schemas.android.com/apk/res/android'
            ET.register_namespace('android', android_namespace)
            android_prefix = '{' + android_namespace + '}'
        else:
            android_prefix = "{" + namespaces["android"] + "}"
        root = tree.getroot()
        referenced_drawables = []
        xml_modified = False
        for elem in root.iter():
            drawable = elem.get(android_prefix+'drawable')
            if drawable is not None and drawable.startswith('@drawable/'):
                referenced_drawables.append(drawable.split('/')[1])
            fill_color = elem.get(android_prefix+'fillColor')
            if fill_color is not None and fill_color.startswith('#'):
                elem.set(android_prefix+'fillColor', self._turn_html_color_to_grayscale(fill_color))
                xml_modified = True
            strokeColor = elem.get(android_prefix + 'strokeColor')
            if strokeColor is not None and strokeColor.startswith('#'):
                elem.set(android_prefix + 'strokeColor', self._turn_html_color_to_grayscale(strokeColor))
                xml_modified = True
        if xml_modified:
            if not self.skip_modifications:
                tree.write(xml_path)
            self.qtd_files_edited = self.qtd_files_edited + 1
            self.edited_files.append(xml_path)
        return referenced_drawables

    def _hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        alpha = int(hex_color[0:2], 16)
        red = int(hex_color[2:4], 16)
        green = int(hex_color[4:6], 16)
        blue = int(hex_color[6:8], 16)
        return alpha, red, green, blue

    def _rgb_to_grayscale(self, r, g, b):
        grayscale = int(0.299 * r + 0.587 * g + 0.114 * b)
        return grayscale

    def _grayscale_to_hex(self, alpha, grayscale):
        return f'#{alpha:02x}{grayscale:02x}{grayscale:02x}{grayscale:02x}'

    def _turn_html_color_to_grayscale(self, input_color):
        alpha, red, green, blue = self._hex_to_rgb(input_color)
        grayscale_value = self._rgb_to_grayscale(red, green, blue)
        grayscale_hex = self._grayscale_to_hex(alpha, grayscale_value)
        return grayscale_hex

    def _select_icon_id_to_be_changed(self):
        android_manifest = os.path.join(self.input_dir, "AndroidManifest.xml")
        try:
            tree = ET.parse(android_manifest)
        except Exception as e:
            tb_exception = traceback.format_exc()
            self.logger.debug(tb_exception)
            raise
        namespaces = dict([node for _, node in
                           ET.iterparse(android_manifest,
                                        events=["start-ns"])])
        for ns in namespaces:
            ET.register_namespace(ns, namespaces[ns])

        if "android" not in namespaces:
            android_namespace = 'http://schemas.android.com/apk/res/android'
            ET.register_namespace('android', android_namespace)
            android_prefix = '{' + android_namespace + '}'
        else:
            android_prefix = "{" + namespaces["android"] + "}"

        selected_id_to_change = None
        for el in tree.findall("application"):
            app_icon = el.get(android_prefix + "icon")
            if app_icon is not None and app_icon.startswith("@mipmap/"):
                selected_id_to_change = app_icon
                break
            else:
                for act in el.findall("activity"):
                    act_icon = act.get(android_prefix + "icon")
                    if act_icon is not None and act_icon.startswith("@mipmap/"):
                        selected_id_to_change = act_icon
                        break
        if selected_id_to_change is not None:
            self.selected_id_to_change = selected_id_to_change.split('/')[1]


def main():
    input_dir = ".\\input\\apk\\random\\reference-app\\"
    tool = ToolChangeIconResource(input_dir=input_dir)
    tool.execute()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)
    main()
