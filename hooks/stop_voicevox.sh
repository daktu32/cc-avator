#!/bin/bash
#
# ClaudeCode Stop フック - VOICEVOX 音声読み上げ
# Claude の応答完了時に自動実行され、音声を読み上げます
#

set -e

# プロジェクトルート
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Python 仮想環境のパス
VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python3"

# Python スクリプトのパス
TTS_SCRIPT="${PROJECT_ROOT}/scripts/voicevox_tts.py"

# ログファイル
LOG_FILE="${PROJECT_ROOT}/voicevox_tts.log"

# stdin から JSON 入力を読み取る
INPUT=$(cat)

# transcript_path を抽出
TRANSCRIPT_PATH=$(echo "$INPUT" | grep -o '"transcript_path":"[^"]*"' | cut -d'"' -f4)

# デバッグ用にログに記録
{
    echo "=== VOICEVOX TTS Hook ==="
    echo "Timestamp: $(date)"
    echo "Transcript: $TRANSCRIPT_PATH"
} >> "$LOG_FILE" 2>&1

# transcript_path が取得できない場合はエラー
if [ -z "$TRANSCRIPT_PATH" ]; then
    echo "Error: transcript_path not found in input" >> "$LOG_FILE" 2>&1
    exit 0  # ClaudeCode を妨げないため exit 0
fi

# Python スクリプトをバックグラウンドで実行
# エラーが発生しても ClaudeCode の動作を妨げない
{
    "$VENV_PYTHON" "$TTS_SCRIPT" "$TRANSCRIPT_PATH" >> "$LOG_FILE" 2>&1
} &

# 即座に終了（バックグラウンド実行）
exit 0
