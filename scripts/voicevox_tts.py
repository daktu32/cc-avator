#!/usr/bin/env python3
"""
VOICEVOX TTS メイン音声読み上げスクリプト
ClaudeCode の Stop フックから呼び出されます
"""

import sys
import os
import json
import subprocess
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, List
import requests

# セッション設定管理モジュールをインポート
from voicevox_config import load_session_config


def load_config(config_path: Path) -> Dict[str, Any]:
    """
    設定ファイルを読み込む

    Args:
        config_path: 設定ファイルのパス

    Returns:
        設定辞書
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_voicevox_connection(voicevox_url: str, timeout: int = 5) -> bool:
    """
    VOICEVOX Engine への接続をチェック

    Args:
        voicevox_url: VOICEVOX Engine の URL
        timeout: タイムアウト秒数

    Returns:
        接続可能な場合 True
    """
    try:
        response = requests.get(f"{voicevox_url}/version", timeout=timeout)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


class TranscriptStreamReader:
    """
    transcriptファイルをストリーミング読み取り
    tail -f のような動作を実現
    """

    def __init__(self, file_path: str):
        """
        初期化

        Args:
            file_path: 監視対象のtranscriptファイルパス
        """
        self.file_path = file_path
        self.file_handle = None
        self.current_position = 0

    def open(self):
        """
        ファイルを開いて現在位置を末尾にセット
        既存の内容をスキップして、これから追加される行のみを読み取る
        """
        self.file_handle = open(self.file_path, 'r', encoding='utf-8')
        # 既存の内容をスキップして末尾に移動
        self.file_handle.seek(0, 2)  # SEEK_END (0: offset, 2: whence=end)
        self.current_position = self.file_handle.tell()

    def read_new_lines(self) -> List[str]:
        """
        新しく追加された行のみを読み取る

        Returns:
            新しい行のリスト（空白行は除外）
        """
        if not self.file_handle:
            return []

        new_lines = []
        while True:
            line = self.file_handle.readline()
            if not line:
                # EOF到達
                break

            # 空白行を除外
            stripped = line.strip()
            if stripped:
                new_lines.append(stripped)

        # 現在位置を更新
        self.current_position = self.file_handle.tell()
        return new_lines

    def close(self):
        """ファイルハンドルを閉じる"""
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None

    def __enter__(self):
        """with文のサポート"""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """with文のサポート"""
        self.close()
        return False


def clean_text_for_speech(text: str) -> str:
    """
    音声読み上げ用にテキストをクリーンアップ

    Args:
        text: 元のテキスト

    Returns:
        クリーンアップされたテキスト
    """
    import re

    # Markdown記号を除去
    text = re.sub(r'[*_~`#]', '', text)  # *, _, ~, `, # を削除
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # リンク [text](url) → text
    text = re.sub(r'```[a-z]*\n[\s\S]*?```', '', text)  # コードブロック除去
    text = re.sub(r'`[^`]+`', '', text)  # インラインコード除去

    # 絵文字を除去（一部）
    text = re.sub(r'[✅❌🎉📊⚡🔧]', '', text)

    # 連続する空白を1つに
    text = re.sub(r'\s+', ' ', text)

    # 前後の空白を削除
    text = text.strip()

    return text


def extract_latest_assistant_message(transcript_path: str) -> Optional[str]:
    """
    transcript JSONL ファイルから最新の assistant メッセージを抽出

    Args:
        transcript_path: transcript ファイルのパス

    Returns:
        最新の assistant メッセージテキスト、見つからない場合は None
    """
    if not os.path.exists(transcript_path):
        return None

    latest_assistant_message = None

    with open(transcript_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)

                # assistant ロールのメッセージを探す
                # ClaudeCodeのtranscript形式: {"message": {"role": "assistant", "content": [...]}}
                message = entry.get("message", {})
                if message.get("role") == "assistant":
                    content = message.get("content", [])

                    # content から text を抽出
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text_parts.append(item.get("text", ""))

                    if text_parts:
                        latest_assistant_message = " ".join(text_parts)

            except json.JSONDecodeError:
                continue

    return latest_assistant_message


def extract_new_assistant_messages(
    transcript_path: str,
    last_timestamp: Optional[str] = None
) -> list:
    """
    transcript JSONL ファイルから新しい assistant メッセージを抽出

    Args:
        transcript_path: transcript ファイルのパス
        last_timestamp: 前回読み上げた最後のタイムスタンプ（ISO 8601形式）
                       None の場合は全てのメッセージを抽出

    Returns:
        新しい assistant メッセージのリスト
        各要素は {"timestamp": "...", "text": "..."} の辞書
    """
    if not os.path.exists(transcript_path):
        return []

    new_messages = []

    with open(transcript_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)

                # assistant ロールのメッセージを探す
                # ClaudeCodeのtranscript形式: {"message": {"role": "assistant", "content": [...]}, "timestamp": "..."}
                message = entry.get("message", {})
                timestamp = entry.get("timestamp")

                if message.get("role") == "assistant" and timestamp:
                    # last_timestamp より新しいメッセージのみを抽出
                    if last_timestamp is None or timestamp > last_timestamp:
                        content = message.get("content", [])

                        # content から text を抽出
                        text_parts = []
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text_parts.append(item.get("text", ""))

                        if text_parts:
                            raw_text = " ".join(text_parts)
                            # 音声読み上げ用にテキストをクリーンアップ
                            clean_text = clean_text_for_speech(raw_text)
                            if clean_text:  # クリーンアップ後も文字が残っている場合のみ追加
                                new_messages.append({
                                    "timestamp": timestamp,
                                    "text": clean_text
                                })

            except json.JSONDecodeError:
                continue

    return new_messages


def create_audio_query(
    voicevox_url: str,
    text: str,
    speaker_id: int,
    timeout: int = 30
) -> Optional[Dict[str, Any]]:
    """
    音声クエリを作成

    Args:
        voicevox_url: VOICEVOX Engine の URL
        text: 読み上げテキスト
        speaker_id: 話者ID
        timeout: タイムアウト秒数

    Returns:
        音声クエリ辞書、失敗時は None
    """
    try:
        response = requests.post(
            f"{voicevox_url}/audio_query",
            params={"text": text, "speaker": speaker_id},
            timeout=timeout
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"音声クエリの作成に失敗: {e}", file=sys.stderr)
        return None


def synthesize_speech(
    voicevox_url: str,
    audio_query: Dict[str, Any],
    speaker_id: int,
    output_path: str,
    timeout: int = 30
) -> bool:
    """
    音声を合成してファイルに保存

    Args:
        voicevox_url: VOICEVOX Engine の URL
        audio_query: 音声クエリ
        speaker_id: 話者ID
        output_path: 出力WAVファイルパス
        timeout: タイムアウト秒数

    Returns:
        成功時 True
    """
    try:
        response = requests.post(
            f"{voicevox_url}/synthesis",
            params={"speaker": speaker_id},
            json=audio_query,
            timeout=timeout
        )
        response.raise_for_status()

        # WAVファイルとして保存
        with open(output_path, 'wb') as f:
            f.write(response.content)

        return True
    except requests.exceptions.RequestException as e:
        print(f"音声合成に失敗: {e}", file=sys.stderr)
        return False


def play_audio(audio_path: str, dry_run: bool = False) -> bool:
    """
    音声ファイルを再生（macOS の afplay を使用）

    Args:
        audio_path: 音声ファイルパス
        dry_run: True の場合、実際には再生しない

    Returns:
        成功時 True
    """
    if dry_run:
        print(f"[DRY RUN] 音声再生をスキップ: {audio_path}")
        return True

    try:
        # macOS の afplay コマンドで再生
        subprocess.run(
            ["afplay", audio_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"音声再生に失敗: {e}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("afplay コマンドが見つかりません（macOS 以外の環境では使用できません）", file=sys.stderr)
        return False


def main(transcript_path: Optional[str] = None):
    """
    メイン処理

    Args:
        transcript_path: transcript ファイルのパス（オプション）
    """
    # プロジェクトルートを取得
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # transcript パスを取得
    if transcript_path is None:
        # コマンドライン引数から取得
        parser = argparse.ArgumentParser(description="VOICEVOX TTS")
        parser.add_argument("transcript_path", help="Transcript file path")
        args = parser.parse_args()
        transcript_path = args.transcript_path

    # セッションIDを transcript_path から抽出
    # 例: /Users/.../.claude/projects/-Users-...-work-cc-avator/7f4b7a0a-4288-49e5-b3bc-d00136b5c324.jsonl
    # → 7f4b7a0a-4288-49e5-b3bc-d00136b5c324
    session_id = Path(transcript_path).stem

    # セッション設定を読み込む（グローバル設定とマージ）
    config = load_session_config(session_id, project_root)

    # 読み上げが無効の場合は終了
    if not config.get("enabled", False):
        print("VOICEVOX 音声読み上げは無効です")
        sys.exit(0)

    # VOICEVOX Engine への接続をチェック
    voicevox_url = config["voicevox_url"]
    if not check_voicevox_connection(voicevox_url):
        print(f"VOICEVOX Engine に接続できません: {voicevox_url}", file=sys.stderr)
        print("docker-compose up -d で起動してください", file=sys.stderr)
        sys.exit(1)

    # 前回読み上げ位置ファイルのパス
    last_read_file = Path(f"/tmp/voicevox_last_read_{session_id}.txt")

    # 前回のタイムスタンプを読み込む
    last_timestamp = None
    if last_read_file.exists():
        try:
            with open(last_read_file, 'r') as f:
                last_timestamp = f.read().strip()
                print(f"前回読み上げ位置: {last_timestamp}")
        except Exception as e:
            print(f"前回読み上げ位置の読み込みに失敗: {e}", file=sys.stderr)

    # 新しい assistant メッセージを抽出
    new_messages = extract_new_assistant_messages(transcript_path, last_timestamp)
    if not new_messages:
        print("読み上げる新しいメッセージがありません")
        sys.exit(0)

    print(f"新しいメッセージ: {len(new_messages)}件")

    # 出力ディレクトリを作成
    output_dir = Path(config.get("audio_output_dir", "/tmp/voicevox_audio"))
    output_dir.mkdir(parents=True, exist_ok=True)

    # 各メッセージを順番に読み上げる
    for i, msg in enumerate(new_messages):
        message_text = msg["text"]
        timestamp = msg["timestamp"]

        print(f"[{i+1}/{len(new_messages)}] 読み上げ: {message_text[:100]}...")

        # 音声クエリを作成
        audio_query = create_audio_query(
            voicevox_url,
            message_text,
            config["speaker_id"],
            config.get("timeout", 30)
        )

        if not audio_query:
            print(f"メッセージ {i+1} の音声クエリ作成に失敗", file=sys.stderr)
            continue

        # 速度、音高、音量を調整
        audio_query["speedScale"] = config.get("speed_scale", 1.0)
        audio_query["pitchScale"] = config.get("pitch_scale", 0.0)
        audio_query["volumeScale"] = config.get("volume_scale", 1.0)

        # 音声を合成
        output_path = output_dir / f"message_{i}.wav"
        if not synthesize_speech(
            voicevox_url,
            audio_query,
            config["speaker_id"],
            str(output_path),
            config.get("timeout", 30)
        ):
            print(f"メッセージ {i+1} の音声合成に失敗", file=sys.stderr)
            continue

        # 音声を再生
        if not play_audio(str(output_path)):
            print(f"メッセージ {i+1} の音声再生に失敗", file=sys.stderr)
            continue

    # 最後のメッセージのタイムスタンプを保存
    if new_messages:
        last_message_timestamp = new_messages[-1]["timestamp"]
        try:
            with open(last_read_file, 'w') as f:
                f.write(last_message_timestamp)
            print(f"読み上げ位置を保存: {last_message_timestamp}")
        except Exception as e:
            print(f"読み上げ位置の保存に失敗: {e}", file=sys.stderr)

    print(f"音声読み上げが完了しました（{len(new_messages)}件）")


if __name__ == "__main__":
    main()
