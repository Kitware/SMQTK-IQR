#!/usr/bin/env bash
__doc__='
-----------------------------------------
IQR demo with PrePopulated Descriptor Set
-----------------------------------------

The following guide provides steps to run the IQR demo with a prepopulated
descriptor set. The demo was written and run with Python version 3.11.2.
Older versions of packages flask 2.0.1 and werkzeug 2.0.0 were used.
The demo uses two werkzeug method `pop_path_info` and `peek_path_info` that
were removed in werkzeug 2.3.0 release that were deprecated in 2.2.0. These
methods are used by the IQR Search Dispatcher that generates the link for
each IQR instance `smqtk/smqtk_iqr/web/search_app/__init__.py`.

The `build_models_demo.py` script is used to generate the descriptor set
without calling the methods in one of the descriptor generator
modules. Using the PrePopulatedDescriptorGenerator class, the descriptor set
is generated from a manifest file that contains the paths to the image files
and the corresponding descriptor files. The manifest file is created by the
chip_images_demo.py script that generates image chips from kwcoco images and
builds dummy descriptor files.

Workaround issue by installing specific versions
pip install flask==2.0.1 werkzeug==2.0.0

Also need the faiss library to be installed
pip install faiss-cpu==1.8.0
pip install "psycopg2-binary>=2.9.5,<3.0.0"

To install MongoDB see: ../../environment/installing_mongodb.rst

This script should be run from inside the tutorial directory. E.g. on the
developers machine this looks like:

.. code:: bash

    cd ~/code/smqtk-repos/SMQTK-IQR/docs/tutorials/tutorial_001_kwcoco_dummy_descriptors
'

# ---------------------------------------------------------------------------
# Steps to run the IQR demo with a prepopulated descriptor set
# ---------------------------------------------------------------------------

# A. If not already merged into the main branch, git clone the fork for
# SMQTK-Descriptors with the branch
# https://github.com/pbeasly/SMQTK-Descriptors.git@dev/prepopulated_descr_generator
# and install the package with `pip install e.`
# Config files use the
# 'PrePopulatedDescriptorGenerator' class.


# Choose a working directory where we can write data
WORKING_DIRECTORY=$HOME/.cache/smqtk_iqr/demo/tutorial_001_data
# B. (Optional) Remove previous directories and contents for a clean model build
# rm -rf "$WORKING_DIRECTORY"
mkdir -p "$WORKING_DIRECTORY"

echo "
------
Step 1
------
Generate the demo kwcoco data
"

# Generate toy datasets using the "kwcoco toydata" tool
KWCOCO_BUNDLE_DPATH=$WORKING_DIRECTORY/kwcoco_bundle
KWCOCO_FPATH=$KWCOCO_BUNDLE_DPATH/data.kwcoco.json

CHIPPED_IMAGES_DPATH=$WORKING_DIRECTORY/processed/chips
MANIFEST_FPATH=$WORKING_DIRECTORY/processed/manifest.json

kwcoco toydata vidshapes2-frames10-amazon --bundle_dpath "$KWCOCO_BUNDLE_DPATH" --dst "$KWCOCO_FPATH"


# 1. Generate image chips and contrived descriptors for this kwcoco file.
python prepare_contrived_descriptors.py \
    --coco_fpath "$KWCOCO_FPATH" \
    --out_chips_dpath "$CHIPPED_IMAGES_DPATH" \
    --out_mainfest_fpath "$MANIFEST_FPATH"

# NOTE: there is a "workdir" in the runApp configs, which will put outputs in
# this working directory. TODO: make this specifiable on the CLI here.

# 2. Generate the SMQTK-IQR data set, descriptor set and faiss nnindex
python ingest_precomputed_descriptors.py \
    --verbose=True \
    --config runApp.IqrSearchApp.json runApp.IqrRestService.json \
    --manifest_fpath "$MANIFEST_FPATH" \
    --tab "GEOWATCH_DEMO"

# 3. Run mongodb service if not already started - config is set to use default
# host and port ://127.0.0.1:27017
#
# NOTE: depending on versions of mongo version 3.x for Ubuntu 20.04 is the
# above command and 7.x for Ubuntu 22.04
mongo_20_04_startup(){
    sudo systemctl start mongodb
    sudo systemctl status mongodb --no-pager

    # 4. check the status of the service
    mongo --eval "db.getMongo()"
    # Should have message:
    # connecting to: mongodb://127.0.0.1:27017
    # 'smqtk' database will be created when the IQR service is run the first time.
    # Enter a mongo shell, to view available databases:
    mongo
    show dbs
    mongo --eval "show dbs"
}

mongo_22_04_startup(){
    sudo systemctl start mongod
    sudo systemctl status mongod --no-pager
    # 4. check the status of the service
    mongosh --eval "db.getMongo()"
    # Should have message:
    # connecting to: mongodb://127.0.0.1:27017
    # 'smqtk' database will be created when the IQR service is run the first time.
    # Enter a mongo shell, to view available databases:
    mongosh --eval "show dbs"
}

if lsb_release -a | grep "Ubuntu 20.04" ; then
    mongo_20_04_startup
else
    # Assume the commands on 22.04 will work on later versions
    mongo_22_04_startup
fi

# 4. Run the IQR search dispatcher and IQR service from the same directory.

# Following script provides commands to run in two background tmux sessions
COMMAND="runApplication -v -a IqrService -c runApp.IqrRestService.json"
SESSION_ID="SMQTK-IQR-SERVICE"
tmux kill-session -t "$SESSION_ID" || true
tmux new-session -d -s "$SESSION_ID" "bash"
tmux send -t "$SESSION_ID" "$COMMAND" Enter

COMMAND="runApplication -v -a IqrSearchDispatcher -c runApp.IqrSearchApp.json"
SESSION_ID="SMQTK-IQR-SEARCH-DISPATCHER"
tmux kill-session -t "$SESSION_ID" || true
tmux new-session -d -s "$SESSION_ID" "bash"
tmux send -t "$SESSION_ID" "$COMMAND" Enter

# 6. Open a web-browser and navigate to 'localhost:5000'
python -c "import webbrowser; webbrowser.open('127.0.0.1:5000')"

echo "
THE FOLLOWING ARE MANUAL STEPS THE USER MUST TAKE.

7. In the web-browser, select 'GEOWATCH_DEMO' IQR instance

8. Both username and password are set to 'demo' by config files

9. You may now interact with the IQR web interface.
"


## Appendix:  If you want to perform step 5 in separate terminals, run:
#runApplication -a IqrService \
#-c runApp.IqrRestService.json

## In second terminal run the IQRsearch dispatcher
#runApplication -a IqrSearchDispatcher -c runApp.IqrSearchApp.json
