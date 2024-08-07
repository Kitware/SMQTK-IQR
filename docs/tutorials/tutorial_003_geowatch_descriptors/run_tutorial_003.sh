#!/usr/bin/env bash
__doc__='
----------------------------------
IQR demo with real GeoWATCH models
----------------------------------

This script should be run from inside the tutorial directory. E.g. on the
developers machine this looks like:

Prerequisites:
    pip install girder-client

.. code:: bash

    cd $HOME/code/smqtk-repos/SMQTK-IQR/docs/tutorials/tutorial_003_geowatch_descriptors
'

WORKING_DIRECTORY=./workdir

# Choose cpu or gpu
if nvidia-smi > /dev/null ; then
    export ACCELERATOR="${ACCELERATOR:-gpu}"
else
    export ACCELERATOR="${ACCELERATOR:-cpu}"
fi


### Setup Environment Variables
# The location of all important paths should be knowable a-priori to running
# this script and potentially before the data is even generated.

CHIPPED_IMAGES_DPATH=$WORKING_DIRECTORY/processed/chips
MANIFEST_FPATH=$WORKING_DIRECTORY/processed/manifest.json

PREDICT_DPATH=$WORKING_DIRECTORY/predictions
PREDICT_OUTPUT_FPATH="$PREDICT_DPATH"/pred.kwcoco.zip

PACKAGE_FPATH="$WORKING_DIRECTORY"/deep_model.pt

MODEL_DOWNLOAD_DPATH="$WORKING_DIRECTORY"/download_models
MODEL_DOWNLOAD_ZIP_FPATH="$WORKING_DIRECTORY"/download_models/release_2024-01-11.zip

# TODO: provide a mechanism to download this dataset
KWCOCO_FPATH=/media/joncrall/flash1/smart_phase3_data/Drop8-Median10GSD-V1/KR_R002/imgonly-KR_R002-rawbands.kwcoco.zip

#PACKAGE_FPATH="$WORKING_DIRECTORY"/download_models/release_2024-01-11/models/fusion/Drop7-Cropped2GSD/packages/Drop7-Cropped2GSD_SC_bgrn_gnt_split6_V84/Drop7-Cropped2GSD_SC_bgrn_gnt_split6_V84_epoch17_step1548.pt
PACKAGE_FPATH="$WORKING_DIRECTORY/download_models/release_2024-01-11/models/fusion/uconn/D7-V2-COLD-candidate/epoch=203-step=4488.pt"

echo "
ACCELERATOR          = $ACCELERATOR

WORKING_DIRECTORY    = $WORKING_DIRECTORY

KWCOCO_FPATH          = $KWCOCO_FPATH
PACKAGE_FPATH        = $PACKAGE_FPATH

CHIPPED_IMAGES_DPATH = $CHIPPED_IMAGES_DPATH
MANIFEST_FPATH       = $MANIFEST_FPATH

PREDICT_DPATH        = $PREDICT_DPATH
PREDICT_OUTPUT_FPATH = $PREDICT_OUTPUT_FPATH
"

# Download the model if it does not exist
if [ -e "$MODEL_DOWNLOAD_ZIP_FPATH" ] ; then
    echo "Model zip already exists"
else
    girder-client --api-url https://data.kitware.com/api/v1 download --parent-type item 65a94833d5d9e43895a66505 "$MODEL_DOWNLOAD_DPATH"
fi

# Extact the package if necessary
if [ -e "$PACKAGE_FPATH" ] ; then
    echo "Model is unzipped"
else
    unzip $MODEL_DOWNLOAD_ZIP_FPATH -d "$MODEL_DOWNLOAD_DPATH"
    geowatch torch_model_stats "$PACKAGE_FPATH"
fi


if [[ "$ACCELERATOR" == "gpu" ]]; then
    PREDICT_DEVICE_ARGS=(--devices="0,")
else
    PREDICT_DEVICE_ARGS=()
fi
python -m geowatch.tasks.fusion.predict \
    --test_dataset="$KWCOCO_FPATH" \
    --package_fpath="$PACKAGE_FPATH" \
    --pred_dataset="$PREDICT_OUTPUT_FPATH" \
    --with_hidden_layers=True \
    --with_class=False \
    --with_saliency=True \
    --quality_threshold=0 \
    --use_cloudmask=False \
    --fixed_resolution=10GSD \
     "${PREDICT_DEVICE_ARGS[@]}"


python prepare_real_multitemporal_descriptors.py \
    --coco_fpath "$PREDICT_OUTPUT_FPATH" \
    --out_chips_dpath "$CHIPPED_IMAGES_DPATH" \
    --out_mainfest_fpath "$MANIFEST_FPATH" \
    --visual_channels "red|green|blue" \
    --space_window_size "196,196" \
    --time_window_size 10

python ~/code/smqtk-repos/SMQTK-IQR/docs/tutorials/tutorial_002_kwcoco_real_descriptors/prepare_real_descriptors.py \
    --coco_fpath "$PREDICT_OUTPUT_FPATH" \
    --out_chips_dpath "$CHIPPED_IMAGES_DPATH" \
    --out_mainfest_fpath "$MANIFEST_FPATH" \
    --visual_channels "red|green|blue" \
    --space_window_size "196,196" \


# NOTE: there is a "workdir" in the runApp configs, which will put outputs in
# this working directory. TODO: make this specifiable on the CLI here.
python ingest_precomputed_descriptors.py \
    --verbose=True \
    --config runApp.IqrSearchApp.json runApp.IqrRestService.json \
    --debug_nn_index True \
    --manifest_fpath "$MANIFEST_FPATH" \
    --tab "GEOWATCH_DEMO"


echo "
Step 7
------
Run the IQR search dispatcher and IQR service from the same directory.
"
# Following script provides commands to run in two tmux sessions
COMMAND="runApplication -v -a IqrService -c runApp.IqrRestService.json"
SESSION_ID="SMQTK-IQR-SERVICE"
tmux kill-session -t "$SESSION_ID" 2> /dev/null || true
tmux new-session -d -s "$SESSION_ID" "bash"
tmux send -t "$SESSION_ID" "$COMMAND" Enter

COMMAND="runApplication -v -a IqrSearchDispatcher -c runApp.IqrSearchApp.json"
SESSION_ID="SMQTK-IQR-SEARCH-DISPATCHER"
tmux kill-session -t "$SESSION_ID" 2> /dev/null || true
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
