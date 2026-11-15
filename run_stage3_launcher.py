import sys
from colab_cli.common import state
from colab_cli.runtime import ColabRuntime

s = state.get_session("lopy")
rt = ColabRuntime(s.url, s.token, kernel_id=s.kernel_id)

code = """
import os
cmd = "nohup python3 -u /content/lopy-workflow-colab/pipeline/drama_zerozerozero/run_colab_video.py > /content/video_pipeline.log 2>&1 &"
os.system(cmd)
print("Stage 3 Video Pipeline launched in background!")
"""

def print_output(msg):
    msg_type = msg.get("header", {}).get("msg_type")
    content = msg.get("content", {})
    if msg_type == "stream":
        print(content.get("text", ""), end="", flush=True)

try:
    rt.execute_code(code, output_hook=print_output, timeout=30)
finally:
    try: rt.stop()
    except Exception: pass
