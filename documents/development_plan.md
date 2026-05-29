# 日経225 財務指標可視化アプリ 開発計画

## 目的

日経225採用企業を対象に、株価と財務指標を時系列で確認できるWebアプリを開発する。
初期段階では無料または低コストで試作し、データ取得・指標計算・グラフ表示の基本機能を固める。
その後、AWS環境へ移管し、よりリッチなWebアプリとして拡張する。

## 開発方針

最初から大きな構成にせず、ミニマムな構成で動くプロダクトを作る。
MVPではローカル環境または小規模サーバー上で動作するStreamlitアプリとして実装する。
データ取得元はJ-Quants API Freeプランを中心とし、必要に応じてEDINET APIで補完する。

将来的には、データ取得処理、データベース、Web API、フロントエンドを分離し、AWS上で運用できる構成へ移行する。

## 初期技術スタック

| 分類 | 採用技術 | 役割 |
|---|---|---|
| 言語 | Python | データ取得、加工、指標計算、Webアプリ実装 |
| データ取得 | J-Quants API Free | 株価、銘柄情報、財務情報の取得 |
| 補助データ取得 | EDINET API | 有価証券報告書、XBRL、CSVデータの補完取得 |
| Webアプリ | Streamlit | Pythonだけでダッシュボードを構築 |
| グラフ | Plotly | 株価、財務指標のインタラクティブな時系列グラフ |
| データ処理 | pandas | APIレスポンス、CSV、時系列データの加工 |
| 初期DB | SQLite | ローカル開発、MVP用の簡易データ保存 |
| 本格DB候補 | PostgreSQL | AWS移管後の永続データ保存 |

## 初期アプリで扱う主なデータ

### データベースに保存するデータ

アプリの検索、集計、グラフ表示に使う整形済みデータを保存する。

| テーブル名 | 内容 |
|---|---|
| companies | 証券コード、会社名、業種、市場区分、日経225採用フラグ |
| daily_prices | 日付、証券コード、始値、高値、安値、終値、出来高、調整後終値 |
| financial_statements | 決算期、売上高、営業利益、純利益、総資産、自己資本、負債など |
| financial_metrics | 自己資本比率、ROE、ROA、ROI、営業利益率、PER、PBRなど |
| data_fetch_logs | API取得日時、対象データ、成功/失敗、エラー内容 |

### ファイルとして保存するデータ

初期段階ではローカルの `data/` 配下に保存し、AWS移管後はS3へ移す。

| 保存先例 | 内容 |
|---|---|
| data/raw/jquants/ | J-Quants APIから取得したJSON/CSV原本 |
| data/raw/edinet/ | EDINETから取得したZIP、XBRL、CSV原本 |
| data/processed/ | 整形済みの中間CSV/Parquet |
| data/exports/ | ユーザー向けに出力するCSV、Excel、レポート |

## 財務指標

初期段階では以下の指標を優先する。

| 指標 | 計算例 |
|---|---|
| 自己資本比率 | 自己資本 / 総資産 |
| ROE | 当期純利益 / 自己資本 |
| ROA | 当期純利益 / 総資産 |
| ROI | 営業利益 / 投下資本 |
| 営業利益率 | 営業利益 / 売上高 |
| PER | 株価 / EPS |
| PBR | 株価 / BPS |
| 配当利回り | 年間配当 / 株価 |

ROIは定義が複数あるため、アプリ内では採用した計算式を明記する。

## 画面機能

### MVPで実装する画面

- 日経225銘柄一覧
- 銘柄検索
- 企業別の株価時系列グラフ
- 企業別の財務指標時系列グラフ
- 複数企業の比較グラフ
- 財務指標テーブル
- データ最終更新日時の表示

### 将来的に追加する画面

- 業種別比較
- ランキング画面
- 指標スクリーニング
- 財務指標と株価の相関分析
- お気に入り銘柄
- CSV/Excelエクスポート
- ユーザー認証
- ダッシュボード保存

## マイルストーン

### Milestone 1: ローカルMVPの土台作成

目的: まずローカルで動く最小アプリを作る。

- Pythonプロジェクト構成を作成
- 必要ライブラリを整理
- J-Quants API認証設定を追加
- SQLiteの初期スキーマを作成
- 日経225構成銘柄リストをCSVで管理
- Streamlitのトップ画面を作成

完了条件:

- `streamlit run main.py` でアプリが起動する
- 銘柄一覧を画面に表示できる

### Milestone 2: データ取得処理の実装

目的: J-Quants APIから必要なデータを取得し、保存する。

- 銘柄情報取得
- 日次株価取得
- 財務情報取得
- APIレスポンスのraw保存
- SQLiteへの整形済みデータ保存
- 取得ログ保存
- エラー時のリトライ処理

完了条件:

- 任意の銘柄について株価と財務情報を取得できる
- 取得データをDBに保存できる

### Milestone 3: 財務指標計算

目的: 取得した財務データから主要指標を計算する。

- 自己資本比率の計算
- ROE、ROAの計算
- ROIの計算式定義と実装
- 営業利益率の計算
- PER、PBR、配当利回りの計算
- 欠損値、異常値の扱いを整理

完了条件:

- 銘柄ごとに主要財務指標を時系列で保存できる
- 計算式と欠損値ルールがドキュメント化されている

### Milestone 4: Streamlitダッシュボード実装

目的: ユーザーが銘柄を選び、グラフで確認できる画面を作る。

- 銘柄検索UI
- 株価折れ線グラフ
- 財務指標折れ線グラフ
- 複数銘柄比較
- 指標テーブル
- 表示期間フィルター
- 業種フィルター

完了条件:

- 主要指標と株価を画面上で確認できる
- 複数企業を比較できる

### Milestone 5: PostgreSQL対応

目的: ローカルMVPを本格運用しやすいDB構成へ移す。

- SQLiteからPostgreSQLへ移行
- SQLAlchemyなどのDBアクセス層を整理
- マイグレーション管理を導入
- インデックス設計
- 大量データ取得時のパフォーマンス確認

完了条件:

- SQLiteとPostgreSQLのどちらでも動作できる
- PostgreSQLで日経225全銘柄のデータを扱える

### Milestone 6: AWS移管

目的: ローカル環境からAWS上の運用環境へ移す。

- S3バケット作成
- RDS PostgreSQL作成
- Secrets ManagerにAPIキーとDB認証情報を保存
- データ取得バッチをLambdaまたはECS Fargateへ移行
- EventBridge Schedulerで定期実行
- StreamlitアプリをECS Fargateなどへデプロイ
- CloudWatchでログ監視

完了条件:

- AWS上でアプリが起動する
- 定期的にデータ更新できる
- rawデータをS3、整形済みデータをRDSに保存できる

### Milestone 7: リッチなWebアプリ化

目的: Streamlit中心の画面から、より自由度の高いWebアプリへ発展させる。

- FastAPIでバックエンドAPIを構築
- Reactでフロントエンドを構築
- Plotly.jsまたはEChartsでグラフ表示
- 認証機能を追加
- お気に入り銘柄、保存ダッシュボードを実装
- レスポンシブ対応
- UIデザインの改善

完了条件:

- フロントエンドとバックエンドが分離されている
- ユーザーごとの設定保存ができる
- スマートフォン、タブレット、PCで閲覧できる

## AWS移管後の想定構成

```text
J-Quants API / EDINET API
        ↓
EventBridge Scheduler
        ↓
Lambda or ECS Fargate
        ↓
S3 raw data storage
        ↓
RDS PostgreSQL
        ↓
FastAPI
        ↓
React frontend
        ↓
CloudFront
```

## 初期ディレクトリ構成案

```text
stock_visualizer/
  main.py
  requirements.txt
  README.md
  document/
    development_plan.md
  data/
    raw/
    processed/
    exports/
  src/
    api/
    db/
    metrics/
    visualization/
  tests/
```

## 優先順位

1. J-Quants APIでデータ取得できること
2. 株価と財務データを保存できること
3. 自己資本比率、ROE、ROA、ROIを計算できること
4. Streamlitで折れ線グラフを表示できること
5. 日経225全銘柄に対象を広げること
6. PostgreSQLへ移行すること
7. AWSへ移管すること
8. FastAPI + ReactでリッチなWebアプリにすること

## 注意事項

- J-Quants Freeプランは取得できるデータ範囲や更新タイミングに制限がある。
- 日経225構成銘柄リストの自動取得や再配布は利用規約を確認する。
- EDINET APIは無料で利用できるが、XBRLやCSVの解析コストが高い。
- 財務指標は会計基準やデータ項目の差により、企業間比較で注意が必要。
- 投資判断に使う場合は、データ取得元、更新日時、計算式を画面上に明示する。
