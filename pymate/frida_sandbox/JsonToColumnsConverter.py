from abc import abstractmethod


class JsonToColumnsConverter:

    @abstractmethod
    def get_header(self):
        raise NotImplementedError()

    @abstractmethod
    def get_values(self, json_obj):
        raise NotImplementedError()


class JMethodConverter(JsonToColumnsConverter):
    def get_header(self):
        header = ["timestamp", "signature", "qualifier", "reason", "returnedValue"]
        for i in range(21):
            header.append(f"arg_{i}")
        header.append("stack_trace")
        return header

    def get_values(self, json_obj):
        values = []
        values.append(json_obj["timestamp"])
        values.append(json_obj["java_signature"])
        values.append(json_obj["qualifier"])
        values.append(json_obj["reason"])

        returned_val = json_obj["returnedVal"]
        callResult = returned_val["callResult"]
        values.append(callResult)

        argumentValues = json_obj["argumentValues"]
        for i in range(21):
            arg_key = f"arg_{i}"
            if arg_key in argumentValues:
                arg_value = argumentValues[arg_key]
            else:
                arg_value = ""
            values.append(arg_value)
        if "stack_trace" == json_obj["data_type"]:
            values.append(json_obj["data"])
        else:
            values.append("")
        return values


class ModuleConverter(JsonToColumnsConverter):
    def get_header(self):
        header = ["timestamp", "module_type", "module_name", "module_base", "module_size", "module_path", "export_name",
                  "export_type", "export_address"]
        return header

    def get_values(self, json_obj):
        values = []
        values.append(json_obj["timestamp"])
        values.append(json_obj["module_type"])
        values.append(json_obj["module_name"])
        values.append(json_obj["module_base"])
        values.append(json_obj["module_size"])
        values.append(json_obj["module_path"])
        values.append(json_obj["export_name"])
        values.append(json_obj["export_type"])
        values.append(json_obj["export_address"])
        return values
