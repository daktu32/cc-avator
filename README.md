# ClaudeCode VOICEVOX 音声読み上げプラグイン

ClaudeCode の AI 応答を VOICEVOX Engine で自動音声読み上げするプラグインです。

## 特徴

- **自動読み上げ**: ClaudeCode の応答完了時に自動で音声読み上げ
- **簡単セットアップ**: Docker で VOICEVOX Engine を簡単に起動
- **カスタマイズ可能**: 話者、速度、音高などを自由に設定
- **非侵襲的**: バックグラウンドで動作し、ClaudeCode の操作を妨げない

## 必要な環境

- macOS（音声再生に `afplay` を使用）
- Docker & Docker Compose
- Python 3.8 以上

## セットアップ

### クイックインストール

```bash
# リポジトリをクローン
git clone https://github.com/daktu32/cc-avator.git
cd cc-avator

# セットアップを実行
./scripts/setup.sh
```

詳細なインストール手順は [INSTALLATION.md](INSTALLATION.md) を参照してください。

### 自動セットアップの内容

セットアップスクリプトは以下を実行します：

このスクリプトは以下を自動実行します：
- Python 仮想環境の作成
- 依存関係のインストール
- VOICEVOX Engine の起動
- 接続テスト
- テストの実行

### 3. ClaudeCode の Stop フック設定

`~/.claude/settings.json` に以下を追加：

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/aiq/work/cc-avator/hooks/stop_voicevox.sh"
          }
        ],
        "description": "VOICEVOX 音声読み上げ"
      }
    ]
  }
}
```

**重要**: パスは絶対パスで指定してください。

## 使い方

### 🎯 基本的な使い方

**デフォルトでは読み上げはオフです**。ClaudeCode で明示的に指示した場合のみ読み上げます。

#### 読み上げを開始

```bash
./scripts/monitor.sh enable
```

このコマンドを実行した時点以降の ClaudeCode の応答がリアルタイムで読み上げられます。

#### 読み上げを停止

```bash
./scripts/monitor.sh disable
```

#### ステータス確認

```bash
./scripts/monitor.sh status
```

### 💡 使用例

1. **ClaudeCode で作業中に読み上げたくなったとき**
   ```bash
   # ClaudeCode に「読み上げて」と指示
   # → ClaudeCode が ./scripts/monitor.sh enable を実行
   # → この時点以降の応答が読み上げられる
   ```

2. **読み上げを止めたいとき**
   ```bash
   # ClaudeCode に「読み上げ停止」と指示
   # → ClaudeCode が ./scripts/monitor.sh disable を実行
   # → 読み上げが停止
   ```

### 🚀 リアルタイム読み上げの仕組み

- モニターは transcript ファイルをリアルタイムで監視
- 新しいメッセージが追加されたら即座に読み上げ開始（5秒以内）
- enable コマンド実行時点のタイムスタンプを記録
- それ以降のメッセージのみを読み上げ

### ⚙️ 詳細なコマンド

```bash
# モニターを手動で起動（通常は不要）
./scripts/monitor.sh start

# モニターを手動で停止（通常は不要）
./scripts/monitor.sh stop

# モニターを再起動
./scripts/monitor.sh restart
```

### 📌 Stop フック（非推奨）

Stop フックを使用する場合、ClaudeCode の応答が完全に終了してから読み上げが開始されます。長い応答の場合は読み上げ開始が遅くなるため、enable/disable コマンドの使用を推奨します。

## 設定のカスタマイズ

`config/voicevox.json` で設定を変更できます：

```json
{
  "enabled": true,              // 読み上げの有効/無効
  "voicevox_url": "http://127.0.0.1:50021",
  "speaker_id": 3,              // 話者ID（3=ずんだもん）
  "speed_scale": 1.0,           // 話速（0.5〜2.0）
  "pitch_scale": 0.0,           // 音高（-0.15〜0.15）
  "volume_scale": 1.0,          // 音量（0.0〜2.0）
  "timeout": 30,                // タイムアウト秒数
  "audio_output_dir": "/tmp/voicevox_audio"
}
```

### 話者ID の確認

利用可能な話者を確認：

```bash
curl http://127.0.0.1:50021/speakers | jq
```

主な話者：
- 3: ずんだもん
- 1: 四国めたん
- 8: 春日部つむぎ

## トラブルシューティング

### VOICEVOX Engine に接続できない

```bash
# Engine の起動
docker-compose up -d

# ログの確認
docker-compose logs -f voicevox

# バージョン確認
curl http://127.0.0.1:50021/version
```

### 音声が再生されない

```bash
# ログを確認
tail -f voicevox_tts.log
```

### 一時的に無効化したい

`config/voicevox.json` で `enabled: false` に設定

## ファイル構成

```
cc-avator/
├── docker-compose.yml          # VOICEVOX Engine 起動設定
├── config/
│   └── voicevox.json          # 音声設定
├── scripts/
│   ├── voicevox_tts.py        # メイン音声読み上げスクリプト
│   ├── requirements.txt       # Python 依存関係
│   └── setup.sh               # セットアップスクリプト
├── hooks/
│   └── stop_voicevox.sh       # Stop フック用シェル
├── tests/
│   └── test_voicevox.py      # テストスクリプト
└── README.md                  # このファイル
```

## VOICEVOX Engine の管理

```bash
# 起動
docker-compose up -d

# 停止
docker-compose down

# ログ表示
docker-compose logs -f voicevox

# 再起動
docker-compose restart
```

## テスト

```bash
# すべてのテストを実行
.venv/bin/python3 tests/test_voicevox.py

# 手動テスト（テスト用transcript を使用）
echo '{"transcript_path": "tests/sample_transcript.jsonl"}' | ./hooks/stop_voicevox.sh
```

## 開発

TDD（テスト駆動開発）で実装されています。

### テストの実行

```bash
.venv/bin/python3 tests/test_voicevox.py
```

### 新機能の追加

1. `tests/test_voicevox.py` にテストを追加
2. テストを実行して失敗を確認
3. `scripts/voicevox_tts.py` に実装
4. テストが通ることを確認

## ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

## 参考資料

- [VOICEVOX Engine GitHub](https://github.com/VOICEVOX/voicevox_engine)
- [VOICEVOX Engine Docker Hub](https://hub.docker.com/r/voicevox/voicevox_engine)
- [ClaudeCode Hooks ドキュメント](https://code.claude.com/docs/en/hooks.md)

## 貢献

Issue や Pull Request を歓迎します。

## 謝辞

- [VOICEVOX](https://voicevox.hiroshiba.jp/) - 音声合成エンジン
- [Anthropic](https://www.anthropic.com/) - ClaudeCode
