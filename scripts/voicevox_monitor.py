#!/usr/bin/env python3
"""
VOICEVOX TTS リアルタイムモニター
transcript ファイルをリアルタイムで監視して、新しいメッセージを即座に読み上げる
"""

import sys
import os
import time
import signal
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

# voicevox_tts モジュールをインポート
from voicevox_tts import (
    check_voicevox_connection,
    extract_new_assistant_messages,
    create_audio_query,
    synthesize_speech,
    play_audio,
    clean_text_for_speech,
    TranscriptStreamReader
)


class TranscriptFileHandler(FileSystemEventHandler):
    """
    transcript ファイルの変更を検出するハンドラー
    """

    def __init__(self, monitor: 'TranscriptMonitor'):
        self.monitor = monitor
        super().__init__()

    def on_modified(self, event: FileModifiedEvent):
        """ファイル変更時のコールバック"""
        if event.is_directory:
            return

        # .jsonl ファイルのみを対象
        if not event.src_path.endswith('.jsonl'):
            return

        # モニターに通知
        self.monitor.on_file_modified(event.src_path)


class TranscriptMonitor:
    """
    transcript ファイルをリアルタイムで監視して音声読み上げを行う
    """

    def __init__(self, watch_dir: str, config: Dict[str, Any]):
        """
        初期化

        Args:
            watch_dir: 監視対象ディレクトリ
            config: VOICEVOX 設定
        """
        self.watch_dir = watch_dir
        self.config = config
        self.observer: Optional[Observer] = None
        self.running = False

        # セッションごとの最終読み上げタイムスタンプを記録
        # {session_id: last_timestamp}
        self.last_timestamps: Dict[str, str] = {}

        # セッションごとのStreamReaderを管理
        # {file_path: TranscriptStreamReader}
        self.stream_readers: Dict[str, TranscriptStreamReader] = {}

    def get_pid_file(self) -> Path:
        """
        PIDファイルのパスを取得

        Returns:
            PIDファイルのパス
        """
        # watch_dir をハッシュ化してPIDファイル名に使用
        watch_dir_hash = hashlib.md5(self.watch_dir.encode()).hexdigest()[:8]
        return Path(f"/tmp/voicevox_monitor_{watch_dir_hash}.pid")

    def get_enable_timestamp_file(self) -> Path:
        """
        読み上げ有効化タイムスタンプファイルのパスを取得

        Returns:
            タイムスタンプファイルのパス
        """
        watch_dir_hash = hashlib.md5(self.watch_dir.encode()).hexdigest()[:8]
        return Path(f"/tmp/voicevox_enable_{watch_dir_hash}.timestamp")

    def get_enable_timestamp(self) -> Optional[str]:
        """
        読み上げ開始タイムスタンプを取得

        Returns:
            タイムスタンプ（ISO 8601形式）、ファイルが存在しない場合は None
        """
        timestamp_file = self.get_enable_timestamp_file()
        if not timestamp_file.exists():
            return None

        try:
            with open(timestamp_file, 'r') as f:
                return f.read().strip()
        except Exception as e:
            print(f"[Monitor] タイムスタンプファイルの読み込みに失敗: {e}", file=sys.stderr)
            return None

    def is_running(self) -> bool:
        """
        モニターが起動中かチェック

        Returns:
            起動中の場合 True
        """
        pid_file = self.get_pid_file()

        if not pid_file.exists():
            return False

        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())

            # プロセスが実際に存在するかチェック
            os.kill(pid, 0)
            return True
        except (ValueError, ProcessLookupError, PermissionError):
            # PIDファイルが不正、またはプロセスが存在しない
            pid_file.unlink(missing_ok=True)
            return False

    def write_pid_file(self):
        """PIDファイルを書き込む"""
        pid_file = self.get_pid_file()
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))

    def remove_pid_file(self):
        """PIDファイルを削除"""
        pid_file = self.get_pid_file()
        pid_file.unlink(missing_ok=True)

    def on_file_modified(self, file_path: str):
        """
        ファイル変更時の処理

        Args:
            file_path: 変更されたファイルのパス
        """
        import datetime
        start_time = time.time()

        # 読み上げが有効化されているかチェック
        enable_timestamp = self.get_enable_timestamp()
        if enable_timestamp is None:
            # 読み上げが有効化されていない場合は何もしない
            return

        print(f"[Monitor] [{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] ファイル変更検出: {Path(file_path).name}")

        # セッションIDを抽出
        session_id = Path(file_path).stem

        # StreamReaderを取得または作成
        extract_start = time.time()
        if file_path not in self.stream_readers:
            # 新しいファイルの場合、StreamReaderを作成して開く
            reader = TranscriptStreamReader(file_path)
            reader.open()
            self.stream_readers[file_path] = reader
            print(f"[Monitor] 新しいStreamReaderを作成: {Path(file_path).name}")

        # ストリーミングで新しい行のみを読み取る
        reader = self.stream_readers[file_path]
        new_lines = reader.read_new_lines()

        if not new_lines:
            return

        # 読み取った行をパースしてメッセージを抽出
        import json
        new_messages = []
        for line in new_lines:
            try:
                entry = json.loads(line)
                message = entry.get("message", {})
                timestamp = entry.get("timestamp")

                if message.get("role") == "assistant" and timestamp:
                    # enable_timestamp より新しいメッセージのみを処理
                    if enable_timestamp and timestamp <= enable_timestamp:
                        continue

                    content = message.get("content", [])
                    text_parts = [
                        item.get("text", "")
                        for item in content
                        if isinstance(item, dict) and item.get("type") == "text"
                    ]

                    if text_parts:
                        raw_text = " ".join(text_parts)
                        clean_text = clean_text_for_speech(raw_text)
                        if clean_text:
                            new_messages.append({
                                "timestamp": timestamp,
                                "text": clean_text
                            })
            except json.JSONDecodeError:
                continue

        extract_time = time.time() - extract_start

        if not new_messages:
            return

        print(f"[Monitor] [{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] 新しいメッセージ: {len(new_messages)}件 (抽出: {extract_time:.3f}秒, 検出から: {time.time()-start_time:.3f}秒)")

        # 各メッセージを読み上げ
        output_dir = Path(self.config.get("audio_output_dir", "/tmp/voicevox_audio"))
        output_dir.mkdir(parents=True, exist_ok=True)

        for i, msg in enumerate(new_messages):
            message_text = msg["text"]
            timestamp = msg["timestamp"]
            msg_start_time = time.time()

            print(f"[Monitor] [{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] [{i+1}/{len(new_messages)}] 読み上げ: {message_text[:50]}...")

            # 音声クエリを作成
            query_start = time.time()
            audio_query = create_audio_query(
                self.config["voicevox_url"],
                message_text,
                self.config["speaker_id"],
                self.config.get("timeout", 30)
            )
            query_time = time.time() - query_start

            if not audio_query:
                print(f"[Monitor] 音声クエリ作成に失敗", file=sys.stderr)
                continue

            print(f"[Monitor]   - 音声クエリ作成: {query_time:.3f}秒")

            # 速度、音高、音量を調整
            audio_query["speedScale"] = self.config.get("speed_scale", 1.0)
            audio_query["pitchScale"] = self.config.get("pitch_scale", 0.0)
            audio_query["volumeScale"] = self.config.get("volume_scale", 1.0)

            # 音声を合成
            synth_start = time.time()
            output_path = output_dir / f"monitor_{session_id}_{i}.wav"
            if not synthesize_speech(
                self.config["voicevox_url"],
                audio_query,
                self.config["speaker_id"],
                str(output_path),
                self.config.get("timeout", 30)
            ):
                print(f"[Monitor] 音声合成に失敗", file=sys.stderr)
                continue
            synth_time = time.time() - synth_start

            print(f"[Monitor]   - 音声合成: {synth_time:.3f}秒")

            # 音声を再生
            play_start = time.time()
            if not play_audio(str(output_path)):
                print(f"[Monitor] 音声再生に失敗", file=sys.stderr)
                continue
            play_time = time.time() - play_start

            total_time = time.time() - msg_start_time
            print(f"[Monitor]   - 音声再生: {play_time:.3f}秒 (合計: {total_time:.3f}秒)")

            # タイムスタンプを更新
            self.last_timestamps[session_id] = timestamp

    def start(self):
        """モニターを起動"""
        # 既に起動している場合はエラー
        if self.is_running():
            print(f"モニターは既に起動しています: {self.get_pid_file()}", file=sys.stderr)
            sys.exit(1)

        # VOICEVOX Engine への接続をチェック
        if not check_voicevox_connection(self.config["voicevox_url"]):
            print(f"VOICEVOX Engine に接続できません: {self.config['voicevox_url']}", file=sys.stderr)
            print("docker-compose up -d で起動してください", file=sys.stderr)
            sys.exit(1)

        # PIDファイルを書き込む
        self.write_pid_file()

        # シグナルハンドラーを登録
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        print(f"[Monitor] モニター起動: {self.watch_dir}")
        print(f"[Monitor] PIDファイル: {self.get_pid_file()}")

        # ファイル監視を開始
        self.running = True
        event_handler = TranscriptFileHandler(self)
        # タイムアウトを短くしてファイル変更の検出を高速化（デフォルト1秒 → 0.1秒）
        self.observer = Observer(timeout=0.1)
        self.observer.schedule(event_handler, self.watch_dir, recursive=True)
        self.observer.start()

        print(f"[Monitor] Observer timeout: 0.1秒 (高速検出モード)")

        try:
            # メインループ（ポーリング間隔を短縮）
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        """モニターを停止"""
        if self.observer:
            self.observer.stop()
            self.observer.join()

        self.running = False
        self.remove_pid_file()
        print("[Monitor] モニター停止")

    def _signal_handler(self, signum, frame):
        """シグナルハンドラー"""
        print(f"\n[Monitor] シグナル受信: {signum}")
        self.running = False


def main():
    """メイン処理"""
    import argparse
    from voicevox_tts import load_config

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

    # コマンドライン引数を解析
    parser = argparse.ArgumentParser(description="VOICEVOX TTS リアルタイムモニター")
    parser.add_argument(
        "action",
        choices=["start", "stop", "status"],
        help="実行するアクション"
    )
    parser.add_argument(
        "--watch-dir",
        default=os.path.expanduser("~/.claude/projects"),
        help="監視対象ディレクトリ（デフォルト: ~/.claude/projects）"
    )

    args = parser.parse_args()

    # モニターを初期化
    monitor = TranscriptMonitor(args.watch_dir, config)

    if args.action == "start":
        monitor.start()
    elif args.action == "stop":
        pid_file = monitor.get_pid_file()

        if not pid_file.exists():
            print("モニターは起動していません")
            sys.exit(0)

        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())

            # プロセスに SIGTERM を送信
            os.kill(pid, signal.SIGTERM)
            print(f"モニターを停止しました (PID: {pid})")

            # PIDファイルを削除
            pid_file.unlink(missing_ok=True)
        except (ValueError, ProcessLookupError) as e:
            print(f"モニターの停止に失敗: {e}", file=sys.stderr)
            pid_file.unlink(missing_ok=True)
    elif args.action == "status":
        if monitor.is_running():
            pid_file = monitor.get_pid_file()
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            print(f"モニターは起動中です (PID: {pid})")
            sys.exit(0)
        else:
            print("モニターは停止しています")
            sys.exit(1)


if __name__ == "__main__":
    main()
