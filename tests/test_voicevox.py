#!/usr/bin/env python3
"""
VOICEVOX TTS テストスクリプト
TDD に基づき、期待される入出力を定義
"""

import sys
import os
import json
import tempfile
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "scripts"))

# voicevox_tts モジュールをインポート（まだ存在しないが、テストファースト）
try:
    from voicevox_tts import (
        load_config,
        check_voicevox_connection,
        extract_latest_assistant_message,
        create_audio_query,
        synthesize_speech,
        play_audio
    )
except ImportError as e:
    print(f"警告: voicevox_tts モジュールのインポートに失敗しました: {e}")
    print("これは正常です（TDDファースト）。実装後に再度テストを実行してください。")
    sys.exit(1)


def test_load_config():
    """設定ファイルの読み込みテスト"""
    config_path = project_root / "config" / "voicevox.json"
    config = load_config(config_path)

    # 期待される設定項目が存在することを確認
    assert "enabled" in config
    assert "voicevox_url" in config
    assert "speaker_id" in config
    assert config["enabled"] is True
    assert config["voicevox_url"] == "http://127.0.0.1:50021"
    print("✓ test_load_config passed")


def test_check_voicevox_connection():
    """VOICEVOX Engine への接続テスト"""
    config_path = project_root / "config" / "voicevox.json"
    config = load_config(config_path)

    # 接続チェック（VOICEVOX が起動している必要がある）
    is_connected = check_voicevox_connection(config["voicevox_url"])

    if not is_connected:
        print("警告: VOICEVOX Engine が起動していません")
        print("docker-compose up -d で起動してください")
        return False

    print("✓ test_check_voicevox_connection passed")
    return True


def test_extract_latest_assistant_message():
    """transcript から最新 assistant メッセージを抽出するテスト"""
    # テスト用の transcript JSONL を作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        # ユーザーメッセージ
        f.write(json.dumps({
            "role": "user",
            "content": [{"type": "text", "text": "こんにちは"}]
        }) + "\n")

        # アシスタントメッセージ1
        f.write(json.dumps({
            "role": "assistant",
            "content": [{"type": "text", "text": "こんにちは！お元気ですか？"}]
        }) + "\n")

        # ユーザーメッセージ2
        f.write(json.dumps({
            "role": "user",
            "content": [{"type": "text", "text": "元気です"}]
        }) + "\n")

        # アシスタントメッセージ2（最新）
        f.write(json.dumps({
            "role": "assistant",
            "content": [{"type": "text", "text": "それは良かったです。何かお手伝いできることはありますか？"}]
        }) + "\n")

        temp_path = f.name

    try:
        # 最新のアシスタントメッセージを抽出
        latest_message = extract_latest_assistant_message(temp_path)

        # 期待されるメッセージと一致することを確認
        expected = "それは良かったです。何かお手伝いできることはありますか？"
        assert latest_message == expected, f"Expected: {expected}, Got: {latest_message}"
        print("✓ test_extract_latest_assistant_message passed")
    finally:
        os.unlink(temp_path)


def test_create_audio_query():
    """音声クエリの作成テスト"""
    config_path = project_root / "config" / "voicevox.json"
    config = load_config(config_path)

    # 接続チェック
    if not check_voicevox_connection(config["voicevox_url"]):
        print("スキップ: VOICEVOX Engine が起動していません")
        return

    # 音声クエリを作成
    text = "これはテストです"
    query = create_audio_query(config["voicevox_url"], text, config["speaker_id"])

    # クエリが正しく作成されたことを確認
    assert query is not None
    assert isinstance(query, dict)
    print("✓ test_create_audio_query passed")


def test_synthesize_speech():
    """音声合成のテスト"""
    config_path = project_root / "config" / "voicevox.json"
    config = load_config(config_path)

    # 接続チェック
    if not check_voicevox_connection(config["voicevox_url"]):
        print("スキップ: VOICEVOX Engine が起動していません")
        return

    # 音声クエリを作成
    text = "これは音声合成のテストです"
    query = create_audio_query(config["voicevox_url"], text, config["speaker_id"])

    # 音声を合成
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        output_path = f.name

    try:
        success = synthesize_speech(
            config["voicevox_url"],
            query,
            config["speaker_id"],
            output_path
        )

        # 音声ファイルが作成されたことを確認
        assert success is True
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0
        print("✓ test_synthesize_speech passed")
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_play_audio():
    """音声再生のテスト（実際には再生しない）"""
    # テスト用の空のWAVファイルを作成
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        # 簡易的なWAVヘッダーを書き込む
        # RIFF header
        f.write(b'RIFF')
        f.write((36).to_bytes(4, 'little'))  # file size - 8
        f.write(b'WAVE')
        # fmt chunk
        f.write(b'fmt ')
        f.write((16).to_bytes(4, 'little'))  # chunk size
        f.write((1).to_bytes(2, 'little'))   # audio format (PCM)
        f.write((1).to_bytes(2, 'little'))   # channels
        f.write((24000).to_bytes(4, 'little'))  # sample rate
        f.write((48000).to_bytes(4, 'little'))  # byte rate
        f.write((2).to_bytes(2, 'little'))   # block align
        f.write((16).to_bytes(2, 'little'))  # bits per sample
        # data chunk
        f.write(b'data')
        f.write((0).to_bytes(4, 'little'))   # data size

        temp_path = f.name

    try:
        # play_audio 関数をテスト（実際には再生しない、dry_run モード）
        success = play_audio(temp_path, dry_run=True)
        assert success is True
        print("✓ test_play_audio passed")
    finally:
        os.unlink(temp_path)


def run_all_tests():
    """すべてのテストを実行"""
    print("=" * 60)
    print("VOICEVOX TTS テスト実行")
    print("=" * 60)

    tests = [
        ("設定ファイル読み込み", test_load_config),
        ("VOICEVOX 接続チェック", test_check_voicevox_connection),
        ("最新メッセージ抽出", test_extract_latest_assistant_message),
        ("音声クエリ作成", test_create_audio_query),
        ("音声合成", test_synthesize_speech),
        ("音声再生", test_play_audio),
    ]

    passed = 0
    failed = 0
    skipped = 0

    for name, test_func in tests:
        print(f"\n[テスト] {name}")
        try:
            result = test_func()
            if result is False:
                skipped += 1
            else:
                passed += 1
        except Exception as e:
            print(f"✗ {name} failed: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"結果: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
