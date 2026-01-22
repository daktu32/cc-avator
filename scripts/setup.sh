#!/bin/bash
#
# ClaudeCode VOICEVOX プラグイン セットアップスクリプト
#

set -e

# プロジェクトルート
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "ClaudeCode VOICEVOX プラグイン セットアップ"
echo "=========================================="

# 1. Python 仮想環境の作成
echo ""
echo "[1/5] Python 仮想環境を作成..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "✓ 仮想環境を作成しました"
else
    echo "✓ 仮想環境は既に存在します"
fi

# 2. 依存関係のインストール
echo ""
echo "[2/5] 依存関係をインストール..."
.venv/bin/pip install -q -r scripts/requirements.txt
echo "✓ 依存関係をインストールしました"

# 3. VOICEVOX Engine の起動
echo ""
echo "[3/5] VOICEVOX Engine を起動..."
if docker ps | grep -q voicevox_engine; then
    echo "✓ VOICEVOX Engine は既に起動しています"
else
    docker-compose up -d
    echo "✓ VOICEVOX Engine を起動しました"
    echo "   起動を待機中..."
    sleep 10
fi

# 4. 接続テスト
echo ""
echo "[4/5] VOICEVOX Engine への接続をテスト..."
MAX_RETRIES=10
RETRY=0

while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -s http://127.0.0.1:50021/version > /dev/null; then
        VERSION=$(curl -s http://127.0.0.1:50021/version)
        echo "✓ VOICEVOX Engine に接続しました (version: $VERSION)"
        break
    fi

    RETRY=$((RETRY + 1))
    if [ $RETRY -lt $MAX_RETRIES ]; then
        echo "   接続試行 $RETRY/$MAX_RETRIES..."
        sleep 3
    else
        echo "✗ VOICEVOX Engine への接続に失敗しました"
        echo "   docker-compose logs voicevox でログを確認してください"
        exit 1
    fi
done

# 5. テストの実行
echo ""
echo "[5/5] テストを実行..."
.venv/bin/python3 tests/test_voicevox.py

echo ""
echo "=========================================="
echo "セットアップが完了しました！"
echo "=========================================="
echo ""
echo "次のステップ:"
echo "1. ~/.claude/settings.json に Stop フックを設定"
echo "   詳細は README.md を参照してください"
echo ""
echo "2. ClaudeCode で質問して音声読み上げを確認"
echo ""
echo "VOICEVOX Engine の管理:"
echo "  起動: docker-compose up -d"
echo "  停止: docker-compose down"
echo "  ログ: docker-compose logs -f voicevox"
echo ""
