import stashapi.log as log
from stashapi.stashapp import StashInterface

stash = StashInterface({
    "scheme": "http",
    "host":"localhost",
    "port": "9999",
    "logger": log
})

scene_data = stash.find_scene(1234)
log.info(scene_data)
