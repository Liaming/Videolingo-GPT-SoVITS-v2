import os
import subprocess
from pathlib import Path
from core.utils import rprint

NARRATOR_PROMPT_TEXT = "这是一段测试语音，用于音色克隆参考。"
NARRATOR_FILENAME = "narrator_这是一段测试语音，用于音色克隆参考。.wav"


def _get_configs_dir() -> Path:
    if os.environ.get('DOCKER_MODE') == '1':
        return Path('/workspace/GPT-SoVITS/GPT_SoVITS/configs')
    current = Path(__file__).resolve().parent.parent
    parent = current.parent
    gpt_sovits_dir = next(
        (d for d in parent.iterdir() if d.is_dir() and d.name.startswith('GPT-SoVITS')),
        None
    )
    if gpt_sovits_dir is None:
        raise FileNotFoundError("GPT-SoVITS directory not found")
    return gpt_sovits_dir / 'GPT_SoVITS' / 'configs'


def _extract_raw_audio(video_path: str, start_sec: int = 10, duration: int = 8) -> str:
    tmp_raw = '/workspace/GPT-SoVITS/GPT_SoVITS/configs/auto_voice_raw.wav'
    cmd = [
        'ffmpeg', '-y', '-i', video_path,
        '-ss', str(start_sec), '-t', str(duration),
        '-ac', '1', '-ar', '44100', '-vn',
        tmp_raw
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg extraction failed: {result.stderr.decode()}")
    rprint(f"[cyan]Raw audio extracted: {tmp_raw}[/cyan]")
    return tmp_raw


def _separate_vocals(raw_audio: str) -> str:
    tmp_out_dir = '/workspace/GPT-SoVITS/GPT_SoVITS/configs/sep'
    os.makedirs(tmp_out_dir, exist_ok=True)

    from audio_separator.separator import Separator
    separator = Separator(
        output_dir=tmp_out_dir,
        output_format='wav',
        use_autocast=True,
    )
    separator.load_model('MDX23C-8KFFT-InstVoc_HQ.onnx')
    output_files = separator.separate(raw_audio)

    vocal_file = next(
        (Path(tmp_out_dir) / f for f in output_files if 'Vocals' in f),
        None
    )
    if vocal_file is None or not vocal_file.exists():
        rprint("[yellow]Vocals file not found, falling back to raw audio[/yellow]")
        return raw_audio

    rprint(f"[cyan]Vocals separated: {vocal_file}[/cyan]")
    return str(vocal_file)


def _generate_narrator_wav_via_tts(vocal_path: str, out_path: Path) -> None:
    import requests
    gpt_sovits_url = os.environ.get('GPT_SOVITS_URL', 'http://gpt-sovits:9880')
    payload = {
        'text': NARRATOR_PROMPT_TEXT,
        'text_lang': 'zh',
        'ref_audio_path': vocal_path,
        'prompt_lang': 'en',
        'prompt_text': '',
        'speed_factor': 1.0,
    }
    rprint("[cyan]Calling /tts to generate narrator reference audio...[/cyan]")
    response = requests.post(f'{gpt_sovits_url}/tts', json=payload, timeout=60)
    if response.status_code == 200:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(response.content)
        rprint(f"[bold green]✅ narrator_auto.wav saved: {out_path}[/bold green]")
    else:
        raise RuntimeError(
            f"/tts failed (status {response.status_code}): {response.text}"
        )


def auto_extract_narrator_voice(video_path: str, start_sec: int = 10, duration: int = 8) -> str:
    configs_dir = _get_configs_dir()
    out_wav = configs_dir / NARRATOR_FILENAME

    for old in configs_dir.glob('narrator_*.wav'):
        old.unlink()
        rprint(f"[yellow]Removed old narrator: {old.name}[/yellow]")

    raw_audio = _extract_raw_audio(video_path, start_sec=start_sec, duration=duration)

    try:
        vocal_path = _separate_vocals(raw_audio)
    except Exception as e:
        rprint(f"[yellow]audio-separator failed ({e}), using raw audio[/yellow]")
        vocal_path = raw_audio

    _generate_narrator_wav_via_tts(vocal_path, out_wav)
    return str(out_wav)


if __name__ == '__main__':
    import sys
    video = sys.argv[1] if len(sys.argv) > 1 else 'output/test.mp4'
    auto_extract_narrator_voice(video)
