# -*- coding: utf-8 -*-

"""Python event emitter for OOP applications. Influenced by the pymitter package.

Example:
    ee = TinyEmitter()

    @ee.listener
    class A:
        @ee.on("event")
        @staticmethod
        def f1():
            ...
        @ee.on("event")
        def f2(self):
            ...

    a = A()

    ee.emit("event")

Result:
    Both the method and the static function will be called.
"""

from typing import Dict, Callable, Optional, List
import logging
import inspect

__author__ = "Felix Korovin"
__author_email__ = "felix.korovin@icloud.com"
__copyright__ = "Copyright 2021, Felix Korovin"
__credits__ = ["Felix Korovin"]
__contact__ = "https://github.com/skilef"
__license__ = "MIT"
__status__ = "Development"
__version__ = "0.0.1"
__all__ = ["TinyEmitter", "set_log_level"]

logger = logging.getLogger(__name__)


def set_log_level(verbosity: int) -> None:
    """Sets the module's verbosity

    The verbosity level can be picked from the standard logging module levels.
    For example: logging.DEBUG, logging.INFO and etc...

    Args:
        verbosity: Verbosity level
    Returns:
        None
    """
    logger.setLevel(verbosity)


class TinyEmitter:
    """Acts as an event broker between classes and functions across the application.

        An event can be emitted by calling the "emit" method.
        All callback functions that are registered to emitted event will then be triggered.
    """

    def __init__(self):
        """Initializes the data structures"""

        """Dictionary of all registered callback functions grouped by event type"""
        self._callbacks: Dict[str, List[Callable]] = {}

        """Dictionary of the registered class instances grouped by their class name"""
        self._instances: Dict[str, List[object]] = {}

        """Dictionary of the classes of registered callback functions mapped by class name"""
        self._classes: Dict[str, object] = {}

    def emit_instances(self, event: str, instances: List[object], *args, **kwargs):
        """Emits an event to the specific instances.

        Same as emit, but only the given instances will be called

            Args:
                event: Event string
                instances: List of instances
                *args: argument list
                **kwargs: keyword argument dictionary
            Return:
                None
        """

        return self._emit(event, instances, *args, **kwargs)

    def emit(self, event: str, *args, **kwargs):
        """Emits an event.

        When an event is being emitted, all its registered callback functions will be called.
        If a callback function is a class member, the call will be triggered for all class's instances.

            Args:
                event: Event string
                *args: argument list
                **kwargs: keyword argument dictionary
            Return:
                None
        """
        return self._emit(event, None, *args, **kwargs)

    def on(self, event: str, callback: Optional[Callable] = None) -> Callable:
        """Registers a function that will be called when the given event is being emitted.

            This method has 2 operation modes:
                1. It can work as a decorator factory
                2. Can be used directly

            If the callback argument is None, operation mode 1 is assumed.

            Args:
                event: event string
                callback: an optional callback function

            Return:
                The original callback function unchanged (in both operation modes)

            Raises:
                TypeError: occurs when the callback argument is not callable
        """

        def on(callback: Callable):
            if not callable(callback):
                raise TypeError(f"The given callback argument is not callable")

            logger.debug(f"The function \"{callback.__qualname__}\" is registered to the \"{event}\" event")

            # if it is a first time registration for the given event
            if event not in self._callbacks:
                self._callbacks[event] = []

            self._callbacks[event] += [callback]

            return callback

        # depends on the mode (1 or 2)
        return on(callback) if callback else on

    def unlisten(self, instance: object) -> None:
        logger.debug(f"Instance {hex(id(instance))} of class {type(instance).__name__} is unregistered")
        self._instances[type(instance).__name__].remove(instance)

    def off(self, event: str, callback: Callable) -> None:
        logger.debug(f"Unregisters the function \"{callback.__qualname__}\" from  \"{event}\" event")
        self._callbacks[event].remove(callback)

        # if this is the last callback removed, delete the event key
        if not self._callbacks[event]:
            del self._callbacks[event]

    def listener(self, listener_class: object) -> object:
        """Registers a class as a listener

            This decorator is required for any class that has at least one registered non-static member

            Args:
                 listener_class - the class that will be registered

            Return:
                The original class but the __init__ function also register the class as a listener
        """

        class_name = listener_class.__qualname__

        # register the class as a listener
        self._classes[class_name] = listener_class
        self._instances[class_name] = []

        # keep the original init method
        original_init = listener_class.__init__

        def listener_init(inner_self, *args, **kwargs):

            # first, call the original init
            original_init(inner_self, *args, **kwargs)
            logger.debug(
                f"Instance {hex(id(inner_self))} of class {type(inner_self).__name__} is now registered as a listener")

            self._instances[class_name] += [inner_self]

        # replace the __init__ method with the new one
        listener_class.__init__ = listener_init

        return listener_class

    def finalizer(self, method):
        """Registers a class method as a finalizer, which causes the unlistening.
        """
        def wrapper(_self, *args, **kwargs):
            method(_self, *args, **kwargs)
            try:
                self.unlisten(_self)
            except (ValueError, KeyError):
                pass
        return wrapper
    
    @staticmethod
    def _is_static_method(class_object: object, function_name: str):
        """Checks whether the given function is a static method

            Args:
                class_object: the class of the function
                function_name: function's name

            Return:
                True if the function is static and False otherwise
        """
        return isinstance(inspect.getattr_static(class_object, function_name), staticmethod)

    def _emit(self, event: str, instances: Optional[List[object]] = None, *args, **kwargs):

        # if there are no callback functions for this event
        if event not in self._callbacks:
            logger.debug(f"There are no callback functions for the \"{event}\" event, nothing will be done.")
            return

        for callback in self._callbacks[event]:

            # function name including class name
            full_function_name: str = callback.__qualname__

            # if it is a class function
            if "." in full_function_name:

                # get the class name and the function name separated
                class_name, function_name = full_function_name.split(".")

                # if the class is not registered as a listener
                if class_name not in self._classes:
                    logger.error((
                        f"The function \"{function_name}\" of the \"{class_name}\""
                        " is being triggered but the class has not been registered as a listener."))
                    return

                # if the function is a static method
                if TinyEmitter._is_static_method(self._classes[class_name], function_name):
                    callback(*args, **kwargs)

                # a regular class method - pass the instance in each call
                else:

                    list_of_instances = self._instances[class_name] if instances is None else instances

                    for instance in list_of_instances:
                        callback(instance, *args, *kwargs)

            # if it is a regular function
            else:
                callback(*args, **kwargs)
