#!/usr/bin/env python3
"""
Helper to setup a development environment
"""
import pathlib
import subprocess
import textwrap

REPO_INFOS = [
    {'repo_name': 'SMQTK-Core', 'module_name': 'smqtk_core'},
    {'repo_name': 'SMQTK-Indexing', 'module_name': 'smqtk_indexing'},
    {'repo_name': 'SMQTK-Detection', 'module_name': 'smqtk_detection'},
    {'repo_name': 'SMQTK-Classifier', 'module_name': 'smqtk_classifier'},
    {'repo_name': 'SMQTK-Descriptors', 'module_name': 'smqtk_descriptors'},
    {'repo_name': 'SMQTK-Image-IO', 'module_name': 'smqtk_image_io'},
    {'repo_name': 'SMQTK-Relevancy', 'module_name': 'smqtk_relevancy'},
]


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(
        prog='DevSetupCLI',
        description='SMQTK Developer Setup',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--code_dpath', help='The directory where code should be checked out / installed', default='/home/joncrall/code', dest='code_dpath', required=False)
    parser.add_argument('--clone', help='', default=True, dest='clone', required=False)
    parser.add_argument('--fetch', help='', default=True, dest='fetch', required=False)
    parser.add_argument('--install', help='', default=True, dest='install', required=False)
    ns = parser.parse_args()
    config = ns.__dict__
    return config


def parse_args_scriptconfig():
    """
    Alternative scriptconfig based CLI's are slightly easier to work with IMO,
    but they can typically be ported to pure-argparse to have no deps.
    """
    import scriptconfig as scfg
    class DevSetupCLI(scfg.DataConfig):
        """
        SMQTK Developer Setup
        """
        code_dpath  = scfg.Value(pathlib.Path('~/code').expanduser(), help='The directory where code should be checked out / installed')
        clone = scfg.Value(True, isflag=True)
        fetch = scfg.Value(True, isflag=True)
        install = scfg.Value(True, isflag=True)

    if 1:
        # Print the code for the pure argparse variant
        print(DevSetupCLI().port_to_argparse())

    config = DevSetupCLI.cli()
    return config


def is_installed_in_editable_mode(repo_info):
    """
    Uninstall if we dont have an editable install of the repo
    """
    modname = repo_info['module_name']
    init_fpath = repo_info['module_dpath'] / '__init__.py'

    code = textwrap.dedent(
        f'''
        import sys
        import pathlib
        try:
            import {modname}
        except Exception:
            print('module {modname}  is not installed')
            sys.exit(0)
        modpath = pathlib.Path({modname}.__file__)
        init_fpath = pathlib.Path('{init_fpath}')
        if init_fpath.resolve() == modpath.resolve():
            print('module {modname} is installed in editable mode')
            sys.exit(0)
        else:
            print('module {modname} is installed, but not in editable mode')
            sys.exit(1)
        ''').strip()
    try:
        command = f'python -c "\n{code}"'
        # print(command)
        stdout = subprocess.check_output(command, shell=True, universal_newlines=True)
        print(stdout)
    except Exception:
        return False
    else:
        return True


def main():
    try:
        config = parse_args_scriptconfig()
    except ImportError:
        config = parse_args()

    code_dpath = pathlib.Path(config['code_dpath'])

    for repo_info in REPO_INFOS:
        # This logic should be configurable, but it is correct for SMQTK
        repo_info['repo_dpath'] = code_dpath / repo_info['repo_name']
        repo_info['repo_url'] = 'https://github.com/Kitware/' + repo_info['repo_name'] + '.git'
        repo_info['module_dpath'] = repo_info['repo_dpath'] / repo_info['module_name']
        repo_info['package_name'] = repo_info['module_name']

    if config['clone']:
        for repo_info in REPO_INFOS:
            repo_dpath = repo_info['repo_dpath']
            if not repo_dpath.exists():
                command = 'git clone {repo_url} {repo_dpath}'
                subprocess.call(command)

    if config['fetch']:
        for repo_info in REPO_INFOS:
            repo_dpath = repo_info['repo_dpath']
            if repo_dpath.exists():
                subprocess.call('git fetch', cwd=repo_info['repo_dpath'], shell=True)

    if config['install']:
        to_uninstall = []
        to_install = []
        for repo_info in REPO_INFOS:
            if not is_installed_in_editable_mode(repo_info):
                to_uninstall.append(repo_info['package_name'])
                to_install.append('-e "' + str(repo_info['repo_dpath']) + '"')
        command = 'pip uninstall -y ' + ' '.join(to_uninstall)
        print(command)
        subprocess.call(command, shell=True)

        command = 'pip install ' + ' '.join(to_install)
        print(command)
        subprocess.call(command, shell=True)


if __name__ == '__main__':
    """

    CommandLine:
        python ~/code/SMQTK-IQR/scripts/dev_setup.py --help
        python ~/code/SMQTK-IQR/scripts/dev_setup.py
    """
    main()
