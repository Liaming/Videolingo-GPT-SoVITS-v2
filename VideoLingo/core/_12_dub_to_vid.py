import os
import platform
import subprocess

import cv2
import numpy as np
from rich.console import Console

from core._1_ytdlp import find_video_files
from core.asr_backend.audio_preprocess import normalize_audio_volume
from core.utils import *
from core.utils.models import *

console = Console()

DUB_VIDEO = "output/output_dub.mp4"
DUB_SUB_FILE = 'output/dub.srt'
SRC_SUB_FILE = 'output/src.srt'
DUB_AUDIO = 'output/dub.mp3'

FONT_NAME = 'Arial'
if platform.system() == 'Linux':
    FONT_NAME = 'NotoSansCJK-Regular'
elif platform.system() == 'Darwin':
    FONT_NAME = 'Arial Unicode MS'

def merge_video_audio():
    """Merge video and audio, and reduce video volume"""
    VIDEO_FILE = find_video_files()
    background_file = _BACKGROUND_AUDIO_FILE
    video_volume = load_key("video_volume")
    
    if not load_key("burn_subtitles"):
        rprint("[bold yellow]Warning: A 0-second black video will be generated as a placeholder as subtitles are not burned in.[/bold yellow]")

        # Create a black frame
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(DUB_VIDEO, fourcc, 1, (1920, 1080))
        out.write(frame)
        out.release()

        rprint("[bold green]Placeholder video has been generated.[/bold green]")
        return

    # Normalize dub audio
    normalized_dub_audio = 'output/normalized_dub.wav'
    normalize_audio_volume(DUB_AUDIO, normalized_dub_audio)
    
    # Merge video and audio with translated subtitles
    video = cv2.VideoCapture(VIDEO_FILE)
    TARGET_WIDTH = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    TARGET_HEIGHT = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    video.release()
    rprint(f"[bold green]Video resolution: {TARGET_WIDTH}x{TARGET_HEIGHT}[/bold green]")
    
        # Load subtitle style from config
    sub = load_key("subtitle")
    TRANS_FONT_SIZE = sub.get("trans_font_size", 17)
    TRANS_FONT_COLOR = sub.get("trans_font_color", "&H00FFFF")
    TRANS_OUTLINE_COLOR = sub.get("trans_outline_color", "&H000000")
    TRANS_OUTLINE_WIDTH = sub.get("trans_outline_width", 1)
    TRANS_BACK_COLOR = sub.get("trans_back_color", "&H33000000")
    SRC_FONT_SIZE = sub.get("src_font_size", 15)
    SRC_FONT_COLOR = sub.get("src_font_color", "&HFFFFFF")
    SRC_OUTLINE_COLOR = sub.get("src_outline_color", "&H000000")
    SRC_OUTLINE_WIDTH = sub.get("src_outline_width", 1)
    SRC_SHADOW_COLOR = sub.get("src_shadow_color", "&H80000000")
    SRC_BACK_COLOR = sub.get("src_back_color", "&H80000000")
    BILINGUAL = sub.get("bilingual", True)

    trans_subtitle = (
        f"subtitles={DUB_SUB_FILE}:force_style='FontSize={TRANS_FONT_SIZE},"
        f"FontName={FONT_NAME},PrimaryColour={TRANS_FONT_COLOR},"
        f"OutlineColour={TRANS_OUTLINE_COLOR},OutlineWidth={TRANS_OUTLINE_WIDTH},"
        f"BackColour={TRANS_BACK_COLOR},Alignment=2,MarginV=27,BorderStyle=4'"
    )
    if BILINGUAL and os.path.exists(SRC_SUB_FILE):
        src_subtitle = (
            f"subtitles={SRC_SUB_FILE}:force_style='FontSize={SRC_FONT_SIZE},"
            f"FontName={FONT_NAME},PrimaryColour={SRC_FONT_COLOR},"
            f"OutlineColour={SRC_OUTLINE_COLOR},OutlineWidth={SRC_OUTLINE_WIDTH},"
            f"ShadowColour={SRC_SHADOW_COLOR},BackColour={SRC_BACK_COLOR},Alignment=2,MarginV=45,BorderStyle=4'"
        )
        subtitle_filter = f"{trans_subtitle},{src_subtitle}"
    else:
        subtitle_filter = trans_subtitle
    
    cmd = [
        'ffmpeg', '-y', '-i', VIDEO_FILE, '-i', background_file, '-i', normalized_dub_audio,
        '-filter_complex',
        f'[0:v]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=decrease,'
        f'pad={TARGET_WIDTH}:{TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2,'
        f'{subtitle_filter}[v];'
        f'[1:a]volume={video_volume}[bg];[bg][2:a]amix=inputs=2:duration=first:dropout_transition=3[a]'
    ]

    if load_key("ffmpeg_gpu"):
        rprint("[bold green]Using GPU acceleration...[/bold green]")
        cmd.extend(['-map', '[v]', '-map', '[a]', '-c:v', 'h264_nvenc'])
    else:
        cmd.extend(['-map', '[v]', '-map', '[a]'])
    
    cmd.extend(['-c:a', 'aac', '-b:a', '96k', DUB_VIDEO])
    
    subprocess.run(cmd)
    rprint(f"[bold green]Video and audio successfully merged into {DUB_VIDEO}[/bold green]")

if __name__ == '__main__':
    merge_video_audio()
