FROM pytorch/pytorch:2.4.1-cuda12.4-cudnn9-runtime

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    libsndfile1 \
    curl \
    ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt

# Clone BreezyVoice repo at pinned commit
RUN git clone --recurse-submodules https://github.com/mtkresearch/BreezyVoice /opt/BreezyVoice/code \
    && cd /opt/BreezyVoice/code \
    && git checkout d592c9d3e8927a0f53f68616387060dcd32a05ea \
    && git submodule update --init --recursive

# Copy winstub into /opt/BreezyVoice/winstub
COPY setup/breezyvoice/winstub /opt/BreezyVoice/winstub

# Install Python dependencies
COPY docker/voice/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --no-cache-dir tiktoken numba \
    && pip install --no-cache-dir --no-build-isolation --no-deps "openai-whisper==20231117"

# Build Matcha-TTS extension
RUN cd /opt/BreezyVoice/code/third_party/Matcha-TTS && python setup.py build_ext --inplace || true

# Environment variables
ENV AI_ROOT=/workspace/models
ENV PYTHONPATH=/opt/BreezyVoice/winstub:/opt/BreezyVoice/code:/opt/BreezyVoice/code/third_party/Matcha-TTS:/workspace/tools
ENV PYTHONUNBUFFERED=1
ENV PYTHONUTF8=1

WORKDIR /workspace

# Symlink model paths so code finds them both at /opt/BreezyVoice and /workspace/models
RUN ln -sf /workspace/models/BreezyVoice/G2PWModel /opt/BreezyVoice/code/G2PWModel \
    && ln -sf /workspace/models/BreezyVoice/model /opt/BreezyVoice/model

CMD ["bash"]
