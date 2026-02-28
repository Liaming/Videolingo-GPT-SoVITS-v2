"""
修复 torchaudio 2.10 默认使用 torchcodec 作为后端的问题
在容器启动时运行此脚本
"""
import glob
import os

# 找到 torchaudio __init__.py
candidates = glob.glob('/root/conda/lib/python*/site-packages/torchaudio/__init__.py')
if not candidates:
    print('torchaudio not found, skipping patch')
    exit(0)

path = candidates[0]
content = open(path).read()

old = '''    return load_with_torchcodec(
        uri,
        frame_offset=frame_offset,
        num_frames=num_frames,
        normalize=normalize,
        channels_first=channels_first,
        format=format,
        buffer_size=buffer_size,
        backend=backend,
    )'''

new = '''    import soundfile as sf
    data, sr = sf.read(str(uri), start=frame_offset, stop=None if num_frames==-1 else frame_offset+num_frames, always_2d=True, dtype='float32')
    import torch as _torch
    tensor = _torch.from_numpy(data.T if channels_first else data)
    return tensor, sr'''

if old in content:
    content = content.replace(old, new)
    open(path, 'w').write(content)
    print(f'torchaudio patched successfully: {path}')
elif 'soundfile' in content:
    print('torchaudio already patched, skipping')
else:
    print(f'WARNING: pattern not found in {path}, manual check needed')