FROM nvidia/cuda:12.8.0-devel-ubuntu22.04
ENV DEBIAN_FRONTEND=noninteractive
ARG PYTHON_VERSION=3.10
RUN sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    sed -i 's/security.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common git curl sudo ffmpeg fonts-noto wget \
    libsndfile1 pkg-config libavformat-dev libavcodec-dev libavdevice-dev \
    libavutil-dev libswscale-dev libswresample-dev libavfilter-dev \
    iputils-ping fonts-noto-cjk \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update -y \
    && apt-get install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-dev python${PYTHON_VERSION}-venv \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${PYTHON_VERSION} 1 \
    && update-alternatives --set python3 /usr/bin/python${PYTHON_VERSION} \
    && ln -sf /usr/bin/python${PYTHON_VERSION}-config /usr/bin/python3-config \
    && curl -sS https://bootstrap.pypa.io/get-pip.py | python${PYTHON_VERSION} \
    && python3 --version && python3 -m pip --version
RUN apt-get clean && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip setuptools wheel Cython \
    -i https://mirrors.aliyun.com/pypi/simple/
RUN pip install torch==2.0.0 torchaudio==2.0.0 \
    --index-url https://download.pytorch.org/whl/cu118
RUN pip install "av>=11,<12" \
    -i https://mirrors.aliyun.com/pypi/simple/
WORKDIR /app
COPY . .
RUN pip install "audio-separator[gpu]" --no-deps \
    -i https://mirrors.aliyun.com/pypi/simple/ && \
    pip uninstall -y onnx2torch-py313 onnx-weekly && \
    pip install beartype einops julius ml_collections "onnx==1.16.0" onnxruntime-gpu \
    rotary-embedding-torch samplerate scipy six diffq \
    -i https://mirrors.aliyun.com/pypi/simple/ && \
    pip install "torchvision==0.16.2" \
    --index-url https://download.pytorch.org/whl/cu121 && \
    pip install transformers==4.45.0 --force-reinstall \
    -i https://mirrors.aliyun.com/pypi/simple/ && \
    pip uninstall -y onnx2torch-py313 onnx-weekly
RUN pip install --no-build-isolation \
    "whisperx @ git+https://github.com/m-bain/whisperx.git@7307306a9d8dd0d261e588cc933322454f853853" \
    "demucs[dev] @ git+https://github.com/adefossez/demucs" \
    -i https://mirrors.aliyun.com/pypi/simple/
COPY requirements.txt .
RUN pip install -r requirements.txt \
    -i https://mirrors.aliyun.com/pypi/simple/
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}
EXPOSE 8501
CMD ["streamlit", "run", "st.py", "--server.address=0.0.0.0", "--server.enableCORS=false", "--server.enableXsrfProtection=false", "--server.maxUploadSize=4096"]