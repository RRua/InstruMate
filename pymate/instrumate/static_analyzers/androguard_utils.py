from androguard.core.dex import EncodedMethod, EncodedField, ClassDefItem, MethodIdItem


def get_class_signature(clazz: ClassDefItem):
    return clazz.get_name().replace(';', '')


def get_field_signature(field: EncodedField):
    class_name = field.get_class_name().replace(';', '')
    field_name = field.get_name()
    return f"{class_name}.{field_name}".replace('/', '.')


def get_method_signature(method: EncodedMethod):
    method_name = method.get_name().replace(';', '')
    class_name = method.get_class_name().replace(';', '')
    descriptor = ",".join(method.get_descriptor().replace('(', '').split(')')[0].replace(' ', '').split(';'))
    method_signature = f"{class_name}.{method_name}({descriptor})"
    return method_signature.replace('/', '.')


def get_method_id_signature(method: MethodIdItem):
    method_name = method.get_name().replace(';', '')
    class_name = method.get_class_name().replace(';', '')
    descriptor = ",".join(method.get_descriptor().replace('(', '').split(')')[0].replace(' ', '').split(';'))
    method_signature = f"{class_name}.{method_name}({descriptor})"
    return method_signature.replace('/', '.')
