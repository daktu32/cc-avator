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
from typing import Optional, Dict, Any
import requests


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
                message = json.loads(line)

                # assistant ロールのメッセージを探す
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

    # 設定を読み込む
    config_path = project_root / "config" / "voicevox.json"
    if not config_path.exists():
        print(f"設定ファイルが見つかりません: {config_path}", file=sys.stderr)
        sys.exit(1)

    config = load_config(config_path)

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

    # transcript パスを取得
    if transcript_path is None:
        # コマンドライン引数から取得
        parser = argparse.ArgumentParser(description="VOICEVOX TTS")
        parser.add_argument("transcript_path", help="Transcript file path")
        args = parser.parse_args()
        transcript_path = args.transcript_path

    # 最新の assistant メッセージを抽出
    message = extract_latest_assistant_message(transcript_path)
    if not message:
        print("読み上げるメッセージが見つかりません", file=sys.stderr)
        sys.exit(1)

    print(f"読み上げ: {message[:100]}...")

    # 音声クエリを作成
    audio_query = create_audio_query(
        voicevox_url,
        message,
        config["speaker_id"],
        config.get("timeout", 30)
    )

    if not audio_query:
        sys.exit(1)

    # 速度、音高、音量を調整
    audio_query["speedScale"] = config.get("speed_scale", 1.0)
    audio_query["pitchScale"] = config.get("pitch_scale", 0.0)
    audio_query["volumeScale"] = config.get("volume_scale", 1.0)

    # 出力ディレクトリを作成
    output_dir = Path(config.get("audio_output_dir", "/tmp/voicevox_audio"))
    output_dir.mkdir(parents=True, exist_ok=True)

    # 音声を合成
    output_path = output_dir / "latest.wav"
    if not synthesize_speech(
        voicevox_url,
        audio_query,
        config["speaker_id"],
        str(output_path),
        config.get("timeout", 30)
    ):
        sys.exit(1)

    # 音声を再生
    if not play_audio(str(output_path)):
        sys.exit(1)

    print("音声読み上げが完了しました")


if __name__ == "__main__":
    main()
