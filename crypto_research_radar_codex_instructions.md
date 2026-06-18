# Crypto Research Radar — Codex実装指示書

## 1. プロジェクト概要

暗号・セキュリティ研究に関係するニュース、論文、標準化情報、プレスリリースを定期的に収集し、関連度の高い情報だけをNotion Databaseへ登録するPythonアプリケーションを作成してください。

特に重要度が高い情報はSlackにも通知します。

このアプリケーションはGitHub Actionsで定期実行し、原則として無料で運用できる構成にしてください。

### 基本構成

```text
RSS / Atom / 公開API
        ↓
GitHub Actionsによる定期実行
        ↓
Pythonで取得・正規化
        ↓
重複除去
        ↓
キーワード分類・スコアリング
        ↓
score >= NOTION_THRESHOLD
    → Notion Databaseへ登録

score >= SLACK_THRESHOLD
    → Notion登録 + Slack通知
```

## 2. 最重要方針

以下を必ず守ってください。

1. 最初はMVPを完成させる
2. 有料APIを使用しない
3. LLM APIを使用しない
4. RSS、Atom、公式公開APIを優先する
5. HTMLスクレイピングはMVPでは実装しない
6. 設定値をソースコードへ直接埋め込まない
7. NotionトークンやSlack Webhook URLはGitHub Secretsまたは環境変数で管理する
8. 一部の情報源が取得できなくても、処理全体を停止させない
9. 同じ記事をNotionへ重複登録しない
10. テストしやすいように、取得、分類、保存、通知を分離する
11. READMEだけでセットアップと実行方法が分かる状態にする
12. macOS上のVSCodeでローカル開発できるようにする
13. Python 3.12を使用する
14. 型ヒントを付ける
15. ログを適切に出力する

## 3. MVPの対象範囲

最初のバージョンでは、以下を実装してください。

### 必須機能

- RSS/Atomフィードの取得
- arXiv APIまたはarXiv Atomフィードの取得
- 記事情報の共通形式への正規化
- URLの正規化
- 重複記事の除外
- キーワードマッチング
- 関連度スコアリング
- カテゴリ分類
- Notion Databaseへの登録
- Slack Incoming Webhookへの通知
- GitHub Actionsによる定期実行
- dry-runモード
- pytestによる主要ロジックのテスト
- README
- `.env.example`
- 設定ファイルのサンプル

### MVPでは実装しないもの

- 独自Web UI
- LLMによる要約
- 有料検索API
- ブラウザ自動操作
- JavaScript実行が必要なWebサイトの収集
- PDF本文の解析
- 複雑な自然言語分類
- ユーザー認証
- 複数ユーザー対応
- Slack上の対話型Bot
- Notionからの双方向同期

## 4. 使用技術

推奨構成は以下です。

```text
Language: Python 3.12
HTTP: httpx
RSS/Atom: feedparser
Configuration: PyYAML
Environment variables: python-dotenv
Validation/model: pydantic
Notion: 公式Notion APIをHTTP経由または公式SDKで利用
Slack: Incoming Webhook
Testing: pytest
Lint/format: ruff
CI/Scheduler: GitHub Actions
```

依存関係を増やしすぎないでください。

Notion APIおよびSlack APIについては、実装時点の最新の公式仕様に従ってください。

## 5. プロジェクト構成

以下を基本構成としてください。必要に応じて小さな変更は可能ですが、責務分離を維持してください。

```text
crypto-research-radar/
├── .github/
│   └── workflows/
│       ├── collect.yml
│       └── test.yml
├── config/
│   ├── sources.yaml
│   ├── keywords.yaml
│   └── scoring.yaml
├── data/
│   └── seen_items.json
├── src/
│   └── crypto_radar/
│       ├── __init__.py
│       ├── main.py
│       ├── models.py
│       ├── config.py
│       ├── logging_config.py
│       ├── normalize.py
│       ├── deduplicate.py
│       ├── classifier.py
│       ├── scorer.py
│       ├── state.py
│       ├── collectors/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── rss.py
│       │   └── arxiv.py
│       ├── outputs/
│       │   ├── __init__.py
│       │   ├── notion.py
│       │   └── slack.py
│       └── utils/
│           ├── __init__.py
│           ├── dates.py
│           └── urls.py
├── tests/
│   ├── test_normalize.py
│   ├── test_deduplicate.py
│   ├── test_classifier.py
│   ├── test_scorer.py
│   └── fixtures/
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── LICENSE
```

`src`レイアウトを使用し、次のコマンドで実行できるようにしてください。

```bash
python -m crypto_radar.main
```

可能であれば、以下のCLIオプションも実装してください。

```bash
python -m crypto_radar.main --dry-run
python -m crypto_radar.main --source iacr-eprint
python -m crypto_radar.main --limit 20
python -m crypto_radar.main --verbose
```

## 6. データモデル

収集した情報は、すべて共通のモデルに正規化してください。

Pydanticを使用し、概ね次の項目を持つモデルを作成してください。

```python
class Article:
    id: str
    title: str
    url: str
    normalized_url: str
    source_id: str
    source_name: str
    source_type: str
    content_type: str
    published_at: datetime | None
    fetched_at: datetime
    authors: list[str]
    summary: str
    language: str | None
    matched_keywords: list[str]
    categories: list[str]
    score: int
    fingerprint: str
```

### `content_type` の候補

```text
Paper
News
Standard
Press Release
Advisory
Blog
Other
```

### `categories` の候補

```text
Symmetric-Key
Block Cipher
Lightweight Crypto
AEAD
Post-Quantum
Protocol Security
TLS
MLS
Implementation
Cortex-M
ASIC
FPGA
Side-Channel
Masking
Standardization
Vulnerability
General Security
```

## 7. 初期情報源

MVPでは、まず以下を対象にしてください。

実際のURLは設定ファイルへ記述し、コードへハードコードしないでください。フィードURLが有効か確認し、公式のRSS/Atom/APIを利用してください。

### 必須

- IACR ePrint
- arXiv
- NIST CSRCの更新情報
- JPCERT/CC
- Google Security Blog
- Cloudflare Blog
- Microsoft Security Blog
- Trail of Bits Blog

### 可能なら追加

- CISA
- IPA
- JVN
- IETF関連の公式フィード
- NCC Group Research

情報源が取得不能な場合は、その情報源だけ警告ログを出してスキップしてください。

## 8. `sources.yaml`

情報源をコードから分離してください。

例：

```yaml
sources:
  - id: iacr-eprint
    name: IACR ePrint
    type: rss
    content_type: Paper
    url: "OFFICIAL_FEED_URL"
    enabled: true
    base_score: 5
    default_categories:
      - Symmetric-Key

  - id: arxiv-crypto
    name: arXiv Cryptography
    type: arxiv
    content_type: Paper
    enabled: true
    base_score: 4
    query: >
      all:"cryptography"
      OR all:"block cipher"
      OR all:"authenticated encryption"
      OR all:"post-quantum cryptography"
    max_results: 50
    default_categories: []

  - id: google-security-blog
    name: Google Security Blog
    type: rss
    content_type: Blog
    url: "OFFICIAL_FEED_URL"
    enabled: true
    base_score: 2
    default_categories:
      - General Security
```

各情報源には最低限、以下を設定できるようにしてください。

```text
id
name
type
urlまたはquery
enabled
content_type
base_score
default_categories
```

## 9. `keywords.yaml`

キーワードはカテゴリごとに定義し、日本語と英語の両方に対応してください。

大文字・小文字は区別しないでください。

単純な部分一致だけでなく、可能な範囲で単語境界を考慮してください。ただし、日本語には英語の単語境界処理をそのまま適用しないでください。

例：

```yaml
categories:
  Symmetric-Key:
    weight: 5
    keywords:
      - symmetric-key
      - symmetric key
      - symmetric cryptography
      - 共通鍵暗号
      - 共通鍵

  Block Cipher:
    weight: 5
    keywords:
      - block cipher
      - ブロック暗号
      - AES
      - SPN
      - Feistel

  Lightweight Crypto:
    weight: 5
    keywords:
      - lightweight cryptography
      - lightweight cipher
      - lightweight encryption
      - 軽量暗号
      - 超軽量暗号

  AEAD:
    weight: 4
    keywords:
      - AEAD
      - authenticated encryption
      - authenticated encryption with associated data
      - 認証暗号
      - AES-GCM
      - GCM-SIV
      - ASCON

  Post-Quantum:
    weight: 4
    keywords:
      - post-quantum
      - post quantum
      - PQC
      - quantum-resistant
      - quantum safe
      - 耐量子
      - 耐量子暗号

  Protocol Security:
    weight: 3
    keywords:
      - protocol security
      - secure messaging
      - end-to-end encryption
      - E2EE
      - Signal Protocol
      - プロトコル解析

  TLS:
    weight: 3
    keywords:
      - TLS
      - Transport Layer Security

  MLS:
    weight: 3
    keywords:
      - Messaging Layer Security
      - MLS

  Implementation:
    weight: 3
    keywords:
      - implementation
      - optimized implementation
      - constant-time
      - bitslice
      - fixslice
      - 実装
      - 定数時間

  Cortex-M:
    weight: 4
    keywords:
      - Cortex-M
      - Cortex-M3
      - Cortex-M4
      - ARM microcontroller

  ASIC:
    weight: 4
    keywords:
      - ASIC
      - hardware implementation
      - gate equivalent
      - GE
      - ハードウェア実装

  FPGA:
    weight: 4
    keywords:
      - FPGA

  Side-Channel:
    weight: 3
    keywords:
      - side-channel
      - side channel
      - power analysis
      - fault attack
      - サイドチャネル
      - 電力解析
      - 故障攻撃

  Masking:
    weight: 3
    keywords:
      - masking
      - masked implementation
      - first-order masking
      - higher-order masking
      - マスキング

  Standardization:
    weight: 3
    keywords:
      - standardization
      - draft standard
      - FIPS
      - NIST
      - IETF
      - CFRG
      - 標準化

  Vulnerability:
    weight: 2
    keywords:
      - vulnerability
      - attack
      - exploit
      - security advisory
      - 脆弱性
      - 攻撃
```

### 除外キーワード

暗号資産関係のノイズを抑えるため、除外語または大幅減点語を設定してください。

```yaml
negative_keywords:
  - keyword: 暗号資産
    weight: -10
  - keyword: 仮想通貨
    weight: -10
  - keyword: cryptocurrency
    weight: -10
  - keyword: bitcoin
    weight: -10
  - keyword: ethereum
    weight: -10
  - keyword: NFT
    weight: -10
  - keyword: token price
    weight: -8
  - keyword: crypto exchange
    weight: -8
```

ただし、暗号資産の記事中に実際の暗号技術研究が含まれるケースを完全には排除しない設計にしてください。

強制除外ではなく、基本的には大幅減点としてください。

## 10. スコアリング

`scoring.yaml`でしきい値と補正値を変更できるようにしてください。

例：

```yaml
thresholds:
  notion: 5
  slack: 10

bonuses:
  keyword_in_title_multiplier: 2
  multiple_category_bonus:
    min_categories: 2
    score: 2
  recent_publication_bonus:
    within_hours: 48
    score: 1

limits:
  max_items_per_run: 100
  max_notion_items_per_run: 30
  max_slack_notifications_per_run: 5
```

基本スコアは以下のようにしてください。

```text
score =
    source.base_score
  + title中のキーワード点
  + summary中のキーワード点
  + 複数カテゴリ一致ボーナス
  + 新着ボーナス
  + negative keywordの減点
```

### 条件

- タイトル中の一致は本文・summary中より重くする
- 同じキーワードが何度出ても無制限に加点しない
- 同一カテゴリ内での過剰加点を防ぐ
- 一般語の`security`や`cryptography`だけでは高得点にならない
- なぜそのスコアになったかログまたはArticle情報から確認できるようにする
- スコアリング関数は副作用を持たない純粋関数に近づける

## 11. 重複除去

同一記事を繰り返し登録しないようにしてください。

以下を組み合わせてfingerprintを生成してください。

```text
正規化URL
正規化タイトル
source_id
```

URL正規化では、可能な範囲で以下を処理してください。

- URL fragmentの除去
- `utm_source`など一般的なトラッキングパラメータの除去
- schemeとhostの小文字化
- 末尾スラッシュの統一
- クエリパラメータの安定した並び替え

状態は次のファイルに保存してください。

```text
data/seen_items.json
```

例：

```json
{
  "version": 1,
  "items": {
    "fingerprint-value": {
      "url": "https://example.com/article",
      "title": "Example article",
      "source_id": "example",
      "published_at": "2026-06-18T00:00:00Z",
      "processed_at": "2026-06-18T09:00:00Z",
      "score": 8,
      "sent_to_notion": true,
      "sent_to_slack": false
    }
  }
}
```

### 状態管理上の条件

- JSONを壊さないように一時ファイルへ書いてからatomic renameする
- ファイルが存在しない場合は自動作成する
- JSONが破損している場合は明確なエラーを出す
- dry-runでは更新しない
- 古いデータを削除するcleanup関数を用意する
- デフォルトでは365日以上前の低スコア記事を削除可能にする

GitHub Actions実行後、`seen_items.json`に変更がある場合は、workflowから自動コミットしてください。

無限実行を防ぐため、Actions自身のコミットでは収集workflowが再起動しないようにしてください。

## 12. Notion連携

Notion Databaseへ、スコアがNotionしきい値以上の記事を登録してください。

### 環境変数

```text
NOTION_API_TOKEN
NOTION_DATABASE_ID
NOTION_API_VERSION
```

`NOTION_API_VERSION`には適切なデフォルト値を設定可能にしつつ、環境変数で上書きできるようにしてください。

### 想定するNotionプロパティ

以下のプロパティ名を使用してください。

```text
Name
URL
Published
Source
Content Type
Research Area
Score
Status
Summary
Relevance
Added At
Slack Notified
Fingerprint
```

型は以下を想定します。

| Notion property | 型 |
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

### 登録内容

`Relevance`には、最低限次のような文章をルールベースで生成してください。

```text
Matched categories: AEAD, Cortex-M, Implementation
Matched keywords: AEAD, Cortex-M4, optimized implementation
```

自然言語で高度に要約する必要はありません。

### Notion連携上の条件

- APIエラー時にHTTPステータスと原因をログへ出す
- 429の場合は`Retry-After`に従って再試行する
- 5xxは指数バックオフ付きで数回再試行する
- 4xxの設定ミスは再試行し続けない
- 長いsummaryはNotionの制約に合わせて安全に切り詰める
- プロパティ名は設定ファイルから変更できる設計が望ましい
- dry-runでは実際にNotionへ書き込まない
- Notionへの送信成功後のみ状態を`sent_to_notion: true`にする
- 1件の登録失敗で残りの記事を停止しない

Notion Database内でFingerprintを検索して重複確認する処理も実装してください。

ただし、毎回全件検索しないでください。基本的な重複管理はローカル状態ファイルで行い、Notion側の確認は状態不整合への防御として使用してください。

## 13. Slack連携

Slack Incoming Webhookを使用してください。

### 環境変数

```text
SLACK_WEBHOOK_URL
```

スコアがSlackしきい値以上の記事だけ通知してください。

通知件数が多い場合は、`max_slack_notifications_per_run`で制限してください。

通知には以下を含めてください。

```text
重要度
タイトル
情報源
公開日
スコア
カテゴリ
一致キーワード
短いsummary
元URL
Notion登録結果
```

例：

```text
🔥 Crypto Research Radar

Efficient Lightweight AEAD on Cortex-M4

Source: IACR ePrint
Score: 14
Categories: Lightweight Crypto, AEAD, Cortex-M, Implementation
Matched: lightweight cryptography, AEAD, Cortex-M4

Cortex-M4向け軽量AEAD実装に関する論文。

Original:
https://example.com/paper
```

### Slack連携上の条件

- Webhook URLが未設定ならSlack通知だけ無効化する
- アプリ全体は停止させない
- dry-runではpayloadをログ表示するだけにする
- 通知成功後のみ`sent_to_slack: true`にする
- Slackの文字数制限を超えない
- URLは安全に扱う
- 失敗した記事はログに残す

## 14. dry-runモード

`--dry-run`を実装してください。

dry-runでは以下を行います。

- 情報源からの取得
- 正規化
- 重複判定
- キーワード分類
- スコアリング
- Notion登録予定の記事表示
- Slack通知予定の記事表示

ただし以下は行いません。

- Notionへの書き込み
- Slackへの送信
- `seen_items.json`の更新
- Gitコミット

dry-runの出力から、最低限以下が確認できるようにしてください。

```text
取得件数
新規件数
重複件数
Notion登録候補件数
Slack通知候補件数
各記事のscore
カテゴリ
一致キーワード
除外・減点理由
```

## 15. エラーハンドリング

以下を区別して処理してください。

- HTTPタイムアウト
- DNS・接続エラー
- RSS解析エラー
- 不正な日付
- 不正な設定ファイル
- Notion APIエラー
- Slack Webhookエラー
- 状態ファイル破損
- 一部情報源のみの取得失敗

一部の情報源が失敗しても、他の情報源の処理を継続してください。

最後に実行結果のサマリーをログ出力してください。

例：

```text
Run summary:
Sources attempted: 8
Sources succeeded: 7
Sources failed: 1
Items fetched: 124
Duplicates skipped: 83
Items scored: 41
Sent to Notion: 12
Sent to Slack: 3
Errors: 1
```

## 16. ログ

標準の`logging`モジュールを使用してください。

ログレベルは環境変数またはCLIから変更可能にしてください。

```text
DEBUG
INFO
WARNING
ERROR
```

秘密情報をログへ出さないでください。

以下はマスクしてください。

- Notion API token
- Slack Webhook URL
- その他のAuthorization header

## 17. テスト

最低限、以下の単体テストを実装してください。

### URL正規化

- fragment除去
- UTMパラメータ除去
- パラメータ並び替え
- trailing slash処理

### キーワード分類

- 英語の大文字・小文字を区別しない
- 日本語キーワードに対応する
- タイトル一致が正しく認識される
- 同一キーワードの重複加点を防ぐ
- negative keywordが減点される

### スコアリング

- base scoreが反映される
- title multiplierが反映される
- 複数カテゴリボーナスが反映される
- negative scoreが反映される
- しきい値判定が正しい

### 重複除去

- 同一URL
- トラッキングパラメータのみ異なるURL
- 同一タイトル
- 異なる情報源で同じURL

### 状態ファイル

- 新規ファイル作成
- 読み込み・保存
- dry-runでは変更されない
- 不正JSONの処理

外部APIに依存するテストでは、実ネットワークへアクセスせずmockを使用してください。

## 18. GitHub Actions

### `test.yml`

以下を実行してください。

```text
checkout
Python 3.12セットアップ
依存関係インストール
ruff check
ruff format --check
pytest
```

pull requestと主要ブランチへのpushで実行してください。

### `collect.yml`

以下を実装してください。

- `workflow_dispatch`で手動実行可能
- cronで1日2回程度実行
- タイムゾーンはGitHub ActionsのcronがUTCであることを考慮する
- 日本時間の朝と夕方に近い時刻を設定
- Python 3.12
- Secretsを環境変数として渡す
- アプリを実行
- `data/seen_items.json`に変更があればコミット
- 変更がなければコミットしない
- workflowの多重実行を防ぐため`concurrency`を設定
- 同じworkflow由来のコミットで再度収集処理が起動しないようにする

想定するGitHub Secrets：

```text
NOTION_API_TOKEN
NOTION_DATABASE_ID
SLACK_WEBHOOK_URL
```

GitHub Actions実行時には、外部Pull RequestからSecretsが利用できない点にも配慮してください。

## 19. 環境変数

`.env.example`を作成してください。

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

`.env`は必ず`.gitignore`へ追加してください。

## 20. README

READMEには以下を含めてください。

1. アプリの目的
2. アーキテクチャ
3. 必要環境
4. ローカルセットアップ
5. Python仮想環境の作成方法
6. 依存関係のインストール
7. Notion Integrationの作成方法
8. Notion DatabaseをIntegrationへ共有する方法
9. 必要なNotionプロパティ一覧
10. Slack Incoming Webhookの準備方法
11. `.env`の設定
12. 通常実行
13. dry-run実行
14. テスト実行
15. ruff実行
16. GitHub Secretsの設定
17. GitHub Actionsの説明
18. 情報源の追加方法
19. キーワードの追加方法
20. スコア調整方法
21. よくあるエラー
22. セキュリティ上の注意
23. 制限事項
24. 今後の拡張案

セットアップコマンド例：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
python -m crypto_radar.main --dry-run
```

## 21. セキュリティ要件

- APIトークンをコードに埋め込まない
- `.env`をコミットしない
- ログへ秘密情報を出さない
- Webhook URLをエラーメッセージへそのまま出さない
- 外部から取得した文字列を信用しない
- Notion・Slackへ送信する文字列長を制限する
- URLスキームは基本的に`http`または`https`のみ許可する
- 設定ファイルのバリデーションを行う
- YAMLの読み込みには安全なローダーを使用する
- HTTPリクエストにはタイムアウトを設定する
- リダイレクト回数を無制限にしない
- User-Agentを明示する

## 22. 実装順序

一度にすべてを雑に実装せず、以下の順序で進めてください。

### Phase 1: 基盤

- `pyproject.toml`
- パッケージ構造
- Pydanticモデル
- YAML設定読み込み
- ログ
- CLI
- README骨格

### Phase 2: 収集

- RSS Collector
- arXiv Collector
- 正規化
- 日付処理
- URL正規化

### Phase 3: 判定

- キーワード分類
- スコアリング
- negative keyword
- dry-run出力

### Phase 4: 状態管理

- fingerprint
- `seen_items.json`
- 重複除去
- atomic write

### Phase 5: 外部出力

- Notion登録
- Slack通知
- 再試行
- エラー処理

### Phase 6: 自動化

- pytest
- ruff
- GitHub Actions test
- GitHub Actions collect
- state fileの自動コミット

各Phaseの終了時にテストを実行し、動作を確認してから次へ進んでください。

## 23. 完了条件

以下を満たしたらMVP完成です。

- `python -m crypto_radar.main --dry-run`が成功する
- 複数RSSから記事を取得できる
- arXivから記事を取得できる
- キーワード分類とスコアリング結果を確認できる
- 同じ記事を2回処理しても重複登録されない
- Notionに記事を登録できる
- 高スコア記事をSlackへ通知できる
- 1つの情報源が失敗しても他は処理される
- Secretsが未設定の場合、明確な警告を出して該当機能だけ無効化できる
- pytestがすべて成功する
- ruffが成功する
- GitHub Actionsで定期実行できる
- READMEのみを読んで別環境にセットアップできる

## 24. Codexへの作業指示

まず現在のリポジトリ内容を確認してください。

既存ファイルがある場合は、理由なく削除または上書きしないでください。

その後、以下を行ってください。

1. 実装計画を簡潔に提示する
2. 不足しているファイルを作成する
3. Phase 1から順番に実装する
4. 各Phaseでテストを実行する
5. エラーがあれば修正する
6. 最後に全テストとruffを実行する
7. 作成・変更したファイルを一覧化する
8. ユーザーが次に行うセットアップ作業を説明する

質問が必要な場合でも、実装を完全に停止しないでください。

合理的なデフォルトを選び、設定ファイルで後から変更可能にしてください。

Notion Database IDやAPIトークンなど、ユーザーしか分からない値にはダミー値を入れず、環境変数として扱ってください。

## 25. 将来拡張のための設計

MVPでは実装しませんが、将来的に次を追加しやすい設計にしてください。

- Notionの`Saved`記事だけをBibTeX化
- 日次Slackダイジェスト
- GitHub PagesまたはNext.jsの閲覧画面
- Google News RSS
- 日本企業のプレスリリース監視
- HTML差分監視
- ローカルLLMによる要約
- 類似記事クラスタリング
- 既読・未読の双方向同期
- Notion上の評価をスコアリングへ反映
- 論文PDFとAbstractの保存
- DOI、arXiv ID、ePrint IDの抽出
- 学会締切情報の監視
- メール通知
- 月次研究トレンド集計

ただし、将来機能のためにMVPを過度に複雑化しないでください。
