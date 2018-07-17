import inspect
from typing import List, Dict, Callable, Any
from collections import ChainMap

from apistar import types, validators
from flask_star.component import Component, ComponentMap
from flask_star.flask import COMPONENTS 

from flask import request

class Injector():
    """Injects Components into functions based on type annotations"""

    # Builtin components
    __BUILTIN = COMPONENTS

    def __init__(self, components: List[Component]):
        self.component_map = ComponentMap(self.__BUILTIN + components)

    def _build_params(self, func: Callable, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Build dictionary of values to bind to the <func> from user input and components"""
        print('Injector', func, kwargs)
        func_params = inspect.signature(func).parameters

        # Component parameters
        component_params = {}
        for param_name, param in func_params.items():
            component = self.component_map.lookup(param_name, param.annotation)
            if component:
                # Recursively resolve inputs to components
                component_input_parameters = self._build_params(component.resolve, {})
                component_params[param_name] = component.resolve(**component_input_parameters)
            else:
                # Resolve typesystem types
                value = self._get_request_value(param_name)
                coerced_value = self.coerce_type(value, param.annotation)
                component_params[param_name] = coerced_value

        # User entered parameters
        user_params = kwargs.copy()

        # Components have higher priority than user parameters to protect against
        # knowlegable malicious users overriding injected values with user input.
        bind_params = ChainMap(component_params, user_params)
        return bind_params

    @staticmethod
    def _get_request_value(param_name):
        """Get a parameter from a flask request"""
        return ChainMap(request.view_args or {},
                        request.values or {},
                        request.form or {},
                        request.get_json() or {}
                       ).get(param_name)


    def coerce_type(self, value, annotation):
        """Coerce a value to a given annotation"""
        coerced_value = value

        if issubclass(annotation, types.Type):
            coerced_value = annotation.validate(value)
        converter = {int: int, float: float, str: str}.get(annotation)
        if converter:
            try:
                coerced_value = converter(value)
            except (ValueError, TypeError):
                raise validators.ValidationError(f'Could not convert value to {annotation}')
        return coerced_value


    def submit(self, func: Callable, init_params: Dict[str, Any]) -> Any:
        """Resolve a functions dependencies, and then call it"""
        params = self._build_params(func, init_params)
        return func(**params)
