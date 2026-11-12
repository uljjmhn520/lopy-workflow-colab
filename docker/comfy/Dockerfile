FROM lopy-voice:latest

WORKDIR /opt

# Clone pinned ComfyUI release (v0.40.0)
RUN git clone --depth 1 --branch v0.40.0 https://github.com/comfyanonymous/ComfyUI.git /opt/ComfyUI

# Install ComfyUI dependencies
WORKDIR /opt/ComfyUI
RUN sed -i '/comfyui-workflow-templates/d' requirements.txt \
    && pip install --default-timeout=1000 --retries 10 -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir -r requirements.txt \
    && pip install --default-timeout=1000 --retries 10 -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir comfy-kitchen==0.2.37 accelerate diffusers \
    && pip install --no-cache-dir comfyui-workflow-templates --no-deps -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip install --no-cache-dir "transformers<4.46" -i https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /workspace

# Inject sitecustomize patch for PyTorch 2.4 custom_ops schema compatibility with comfy-kitchen
COPY setup/comfy_patch/sitecustomize.py /opt/conda/lib/python3.11/site-packages/sitecustomize.py

# Default extra model paths configuration for ComfyUI
COPY setup/extra_model_paths_linux.yaml /opt/ComfyUI/extra_model_paths.yaml

EXPOSE 8188

CMD ["python3", "/opt/ComfyUI/main.py", "--disable-cuda-malloc", "--listen", "0.0.0.0", "--port", "8188", "--disable-auto-launch", "--preview-method", "none", "--cache-none", "--lowvram", "--reserve-vram", "4.0", "--input-directory", "/workspace/input", "--output-directory", "/workspace/output"]
