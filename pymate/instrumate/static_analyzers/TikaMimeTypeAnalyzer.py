import json
import logging
import os

from pymate.common.app import App
from pymate.common.tools.ToolRadareRabin2 import ToolRadareRabin2
from pymate.common.tools.ToolTikaParser import ToolTikaParser
from pymate.common.tools.ToolZip import ToolZipUnpack
from pymate.instrumate.static_analyzer import StaticAnalyzer
from pymate.utils import fs_utils, utils

CATEGORIES = {
    'multimedia': ['audio/amr', 'audio/basic', 'audio/midi', 'audio/mp4', 'audio/mpeg', 'audio/opus', 'audio/speex',
                   'audio/vnd.wave', 'audio/vorbis', 'audio/x-aac', 'image/bmp', 'image/emf', 'image/gif', 'image/jpeg',
                   'image/png', 'image/svg+xml', 'image/tiff', 'image/vnd.adobe.photoshop', 'image/vnd.microsoft.icon',
                   'image/vnd.zbrush.pcx', 'image/webp', 'image/wmf', 'image/x-raw-nikon', 'image/x-raw-panasonic',
                   'image/x-rgb', 'image/x-tga', 'video/h264', 'video/mp4', 'video/vnd.vivo', 'video/webm',
                   'video/x-m4v', 'application/x-shockwave-flash'],
    'java': ['application/java-archive', 'application/java-serialized-object', 'application/java-vm'],
    'presentation': ['text/css', 'text/html', 'application/x-font-adobe-metric', 'application/x-font-otf',
                     'application/x-font-ttf', 'text/aspdotnet'],
    'configuration': ['application/x-plist', 'application/json', 'text/x-java-properties', 'application/dita+xml',
                      'application/rdf+xml', 'application/rls-services+xml', 'application/vnd.google-earth.kml+xml',
                      'application/x-dtbresource+xml', 'application/xhtml+xml', 'application/xml',
                      'application/xml-dtd',
                      'application/xslt+xml'],
    'rich_documents': ['application/x-ms-nls', 'application/postscript', 'application/pdf', 'application/msword',
                       'application/onenote', 'application/rtf', 'application/vnd.ms-excel',
                       'application/vnd.ms-powerpoint',
                       'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                       'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                       'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
    'compressed_files': ['application/gzip', 'application/x-7z-compressed', 'application/x-gtar', 'application/x-lzma',
                         'application/x-xz', 'application/zip', 'application/zstd'],
    'crypto': ['application/pgp-signature', 'application/pkcs7-signature', 'application/pkix-cert',
               'application/vnd.mophun.certificate', 'application/x-pkcs12', 'application/x-x509-cert',
               'application/x-x509-key'],
    'javascript': ['application/javascript'],
    'automation': ['application/x-bat', 'application/x-sh', 'text/x-groovy', 'text/x-lua', 'text/x-matlab',
                   'text/x-perl', 'text/x-python', 'text/x-tcl'],
    'source_code': ['text/x-java-source', 'application/javascript', 'text/x-python', 'text/aspdotnet'],
    'compiled_dex': ['application/x-dex'],
    'compiled_native': ['application/x-executable', 'application/x-sharedlib'],
    'binary_files': ['application/octet-stream'],
    'text_files': ['text/x-eiffel', 'text/plain', 'text/csv', 'text/x-pascal', 'text/x-yaml', 'text/x-csrc',
                   'text/x-sql', 'text/tsv', 'text/x-config', 'text/x-chdr', 'text/x-prolog', 'text/x-ini',
                   'text/x-web-markdown', 'text/x-d', 'text/x-fortran', 'text/x-jsp', 'text/troff', 'text/x-objcsrc',
                   'text/x-verilog', 'text/x-rsrc', 'text/x-assembly', 'text/x-yacc', 'text/x-lex', 'text/x-robots',
                   'text/x-log', 'text/x-c++src', 'text/vnd.graphviz', 'text/vnd.fmi.flexstor', 'text/x-stsrc',
                   'text/x-modula']
}

NOT_CLASSIFIED = 'unknown'


def _set_categories_in_dict(content_type, result):
    match_count = 0
    for c in CATEGORIES:
        result[c] = False
        if content_type is not None:
            for item in CATEGORIES[c]:
                if item in content_type:
                    result[c] = True
                    match_count = match_count + 1
                    break
    result['matched_categories'] = match_count
    if match_count == 0:
        result['unknown'] = True
    else:
        result['unknown'] = False


def load_json_file_encoded_by(file_name, encoding):
    try:
        with open(file_name, 'r', encoding=encoding) as file:
            json_data = json.load(file)
        return json_data
    except:
        # traceback.print_exc()
        return None


def load_json_file(file_name):
    encodings = ['utf-8', 'iso8859-1', 'utf-16']
    for item in encodings:
        json_object = load_json_file_encoded_by(file_name, item)
        if json_object is not None:
            return json_object
    return None


class TikaMimeTypeAnalyzer(StaticAnalyzer):

    def __init__(self, expand_dex=False, expand_native=False):
        self.expand_dex = expand_dex
        self.expand_native = expand_native

    def configure(self, tmp_dir: str = None, output_dir: str = None, tools_dir: str = None, name: str = None,
                  instrumate_log=None):
        super().configure(tmp_dir=tmp_dir, output_dir=output_dir, tools_dir=tools_dir,
                          name="Androguard DEX Analyzer", instrumate_log=instrumate_log)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.apktool_path = os.path.join(self.tools_dir, "misc", "apktool.jar")
        self.tika_parser_path = os.path.join(self.tools_dir, "misc", "apache_tika.jar")

    def analyze_app(self, app: App):
        base_apk_analysis, dex_analysis, native_analysis = self._analyze_single_apk(
            apk_path=app.get_base_pkg(),
            source_information="base")
        self._collect_compiled_code_files(split_name=None, app=app, dex_analysis=dex_analysis,
                                          native_analysis=native_analysis)
        for index, item in enumerate(app.get_split_pkgs()):
            split_apk_analysis, split_dex_analysis, split_native_analysis = self._analyze_single_apk(
                item,
                f"split_{index}")
            self._collect_compiled_code_files(split_name=fs_utils.get_file_without_parent(item), app=app,
                                              dex_analysis=split_dex_analysis, native_analysis=split_native_analysis)
            base_apk_analysis = base_apk_analysis + split_apk_analysis
            dex_analysis = dex_analysis + split_dex_analysis
            native_analysis = native_analysis + split_native_analysis
        app.set_content_type_analysis(content_type_analysis=base_apk_analysis)
        app.set_dex_static_analysis(dex_static_analysis=dex_analysis)
        app.set_native_static_analysis(native_static_analysis=native_analysis)

    def _collect_compiled_code_files(self, app: App, split_name, dex_analysis, native_analysis):
        for item in dex_analysis:
            if split_name is None:
                app.add_dex_file_in_base(file_name=item["relative_path"])
            else:
                app.add_dex_file_in_split(split_name=split_name, file_name=item["relative_path"])
        for item in native_analysis:
            if split_name is None:
                app.add_native_file_in_base(file_name=item["relative_path"])
            else:
                app.add_native_file_in_split(split_name=split_name, file_name=item["relative_path"])

    def _analyze_single_apk(self, apk_path: str, source_information=None):
        analysis = []
        dex_analysis = []
        native_analysis = []
        tmp_dir = fs_utils.get_tmp_dir(self.tmp_dir, "tika-unpack")
        tool_zip_unpack = ToolZipUnpack(input_file=apk_path, output_dir=tmp_dir, fail_on_ms_windows_overwrite=False)
        tool_result = tool_zip_unpack.execute()
        if tool_result["success"]:
            tika_output_dir = f"{tmp_dir}-tikaout"
            tika_parser_result = ToolTikaParser(tool_path=self.tika_parser_path, input_dir=tmp_dir,
                                                output_dir=tika_output_dir).execute()
            if tika_parser_result["success"]:
                files_in_apk = fs_utils.list_files(tmp_dir)
                for file in files_in_apk:
                    sha256_hash = utils.get_sha256_hash(file)
                    file_size = os.path.getsize(file)
                    content_type = None
                    relative_path = os.path.relpath(file, tmp_dir)
                    metadata_path = os.path.join(tika_output_dir, f"{relative_path}.json")
                    if os.path.exists(metadata_path):
                        metadata_array = utils.read_json_as_dict(metadata_path)
                        for metadata_item in metadata_array:
                            for key in metadata_item:
                                if key == "Content-Type":
                                    content_type = metadata_item[key]
                    analysis_item = {
                        "source": source_information,
                        "file": relative_path,
                        "size": file_size,
                        "sha256": sha256_hash,
                        "content_type": content_type,
                    }
                    _set_categories_in_dict(content_type=content_type, result=analysis_item)
                    analysis.append(analysis_item)
                    if self.expand_dex and analysis_item['compiled_dex']:
                        rabin2_stderr_file = fs_utils.get_tmp_file(tmp_dir=self.tmp_dir, tag='tika',
                                                                   label='rabin2-stderr')
                        rabin2_stdout_file = fs_utils.get_tmp_file(tmp_dir=self.tmp_dir, tag='tika',
                                                                   label='rabin2-stdout')

                        rabin2_result = ToolRadareRabin2(input_file=file, stdout_file=rabin2_stdout_file,
                                                         stderr_file=rabin2_stderr_file).execute()
                        if rabin2_result['success']:
                            dex_analysis.append({
                                "source": source_information,
                                "relative_path": relative_path,
                                "rabin2_analysis": rabin2_stdout_file
                            })
                        else:
                            self.logger.warning(f"RadareRabin2 failed for file: {file}")
                    if self.expand_native and analysis_item['compiled_native']:
                        rabin2_stderr_file = fs_utils.get_tmp_file(tmp_dir=self.tmp_dir, tag='tika',
                                                                   label='rabin2-stderr')
                        rabin2_stdout_file = fs_utils.get_tmp_file(tmp_dir=self.tmp_dir, tag='tika',
                                                                   label='rabin2-stdout')

                        rabin2_result = ToolRadareRabin2(input_file=file, stdout_file=rabin2_stdout_file,
                                                         stderr_file=rabin2_stderr_file).execute()
                        if rabin2_result['success']:
                            native_analysis.append({
                                "source": source_information,
                                "relative_path": relative_path,
                                "rabin2_analysis": rabin2_stdout_file
                            })
                        else:
                            self.logger.warning(f"RadareRabin2 failed for file: {file}")
            fs_utils.destroy_dir_files(tika_output_dir)
        fs_utils.destroy_dir_files(tmp_dir)
        return analysis, dex_analysis, native_analysis

    def save_analysis(self, app: App):
        content_type_analysis = app.get_content_type_analysis()
        if len(content_type_analysis) > 0:
            item_0 = content_type_analysis[0]
            header = [key for key in item_0]
            self.register_log(
                "apk_content_type_analysis",
                header
            )
            if content_type_analysis is not None:
                for item in content_type_analysis:
                    record_value = [item[key] for key in header]
                    self.record_log("apk_content_type_analysis",
                                    app,
                                    record_value)

        dex_analysis = app.get_dex_static_analysis()
        if len(dex_analysis) > 0:
            self.process_rabin2_analysis(app, 'dex', dex_analysis)
        native_analysis = app.get_native_static_analysis()
        if len(native_analysis) > 0:
            self.process_rabin2_analysis(app, 'native', native_analysis)

    def process_rabin2_analysis(self, app: App, qualifier: str, analysis_list):
        self.register_log(
            f"apk_{qualifier}_classes",
            ["source", "relative_path", "classname", "addr", "rawsuper", "super", "visibility", "lang_impl"]
        )
        self.register_log(
            f"apk_{qualifier}_methods",
            ["source", "relative_path", "classname", "method", "addr", "is_final", "is_public", "flags", "lang_impl"]
        )
        self.register_log(
            f"apk_{qualifier}_fields",
            ["source", "relative_path", "classname", "field", "addr"]
        )
        self.register_log(
            f"apk_{qualifier}_imports",
            ["source", "relative_path", "import_name", "proc_linkage_table_addr", "bind_type"]
        )
        self.register_log(
            f"apk_{qualifier}_debug_information",
            ["source", "relative_path", "addr", "debug_info"]
        )
        for item in analysis_list:
            source = item["source"] if "source" in item else None
            relative_path = item["relative_path"] if "relative_path" in item else None
            rabin2_analysis_file = item["rabin2_analysis"] if "rabin2_analysis" in item else None
            rabin2_analysis = load_json_file(rabin2_analysis_file)
            if rabin2_analysis is None:
                self.logger.warning(f"RadareRabin2 failed for file: {rabin2_analysis_file}")
            else:
                classes = rabin2_analysis["classes"] if "classes" in rabin2_analysis else []
                for class_item in classes:
                    cls_addr = class_item["addr"] if "addr" in class_item else None
                    cls_lang = class_item["lang"] if "lang" in class_item else None
                    classname = class_item["classname"] if "classname" in class_item else None
                    methods = class_item["methods"] if "methods" in class_item else []
                    fields = class_item["fields"] if "fields" in class_item else []
                    super_class = class_item["super"] if "super" in class_item else None
                    raw_super = class_item["rawsuper"] if "rawsuper" in class_item else None
                    cls_visibility = class_item["visibility"] if "visibility" in class_item else None
                    self.record_log(f"apk_{qualifier}_classes",
                                    app,
                                    [source, relative_path, classname, cls_addr, raw_super, super_class,
                                     cls_visibility, cls_lang])
                    for method in methods:
                        m_addr = method["addr"] if "addr" in method else None
                        m_name = method["name"] if "name" in method else None
                        m_lang = method["lang"] if "lang" in method else None
                        m_flags = ",".join(method["flags"]) if "flags" in method and method[
                            "flags"] is not None else ""
                        m_is_public = "public" in m_flags
                        m_is_final = "final" in m_flags
                        self.record_log(f"apk_{qualifier}_methods",
                                        app,
                                        [source, relative_path, classname, m_name, m_addr, m_is_final, m_is_public,
                                         m_flags, m_lang])

                    for field in fields:
                        f_addr = field["addr"] if "addr" in field else None
                        f_name = field["name"] if "name" in field else None
                        self.record_log(f"apk_{qualifier}_fields",
                                        app,
                                        [source, relative_path, classname, f_name, f_addr])
                bin_imports = rabin2_analysis["imports"] if "imports" in rabin2_analysis else []
                for bin_import in bin_imports:
                    self.record_log(f"apk_{qualifier}_imports",
                                    app,
                                    [source, relative_path, bin_import["name"],
                                     bin_import["plt"] if "plt" in bin_import else None,
                                     bin_import["bind"]])
                debug_infos = rabin2_analysis["dwarf"] if "dwarf" in rabin2_analysis else []
                visited_debug_infos = set()
                for debug_info_by_name in debug_infos:
                    for debug_info in debug_info_by_name:
                        file_debug_info = debug_info["file"] if "file" in debug_info else None
                        addr_debug_info = debug_info["addr"] if "addr" in debug_info else None
                        if file_debug_info not in visited_debug_infos:
                            self.record_log(f"apk_{qualifier}_debug_information",
                                            app,
                                            [source, relative_path, addr_debug_info, file_debug_info])
                            visited_debug_infos.add(file_debug_info)
