import os, shutil, subprocess
from pathlib import Path

print("1. Extracting codebase...")
shutil.unpack_archive("/content/lopy_code.tar.gz", "/content/lopy-workflow-colab")

print("2. Running colab_setup.sh...")
cmd = "bash /content/lopy-workflow-colab/cloud/colab_setup.sh"
subprocess.run(cmd, shell=True, executable="/bin/bash", check=True)

# Ensure symlinks
base = Path("/content/lopy-workflow-colab")
for d in ["inputs", "outputs", "chars", "first"]:
    (base / f"runtime/{d}").mkdir(parents=True, exist_ok=True)
if not (base / "input").exists():
    (base / "input").symlink_to(base / "runtime/inputs")
if not (base / "output").exists():
    (base / "output").symlink_to(base / "runtime/outputs")

print("3. Launching run_colab_keyframes.py...")
cmd_run = "nohup python3 -u /content/lopy-workflow-colab/pipeline/drama_real_fake_daughter/run_colab_keyframes.py > /content/keyframes_pipeline.log 2>&1 &"
os.system(cmd_run)
print("Keyframes Pipeline launched successfully!")
