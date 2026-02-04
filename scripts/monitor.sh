#!/bin/bash
#
# VOICEVOX TTS リアルタイムモニター 起動/停止スクリプト
#

set -e

# プロジェクトルート
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Python 仮想環境のパス
VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python3"

# モニタースクリプトのパス
MONITOR_SCRIPT="${PROJECT_ROOT}/scripts/voicevox_monitor.py"

# ログファイル
LOG_FILE="${PROJECT_ROOT}/voicevox_monitor.log"

# 監視対象ディレクトリ（現在のプロジェクトのClaudeCodeディレクトリのみ）
# /Users/aiq/work/cc-avator → -Users-aiq-work-cc-avator
PROJECT_ABS_PATH="$(cd "$PROJECT_ROOT" && pwd)"
# 先頭の / を削除してから / を - に置換し、先頭に - を追加
PROJECT_NAME="-${PROJECT_ABS_PATH:1}"
PROJECT_NAME="${PROJECT_NAME//\//-}"
WATCH_DIR="${HOME}/.claude/projects/${PROJECT_NAME}"

# プロジェクトハッシュ（PIDファイルやタイムスタンプファイルの識別用）
PROJECT_HASH=$(echo -n "$WATCH_DIR" | md5 | cut -c1-8)

# 読み上げ開始タイムスタンプファイル
ENABLE_TIMESTAMP_FILE="/tmp/voicevox_enable_${PROJECT_HASH}.timestamp"

# 使用方法を表示
usage() {
    echo "使用方法: $0 {start|stop|restart|status|enable|disable}"
    echo ""
    echo "  start   - モニターをバックグラウンドで起動"
    echo "  stop    - モニターを停止"
    echo "  restart - モニターを再起動"
    echo "  status  - モニターの状態を確認"
    echo "  enable  - 読み上げを開始（この時点以降のメッセージを読み上げ）"
    echo "  disable - 読み上げを停止"
    exit 1
}

# 引数チェック
if [ $# -ne 1 ]; then
    usage
fi

ACTION=$1

case "$ACTION" in
    start)
        echo "VOICEVOX TTS モニターを起動します..."
        echo "監視対象: $WATCH_DIR"
        echo "ログファイル: $LOG_FILE"

        # バックグラウンドでモニターを起動
        nohup "$VENV_PYTHON" "$MONITOR_SCRIPT" start --watch-dir "$WATCH_DIR" >> "$LOG_FILE" 2>&1 &

        # 起動確認（少し待つ）
        sleep 2

        # ステータスをチェック
        "$VENV_PYTHON" "$MONITOR_SCRIPT" status --watch-dir "$WATCH_DIR"

        echo ""
        echo "モニターが起動しました！"
        echo "ログを確認: tail -f $LOG_FILE"
        ;;

    stop)
        echo "VOICEVOX TTS モニターを停止します..."
        "$VENV_PYTHON" "$MONITOR_SCRIPT" stop --watch-dir "$WATCH_DIR"
        ;;

    restart)
        echo "VOICEVOX TTS モニターを再起動します..."
        "$0" stop
        sleep 1
        "$0" start
        ;;

    status)
        "$VENV_PYTHON" "$MONITOR_SCRIPT" status --watch-dir "$WATCH_DIR"
        ;;

    enable)
        echo "VOICEVOX TTS 読み上げを開始します..."

        # 現在のタイムスタンプ（ISO 8601形式）を取得して保存
        CURRENT_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")
        echo "$CURRENT_TIMESTAMP" > "$ENABLE_TIMESTAMP_FILE"
        echo "読み上げ開始時刻: $CURRENT_TIMESTAMP"

        # モニターが起動していない場合は起動
        if ! "$VENV_PYTHON" "$MONITOR_SCRIPT" status --watch-dir "$WATCH_DIR" > /dev/null 2>&1; then
            echo "モニターを起動します..."
            nohup "$VENV_PYTHON" "$MONITOR_SCRIPT" start --watch-dir "$WATCH_DIR" >> "$LOG_FILE" 2>&1 &
            sleep 2
        else
            echo "モニターは既に起動しています"
        fi

        echo "この時点以降のメッセージを読み上げます"
        ;;

    disable)
        echo "VOICEVOX TTS 読み上げを停止します..."

        # タイムスタンプファイルを削除
        if [ -f "$ENABLE_TIMESTAMP_FILE" ]; then
            rm -f "$ENABLE_TIMESTAMP_FILE"
            echo "読み上げを無効化しました"
        fi

        # モニターを停止
        "$VENV_PYTHON" "$MONITOR_SCRIPT" stop --watch-dir "$WATCH_DIR"
        ;;

    *)
        usage
        ;;
esac

exit 0
