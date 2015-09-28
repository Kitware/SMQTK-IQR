"""
SMQTK Web Applications
"""

import inspect
import logging
import os

import flask

import smqtk.utils


class SmqtkWebApp (flask.Flask, smqtk.utils.Configurable):
    """
    Base class for SMQTK web applications
    """

    @classmethod
    def impl_directory(cls):
        """
        :return: Directory in which this implementation is contained.
        :rtype: str
        """
        return os.path.dirname(os.path.abspath(inspect.getfile(cls)))

    @classmethod
    def get_default_config(cls):
        """
        Generate and return a default configuration dictionary for this class.
        This will be primarily used for generating what the configuration
        dictionary would look like for this class without instantiating it.

        This should be overridden in each implemented application class to add
        appropriate configuration.

        :return: Default configuration dictionary for the class.
        :rtype: dict

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
    def from_config(cls, config_dict):
        return cls(config_dict)

    def __init__(self, json_config):
        """
        Initialize application based of supplied JSON configuration

        :param json_config: JSON configuration dictionary
        :type json_config: dict

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

    def get_config(self):
        return self.json_config

    @property
    def log(self):
        return logging.getLogger('.'.join((self.__module__,
                                           self.__class__.__name__)))

    def run(self, host=None, port=None, debug=False, **options):
        """
        Override of the run method, drawing running host and port from
        configuration by default. 'host' and 'port' values specified as argument
        or keyword will override the app configuration.
        """
        super(SmqtkWebApp, self)\
            .run(host=(host or self.json_config['server']['host']),
                 port=(port or self.json_config['server']['port']),
                 **options)


def get_web_applications():
    """
    Discover and return SmqtkWebApp implementation classes found in the plugin
    directory. Keys in the returned map are the names of the discovered classes
    and the paired values are the actual class type objects.

    We look for modules (directories or files) that start with and alphanumeric
    character ('_' prefixed files/directories are hidden, but not recommended).

    Within a module, we first look for a helper variable by the name
    ``APPLICATION_CLASS``, which can either be a single class object or
    an iterable of class objects, to be exported. If the variable is set to
    None, we skip that module and do not import anything. If the variable is not
    present, we look for a class by the same na e and casing as the module's
    name. If neither are found, the module is skipped.

    :return: Map of discovered class objects of type ``SmqtkWebApp`` whose
        keys are the string names of the classes.
    :rtype: dict[str, type]

    """
    import os
    from smqtk.utils.plugin import get_plugins

    this_dir = os.path.abspath(os.path.dirname(__file__))
    helper_var = "APPLICATION_CLASS"
    return get_plugins(__name__, this_dir, helper_var, SmqtkWebApp)
