#!/usr/bin/env python3
"""
VOICEVOX スキルハンドラー
/voicevox コマンドの実装
"""

import sys
import os
from pathlib import Path
from typing import Optional

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "scripts"))

from voicevox_config import (
    load_session_config,
    save_session_config,
    delete_session_config
)


def get_current_session_id() -> Optional[str]:
    """
    現在のセッションIDを取得

    環境変数 CLAUDE_SESSION_ID から取得
    設定されていない場合は None を返す

    Returns:
        セッションID、または None
    """
    return os.environ.get("CLAUDE_SESSION_ID")


def execute_on(session_id: str, project_root: Path) -> str:
    """
    VOICEVOX 読み上げを有効化

    Args:
        session_id: セッションID
        project_root: プロジェクトルート

    Returns:
        実行結果メッセージ
    """
    # 現在の設定を読み込む
    config = load_session_config(session_id, project_root)

    # enabled を True に設定
    config["enabled"] = True

    # セッション設定を保存
    save_session_config(session_id, config, project_root)

    return f"✅ VOICEVOX読み上げを有効化しました (session: {session_id})"


def execute_off(session_id: str, project_root: Path) -> str:
    """
    VOICEVOX 読み上げを無効化

    Args:
        session_id: セッションID
        project_root: プロジェクトルート

    Returns:
        実行結果メッセージ
    """
    # 現在の設定を読み込む
    config = load_session_config(session_id, project_root)

    # enabled を False に設定
    config["enabled"] = False

    # セッション設定を保存
    save_session_config(session_id, config, project_root)

    return f"⛔ VOICEVOX読み上げを無効化しました (session: {session_id})"


def execute_speaker(session_id: str, speaker_id: int, project_root: Path) -> str:
    """
    VOICEVOX 話者を変更

    Args:
        session_id: セッションID
        speaker_id: 話者ID
        project_root: プロジェクトルート

    Returns:
        実行結果メッセージ
    """
    # 現在の設定を読み込む
    config = load_session_config(session_id, project_root)

    # speaker_id を設定
    config["speaker_id"] = speaker_id

    # セッション設定を保存
    save_session_config(session_id, config, project_root)

    return f"🎤 VOICEVOX話者をID {speaker_id} に変更しました (session: {session_id})"


def execute_speed(session_id: str, speed_scale: float, project_root: Path) -> str:
    """
    VOICEVOX 読み上げ速度を変更

    Args:
        session_id: セッションID
        speed_scale: 速度倍率
        project_root: プロジェクトルート

    Returns:
        実行結果メッセージ
    """
    # 現在の設定を読み込む
    config = load_session_config(session_id, project_root)

    # speed_scale を設定
    config["speed_scale"] = speed_scale

    # セッション設定を保存
    save_session_config(session_id, config, project_root)

    return f"⚡ VOICEVOX読み上げ速度を {speed_scale}x に変更しました (session: {session_id})"


def execute_status(session_id: str, project_root: Path) -> str:
    """
    現在の VOICEVOX 設定を表示

    Args:
        session_id: セッションID
        project_root: プロジェクトルート

    Returns:
        設定情報の文字列
    """
    # 現在の設定を読み込む
    config = load_session_config(session_id, project_root)

    # 設定情報を整形
    status_lines = [
        "📊 VOICEVOX 設定状態",
        f"  Session ID: {session_id}",
        f"  有効/無効: {'✅ 有効' if config.get('enabled', False) else '⛔ 無効'}",
        f"  話者ID: {config.get('speaker_id', 'N/A')}",
        f"  速度倍率: {config.get('speed_scale', 'N/A')}x",
        f"  音程: {config.get('pitch_scale', 'N/A')}",
        f"  音量: {config.get('volume_scale', 'N/A')}",
        f"  VOICEVOX URL: {config.get('voicevox_url', 'N/A')}",
    ]

    return "\n".join(status_lines)


def main():
    """
    メイン処理
    コマンドライン引数を解析してスキルを実行
    """
    if len(sys.argv) < 2:
        print("使い方: voicevox_skill.py <command> [args...]", file=sys.stderr)
        print("", file=sys.stderr)
        print("コマンド:", file=sys.stderr)
        print("  on              読み上げを有効化", file=sys.stderr)
        print("  off             読み上げを無効化", file=sys.stderr)
        print("  speaker <id>    話者を変更", file=sys.stderr)
        print("  speed <rate>    速度を変更", file=sys.stderr)
        print("  status          現在の設定を表示", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1].lower()

    # セッションIDを取得
    session_id = get_current_session_id()
    if not session_id:
        # 環境変数が設定されていない場合、transcriptパスから取得を試みる
        # （テスト時など）
        if len(sys.argv) > 2 and command in ["on", "off", "status"]:
            # 引数として session_id が渡されている可能性
            pass
        else:
            print("エラー: セッションIDが取得できません", file=sys.stderr)
            print("環境変数 CLAUDE_SESSION_ID を設定してください", file=sys.stderr)
            sys.exit(1)

    try:
        if command == "on":
            result = execute_on(session_id, project_root)
            print(result)

        elif command == "off":
            result = execute_off(session_id, project_root)
            print(result)

        elif command == "speaker":
            if len(sys.argv) < 3:
                print("エラー: speaker コマンドには話者IDが必要です", file=sys.stderr)
                print("使い方: voicevox_skill.py speaker <id>", file=sys.stderr)
                sys.exit(1)

            speaker_id = int(sys.argv[2])
            result = execute_speaker(session_id, speaker_id, project_root)
            print(result)

        elif command == "speed":
            if len(sys.argv) < 3:
                print("エラー: speed コマンドには速度倍率が必要です", file=sys.stderr)
                print("使い方: voicevox_skill.py speed <rate>", file=sys.stderr)
                sys.exit(1)

            speed_scale = float(sys.argv[2])
            result = execute_speed(session_id, speed_scale, project_root)
            print(result)

        elif command == "status":
            result = execute_status(session_id, project_root)
            print(result)

        else:
            print(f"エラー: 不明なコマンド '{command}'", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
