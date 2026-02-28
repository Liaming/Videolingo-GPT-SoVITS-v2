# VideoLingo + GPT-SoVITS Docker Integration

本项目基于 [VideoLingo](https://github.com/Huanshere/VideoLingo) 和 [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)，通过 Docker Compose 将两者集成，实现全自动视频翻译与中文配音。

## 环境要求

| 组件 | 要求 |
|------|------|
| GPU | NVIDIA GPU，显存 ≥ 8GB（推荐 RTX 2070 及以上） |
| NVIDIA 驱动 | ≥ 570（支持 CUDA 12.8） |
| 内存 | ≥ 16GB |
| 磁盘 | ≥ 100GB 可用空间 |
| 系统 | Windows 11 + WSL2，或 Linux |
| Docker | Docker Desktop（Windows）或 Docker Engine（Linux） |

## 目录结构

```
projects/
├── VideoLingo/          # 主项目（本仓库）
└── GPT-SoVITS/          # GPT-SoVITS 项目（本仓库）
```

两个文件夹必须位于**同一个父目录**下，因为 docker-compose.yml 使用相对路径挂载 GPT-SoVITS。

## 部署步骤

### 1. 克隆本仓库

```bash
mkdir -p ~/Codebase/projects
cd ~/Codebase/projects
git clone https://github.com/你的用户名/Videolingo-GPT-SoVITS-v2.git .
```

### 2. 下载 GPT-SoVITS 预训练模型

将以下模型文件放入 `GPT-SoVITS/GPT_SoVITS/pretrained_models/` 目录：

| 文件/目录 | 说明 | 下载地址 |
|-----------|------|----------|
| `s1v3.ckpt` | Text2Semantic 模型 | [HuggingFace](https://huggingface.co/lj1995/GPT-SoVITS) |
| `v2Pro/s2Gv2ProPlus.pth` | VITS 模型 | 同上 |
| `chinese-roberta-wwm-ext-large/` | BERT 模型 | 同上 |
| `chinese-hubert-base/` | HuBERT 模型 | 同上 |

> 国内可使用镜像：`https://hf-mirror.com`

### 3. 准备参考音频

录制一段 3-10 秒的清晰中文语音，命名格式为：

```
narrator_你说的内容.wav
```

例如：`narrator_这是一段测试音频.wav`

将文件放入：
```
GPT-SoVITS/GPT_SoVITS/configs/
```

### 4. 配置 VideoLingo

复制配置模板并填写 API key：

```bash
cp VideoLingo/configbackup.yaml VideoLingo/config.yaml
```

编辑 `VideoLingo/config.yaml`，填写以下字段：

```yaml
api:
  key: '你的 DeepSeek API Key'
  base_url: 'https://api.deepseek.com/v1'
  model: 'deepseek-chat'
```

> DeepSeek API Key 申请地址：https://platform.deepseek.com

### 5. 启动服务

```bash
cd VideoLingo
docker compose up -d
```

首次启动会自动构建 VideoLingo 镜像，约需 20-30 分钟（取决于网速）。

GPT-SoVITS 容器启动需要约 60-120 秒加载模型，VideoLingo 会等待其健康检查通过后自动启动。

### 6. 访问界面

浏览器打开：
```
http://localhost:8501
```

## 重要参数说明

编辑 `VideoLingo/config.yaml` 调整以下参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `whisper.model` | `large-v3` | 语音识别模型，显存不足可改为 `large-v3-turbo` |
| `whisper.language` | `en` | 原视频语言 |
| `target_language` | `简体中文` | 目标翻译语言 |
| `demucs` | `true` | 人声分离，提高识别质量 |
| `video_volume` | `0.0` | 原视频音量（0.0=静音，1.0=保留原声） |
| `max_workers` | `8` | LLM 并发数 |
| `burn_subtitles` | `true` | 是否将字幕烧录进视频 |
| `gpt_sovits.character` | `narrator` | 配音角色名，对应 configs 目录下的 yaml 文件 |
| `gpt_sovits.refer_mode` | `1` | 参考模式（1=使用预设参考音频） |

## 常用命令

```bash
# 启动所有服务
docker compose up -d

# 停止所有服务
docker compose down

# 查看日志
docker logs gpt-sovits_container
docker logs videolingo_container

# 重新构建 VideoLingo 镜像（修改 Dockerfile 后需要执行）
docker compose up --build -d --force-recreate videolingo

# 清理构建缓存（磁盘不足时使用）
docker builder prune -f
```

## 注意事项

- `config.yaml` 包含 API key，已加入 `.gitignore`，**不要提交到 Git**
- 模型文件体积较大（约 20GB），已加入 `.gitignore`，需要手动下载
- 参考音频已加入 `.gitignore`，需要手动录制并放置
- 视频处理建议不超过 90 分钟（RTX 2070 8GB 显存限制）
- 上传视频大小限制为 4GB

## 硬件兼容性

本项目依赖 CUDA 12.8，需要以下硬件支持：

- NVIDIA GPU，Compute Capability ≥ 7.0（Volta 架构及以上，即 GTX 1080 Ti / RTX 系列）
- NVIDIA 驱动版本 ≥ 570
- 不支持 AMD GPU 或纯 CPU 运行
