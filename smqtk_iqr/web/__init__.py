"""
SMQTK Web Applications
"""

import inspect
import os
import flask

from smqtk_core import Plugfigurable
from smqtk_core.dict import merge_dict

from typing import Dict, Type, Any, Optional, TypeVar


T = TypeVar("T", bound="SmqtkWebApp")


class SmqtkWebApp (flask.Flask, Plugfigurable):
    """
    Base class for SMQTK web applications
    """

    @classmethod
    def impl_directory(cls) -> str:
        """
        :return: Directory in which this implementation is contained.
        """
        return os.path.dirname(os.path.abspath(inspect.getfile(cls)))

    @classmethod
    def get_default_config(cls) -> Dict:
        """
        Generate and return a default configuration dictionary for this class.
        This will be primarily used for generating what the configuration
        dictionary would look like for this class without instantiating it.

        This should be overridden in each implemented application class to add
        appropriate configuration.

        :return: Default configuration dictionary for the class.

        """
        return {
            "flask_app": {
                "SECRET_KEY": "MySuperUltraSecret",
                "BASIC_AUTH_USERNAME": "demo",
                "BASIC_AUTH_PASSWORD": "demo"
            },
            "server": {
                'host': "127.0.0.1",
                'port': 5000
            }
        }

    @classmethod
    def from_config(
        cls: Type[T], config_dict: Dict[str, Any],
        merge_default: bool = True
    ) -> T:
        """
        Override to just pass the configuration dictionary to constructor
        """
        # Repeated from super method due to overriding how constructor is called
        if merge_default:
            merged = cls.get_default_config()
            merge_dict(merged, config_dict)
            config_dict = merged
        return cls(config_dict)

    def __init__(self, json_config: Dict[str, Any]) -> None:
        """
        Initialize application based of supplied JSON configuration

        :param json_config: JSON configuration dictionary

        """
        super(SmqtkWebApp, self).__init__(
            self.__class__.__name__,
            static_folder=os.path.join(self.impl_directory(), 'static'),
            template_folder=os.path.join(self.impl_directory(), 'templates')
        )

        #
        # Configuration setup
        #
        self.json_config = json_config

        # Factor 'flask_app' configuration properties into self.config
        for k in self.json_config['flask_app']:
            self.config[k] = self.json_config['flask_app'][k]

        #
        # Security
        #
        self.secret_key = self.config['SECRET_KEY']

    def get_config(self) -> Dict[str, Any]:
        return self.json_config

    def run(
        self, host: Optional[str] = None, port: Optional[int] = None,
        debug: Optional[bool] = False,  load_dotenv: bool = False,
        **options: Any
    ) -> None:
        """
        Override of the run method, drawing running host and port from
        configuration by default. 'host' and 'port' values specified as argument
        or keyword will override the app configuration.
        """
        host = (host or self.json_config['server']['host'])
        port = (port or self.json_config['server']['port'])
        runkw = dict(
            host=host,
            port=port,
            debug=debug,
            load_dotenv=load_dotenv,
            **options
        )

        try:
            super().run(**runkw)  # type: ignore
        except Exception as ex:
            note_parts = [f'Issue running server with {runkw}']
            if 'Address already in use' in str(ex):
                note_parts.append(
                    'On Linux you can debug which ports are in use with '
                    '``netstat -ntlp``, and determine which process ids '
                    'are using which ports with '
                    f'``sudo lsof -t -i tcp:{port}``'
                )
            note = '. '.join(note_parts)
            raise add_exception_note(ex, note)


def add_exception_note(
        ex: BaseException,
        note: str,
        force_legacy: bool = False
) -> BaseException:
    """
    Add unstructured information to an exception.

    If PEP 678 is available (i.e. on Python >= 3.11), use it, otherwise create
    a new exeception based on the old one with an updated note.

    Args:
        ex (BaseException): the exception to modify
        note (str): extra information to append to the exception
        force_legacy (bool): for testing

    Returns:
        BaseException: modified exception

    Example:
        >>> ex = Exception('foo')
        >>> new_ex = add_exception_note(ex, 'hello world', force_legacy=False)
        >>> print(new_ex)
        >>> new_ex = add_exception_note(ex, 'hello world', force_legacy=True)
        >>> print(new_ex)
    """
    if not force_legacy and hasattr(ex, 'add_note'):
        # Requires python.311 PEP 678
        ex.add_note(note)  # type: ignore
        return ex
    else:
        return type(ex)(f'{ex}\n{note}')
