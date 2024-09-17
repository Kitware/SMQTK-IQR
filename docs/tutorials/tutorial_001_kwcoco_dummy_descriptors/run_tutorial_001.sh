#!/usr/bin/env bash
__doc__='
-----------------------------------------
IQR demo with PrePopulated Descriptor Set
-----------------------------------------

The following guide provides steps to run the IQR demo with a prepopulated
descriptor set. The demo was written and run with Python version 3.11.2.

The ``ingest_precomputed_descriptors.py`` script is used to generate the descriptor set
without calling the methods in one of the descriptor generator
modules. Using the PrePopulatedDescriptorGenerator class, the descriptor set
is generated from a manifest file that contains the paths to the image files
and the corresponding descriptor files. The manifest file is created by the
``prepare_contrived_descriptors.py`` script that generates image chips from
kwcoco images and builds dummy descriptor files.

This tutorial has additional Python requirements:

    pip install faiss-cpu==1.8.0
    pip install "psycopg2-binary>=2.9.5,<3.0.0"
    pip install scriptconfig ubelt rich kwcoco


To install MongoDB see: ../../environment/installing_mongodb.rst

This script also assumes that tmux is installed.

This script should be run from inside the tutorial directory. E.g. on the
developers machine this looks like:

.. code:: bash

    cd ~/code/smqtk-repos/SMQTK-IQR/docs/tutorials/tutorial_001_kwcoco_dummy_descriptors
'

# ---------------------------------------------------------------------------
# Steps to run the IQR demo with a prepopulated descriptor set
# ---------------------------------------------------------------------------


# Choose a working directory where we can write data
WORKING_DIRECTORY=./workdir


### Setup Environment Variables
# The location of all important paths should be knowable a-priori to running
# this script and potentially before the data is even generated.
KWCOCO_FPATH=$WORKING_DIRECTORY/kwcoco_bundle/data.kwcoco.json
CHIPPED_IMAGES_DPATH=$WORKING_DIRECTORY/processed/chips
MANIFEST_FPATH=$WORKING_DIRECTORY/processed/manifest.json

echo "
KWCOCO_FPATH         = $KWCOCO_FPATH
CHIPPED_IMAGES_DPATH = $CHIPPED_IMAGES_DPATH
MANIFEST_FPATH       = $MANIFEST_FPATH
"

# (Optional) Remove previous directories and contents for a clean model build
# rm -rf "$WORKING_DIRECTORY"
mkdir -p "$WORKING_DIRECTORY"

echo "
------
Step 1
------
Generate the demo kwcoco data
"

# Generate toy datasets using the "kwcoco toydata" tool
kwcoco toydata vidshapes2-frames10-amazon --dst "$KWCOCO_FPATH"


echo "
------
Step 2
------
Convert the kwcoco file into a directory of chipped images with descriptors.
"
python prepare_contrived_descriptors.py \
    --coco_fpath "$KWCOCO_FPATH" \
    --out_chips_dpath "$CHIPPED_IMAGES_DPATH" \
    --out_mainfest_fpath "$MANIFEST_FPATH"


echo "
------
Step 3
------
Ingest the images and descriptors into the SMQTK database.
"
# NOTE: there is a "workdir" in the runApp configs, which will put outputs in
# this working directory. TODO: make this specifiable on the CLI here.
# 2. Generate the SMQTK-IQR data set, descriptor set and faiss nnindex
python ingest_precomputed_descriptors.py \
    --verbose=True \
    --config runApp.IqrSearchApp.json runApp.IqrRestService.json \
    --manifest_fpath "$MANIFEST_FPATH" \
    --debug_nn_index=True \
    --tab "GEOWATCH_DEMO"

echo "
Step 4
------
Ensure MongoDB is running
"
if ! systemctl status mongod --no-pager; then
    sudo systemctl start mongod
    systemctl status mongod --no-pager
fi


echo "
Step 5
------
Run the IQR search dispatcher and IQR service from the same directory.

Alternative: Instead of running the commands in tmux sessions, you can simply
two open different terminals and execute the service and dispatcher in each

In the first terminal:

    runApplication -a IqrService -c runApp.IqrRestService.json

In the second terminal:

    runApplication -a IqrSearchDispatcher -c runApp.IqrSearchApp.json
"

# NOTE: ensure the relevant venv is activated in the new sessions.

# Following script provides commands to run in a single tmux session
# with two split windows
SESSION_NAME="SMQTK-TUTORAL1-SERVERS"
tmux kill-session -t "${SESSION_NAME}" || true
tmux new-session -d -s "${SESSION_NAME}" "/bin/bash"
tmux rename-window -t "${SESSION_NAME}:0" 'main'

COMMAND="runApplication -v -a IqrService -c runApp.IqrRestService.json"
tmux split-window -v -t "${SESSION_NAME}:0.0"
tmux select-pane -t "${SESSION_NAME}:0.0"
tmux send -t "$SESSION_NAME" "$COMMAND" Enter

COMMAND="runApplication -v -a IqrSearchDispatcher -c runApp.IqrSearchApp.json"
tmux select-pane -t "${SESSION_NAME}:0.1"
tmux send -t "$SESSION_NAME" "$COMMAND" Enter

# Fixup the pane layout
tmux select-layout -t "${SESSION_NAME}" even-vertical

# 6. Open a web-browser and navigate to 'localhost:5000'
python -c "import webbrowser; webbrowser.open('127.0.0.1:5000')"

# Reminder: ctrl+b + <arrow-key> lets you move between splits
# within a tmux session.
if [[ "$TMUX" == "" ]]; then
    # not in tmux, attach to the session
    tmux attach-session -t "${SESSION_NAME}"
else
    # already in tmux, switch to the session
    tmux switch -t "${SESSION_NAME}"
fi

echo "
THE FOLLOWING ARE MANUAL STEPS THE USER MUST TAKE.

7. In the web-browser, select 'GEOWATCH_DEMO' IQR instance

8. Both username and password are set to 'demo' by config files

9. You may now interact with the IQR web interface.
"
