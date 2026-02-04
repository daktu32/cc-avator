#!/usr/bin/env python3
"""
VOICEVOX セッション設定管理モジュール
セッションごとに VOICEVOX の設定を管理する
"""

import json
from pathlib import Path
from typing import Dict, Any


def get_session_config_path(session_id: str, project_root: Path) -> Path:
    """
    セッション設定ファイルのパスを取得

    Args:
        session_id: セッションID
        project_root: プロジェクトルートディレクトリ

    Returns:
        セッション設定ファイルのパス
    """
    return project_root / ".claude" / "voicevox_sessions" / f"{session_id}.json"


def load_global_config(project_root: Path) -> Dict[str, Any]:
    """
    グローバル設定を読み込む

    Args:
        project_root: プロジェクトルートディレクトリ

    Returns:
        グローバル設定の辞書
    """
    global_config_path = project_root / "config" / "voicevox.json"

    if not global_config_path.exists():
        # デフォルト設定を返す
        return {
            "enabled": True,
            "voicevox_url": "http://127.0.0.1:50021",
            "speaker_id": 3,
            "speed_scale": 1.0,
            "pitch_scale": 0.0,
            "volume_scale": 1.0,
            "timeout": 60,
            "audio_output_dir": "/tmp/voicevox_audio"
        }

    with open(global_config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_session_config(session_id: str, project_root: Path) -> Dict[str, Any]:
    """
    セッション設定を読み込む（グローバル設定とマージ）

    優先順位:
    1. セッション設定（.claude/voicevox_sessions/{session_id}.json）
    2. グローバル設定（config/voicevox.json）
    3. デフォルト値

    Args:
        session_id: セッションID
        project_root: プロジェクトルートディレクトリ

    Returns:
        マージされた設定の辞書
    """
    # グローバル設定をベースに読み込む
    config = load_global_config(project_root)

    # セッション設定を読み込む
    session_config_path = get_session_config_path(session_id, project_root)

    if session_config_path.exists():
        with open(session_config_path, 'r', encoding='utf-8') as f:
            session_config = json.load(f)
            # セッション設定でグローバル設定を上書き
            config.update(session_config)

    return config


def save_session_config(session_id: str, config: Dict[str, Any], project_root: Path) -> None:
    """
    セッション設定を保存

    Args:
        session_id: セッションID
        config: 保存する設定の辞書
        project_root: プロジェクトルートディレクトリ
    """
    session_config_path = get_session_config_path(session_id, project_root)

    # ディレクトリが存在しない場合は作成
    session_config_path.parent.mkdir(parents=True, exist_ok=True)

    # 設定を保存
    with open(session_config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def delete_session_config(session_id: str, project_root: Path) -> None:
    """
    セッション設定を削除

    Args:
        session_id: セッションID
        project_root: プロジェクトルートディレクトリ
    """
    session_config_path = get_session_config_path(session_id, project_root)

    if session_config_path.exists():
        session_config_path.unlink()
