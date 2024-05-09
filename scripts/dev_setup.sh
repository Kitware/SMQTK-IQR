#!/bin/bash
__doc__="
Pulls down a multi-module working environment


TODO:
    - [ ] Parameterize relevant options, in the meantime edit the script to modify them.


Usage:
    source scripts/dev_setup.sh
"

#### PARAMTERS #####

# Place where the source packages are located
CODE_DPATH=$HOME/code

DO_CLONE=1
DO_FETCH=1
DRY_RUN=0
FORCE_INSTALL=1

####################

bash_array_repr(){
    __doc__='
    Given a bash array, this should print a literal copy-pastable
    representation

    From:
        https://raw.githubusercontent.com/Erotemic/local/main/init/utils.sh

    Example:
        ARR=(1 "2 3" 4)
        bash_array_repr "${ARR[@]}"
    '
    ARGS=("$@")
    if [ "${#ARGS}" -gt 0 ]; then
        # Not sure if the double or single quotes is better here
        echo "($(printf "'%s' " "${ARGS[@]}"))"
        #echo "($(printf "\'%s\' " "${ARGS[@]}"))"
    else
        echo "()"
    fi
}

mylibs=(
SMQTK-Core
SMQTK-Indexing
SMQTK-Detection
SMQTK-Classifier
SMQTK-Descriptors
SMQTK-Image-IO
SMQTK-Relevancy
)

if [[ "$DO_CLONE" == "1" ]]; then
    ### Clone
    for name in "${mylibs[@]}"
    do
        echo "name = $name"
        dpath=$CODE_DPATH/$name
        if [ -d "$dpath" ]; then
            echo "already have dpath = $dpath"
        else
            echo "does not exist dpath. Need to clone = $dpath"
            # todo: need proper url lookup
            git clone https://github.com/Kitware/"$name".git "$dpath"
        fi
    done
fi



if [[ "$DO_FETCH" == "1" ]]; then
    ### Pull and update
    for name in "${mylibs[@]}"
    do
        echo "name = $name"
        dpath=$CODE_DPATH/$name
        if [ -d "$dpath" ]; then
            #git fetch
            #(cd "$dpath" && gup)
            echo "dpath = $dpath"
            #(cd "$dpath" && git fetch && python ~/local/git_tools/git_devbranch.py update)
            # Git-well branch_upgrade looks for "dev/{version}" branches and updates to the latest
            #(cd "$dpath" && git fetch && git-well branch_upgrade)
            (cd "$dpath" && git fetch)
        else
            echo "does not exist dpath = $dpath"
        fi
    done
fi

echo "
My Libs:"
bash_array_repr "${mylibs[@]}"

needs_uninstall=()
needs_install=()
for name in "${mylibs[@]}"
do
    echo "Check: name = $name"
    dpath=$CODE_DPATH/$name
    if [[ -d $dpath ]]; then
        #base_fpath=$(python -c "import $name; print($name.__file__)")
        modname=$(python -c "print('$name'.replace('-', '_').lower())")
        pkgname=$(python -c "print('$name'.replace('-', '_').lower())")
        echo "modname = $modname"
        if [[ "$FORCE_INSTALL" == "1" ]]; then
            needs_install+=("-e" "$dpath")
        else
            if python -c "import sys, $modname; sys.exit(1 if 'site-packages' in $modname.__file__ else 0)"; then
                echo " * already have dpath = $dpath"
            else
                echo " * will ensure dpath = $dpath"
                needs_uninstall+=("$pkgname")
                needs_install+=("-e" "$dpath")
                #pip uninstall "$name" -y
                #pip uninstall "$name" -y
                #pip install -e "$dpath"
            fi
        fi
    else
        echo " * does not exist dpath = $dpath"
    fi
done

echo "
Needs Uninstall:"
bash_array_repr "${needs_uninstall[@]}"


echo "
Needs Install:"
bash_array_repr "${needs_install[@]}"



if [[ "$DRY_RUN" == "0" ]]; then

    if [[ ${#needs_uninstall[@]} -gt 0 ]]; then
        echo "
        Uninstalling:
        "
        set -x
        pip uninstall -y "${needs_uninstall[@]}"
        set +x
        echo "
        Finished Uninstalling.
        "
    else
        echo "
        No uninstall needed
        "
    fi

    if [[ ${#needs_install[@]} -gt 0 ]]; then
        echo "
        Installing:
        "
        # * Disable build isolation because it is faster and we usually wont need it.
        # * Note the -e needs to be before every package, this is handled earlier
        set -x
        pip install "${needs_install[@]}"
        #pip install --no-build-isolation "${needs_install[@]}"
        set +x
        echo "
        Finished Installing
        "
    else
        echo "
        No install needed
        "
    fi

fi


echo "
Check that the installed versions / paths are what you expect:
"
for name in "${mylibs[@]}"
do
    modname=$(python -c "print('$name'.replace('-', '_').lower())")
    python -c "import $modname; print(f'{$modname.__name__:<17} - {getattr($modname, \"__version__\", \"No __version__ attribute\")} - {$modname.__file__}')"
done

