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
        extract_new_assistant_messages,
        create_audio_query,
        synthesize_speech,
        play_audio
    )
except ImportError as e:
    print(f"警告: voicevox_tts モジュールのインポートに失敗しました: {e}")
    print("これは正常です（TDDファースト）。実装後に再度テストを実行してください。")
    sys.exit(1)

# voicevox_monitor モジュールをインポート
try:
    from voicevox_monitor import TranscriptMonitor
except ImportError as e:
    print(f"警告: voicevox_monitor モジュールのインポートに失敗しました: {e}")
    print("これは正常です（TDDファースト）。実装後に再度テストを実行してください。")
    # モニターのテストはスキップするが、既存テストは実行する
    TranscriptMonitor = None

# voicevox_config モジュールをインポート（Phase 1: セッション管理）
try:
    from voicevox_config import (
        get_session_config_path,
        load_session_config,
        save_session_config,
        delete_session_config
    )
except ImportError as e:
    print(f"警告: voicevox_config モジュールのインポートに失敗しました: {e}")
    print("これは正常です（TDDファースト）。実装後に再度テストを実行してください。")
    get_session_config_path = None
    load_session_config = None
    save_session_config = None
    delete_session_config = None


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
    # ClaudeCode の実際の transcript 形式でテスト用データを作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        # ユーザーメッセージ
        f.write(json.dumps({
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "こんにちは"}]
            },
            "timestamp": "2026-01-22T05:00:00.000Z",
            "uuid": "uuid-1"
        }) + "\n")

        # アシスタントメッセージ1
        f.write(json.dumps({
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "こんにちは！お元気ですか？"}]
            },
            "timestamp": "2026-01-22T05:01:00.000Z",
            "uuid": "uuid-2"
        }) + "\n")

        # ユーザーメッセージ2
        f.write(json.dumps({
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "元気です"}]
            },
            "timestamp": "2026-01-22T05:02:00.000Z",
            "uuid": "uuid-3"
        }) + "\n")

        # アシスタントメッセージ2（最新）
        f.write(json.dumps({
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "それは良かったです。何かお手伝いできることはありますか？"}]
            },
            "timestamp": "2026-01-22T05:03:00.000Z",
            "uuid": "uuid-4"
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


def test_extract_new_assistant_messages():
    """transcript から新しい assistant メッセージを抽出するテスト"""
    # ClaudeCode の実際の transcript 形式でテスト用データを作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        # アシスタントメッセージ1（古い）
        f.write(json.dumps({
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "最初のメッセージです。"}]
            },
            "timestamp": "2026-01-22T05:00:00.000Z",
            "uuid": "uuid-1"
        }) + "\n")

        # アシスタントメッセージ2（これより後を取得）
        f.write(json.dumps({
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "2番目のメッセージです。"}]
            },
            "timestamp": "2026-01-22T05:01:00.000Z",
            "uuid": "uuid-2"
        }) + "\n")

        # ユーザーメッセージ（スキップされる）
        f.write(json.dumps({
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "ユーザーの質問"}]
            },
            "timestamp": "2026-01-22T05:02:00.000Z",
            "uuid": "uuid-3"
        }) + "\n")

        # アシスタントメッセージ3（新しい1）
        f.write(json.dumps({
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "3番目のメッセージです。"}]
            },
            "timestamp": "2026-01-22T05:03:00.000Z",
            "uuid": "uuid-4"
        }) + "\n")

        # アシスタントメッセージ4（新しい2）
        f.write(json.dumps({
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "4番目のメッセージです。"}]
            },
            "timestamp": "2026-01-22T05:04:00.000Z",
            "uuid": "uuid-5"
        }) + "\n")

        temp_path = f.name

    try:
        # last_timestamp = "2026-01-22T05:01:00.000Z" より後のメッセージを抽出
        new_messages = extract_new_assistant_messages(
            temp_path,
            last_timestamp="2026-01-22T05:01:00.000Z"
        )

        # 期待される結果: メッセージ3と4が抽出される
        assert len(new_messages) == 2, f"Expected 2 messages, got {len(new_messages)}"
        assert new_messages[0]["text"] == "3番目のメッセージです。"
        assert new_messages[0]["timestamp"] == "2026-01-22T05:03:00.000Z"
        assert new_messages[1]["text"] == "4番目のメッセージです。"
        assert new_messages[1]["timestamp"] == "2026-01-22T05:04:00.000Z"

        # last_timestamp が None の場合: 全てのメッセージを抽出
        all_messages = extract_new_assistant_messages(temp_path, last_timestamp=None)
        assert len(all_messages) == 4, f"Expected 4 messages, got {len(all_messages)}"

        print("✓ test_extract_new_assistant_messages passed")
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


def test_monitor_initialization():
    """TranscriptMonitor の初期化テスト"""
    if TranscriptMonitor is None:
        print("スキップ: TranscriptMonitor がインポートできません")
        return False

    config_path = project_root / "config" / "voicevox.json"
    config = load_config(config_path)

    # モニターを初期化
    with tempfile.TemporaryDirectory() as watch_dir:
        monitor = TranscriptMonitor(
            watch_dir=watch_dir,
            config=config
        )

        # モニターが正しく初期化されたことを確認
        assert monitor.watch_dir == watch_dir
        assert monitor.config == config
        print("✓ test_monitor_initialization passed")

    return True


def test_monitor_pid_file():
    """モニターのPIDファイル管理テスト"""
    if TranscriptMonitor is None:
        print("スキップ: TranscriptMonitor がインポートできません")
        return False

    config_path = project_root / "config" / "voicevox.json"
    config = load_config(config_path)

    with tempfile.TemporaryDirectory() as watch_dir:
        monitor = TranscriptMonitor(
            watch_dir=watch_dir,
            config=config
        )

        # PIDファイルのパスを取得
        pid_file = monitor.get_pid_file()

        # PIDファイルのパスが期待通りであることを確認
        assert str(pid_file).startswith("/tmp/voicevox_monitor_")
        assert str(pid_file).endswith(".pid")

        # PIDファイルは初期状態では存在しないはず
        assert not pid_file.exists()

        print("✓ test_monitor_pid_file passed")

    return True


def test_transcript_stream_reader():
    """TranscriptStreamReader のテスト"""
    try:
        from voicevox_tts import TranscriptStreamReader
    except ImportError:
        print("スキップ: TranscriptStreamReader がインポートできません")
        return False

    # 一時ファイルを作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        # 初期データ
        f.write(json.dumps({
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "最初のメッセージ"}]
            },
            "timestamp": "2026-01-23T00:00:00.000Z"
        }) + "\n")
        temp_path = f.name

    try:
        # StreamReader を初期化
        reader = TranscriptStreamReader(temp_path)
        reader.open()

        # 最初は新しい行がないはず
        new_lines = reader.read_new_lines()
        assert len(new_lines) == 0, f"Expected 0 new lines, got {len(new_lines)}"

        # ファイルに新しい行を追加
        with open(temp_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "2番目のメッセージ"}]
                },
                "timestamp": "2026-01-23T00:01:00.000Z"
            }) + "\n")

        # 新しい行を読み取る
        new_lines = reader.read_new_lines()
        assert len(new_lines) == 1, f"Expected 1 new line, got {len(new_lines)}"

        # 内容を確認
        entry = json.loads(new_lines[0])
        assert entry["message"]["content"][0]["text"] == "2番目のメッセージ"

        # さらに複数行を追加
        with open(temp_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "3番目のメッセージ"}]
                },
                "timestamp": "2026-01-23T00:02:00.000Z"
            }) + "\n")
            f.write(json.dumps({
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "4番目のメッセージ"}]
                },
                "timestamp": "2026-01-23T00:03:00.000Z"
            }) + "\n")

        # 複数の新しい行を読み取る
        new_lines = reader.read_new_lines()
        assert len(new_lines) == 2, f"Expected 2 new lines, got {len(new_lines)}"

        reader.close()
        print("✓ test_transcript_stream_reader passed")
        return True

    finally:
        os.unlink(temp_path)


# ===================================================================
# Phase 1: セッション管理テスト
# ===================================================================

def test_get_session_config_path():
    """セッション設定ファイルのパス取得テスト"""
    if get_session_config_path is None:
        print("スキップ: voicevox_config モジュールがインポートできません")
        return False

    session_id = "test-session-123"
    config_path = get_session_config_path(session_id, project_root)

    # パスの形式を確認
    expected_path = project_root / ".claude" / "voicevox_sessions" / f"{session_id}.json"
    assert config_path == expected_path, f"Expected: {expected_path}, Got: {config_path}"

    print("✓ test_get_session_config_path passed")
    return True


def test_save_and_load_session_config():
    """セッション設定の保存と読み込みテスト"""
    if save_session_config is None or load_session_config is None:
        print("スキップ: voicevox_config モジュールがインポートできません")
        return False

    session_id = "test-session-save-load"

    try:
        # テスト用の設定を保存
        test_config = {
            "enabled": False,
            "speaker_id": 8,
            "speed_scale": 1.5
        }
        save_session_config(session_id, test_config, project_root)

        # 保存した設定を読み込む
        loaded_config = load_session_config(session_id, project_root)

        # セッション設定が正しく反映されていることを確認
        assert loaded_config["enabled"] == False, f"Expected enabled=False, Got: {loaded_config['enabled']}"
        assert loaded_config["speaker_id"] == 8, f"Expected speaker_id=8, Got: {loaded_config['speaker_id']}"
        assert loaded_config["speed_scale"] == 1.5, f"Expected speed_scale=1.5, Got: {loaded_config['speed_scale']}"

        # グローバル設定から継承されている項目も確認
        assert "voicevox_url" in loaded_config, "voicevox_url should be inherited from global config"
        assert "timeout" in loaded_config, "timeout should be inherited from global config"

        print("✓ test_save_and_load_session_config passed")
        return True

    finally:
        # クリーンアップ
        if delete_session_config:
            delete_session_config(session_id, project_root)


def test_config_merge_priority():
    """設定のマージ優先順位テスト"""
    if save_session_config is None or load_session_config is None:
        print("スキップ: voicevox_config モジュールがインポートできません")
        return False

    session_id = "test-session-priority"

    try:
        # グローバル設定: speaker_id=3, enabled=true（config/voicevox.json）
        # セッション設定: speaker_id=8, enabled=false
        session_config = {
            "enabled": False,
            "speaker_id": 8
        }
        save_session_config(session_id, session_config, project_root)

        # マージされた設定を読み込む
        merged_config = load_session_config(session_id, project_root)

        # セッション設定が優先されることを確認
        assert merged_config["enabled"] == False, "Session config should override global config for 'enabled'"
        assert merged_config["speaker_id"] == 8, "Session config should override global config for 'speaker_id'"

        # セッション設定にない項目はグローバル設定が使われることを確認
        assert merged_config["voicevox_url"] == "http://127.0.0.1:50021", "Global config should be used for 'voicevox_url'"
        assert merged_config["timeout"] == 60, "Global config should be used for 'timeout'"

        print("✓ test_config_merge_priority passed")
        return True

    finally:
        # クリーンアップ
        if delete_session_config:
            delete_session_config(session_id, project_root)


def test_session_config_not_exists():
    """セッション設定が存在しない場合のテスト"""
    if load_session_config is None:
        print("スキップ: voicevox_config モジュールがインポートできません")
        return False

    # 存在しないセッションIDで設定を読み込む
    session_id = "non-existent-session-999"
    config = load_session_config(session_id, project_root)

    # グローバル設定が返されることを確認
    assert config["enabled"] == True, "Should use global config when session config doesn't exist"
    assert config["speaker_id"] == 3, "Should use global config speaker_id"
    assert config["voicevox_url"] == "http://127.0.0.1:50021", "Should use global config voicevox_url"

    print("✓ test_session_config_not_exists passed")
    return True


def test_delete_session_config():
    """セッション設定の削除テスト"""
    if save_session_config is None or delete_session_config is None:
        print("スキップ: voicevox_config モジュールがインポートできません")
        return False

    session_id = "test-session-delete"

    # 設定を作成
    test_config = {"enabled": False}
    save_session_config(session_id, test_config, project_root)

    # 設定ファイルが存在することを確認
    config_path = get_session_config_path(session_id, project_root)
    assert config_path.exists(), "Config file should exist after save"

    # 設定を削除
    delete_session_config(session_id, project_root)

    # 設定ファイルが削除されたことを確認
    assert not config_path.exists(), "Config file should be deleted"

    print("✓ test_delete_session_config passed")
    return True


# ===================================================================
# Phase 2: スキル実装テスト
# ===================================================================

def test_skill_on_off():
    """スキルの on/off コマンドテスト"""
    try:
        from voicevox_skill import execute_on, execute_off, get_current_session_id
    except ImportError:
        print("スキップ: voicevox_skill モジュールがインポートできません")
        return False

    session_id = "test-session-skill-on-off"

    try:
        # on コマンドを実行
        result = execute_on(session_id, project_root)
        assert "有効化" in result or "enabled" in result.lower(), f"Expected success message, got: {result}"

        # セッション設定を確認
        config = load_session_config(session_id, project_root)
        assert config["enabled"] == True, f"Expected enabled=True, got: {config['enabled']}"

        # off コマンドを実行
        result = execute_off(session_id, project_root)
        assert "無効化" in result or "disabled" in result.lower(), f"Expected success message, got: {result}"

        # セッション設定を確認
        config = load_session_config(session_id, project_root)
        assert config["enabled"] == False, f"Expected enabled=False, got: {config['enabled']}"

        print("✓ test_skill_on_off passed")
        return True

    finally:
        # クリーンアップ
        if delete_session_config:
            delete_session_config(session_id, project_root)


def test_skill_speaker():
    """スキルの speaker コマンドテスト"""
    try:
        from voicevox_skill import execute_speaker
    except ImportError:
        print("スキップ: voicevox_skill モジュールがインポートできません")
        return False

    session_id = "test-session-skill-speaker"

    try:
        # speaker コマンドを実行
        result = execute_speaker(session_id, 8, project_root)
        assert "話者" in result or "speaker" in result.lower(), f"Expected success message, got: {result}"

        # セッション設定を確認
        config = load_session_config(session_id, project_root)
        assert config["speaker_id"] == 8, f"Expected speaker_id=8, got: {config['speaker_id']}"

        print("✓ test_skill_speaker passed")
        return True

    finally:
        # クリーンアップ
        if delete_session_config:
            delete_session_config(session_id, project_root)


def test_skill_speed():
    """スキルの speed コマンドテスト"""
    try:
        from voicevox_skill import execute_speed
    except ImportError:
        print("スキップ: voicevox_skill モジュールがインポートできません")
        return False

    session_id = "test-session-skill-speed"

    try:
        # speed コマンドを実行
        result = execute_speed(session_id, 1.5, project_root)
        assert "速度" in result or "speed" in result.lower(), f"Expected success message, got: {result}"

        # セッション設定を確認
        config = load_session_config(session_id, project_root)
        assert config["speed_scale"] == 1.5, f"Expected speed_scale=1.5, got: {config['speed_scale']}"

        print("✓ test_skill_speed passed")
        return True

    finally:
        # クリーンアップ
        if delete_session_config:
            delete_session_config(session_id, project_root)


def test_skill_status():
    """スキルの status コマンドテスト"""
    try:
        from voicevox_skill import execute_status
    except ImportError:
        print("スキップ: voicevox_skill モジュールがインポートできません")
        return False

    session_id = "test-session-skill-status"

    try:
        # セッション設定を作成
        test_config = {
            "enabled": True,
            "speaker_id": 8,
            "speed_scale": 1.5
        }
        save_session_config(session_id, test_config, project_root)

        # status コマンドを実行
        result = execute_status(session_id, project_root)

        # 出力に設定情報が含まれていることを確認
        assert "enabled" in result.lower() or "有効" in result, "Status should show enabled state"
        assert "8" in result, "Status should show speaker_id"
        assert "1.5" in result, "Status should show speed_scale"

        print("✓ test_skill_status passed")
        return True

    finally:
        # クリーンアップ
        if delete_session_config:
            delete_session_config(session_id, project_root)


def run_all_tests():
    """すべてのテストを実行"""
    print("=" * 60)
    print("VOICEVOX TTS テスト実行")
    print("=" * 60)

    tests = [
        ("設定ファイル読み込み", test_load_config),
        ("VOICEVOX 接続チェック", test_check_voicevox_connection),
        ("最新メッセージ抽出", test_extract_latest_assistant_message),
        ("新しいメッセージ抽出", test_extract_new_assistant_messages),
        ("音声クエリ作成", test_create_audio_query),
        ("音声合成", test_synthesize_speech),
        ("音声再生", test_play_audio),
        ("モニター初期化", test_monitor_initialization),
        ("モニターPIDファイル", test_monitor_pid_file),
        ("TranscriptStreamReader", test_transcript_stream_reader),
        # Phase 1: セッション管理テスト
        ("[Phase1] セッション設定パス取得", test_get_session_config_path),
        ("[Phase1] セッション設定の保存と読み込み", test_save_and_load_session_config),
        ("[Phase1] 設定マージ優先順位", test_config_merge_priority),
        ("[Phase1] セッション設定が存在しない場合", test_session_config_not_exists),
        ("[Phase1] セッション設定の削除", test_delete_session_config),
        # Phase 2: スキル実装テスト
        ("[Phase2] スキル on/off コマンド", test_skill_on_off),
        ("[Phase2] スキル speaker コマンド", test_skill_speaker),
        ("[Phase2] スキル speed コマンド", test_skill_speed),
        ("[Phase2] スキル status コマンド", test_skill_status),
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
