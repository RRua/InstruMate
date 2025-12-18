# FLAG_DEBUGGABLE = 1 << 1
# FLAG_RESOURCE_ENC_DEC = 1 << 2
# FLAG_TRANSITION_NONE = 1 << 3
# FLAG_TRANSITION_SMALI = 1 << 4
# FLAG_TRANSITION_JAVA = 1 << 5
# FLAG_TRANSITION_SOOT = 1 << 6

# FLAG_LABELS = {
#     FLAG_DEBUGGABLE: "debuggable",
#     FLAG_RESOURCE_ENC_DEC: "resource",
#     FLAG_TRANSITION_SMALI: "transition-smali",
#     FLAG_TRANSITION_JAVA: "transition-java",
#     FLAG_TRANSITION_SOOT: "transition-soot",
#     FLAG_TRANSITION_NONE: "transition-none"
# }

FEATURE_REPACKAGED = 1 << 0  # changed signature
FEATURE_DEBUGGABLE = 1 << 1  # manifest is edited
FEATURE_ALLOW_PRIVATE_DATA_BKP = 1 << 2  # manifest is edited
FEATURE_TRUST_USER_INSTALLED_CERTS = 1 << 3  # manifest is edited and a new net config file is created
FEATURE_REVEAL_PASSWORD_FIELDS = 1 << 4  # edit layout resources
FEATURE_CHANGE_STRING_RESOURCE = 1 << 5  # string resources
FEATURE_GRAYSCALE_IMAGES = 1 << 6  # image resources
FEATURE_MONITOR_METHOD_CALLS_WITH_ACVTOOL = 1 << 7  # instrument
FEATURE_MONITOR_CRYPTO_API_MISUSE = 1 << 8  # instrument
FEATURE_MONITOR_METHOD_CALLS_WITH_DROIDFAX = 1 << 9  # instrument
FEATURE_MONITOR_METHOD_CALLS_WITH_COSMO = 1 << 10  # instrument
FEATURE_MONITOR_METHOD_CALLS_WITH_ANDROLOG = 1 << 11  # instrument
FEATURE_MONITOR_METHOD_CALLS_WITH_AOP = 1 << 12  # instrument
FEATURE_MONITOR_METHOD_CALLS_WITH_FRIDA_GADGET = 1 << 13  # instrument
FEATURE_MONITOR_METHOD_CALLS_WITH_IMCOVERAGE = 1 << 14  # instrument
FEATURE_MERGED_APP = 1 << 16

VARIANT_LEVEL_MODIFY_SIGNATURE = 1 << 0
VARIANT_LEVEL_MODIFY_MANIFEST = 1 << 1
VARIANT_LEVEL_MODIFY_RESOURCES = 1 << 2
VARIANT_LEVEL_MODIFY_BEHAVIOUR = 1 << 3

LEVEL_AND_FEATURES_MAP = {
    VARIANT_LEVEL_MODIFY_SIGNATURE: [FEATURE_REPACKAGED],
    VARIANT_LEVEL_MODIFY_MANIFEST: [FEATURE_DEBUGGABLE,
                                    FEATURE_ALLOW_PRIVATE_DATA_BKP,
                                    FEATURE_TRUST_USER_INSTALLED_CERTS],
    VARIANT_LEVEL_MODIFY_RESOURCES: [FEATURE_REVEAL_PASSWORD_FIELDS,
                                     FEATURE_CHANGE_STRING_RESOURCE,
                                     FEATURE_GRAYSCALE_IMAGES],
    VARIANT_LEVEL_MODIFY_BEHAVIOUR: [FEATURE_MONITOR_METHOD_CALLS_WITH_ACVTOOL,
                                     FEATURE_MONITOR_CRYPTO_API_MISUSE,
                                     FEATURE_MONITOR_METHOD_CALLS_WITH_DROIDFAX,
                                     FEATURE_MONITOR_METHOD_CALLS_WITH_COSMO,
                                     FEATURE_MONITOR_METHOD_CALLS_WITH_ANDROLOG,
                                     FEATURE_MONITOR_METHOD_CALLS_WITH_AOP,
                                     FEATURE_MONITOR_METHOD_CALLS_WITH_FRIDA_GADGET,
                                     FEATURE_MONITOR_METHOD_CALLS_WITH_IMCOVERAGE]
}


def get_levels_based_on_features(features: list):
    levels = []
    for key in LEVEL_AND_FEATURES_MAP:
        for feature in features:
            if feature in LEVEL_AND_FEATURES_MAP[key]:
                levels.append(key)
    return levels


FEATURE_LABELS = {
    FEATURE_REPACKAGED: "repackaged",
    FEATURE_DEBUGGABLE: "debuggable",
    FEATURE_ALLOW_PRIVATE_DATA_BKP: "allowbackup",
    FEATURE_TRUST_USER_INSTALLED_CERTS: "trustcerts",
    FEATURE_REVEAL_PASSWORD_FIELDS: "hpasswords",
    FEATURE_CHANGE_STRING_RESOURCE: "chgstringres",
    FEATURE_GRAYSCALE_IMAGES: "grayscaleimgs",
    FEATURE_MONITOR_CRYPTO_API_MISUSE: "cryptomisuse",
    FEATURE_MONITOR_METHOD_CALLS_WITH_DROIDFAX: "droidfax",
    FEATURE_MONITOR_METHOD_CALLS_WITH_COSMO: "cosmo",
    FEATURE_MONITOR_METHOD_CALLS_WITH_ACVTOOL: "acvtool",
    FEATURE_MONITOR_METHOD_CALLS_WITH_ANDROLOG: "androlog",
    FEATURE_MONITOR_METHOD_CALLS_WITH_AOP: "aspectj",
    FEATURE_MONITOR_METHOD_CALLS_WITH_FRIDA_GADGET: "fridagadget",
    FEATURE_MONITOR_METHOD_CALLS_WITH_IMCOVERAGE: "imcoverage",
    FEATURE_MERGED_APP: "merged"
}

LEVEL_LABELS = {
    VARIANT_LEVEL_MODIFY_SIGNATURE: "signature",
    VARIANT_LEVEL_MODIFY_MANIFEST: "manifest",
    VARIANT_LEVEL_MODIFY_RESOURCES: "resources",
    VARIANT_LEVEL_MODIFY_BEHAVIOUR: "instrumentation",
}


class AppVariant:
    def __init__(self, variant_features=0, variant_levels=None, tag: str = None):
        """
            Creates variant information.

            :param variant_features: flags that specify how the variant was made.
            :type variant_features: int
            :param variant_levels: all features of that level will be activated
            :type variant_levels: int
            :param tag: Extra string that identifies who made the variant
            :type tag: list
            """
        self.variant_features = variant_features
        self.variant_levels = variant_levels
        self.tag = tag

    def set_feature(self, feature):
        return self.variant_features | feature

    def clear_feature(self, feature):
        return self.variant_features & ~feature

    def is_feature_set(self, feature):
        return (self.variant_features & feature) != 0

    def is_at_least_one_feature_active(self, features):
        combined_flags = 0
        for feature in features:
            combined_flags |= feature
        at_least_one_active = (self.variant_features & combined_flags) != 0
        return at_least_one_active

    def is_other_feature_active(self, features):
        combined_features = 0
        for f in features:
            combined_features |= f
        other_features_active = (self.variant_features & ~combined_features) != 0
        return other_features_active

    def is_all_features_set(self, required_features):
        for f in required_features:
            if (self.variant_features & f) != f:
                return False
        return True

    def get_bin_features(self):
        return bin(self.variant_features)

    def get_feature_labels(self):
        return [FEATURE_LABELS[key] for key in FEATURE_LABELS if self.is_feature_set(key)]

    def set_tag(self, tag: str):
        self.tag = tag

    def get_tag(self):
        return self.tag

    def get_bin_levels(self):
        return bin(self.variant_levels)

    def get_levels(self):
        return self.variant_levels

    def set_level(self, level):
        return self.variant_levels | level

    def clear_level(self, level):
        return self.variant_levels & ~level

    def is_level_set(self, level):
        return (self.variant_levels & level) != 0

    def is_at_level(self, level):
        if not self.is_level_set(level):
            return False
        higher_level = level << 1
        while higher_level <= VARIANT_LEVEL_MODIFY_BEHAVIOUR:
            if self.is_level_set(higher_level):
                return False
            higher_level = higher_level << 1
        return True

    def get_level_labels(self):
        return [LEVEL_LABELS[key] for key in LEVEL_LABELS if self.is_level_set(key)]

    def to_dict(self):
        variant_dict = {
            "variant_features": self.variant_features,
            "variant_features_bin": self.get_bin_features(),
            "variant_feature_labels": self.get_feature_labels(),
            "variant_levels": self.get_levels(),
            "variant_levels_bin": self.get_bin_levels(),
            "variant_level_labels": self.get_level_labels(),
            "variant_tag": self.tag
        }
        return variant_dict

    @staticmethod
    def from_dict(self, variant_dict):
        features = variant_dict["variant_features"]
        tag = variant_dict["variant_tag"]
        levels = variant_dict["variant_levels"]
        return AppVariant(variant_features=features, variant_levels=levels, tag=tag)


def _remove_disabled_features(features, behaviour_androlog=True, behaviour_acvtool=True, behaviour_aspectj=True,
                              behaviour_fridagadget=True, behaviour_imcoverage=True):
    disabled_features = [FEATURE_GRAYSCALE_IMAGES, FEATURE_REVEAL_PASSWORD_FIELDS, FEATURE_ALLOW_PRIVATE_DATA_BKP,
                         FEATURE_TRUST_USER_INSTALLED_CERTS, FEATURE_MONITOR_CRYPTO_API_MISUSE,
                         FEATURE_MONITOR_METHOD_CALLS_WITH_DROIDFAX,
                         FEATURE_MONITOR_METHOD_CALLS_WITH_COSMO]
    if not behaviour_androlog:
        disabled_features.append(FEATURE_MONITOR_METHOD_CALLS_WITH_ANDROLOG)
    if not behaviour_acvtool:
        disabled_features.append(FEATURE_MONITOR_METHOD_CALLS_WITH_ACVTOOL)
    if not behaviour_aspectj:
        disabled_features.append(FEATURE_MONITOR_METHOD_CALLS_WITH_AOP)
    if not behaviour_fridagadget:
        disabled_features.append(FEATURE_MONITOR_METHOD_CALLS_WITH_FRIDA_GADGET)
    if not behaviour_imcoverage:
        disabled_features.append(FEATURE_MONITOR_METHOD_CALLS_WITH_IMCOVERAGE)
    return [f for f in features if f not in disabled_features]


def create_variant_specifications(modify_manifest=False, modify_resources=False, modify_behaviour=False,
                                  behaviour_androlog=True, behaviour_acvtool=True, behaviour_aspectj=True,
                                  behaviour_fridagadget=True,
                                  behaviour_imcoverage=True):
    specs = []
    if not modify_manifest and not modify_resources and not modify_behaviour:
        for feature in _remove_disabled_features(LEVEL_AND_FEATURES_MAP[VARIANT_LEVEL_MODIFY_SIGNATURE],
                                                 behaviour_androlog=behaviour_androlog,
                                                 behaviour_acvtool=behaviour_acvtool,
                                                 behaviour_aspectj=behaviour_aspectj,
                                                 behaviour_fridagadget=behaviour_fridagadget,
                                                 behaviour_imcoverage=behaviour_imcoverage):
            specs.append(AppVariant(variant_features=feature,
                                    variant_levels=VARIANT_LEVEL_MODIFY_SIGNATURE))

    if modify_manifest:
        for feature in _remove_disabled_features(LEVEL_AND_FEATURES_MAP[VARIANT_LEVEL_MODIFY_MANIFEST],
                                                 behaviour_androlog=behaviour_androlog,
                                                 behaviour_acvtool=behaviour_acvtool,
                                                 behaviour_aspectj=behaviour_aspectj,
                                                 behaviour_fridagadget=behaviour_fridagadget,
                                                 behaviour_imcoverage=behaviour_imcoverage):
            specs.append(AppVariant(variant_features=feature,
                                    variant_levels=VARIANT_LEVEL_MODIFY_SIGNATURE | VARIANT_LEVEL_MODIFY_MANIFEST))

    if modify_resources:
        for feature in _remove_disabled_features(LEVEL_AND_FEATURES_MAP[VARIANT_LEVEL_MODIFY_RESOURCES],
                                                 behaviour_androlog=behaviour_androlog,
                                                 behaviour_acvtool=behaviour_acvtool,
                                                 behaviour_aspectj=behaviour_aspectj,
                                                 behaviour_fridagadget=behaviour_fridagadget,
                                                 behaviour_imcoverage=behaviour_imcoverage):
            specs.append(AppVariant(variant_features=feature,
                                    variant_levels=VARIANT_LEVEL_MODIFY_SIGNATURE | VARIANT_LEVEL_MODIFY_RESOURCES))

    if modify_behaviour:
        for feature in _remove_disabled_features(LEVEL_AND_FEATURES_MAP[VARIANT_LEVEL_MODIFY_BEHAVIOUR],
                                                 behaviour_androlog=behaviour_androlog,
                                                 behaviour_acvtool=behaviour_acvtool,
                                                 behaviour_aspectj=behaviour_aspectj,
                                                 behaviour_fridagadget=behaviour_fridagadget,
                                                 behaviour_imcoverage=behaviour_imcoverage):
            final_level = VARIANT_LEVEL_MODIFY_SIGNATURE | VARIANT_LEVEL_MODIFY_BEHAVIOUR
            if feature == FEATURE_MONITOR_METHOD_CALLS_WITH_COSMO:
                final_level = VARIANT_LEVEL_MODIFY_SIGNATURE | VARIANT_LEVEL_MODIFY_MANIFEST | VARIANT_LEVEL_MODIFY_BEHAVIOUR
            specs.append(AppVariant(variant_features=feature,
                                    variant_levels=final_level))

    # by now, this creates a large set of items
    merged_specs = [AppVariant(variant_features=spec.variant_features | FEATURE_MERGED_APP,
                               variant_levels=spec.variant_levels | VARIANT_LEVEL_MODIFY_MANIFEST | VARIANT_LEVEL_MODIFY_RESOURCES)
                    for spec in specs]
    return specs + merged_specs


def old_create_variant_specifications():
    specs = [
        # Level signature changed
        AppVariant(variant_features=FEATURE_REPACKAGED,
                   variant_levels=VARIANT_LEVEL_MODIFY_SIGNATURE),

        # Level manifiest changed
        AppVariant(variant_features=FEATURE_REPACKAGED |
                                    FEATURE_DEBUGGABLE,
                   variant_levels=VARIANT_LEVEL_MODIFY_SIGNATURE |
                                  VARIANT_LEVEL_MODIFY_MANIFEST),
        AppVariant(
            variant_features=FEATURE_REPACKAGED |
                             FEATURE_DEBUGGABLE |
                             FEATURE_ALLOW_PRIVATE_DATA_BKP |
                             FEATURE_TRUST_USER_INSTALLED_CERTS,
            variant_levels=VARIANT_LEVEL_MODIFY_SIGNATURE |
                           VARIANT_LEVEL_MODIFY_MANIFEST),

        # Level resources
        AppVariant(variant_features=FEATURE_REPACKAGED |
                                    FEATURE_MERGED_APP,
                   variant_levels=VARIANT_LEVEL_MODIFY_SIGNATURE |
                                  VARIANT_LEVEL_MODIFY_MANIFEST |
                                  VARIANT_LEVEL_MODIFY_RESOURCES),
        AppVariant(variant_features=FEATURE_REPACKAGED |
                                    FEATURE_REVEAL_PASSWORD_FIELDS,
                   variant_levels=VARIANT_LEVEL_MODIFY_SIGNATURE |
                                  VARIANT_LEVEL_MODIFY_MANIFEST |
                                  VARIANT_LEVEL_MODIFY_RESOURCES),
        AppVariant(variant_features=FEATURE_REPACKAGED |
                                    FEATURE_MERGED_APP |
                                    FEATURE_REVEAL_PASSWORD_FIELDS,
                   variant_levels=VARIANT_LEVEL_MODIFY_SIGNATURE |
                                  VARIANT_LEVEL_MODIFY_MANIFEST |
                                  VARIANT_LEVEL_MODIFY_RESOURCES),

        # level behaviour
        AppVariant(variant_features=FEATURE_REPACKAGED |
                                    FEATURE_MONITOR_METHOD_CALLS_WITH_ACVTOOL,
                   variant_levels=VARIANT_LEVEL_MODIFY_SIGNATURE |
                                  VARIANT_LEVEL_MODIFY_MANIFEST |
                                  VARIANT_LEVEL_MODIFY_RESOURCES |
                                  VARIANT_LEVEL_MODIFY_BEHAVIOUR),
        AppVariant(variant_features=FEATURE_REPACKAGED |
                                    FEATURE_MONITOR_METHOD_CALLS_WITH_DROIDFAX,
                   variant_levels=VARIANT_LEVEL_MODIFY_SIGNATURE |
                                  VARIANT_LEVEL_MODIFY_MANIFEST |
                                  VARIANT_LEVEL_MODIFY_RESOURCES |
                                  VARIANT_LEVEL_MODIFY_BEHAVIOUR),
        AppVariant(variant_features=FEATURE_REPACKAGED |
                                    FEATURE_MONITOR_CRYPTO_API_MISUSE,
                   variant_levels=VARIANT_LEVEL_MODIFY_BEHAVIOUR),

        AppVariant(variant_features=FEATURE_REPACKAGED |
                                    FEATURE_MERGED_APP |
                                    FEATURE_MONITOR_METHOD_CALLS_WITH_ACVTOOL,
                   variant_levels=VARIANT_LEVEL_MODIFY_SIGNATURE |
                                  VARIANT_LEVEL_MODIFY_MANIFEST |
                                  VARIANT_LEVEL_MODIFY_RESOURCES |
                                  VARIANT_LEVEL_MODIFY_BEHAVIOUR),
        AppVariant(variant_features=FEATURE_REPACKAGED |
                                    FEATURE_MERGED_APP |
                                    FEATURE_MONITOR_METHOD_CALLS_WITH_DROIDFAX,
                   variant_levels=VARIANT_LEVEL_MODIFY_SIGNATURE |
                                  VARIANT_LEVEL_MODIFY_MANIFEST |
                                  VARIANT_LEVEL_MODIFY_RESOURCES |
                                  VARIANT_LEVEL_MODIFY_BEHAVIOUR),
        AppVariant(variant_features=FEATURE_REPACKAGED |
                                    FEATURE_MERGED_APP |
                                    VARIANT_LEVEL_MODIFY_SIGNATURE |
                                    VARIANT_LEVEL_MODIFY_MANIFEST |
                                    VARIANT_LEVEL_MODIFY_RESOURCES |
                                    FEATURE_MONITOR_CRYPTO_API_MISUSE,
                   variant_levels=VARIANT_LEVEL_MODIFY_SIGNATURE |
                                  VARIANT_LEVEL_MODIFY_MANIFEST |
                                  VARIANT_LEVEL_MODIFY_RESOURCES |
                                  VARIANT_LEVEL_MODIFY_BEHAVIOUR)

    ]
    return specs
