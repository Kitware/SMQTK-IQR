#!/usr/bin/env bash
# --------------------------------------------------------------------------
# IQR demo with PrePopulated Hidden Layer/Activations Descriptors
# ---------------------------------------------------------------------------

__doc__='
The following guide provides steps to run the IQR demo using a prepopulated
hidden activation descriptor set.
The overall process is outlined as follows:
1. Generate a geowatch toydata set based upon the code in Geowatch Tutorial 1.
2. Perform the geowatch.fusion.predict operation to generate the hidden layer
   descriptors, and stitch them back to form the kwcoco data set.
3. Build the IQR model using the build_models_demo.py script.
4. Run the IQR service and search dispatcher with the config files provided
in the tutorials directory.

More details and comments on the steps are provided with the commands below.

Details on library packages, versions and depencies:
The demo was written and run with Python version 3.11.2.
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
pip install faiss-cpu

Install Mongo:
https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/

curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
  sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg \
  --dearmor

  echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] \
  https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | \
  sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

  sudo apt-get install -y mongodb-org

  sudo systemctl start mongod
'

# ---------------------------------------------------------------------------
# Commands and comments to run the IQR demo
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Build the toydata set.  (See Geowatch Tutorial 1 for more details)

export ACCELERATOR="${ACCELERATOR:-gpu}"

echo "
------
Step 1
------
Generate the demo kwcoco data
"

DVC_DATA_DPATH=$HOME/data/dvc-repos/toy_data_dvc
DVC_EXPT_DPATH=$HOME/data/dvc-repos/toy_expt_dvc
TRAIN_FPATH=$DVC_DATA_DPATH/vidshapes_rgb_train/data.kwcoco.json
VALI_FPATH=$DVC_DATA_DPATH/vidshapes_rgb_vali/data.kwcoco.json
TEST_FPATH=$DVC_DATA_DPATH/vidshapes_rgb_test/data.kwcoco.json

# Generate toy datasets using the "kwcoco toydata" tool
kwcoco toydata vidshapes2-frames10-amazon --bundle_dpath "$DVC_DATA_DPATH"/vidshapes_rgb_train
kwcoco toydata vidshapes4-frames10-amazon --bundle_dpath "$DVC_DATA_DPATH"/vidshapes_rgb_vali
kwcoco toydata vidshapes2-frames6-amazon --bundle_dpath "$DVC_DATA_DPATH"/vidshapes_rgb_test


echo "
------
Step 2
------
The next step is to train a small model on these images.
This step is only needed if you don't already have a pretrained model.
"

WORKDIR=$DVC_EXPT_DPATH/training/$HOSTNAME/$USER
EXPERIMENT_NAME=ToyRGB_Demo_V001
DATASET_CODE=ToyRGB
DEFAULT_ROOT_DIR=$WORKDIR/$DATASET_CODE/runs/$EXPERIMENT_NAME
MAX_STEPS=32
TARGET_LR=3e-4
WEIGHT_DECAY=$(python -c "print($TARGET_LR * 1e-2)")
python -m geowatch.tasks.fusion fit --config "
data:
    num_workers          : 0
    train_dataset        : $TRAIN_FPATH
    vali_dataset         : $VALI_FPATH
    channels             : 'r|g|b'
    time_steps           : 5
    chip_dims            : 128
    batch_size           : 3
model:
    class_path: MultimodalTransformer
    init_args:
        name        : $EXPERIMENT_NAME
        arch_name   : smt_it_stm_p8
        global_box_weight: 1
optimizer:
  class_path: torch.optim.AdamW
  init_args:
    lr: $TARGET_LR
    weight_decay: $WEIGHT_DECAY
trainer:
  default_root_dir     : $DEFAULT_ROOT_DIR
  accelerator          : $ACCELERATOR
  devices              : 1
  #devices              : 0,
  max_steps: $MAX_STEPS
  num_sanity_val_steps: 0
  limit_val_batches    : 2
  limit_train_batches  : 4
"

PACKAGE_FPATH="$DEFAULT_ROOT_DIR"/final_package.pt

# Find a package if training did not complete
PACKAGE_FPATH=$(python -c "if 1:
    import pathlib
    default_root = pathlib.Path(r'$DEFAULT_ROOT_DIR')
    pkg = default_root / 'final_package.pt'
    if pkg.exists():
        print(pkg)
    else:
        cand = sorted(default_root.glob('package-interupt/*.pt'))
        assert len(cand)
        print(cand[-1])
")
echo "$PACKAGE_FPATH"


echo "
------
Step 3
------
Predict deep descriptors for a kwcoco file.
"

# ---------------------------------------------------------------------------
# Perform the predict operation to generate the hidden layer descriptors
# and build the kwcoco dataset for IQR
python -m geowatch.tasks.fusion.predict \
    --test_dataset="$TEST_FPATH" \
    --package_fpath="$PACKAGE_FPATH"  \
    --with_hidden_layers=True  \
    --pred_dataset="$DVC_EXPT_DPATH"/predictions/pred.kwcoco.json

PREDICT_OUTPUT_FPATH="$DVC_EXPT_DPATH"/predictions/pred.kwcoco.json

# ---------------------------------------------------------------------------
# Build the models for IQR.  More detailed steps and setup follows:


# A. (Optional) Remove previous directories and contents for a clean model build
# /smqtk_iqr/demodata
# /smqtk_iqr/docs/tutorials/models and /workdir

# 1. Generate image chips with hidden layer descriptors
# TODO: Update this info
# navigate to smqtk_iqr/docs/tutorials then run:
OUTPUT_DPATH=./output
cd ~/code/SMQTK-IQR/smqtk_iqr/docs/tutorials/
python chip_hidden_layers.py --DEMODATA_OUTPUT_PATH=$OUTPUT_DPATH --DATA_FPATH=$PREDICT_OUTPUT_FPATH

# cat $OUTPUT_DPATH

# 2. Generate the SMQTK-IQR data set, descriptor set and faiss nnindex
python build_models_demo.py -v \
  -c runApp.IqrSearchApp.json runApp.IqrRestService.json \
  -m $OUTPUT_DPATH/manifest.json \
  -t "GEOWATCH_DEMO"

# 3. Run mongodb service if not already started - config is set to use default
# host and port ://127.0.0.1:27017
sudo systemctl start mongodb
sudo systemctl status mongodb

# 4. check the status of the service
mongo --eval "db.getMongo()"
# Should have message:
# connecting to: mongodb://127.0.0.1:27017
# 'smqtk' database will be created when the IQR service is run the first time.
# Enter a mongo shell, to view available databases:
mongo
show dbs
mongo --eval "show dbs"

# NOTE: depending on versions of mongo version 3.x for Ubuntu 20.04 is the
# above command and 7.x for Ubuntu 22.04,
mongo_22_04(){
# 3. Run mongodb service if not already started - config is set to use default
# host and port ://127.0.0.1:27017
sudo systemctl start mongod
sudo systemctl status mongod

# 4. check the status of the service
mongosh --eval "db.getMongo()"
# Should have message:
# connecting to: mongodb://127.0.0.1:27017
# 'smqtk' database will be created when the IQR service is run the first time.
# Enter a mongo shell, to view available databases:
mongosh --eval "show dbs"
}


# 5. Run the IQR search dispatcher and IQR service from the same directory.

# Following script provides commands to run in two tmux sessions
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

# 7. In the web-browser, select 'GEOWATCH_DEMO' IQR instance

# 8. Both username and password are set to 'demo' by config files

# Appendix:  If you want to perform step 5 in separate terminals, run:
runApplication -a IqrService \
-c runApp.IqrRestService.json

# In second terminal run the IQRsearch dispatcher
runApplication -a IqrSearchDispatcher
-c runApp.IqrSearchApp.json
