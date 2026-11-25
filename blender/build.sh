#!/bin/sh
# Rebuild the watch: model + textures in Blender, then compress for the web.
#   sh blender/build.sh            export only
#   sh blender/build.sh --render   also render Cycles reference stills
set -e
cd "$(dirname "$0")/.."
BLENDER=${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}
"$BLENDER" -b --factory-startup -P blender/build_watch.py -- "$@"
npx gltf-transform meshopt blender/out/watch_raw.glb public/models/watch.glb
mkdir -p public/models/textures
for t in cotes perlage; do
  sips -Z 1024 -s format jpeg -s formatOptions 88 "blender/out/textures/$t.png" --out "public/models/textures/$t.jpg" >/dev/null
done
ls -lh public/models public/models/textures
