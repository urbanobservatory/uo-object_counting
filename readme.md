# uo-object_counting API
Simple flask + tensorflow API for counting objects in online images.
based on python-flask-docker-sklearn-template \
https://github.com/Soluto/python-flask-sklearn-docker-template

#### Build
build for use with or without GPU \
`docker build . -f Dockerfile-with_gpu -t tflsk_gpu` 
`docker build . -f Dockerfile-without_gpu -t tflsk_nogpu`

run with environmental variable `GPU=1` even if there's no GPU in use (i.e. you're starting tflsk_nogpu)\
this way you won't trigger any changes to defaults (which would cause an error if there's no GPU)\
`docker run -d --rm -e PYTHONPATH='/tensorflow/models/research:/tensorflow/models/research/slim' -e ENVIRONMENT='production' -e MODEL='fig_frcnn_rebuscov-3.pb' -e LABELS='rebuscov-classes-3.pbtxt' -e GPU_MEMORY=1 -e MIN_CONF=0.33 -e W=640 -e H=480 -p 6001:80 tflsk_nogpu`

running with GPU requires nvidia-docker rather than regular docker (setting runtime depends on nvidia-docker version, either `"--runtime=nvidia"` or `"--gpus all"`)

`docker run -d --runtime=nvidia --rm -e PYTHONPATH='/tensorflow/models/research:/tensorflow/models/research/slim' -e ENVIRONMENT='production' -e MODEL='fig_frcnn_rebuscov-1.pb' -e LABELS='rebuscov-classes-1.pbtxt' -e GPU_MEMORY=1 -e MIN_CONF=0.33 -e W=640 -e H=480 -p 6001:80 tflsk_gpu`

#### Usage
call API\
`127.0.0.1:6001/detection/api/v1.0/count_vehicles?img_url=https://file.newcastle.urbanobservatory.ac.uk/camera-feeds/GH_A692B1/20200319/191336.jpg`

respose will be e.g.\
`{car: {count: 4}, bus: {count: 1}, van: {count: 1}, cyclist: {count: 1}, person: {count: 4}, total: {count: 11}}`

#### Object Detection Model
The model included in `/app/` folder is FRCNN 640x480 trained on PitchIn Rebuscov dataset (collection of ~10K traffic CCTV images), publicly available soon...