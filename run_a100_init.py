import sys
from colab_cli.common import state
from colab_cli.runtime import ColabRuntime

s = state.get_session("lopy")
rt = ColabRuntime(s.url, s.token, kernel_id=s.kernel_id)

code = """
import os, shutil, subprocess
from pathlib import Path

print("1. Extracting codebase...")
shutil.unpack_archive("/content/lopy_code.tar.gz", "/content/lopy-workflow-colab")

# Replace run_colab_video.py
if Path("/content/run_colab_video.py").exists():
    shutil.copy2("/content/run_colab_video.py", "/content/lopy-workflow-colab/pipeline/drama_real_fake_daughter/run_colab_video.py")

print("2. Extracting audio and frames...")
drama_dir = Path("/content/lopy-workflow-colab/pipeline/drama_real_fake_daughter")
drama_dir.mkdir(parents=True, exist_ok=True)
shutil.unpack_archive("/content/drama_audio.tar.gz", str(drama_dir))
shutil.unpack_archive("/content/drama_frames.tar.gz", str(drama_dir))

# Ensure runtime dirs and symlinks
base = Path("/content/lopy-workflow-colab")
for d in ["inputs", "outputs", "chars", "first"]:
    (base / f"runtime/{d}").mkdir(parents=True, exist_ok=True)
if not (base / "input").exists():
    (base / "input").symlink_to(base / "runtime/inputs")
if not (base / "output").exists():
    (base / "output").symlink_to(base / "runtime/outputs")

print("3. Running colab_setup.sh...")
cmd = "bash /content/lopy-workflow-colab/cloud/colab_setup.sh"
subprocess.run(cmd, shell=True, executable="/bin/bash", check=True)

print("4. Launching Stage 3 video rendering on A100...")
cmd_run = "nohup python3 -u /content/lopy-workflow-colab/pipeline/drama_real_fake_daughter/run_colab_video.py > /content/video_pipeline.log 2>&1 &"
os.system(cmd_run)
print("Pipeline successfully launched on A100!")
"""

def print_output(msg):
    msg_type = msg.get("header", {}).get("msg_type")
    content = msg.get("content", {})
    if msg_type == "stream":
        print(content.get("text", ""), end="", flush=True)
    elif msg_type == "error":
        print("ERROR:", content.get("ename"), content.get("evalue"), flush=True)

try:
    rt.execute_code(code, output_hook=print_output, timeout=300)
finally:
    try: rt.stop()
    except Exception: pass
