#!/usr/bin/env python3
"""
メモリ使用量ベンチマーク
従来方式（全ファイル読み込み）vs ストリーミング方式
"""

import os
import sys
import json
import tempfile
import tracemalloc
from pathlib import Path

# プロジェクトルートをパスに追加
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from voicevox_tts import (
    extract_new_assistant_messages,
    TranscriptStreamReader,
    clean_text_for_speech
)


def create_large_transcript(num_messages: int = 1000) -> str:
    """
    テスト用の大きなtranscriptファイルを作成

    Args:
        num_messages: 作成するメッセージ数

    Returns:
        作成したファイルのパス
    """
    temp_file = tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.jsonl',
        delete=False,
        encoding='utf-8'
    )

    for i in range(num_messages):
        entry = {
            "message": {
                "role": "assistant",
                "content": [{
                    "type": "text",
                    "text": f"これはテストメッセージ {i} です。" * 10  # 長いテキスト
                }]
            },
            "timestamp": f"2026-01-23T00:{i//60:02d}:{i%60:02d}.000Z"
        }
        temp_file.write(json.dumps(entry, ensure_ascii=False) + "\n")

    temp_file.close()
    return temp_file.name


def benchmark_traditional_read(file_path: str) -> tuple:
    """
    従来方式（全ファイル読み込み）のメモリ使用量を測定

    Args:
        file_path: テストファイルのパス

    Returns:
        (ピークメモリ使用量(MB), メッセージ数)
    """
    tracemalloc.start()

    # 全ファイルを読み込む従来方式
    messages = extract_new_assistant_messages(file_path, last_timestamp=None)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return peak / 1024 / 1024, len(messages)


def benchmark_streaming_read(file_path: str, new_messages_count: int = 10) -> tuple:
    """
    ストリーミング方式のメモリ使用量を測定
    実際の使用シナリオ：ファイル末尾から新しい数行のみを読み取る

    Args:
        file_path: テストファイルのパス
        new_messages_count: 新しく追加されたメッセージ数（シミュレーション）

    Returns:
        (ピークメモリ使用量(MB), メッセージ数)
    """
    # StreamReaderを開いて末尾に移動（既存データをスキップ）
    reader = TranscriptStreamReader(file_path)
    reader.open()

    # ファイルに新しい行を追加（実際の使用シナリオをシミュレート）
    with open(file_path, 'a', encoding='utf-8') as f:
        for i in range(new_messages_count):
            entry = {
                "message": {
                    "role": "assistant",
                    "content": [{
                        "type": "text",
                        "text": f"新しいメッセージ {i} です。" * 10
                    }]
                },
                "timestamp": f"2026-01-23T10:00:{i:02d}.000Z"
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ここからメモリ測定開始（新しい行のみを読み取る）
    tracemalloc.start()

    # 新しく追加された行のみを読み取る
    new_lines = reader.read_new_lines()

    # メッセージをパース
    messages = []
    for line in new_lines:
        try:
            entry = json.loads(line)
            message = entry.get("message", {})
            timestamp = entry.get("timestamp")

            if message.get("role") == "assistant" and timestamp:
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
                        messages.append({
                            "timestamp": timestamp,
                            "text": clean_text
                        })
        except json.JSONDecodeError:
            continue

    reader.close()

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return peak / 1024 / 1024, len(messages)


def main():
    """メイン処理"""
    print("=" * 60)
    print("メモリ使用量ベンチマーク: 従来方式 vs ストリーミング方式")
    print("=" * 60)
    print()
    print("シナリオ: 既に大きなtranscriptファイルがあり、")
    print("         新しいメッセージが10件追加された場合")
    print()

    # テストサイズ（既存のtranscriptファイルのサイズ）
    test_sizes = [100, 500, 1000, 2000, 5000]
    new_messages = 10  # 新しく追加されるメッセージ数

    for size in test_sizes:
        print(f"[テスト] 既存メッセージ数: {size} + 新規: {new_messages}")

        # テストファイルを作成
        file_path = create_large_transcript(size)
        file_size = os.path.getsize(file_path) / 1024 / 1024  # MB

        print(f"  ファイルサイズ: {file_size:.2f} MB")

        # 従来方式（全ファイルを読み込んで新しいメッセージを探す）
        trad_memory, trad_count = benchmark_traditional_read(file_path)
        print(f"  従来方式（全読込）: {trad_memory:.2f} MB (読込: {trad_count}件)")

        # ストリーミング方式（新しい行のみを読み取る）
        stream_memory, stream_count = benchmark_streaming_read(file_path, new_messages)
        print(f"  ストリーミング方式: {stream_memory:.2f} MB (読込: {stream_count}件)")

        # 効率改善率
        if trad_memory > 0:
            improvement = ((trad_memory - stream_memory) / trad_memory) * 100
            print(f"  メモリ削減率: {improvement:.1f}%")
        else:
            print(f"  メモリ削減率: N/A")

        # クリーンアップ
        os.unlink(file_path)
        print()

    print("=" * 60)
    print("ベンチマーク完了")
    print("=" * 60)
    print()
    print("結論: ストリーミング方式では、ファイルサイズに関係なく")
    print("      新しいメッセージ分のメモリのみを使用します。")
    print("      ファイルが大きくなるほど、メモリ削減効果が高くなります。")


if __name__ == "__main__":
    main()
