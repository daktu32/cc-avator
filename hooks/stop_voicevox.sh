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

# デバッグ用に入力全体をログに記録
{
    echo "=== VOICEVOX TTS Hook ==="
    echo "Timestamp: $(date)"
    echo "Input (first 500 chars): ${INPUT:0:500}"
} >> "$LOG_FILE" 2>&1

# transcript_path を抽出 (jq を使用、なければ grep で fallback)
if command -v jq &> /dev/null; then
    TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)
else
    TRANSCRIPT_PATH=$(echo "$INPUT" | grep -o '"transcript_path":"[^"]*"' | cut -d'"' -f4)
fi

# デバッグ: 抽出結果をログに記録
{
    echo "Extracted transcript_path: $TRANSCRIPT_PATH"
} >> "$LOG_FILE" 2>&1

# transcript_path が取得できない場合はエラー
if [ -z "$TRANSCRIPT_PATH" ]; then
    echo "Error: transcript_path not found in input" >> "$LOG_FILE" 2>&1
    exit 0  # ClaudeCode を妨げないため exit 0
fi

# セッションIDを抽出
# 例: /Users/.../.claude/projects/.../7f4b7a0a-4288-49e5-b3bc-d00136b5c324.jsonl
# → 7f4b7a0a-4288-49e5-b3bc-d00136b5c324
SESSION_ID=$(basename "$TRANSCRIPT_PATH" .jsonl)

{
    echo "Session ID: $SESSION_ID"
} >> "$LOG_FILE" 2>&1

# セッション設定をチェック（enabled=false ならスキップ）
SESSION_CONFIG="${PROJECT_ROOT}/.claude/voicevox_sessions/${SESSION_ID}.json"
GLOBAL_CONFIG="${PROJECT_ROOT}/config/voicevox.json"

# セッション設定が存在する場合はそちらを優先
if [ -f "$SESSION_CONFIG" ] && command -v jq &> /dev/null; then
    ENABLED=$(jq -r '.enabled // "null"' "$SESSION_CONFIG" 2>/dev/null)
    if [ "$ENABLED" = "false" ]; then
        {
            echo "VOICEVOX is disabled for this session (session config)"
        } >> "$LOG_FILE" 2>&1
        echo "$INPUT"
        exit 0
    fi
fi

# セッション設定がない場合はグローバル設定をチェック
if [ ! -f "$SESSION_CONFIG" ] && [ -f "$GLOBAL_CONFIG" ] && command -v jq &> /dev/null; then
    ENABLED=$(jq -r '.enabled // true' "$GLOBAL_CONFIG" 2>/dev/null)
    if [ "$ENABLED" = "false" ]; then
        {
            echo "VOICEVOX is disabled (global config)"
        } >> "$LOG_FILE" 2>&1
        echo "$INPUT"
        exit 0
    fi
fi

# Python スクリプトをバックグラウンドで実行
# エラーが発生しても ClaudeCode の動作を妨げない
{
    "$VENV_PYTHON" "$TTS_SCRIPT" "$TRANSCRIPT_PATH" >> "$LOG_FILE" 2>&1
} &

# 入力を次のフックに渡す（フックチェーンを継続）
echo "$INPUT"

# 正常終了
exit 0
