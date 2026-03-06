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


def _find_main_speaker_segment(video_path: str, analyze_duration: int = 480) -> tuple:
    """用pyannote分析前8分钟，找主说话人第一次出现的时间点，返回(start_sec, 300)"""
    try:
        import torch
        from pyannote.audio import Pipeline
        rprint("[cyan]Analyzing speakers on cuda...[/cyan]")
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=os.environ.get('HUGGING_FACE_HUB_TOKEN')
        )
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        pipeline = pipeline.to(device)
        # 只分析前8分钟
        from pyannote.audio import Audio
        # 先用ffmpeg提取音频，pyannote不能直接读mp4
        tmp_wav = '/tmp/pyannote_input.wav'
        subprocess.run(['ffmpeg', '-y', '-i', video_path, '-t', str(analyze_duration),
                       '-ac', '1', '-ar', '16000', '-vn', tmp_wav], capture_output=True)
        audio = Audio(sample_rate=16000, mono=True)
        waveform, sample_rate = audio({'audio': tmp_wav})
        max_samples = analyze_duration * sample_rate
        if waveform.shape[1] > max_samples:
            waveform = waveform[:, :max_samples]
        import io
        import soundfile as sf
        buf = io.BytesIO()
        sf.write(buf, waveform.squeeze().numpy(), sample_rate, format='wav')
        buf.seek(0)
        diarization = pipeline({'waveform': waveform, 'sample_rate': sample_rate}, num_speakers=None)
        # 统计每个说话人总时长
        speaker_duration = {}
        speaker_segments = {}
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speaker_duration[speaker] = speaker_duration.get(speaker, 0) + turn.end - turn.start
            if speaker not in speaker_segments:
                speaker_segments[speaker] = []
            speaker_segments[speaker].append((turn.start, turn.end))
        if not speaker_duration:
            rprint("[yellow]No speakers detected, using default start_sec=30[/yellow]")
            return (30, 300)
        main_speaker = max(speaker_duration, key=speaker_duration.get)
        rprint(f"[cyan]Main speaker: {main_speaker} ({speaker_duration[main_speaker]:.1f}s total)[/cyan]")
        # 找主说话人第一次出现的时间点
        first_start = min(start for start, end in speaker_segments[main_speaker])
        rprint(f"[cyan]Main speaker first appears at {first_start:.1f}s, extracting 5 minutes[/cyan]")
        return (int(first_start), 300)
    except Exception as e:
        rprint(f"[yellow]Speaker analysis failed ({e}), using default start_sec=30[/yellow]")
        return (30, 300)

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

    # torch兼容补丁
    import torch.amp
    import torch.amp.autocast_mode
    if not hasattr(torch.amp.autocast_mode, 'is_autocast_available'):
        torch.amp.autocast_mode.is_autocast_available = lambda dtype: True
    if not hasattr(torch.amp, 'is_autocast_available'):
        torch.amp.is_autocast_available = lambda dtype: True
    from audio_separator.separator import Separator
    separator = Separator(
        output_dir=tmp_out_dir,
        output_format='wav',
        use_autocast=True,
    )
    separator.load_model('model_bs_roformer_ep_317_sdr_12.9755.ckpt')
    output_files = separator.separate(raw_audio)

    vocal_file = next(
        (Path(tmp_out_dir) / f for f in output_files if 'Vocals' in f),
        None
    )
    if vocal_file is None or not vocal_file.exists():
        rprint("[yellow]Vocals file not found, falling back to raw audio[/yellow]")
        return raw_audio

    # 复制到configs/方便试听
    import shutil
    preview_path = str(Path(tmp_out_dir).parent / 'VoiceSeparation.wav')
    shutil.copy2(str(vocal_file), preview_path)
    rprint(f"[cyan]Vocals separated: {vocal_file}[/cyan]")
    rprint(f"[cyan]Preview copy saved to: {preview_path}[/cyan]")
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
        # 重采样到44100Hz，GPT-SoVITS要求
        resampled = str(out_path) + '_44k.wav'
        subprocess.run(['ffmpeg', '-y', '-i', str(out_path), '-ar', '44100', '-ac', '1', resampled], capture_output=True)
        if Path(resampled).exists() and Path(resampled).stat().st_size > 1000:
            Path(resampled).replace(out_path)
            rprint("[cyan]Resampled to 44100Hz[/cyan]")
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

    seg_start, seg_duration = _find_main_speaker_segment(video_path)
    raw_audio = _extract_raw_audio(video_path, start_sec=seg_start, duration=seg_duration)

    try:
        vocal_path = _separate_vocals(raw_audio)
    except Exception as e:
        rprint(f"[yellow]audio-separator failed ({e}), trimming raw audio to 8s[/yellow]")
        trimmed = raw_audio.replace('.wav', '_8s.wav')
        subprocess.run(['ffmpeg', '-y', '-i', raw_audio, '-t', '8', trimmed], capture_output=True)
        vocal_path = trimmed if Path(trimmed).exists() else raw_audio

    # 截取前8秒送给TTS，GPT-SoVITS要求3-10秒
    trimmed_path = vocal_path.replace('.wav', '_8s.wav')
    subprocess.run([
        'ffmpeg', '-y', '-i', vocal_path, '-t', '8',
        '-ar', '44100', '-ac', '1', trimmed_path
    ], capture_output=True)
    if Path(trimmed_path).exists() and Path(trimmed_path).stat().st_size > 1000:
        rprint(f"[cyan]Trimmed to 8s: {trimmed_path}[/cyan]")
        vocal_path = trimmed_path
    _generate_narrator_wav_via_tts(vocal_path, out_wav)
    return str(out_wav)


if __name__ == '__main__':
    import sys
    video = sys.argv[1] if len(sys.argv) > 1 else 'output/test.mp4'
    auto_extract_narrator_voice(video)
