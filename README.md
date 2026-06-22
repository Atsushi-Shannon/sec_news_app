# Crypto Research Radar

Crypto Research Radarは、暗号・セキュリティ研究に関係するRSS/Atom/APIを定期収集し、キーワード分類とスコアリングで関連度の高い情報だけをNotion Databaseへ登録するPythonアプリです。特に重要度が高い記事はSlack Incoming Webhookにも通知します。

## アーキテクチャ

RSS / Atom / 公開APIをGitHub Actionsから取得し、`src/crypto_radar`で正規化、URL正規化、重複除去、分類、スコアリングを行います。`score >= NOTION_SCORE_THRESHOLD`ならNotionへ登録し、`score >= SLACK_SCORE_THRESHOLD`ならSlackにも通知します。LLM API、有料検索API、HTMLスクレイピングはMVPでは使いません。

## 必要環境

- Python 3.12
- macOS、Linux、またはGitHub Actions
- Notion Integration tokenとDatabase ID
- Slack Incoming Webhook URL

## ローカルセットアップ

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
python -m crypto_radar.main --dry-run
```

Python 3.12が未導入の場合は、Homebrewやpyenvなどで先にインストールしてください。

## Notion設定

1. Notionの「My integrations」からInternal Integrationを作成します。
2. IntegrationのSecretを`.env`の`NOTION_API_TOKEN`へ設定します。
3. 登録先Databaseを作成し、右上の共有メニューからIntegrationを招待します。
4. Database URLからDatabase IDを取得し、`.env`の`NOTION_DATABASE_ID`へ設定します。

想定プロパティは次の通りです。

| Property | Type |
|---|---|
| Name | Title |
| URL | URL |
| Published | Date |
| Source | Select |
| Content Type | Select |
| Research Area | Multi-select |
| Score | Number |
| Status | StatusまたはSelect |
| Summary | Rich text |
| Relevance | Rich text |
| Added At | Date |
| Slack Notified | Checkbox |
| Fingerprint | Rich text |

プロパティ名や`Status`の型は`config/scoring.yaml`の`notion.properties`で変更できます。

## Slack設定

Slack AppでIncoming Webhookを有効化し、Webhook URLを`.env`の`SLACK_WEBHOOK_URL`へ設定します。未設定の場合、Slack通知だけが無効化され、収集処理は継続します。

## 環境変数

`.env.example`を`.env`へコピーし、次を設定します。

```dotenv
NOTION_API_TOKEN=
NOTION_DATABASE_ID=
NOTION_API_VERSION=
SLACK_WEBHOOK_URL=

NOTION_SCORE_THRESHOLD=5
SLACK_SCORE_THRESHOLD=10
LOG_LEVEL=INFO
STATE_FILE=data/seen_items.json
```

秘密情報はコードやログへ出さず、GitHub ActionsではSecretsとして渡します。

## 実行方法

```bash
python -m crypto_radar.main
python -m crypto_radar.main --dry-run
python -m crypto_radar.main --source iacr-eprint
python -m crypto_radar.main --limit 20
python -m crypto_radar.main --verbose
```

dry-runでは取得、正規化、分類、スコアリング、重複判定、Notion/Slack候補表示まで行い、Notion、Slack、`data/seen_items.json`は更新しません。

## テストと整形

```bash
pytest
ruff check .
ruff format .
ruff format --check .
```

外部APIに依存するユニットテストは置かず、ネットワークなしで主要ロジックを検証します。

## GitHub Actions

`.github/workflows/test.yml`はpull requestと`main`/`master`へのpushで`ruff check`、`ruff format --check`、`pytest`を実行します。

`.github/workflows/collect.yml`は`workflow_dispatch`と1日2回のcronで実行します。GitHub cronはUTCなので、日本時間の朝夕に近い時刻に設定しています。`data/seen_items.json`に変更がある時だけ`[skip collect]`付きで自動コミットし、収集workflowの再起動を避けます。

GitHub Secretsには次を設定してください。

- `NOTION_API_TOKEN`
- `NOTION_DATABASE_ID`
- `SLACK_WEBHOOK_URL`

GitHub Actions上でしきい値を変えたい場合は、Repository Variablesに次を任意で設定してください。

- `NOTION_SCORE_THRESHOLD`
- `SLACK_SCORE_THRESHOLD`

外部Pull RequestではSecretsが利用できないため、収集workflowは通常のscheduleまたは手動実行で使う想定です。

## 情報源の追加

`config/sources.yaml`へ次の項目を追加します。

- `id`
- `name`
- `type`: `rss`または`arxiv`
- `url`または`query`
- `enabled`
- `content_type`
- `base_score`
- `default_categories`

一部の情報源が失敗しても、そのsourceだけ警告ログを出して他のsourceを継続します。

## キーワードとスコア調整

`config/keywords.yaml`でカテゴリごとのキーワードと重みを設定します。英語は大文字小文字を区別せず、単語境界を考慮します。日本語は部分一致で判定します。暗号資産系ノイズは`negative_keywords`で大幅減点し、強制除外はしません。

`config/scoring.yaml`でNotion/Slackしきい値、タイトル一致倍率、複数カテゴリボーナス、新着ボーナス、1回あたりの上限を変更できます。

## よくあるエラー

- `NOTION_API_TOKEN or NOTION_DATABASE_ID is unset`: Notion登録だけ無効です。
- `Slack is disabled`: Slack通知だけ無効です。
- `State file is not valid JSON`: `data/seen_items.json`が壊れています。手で修正するかバックアップから戻してください。
- `Notion API returned HTTP 400`: Notion Databaseのプロパティ名や型が設定と一致していない可能性があります。
- feed取得のHTTP/DNS/timeoutエラー: 対象sourceだけスキップされます。

## セキュリティ

- APIトークンとWebhook URLは環境変数またはGitHub Secretsで管理してください。
- `.env`は`.gitignore`に含まれており、コミットしません。
- HTTPリクエストにはtimeout、User-Agent、リダイレクト上限を設定しています。
- URLは`http`/`https`を基本とし、Notion/Slackへ送る文字列は長さを制限します。
- YAMLは`yaml.safe_load`で読み込みます。

## 制限事項

MVPでは独自Web UI、LLM要約、有料検索API、HTMLスクレイピング、PDF本文解析、複雑な自然言語分類、Slack対話Bot、Notion双方向同期は実装していません。

## 今後の拡張案

- Notionの`Saved`記事だけをBibTeX化
- 日次Slackダイジェスト
- GitHub PagesまたはNext.jsの閲覧画面
- Google News RSS
- 日本企業のプレスリリース監視
- HTML差分監視
- ローカルLLMによる要約
- 類似記事クラスタリング
- Notion評価のスコアリング反映
- DOI、arXiv ID、ePrint ID抽出
