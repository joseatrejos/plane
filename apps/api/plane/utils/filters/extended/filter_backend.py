# Python imports
import re

# Module imports
from ..filter_backend import ComplexFilterBackend


class ExtendedComplexFilterBackend(ComplexFilterBackend):
    """
    Extended filter backend that supports custom property filtering.

    For full, up-to-date examples and usage, see the package README
    at `plane/utils/filters/README.md`.
    """

    def _is_custom_property_filter(self, field_name):
        """Check if a field name is a custom property filter."""
        return field_name.startswith("customproperty_")

    def _transform_field_name_for_validation(self, field_name):
        """Transform custom property filter names for validation.

        Transforms 'customproperty_<property_id>__<lookup>' to
        'customproperty_value__<lookup>' for FilterSet validation.
        """
        if not self._is_custom_property_filter(field_name):
            return field_name

        match = re.match(r"^customproperty_([a-f0-9-]+)__(.+)$", field_name)
        if match:
            lookup = match.group(2)
            return f"customproperty_value__{lookup}"

        return field_name

    def _preprocess_leaf_conditions(self, leaf_conditions, view, queryset):
        """Transform custom property filters from frontend to backend format.

        Frontend format: customproperty_<property_id>__<lookup>=<value>
        Backend format: customproperty_value__<lookup>=<property_id>;<value>
        """
        transformed = {}

        for key, value in leaf_conditions.items():
            if self._is_custom_property_filter(key):
                # Extract property_id and lookup from the key
                match = re.match(r"^customproperty_([a-f0-9-]+)__(.+)$", key)
                if match:
                    property_id = match.group(1)
                    lookup = match.group(2)

                    # Check if the value is separated by ','
                    value = value.split(',') if isinstance(value, str) and ',' in value and lookup == "in" else value
                    if isinstance(value, list) and len(value) > 1:
                        transformed[f"customproperty_value__{lookup}"] = ','.join([f"{property_id};{v}" for v in value])
                    else:
                        transformed[f"customproperty_value__{lookup}"] = f"{property_id};{value}"
                else:
                    # If format is invalid, keep the original key
                    transformed[key] = value
            else:
                transformed[key] = value

        return transformed