# インストールガイド

## クイックインストール

```bash
# 1. リポジトリをクローン
git clone https://github.com/daktu32/cc-avator.git
cd cc-avator

# 2. セットアップを実行
./scripts/setup.sh
```

セットアップスクリプトは以下を自動実行します：
- Python 仮想環境の作成
- 依存関係のインストール
- VOICEVOX Engine の起動
- 接続テストの実行

---

## ClaudeCode 設定

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
            "command": "/path/to/cc-avator/hooks/stop_voicevox.sh"
          }
        ],
        "description": "VOICEVOX 音声読み上げ"
      }
    ]
  }
}
```

**重要**: `/path/to/cc-avator` を実際のパスに置き換えてください。

---

## プロジェクトごとに設定を変える

### オプション1: 設定ファイルのコピー

各プロジェクトに設定をコピー：

```bash
# プロジェクトディレクトリに移動
cd /path/to/your-project

# 設定をコピー
mkdir -p .claude-voicevox
cp /path/to/cc-avator/config/voicevox.json .claude-voicevox/

# スクリプトを編集して、プロジェクト固有の設定を読み込むように変更
```

### オプション2: matcher でプロジェクトを絞る

特定のプロジェクトのみで有効化：

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "cwd matches \"/Users/aiq/work/my-project\"",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/cc-avator/hooks/stop_voicevox.sh"
          }
        ],
        "description": "VOICEVOX 音声読み上げ (my-project)"
      }
    ]
  }
}
```

### オプション3: 環境変数で制御

プロジェクトごとに設定を変更：

```bash
# プロジェクトAの設定
export VOICEVOX_CONFIG=/path/to/project-a/voicevox.json
export VOICEVOX_SPEAKER_ID=3  # ずんだもん

# プロジェクトBの設定
export VOICEVOX_CONFIG=/path/to/project-b/voicevox.json
export VOICEVOX_SPEAKER_ID=1  # 四国めたん
```

`scripts/voicevox_tts.py` を編集して環境変数をサポート：

```python
# 環境変数から設定パスを取得
config_path = os.getenv('VOICEVOX_CONFIG') or (project_root / "config" / "voicevox.json")
```

---

## 一時的に無効化する

### 方法1: 設定ファイルで無効化

`config/voicevox.json`:
```json
{
  "enabled": false
}
```

### 方法2: VOICEVOX Engine を停止

```bash
docker-compose down
```

VOICEVOX が起動していない場合、音声読み上げはスキップされます。

### 方法3: フックをコメントアウト

`~/.claude/settings.json` で該当部分をコメントアウト：

```json
{
  "hooks": {
    "Stop": [
      // {
      //   "matcher": "*",
      //   "hooks": [...]
      // }
    ]
  }
}
```

---

## チーム・他のユーザーへの共有

### 1. リポジトリを共有

```bash
# リポジトリURLを共有
https://github.com/daktu32/cc-avator

# または、プライベートリポジトリにフォーク
```

### 2. ドキュメントを提供

- `README.md` - 利用ガイド
- `INSTALLATION.md` - このファイル
- `PROGRESS.md` - 開発履歴

### 3. セットアップスクリプトを実行してもらう

```bash
git clone <your-repo-url>
cd cc-avator
./scripts/setup.sh
```

---

## カスタマイズ

### 話者を変更

`config/voicevox.json`:
```json
{
  "speaker_id": 3  // 3=ずんだもん, 1=四国めたん, 8=春日部つむぎ
}
```

利用可能な話者を確認：
```bash
curl http://127.0.0.1:50021/speakers | jq
```

### 話速・音高を調整

```json
{
  "speed_scale": 1.2,   // 1.2倍速
  "pitch_scale": 0.05,  // 少し高め
  "volume_scale": 1.5   // 音量1.5倍
}
```

### 音声ファイルの保存先を変更

```json
{
  "audio_output_dir": "/tmp/voicevox_audio"
}
```

---

## トラブルシューティング

### VOICEVOX Engine が起動しない

```bash
# Docker のログを確認
docker-compose logs -f voicevox

# 再起動
docker-compose restart
```

### 音声が再生されない

```bash
# ログを確認
tail -f voicevox_tts.log

# 手動テスト
echo '{"transcript_path": "/path/to/transcript.jsonl"}' | ./hooks/stop_voicevox.sh
```

### macOS 以外の環境

現在、音声再生は macOS の `afplay` に依存しています。

Linux/Windows での対応：
- Linux: `aplay` または `mpg123` を使用
- Windows: `Windows.Media.SpeechSynthesis` を使用

`scripts/voicevox_tts.py` の `play_audio` 関数を編集してください。

---

## システム要件

- **OS**: macOS (音声再生に afplay を使用)
- **Docker**: VOICEVOX Engine の実行に必要
- **Python**: 3.8 以上
- **ClaudeCode**: Stop フック対応版

---

## ライセンス

MIT License

詳細は [README.md](README.md) を参照してください。
