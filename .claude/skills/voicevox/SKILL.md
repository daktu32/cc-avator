---
name: voicevox
description: VOICEVOX音声読み上げのセッションごとの設定を管理
disable-model-invocation: true
allowed-tools: Bash
---

# VOICEVOX スキル

このスキルは、VOICEVOX音声読み上げのセッションごとの設定を管理します。

## コマンド

- `on` - 現在のセッションで読み上げを有効化
- `off` - 現在のセッションで読み上げを無効化
- `speaker <id>` - 話者を変更
- `speed <rate>` - 読み上げ速度を変更
- `status` - 現在の設定を表示

## 使用例

```bash
/voicevox on              # 読み上げを有効化
/voicevox off             # 読み上げを無効化
/voicevox speaker 8       # 話者をID 8に変更
/voicevox speed 1.5       # 速度を1.5倍に変更
/voicevox status          # 現在の設定を表示
```

## 実装

```bash
#!/bin/bash

# プロジェクトルートを取得
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Python 仮想環境のパス
VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python3"

# スキルスクリプトのパス
SKILL_SCRIPT="${PROJECT_ROOT}/scripts/voicevox_skill.py"

# セッションIDを環境変数に設定
export CLAUDE_SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"

# スキルスクリプトを実行
"$VENV_PYTHON" "$SKILL_SCRIPT" $ARGUMENTS
```
