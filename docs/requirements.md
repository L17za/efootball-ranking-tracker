## efootball-ranking-tracker 要件定義

**概要:**
- 本プロジェクトは既存の `efootball-ranking-tracker` のロジックをベースに、ウェブアプリ化を行う。
- ランキングイベントのレート、順位等の大規模データを、専用入力画面で入力しやすくすることで、データ収集の効率化を図る。
- バックエンドで勝ち点・順位・時刻などの時刻における順位データを管理し、フロントエンドでデータ入力（単票・一括）、および時系列グラフを表示する。
- ユーザーは、その時点での 勝ち点と順位のグラフを確認することで、目標の順位になるためにはどの程度の勝ち点が必要か推測できるものとする。

**目的:**
- 管理者やアナリストがチーム別の勝ち点・順位の推移を容易に入力・確認できるようにする。
- CSVやコピペによる一括投入で既存データを素早く取り込める。

**主要ユーザーストーリー:**
- ユーザーは、フォームで順位データを登録できる。
    - 順位データの内容
        - 日付 yyyymmddhhmm
        - 勝ち点/レート
        - 順位
        - 入力したユーザー
- ユーザーはCSVを作成し、テキスト領域に貼り付けて複数行を一括登録できる。
- ユーザーは、ランキングイベント全体を俯瞰した勝ち点・順位の時系列グラフを閲覧できる。

**機能要件（高レベル）:**
- FR1: 単票データ入力画面
  - 入力項目: 日付時刻、勝ち点、順位
  - バリデーション: 日付形式、数値範囲（勝ち点>=0、順位>=1）
- FR2: 一括貼付け（CSVコピペ）画面
  - テキストボックスにCSV（またはTSV）を貼り付けて解析、プレビュー表示、誤り行の検出、インポート
  - パースはヘッダ有無に対応、カラムマッピングUIを提供
- FR3: グラフ表示画面
  - 勝ち点および順位の時系列線グラフを表示（同一画面で切替）
- FR4: API（バックエンド）
  - エンドポイント: 登録（POST /api/entries）、取得（GET /api/entries）、バルク登録（POST /api/entries/bulk）、削除/更新
  - 集計API: チーム別時系列取得（GET /api/teams/:id/series）
- FR5: 認証・認可
  - 最低限の管理者認証（Supabase Authを想定）。公開閲覧のみなら匿名アクセスを許可するオプション

**非機能要件:**
- NFR1: データ永続化はSupabase（Postgres）を採用
- NFR2: デプロイはVercel（Next.js）を想定、CIはGitHub Actions
- NFR3: レスポンス性能: 単一エンドポイントの取得は<500ms目標（小規模データ）
- NFR4: セキュリティ: SQLインジェクション防止、認証済みAPIのみ編集を許可

**データモデル（匿名スナップショット / イベント中心）:**
- 概要: プレイヤー識別子を収集しない運用を前提に、イベント単位での"時刻付きスナップショット"を保持する。個別プレイヤーを追跡しないため、観測は匿名のまま保持し、しきい値解析や勝ち点分布（同勝ち点の人数・増減速度）を主に扱う。
- `events`（イベントマスタ）
  - id (uuid, pk)
  - name (text)
  - reward_line_rank (integer) — 例: 500000（イベント固有の報酬獲得ライン）
  - start_at (timestamp)
  - end_at (timestamp)
  - metadata (jsonb)
  - created_at
- `imports`（バルク取込メタ）
  - id (uuid, pk)
  - event_id (uuid, fk -> events.id)
  - source (text: scrape/upload/manual)
  - file_name (text)
  - uploader (text/null)
  - raw_text (text)
  - status (text)
  - created_at
- `observations`（匿名スナップショットの各行）
  - id (uuid, pk)
  - event_id (uuid, fk -> events.id)
  - import_id (uuid, fk -> imports.id, nullable)
  - observed_at (timestamp)
  - points (integer)
  - rank (integer)
  - raw_row (jsonb/text) — 元データ保存
  - source (text)
  - created_at

インデックス案:
- `(event_id, observed_at)` — イベント内で時系列取得を高速化
- `(observed_at, rank)` — 全体しきい値集計を効率化

運用上の方針:
- プレイヤーIDは収集しない（匿名スナップショット）。
- 同一時刻・同一勝ち点・同一順位の重複観測はすべて保持する（履歴保持）。
- しきい値はイベントごとに異なるため `events.reward_line_rank` を基に可変に扱う。

注: 将来的に個別プレイヤーを扱う予定が出た場合は、`participants` テーブルと `observations.participant_id` を追加する拡張を検討する。

**API設計（例・イベント/匿名スナップショット前提）:**
- POST /api/events
  - ボディ: `{ name, reward_line_rank, start_at, end_at }` → イベント作成
- GET /api/events
  - イベント一覧
- POST /api/imports
  - ボディ: `{ event_id, source, raw_text }` → TSV/CSVの一括取り込み（サーバ側でパース・observations登録）
- POST /api/observations
  - 単票登録（manual or scrape）: `{ event_id, observed_at, points, rank, source }`
- GET /api/observations?event_id=&from=&to=&aggregate=... 
  - event_id 指定で時系列取得。`aggregate=count_by_points` 等のオプションで、勝ち点ごとのカウントや分布を返す。
- GET /api/thresholds?event_id=&rank=
  - 指定rank（例: 500000）に入るための必要勝ち点の時系列を返す（オンザフライ or キャッシュ）

備考:
- `POST /api/imports` はファイルの生データを受け取り、`imports` を作成→非同期でパース＆`observations` を登録するワークフローが望ましい。
- フロントエンドではイベント選択 UI を設け、イベント毎の報酬ライン（`reward_line_rank`）に基づくしきい値表示を可能にする。

**フロントエンド画面:**
- 画面A: ダッシュボード（チーム一覧、最近の更新、グラフへのショートカット）
- 画面B: 単票入力フォーム（新規/編集）
- 画面C: 一括貼付けインポート（テキスト領域、プレビュー、マッピング、インポートボタン）
- 画面D: グラフ表示（チーム選択、期間選択、複数チーム比較、ツールチップ）

推奨UIライブラリ: Next.js（App Router or Pages Router）、UI：Tailwind CSS or Chakra UI
推奨チャート: Chart.js (react-chartjs-2) または ApexCharts
CSVパース: PapaParse

**技術スタック案:**
- フロントエンド: Next.js（React）
- バックエンド: Next.js API Routes or Edge Functions（Vercel上で動作）
- データベース/認証: Supabase (Postgres + Auth)
- デプロイ: Vercel（Next.js、環境変数でSupabase接続情報）

**受け入れ基準 / マイルストーン（最小実装 MVP）:**
1. Supabase に `teams` と `entries` を作成し、APIからデータ登録と取得ができる
2. 単票入力フォームから登録できる
3. 一括貼付けでCSVを解析して登録できる（簡易マッピングで可）
4. チーム別の時系列グラフが表示できる

**運用・拡張案:**
- 定期インポート（外部CSVの自動取り込み）
- ユーザー・権限管理（複数の編集者、ロール）
- データ差分表示（同一日に複数観測がある場合の扱い）

**前提・保留事項（要確認）:**
- データの粒度: 1試合毎か、日次/週次の順位スナップショットか
- 誰が閲覧可能か（公開 or 認証必要）
- 既存ロジックのどの部分をAPIに持ち込むか（計算ロジックの移譲）

**TSV解析 / しきい値解析（ローカルスクリプト）:**
- 概要: 既存の `data/Jイベレート変動.tsv` のような時刻付きスナップショットから、"指定した順位以内に入るために必要な勝ち点"（しきい値）を時系列で算出する機能を要件に含める。
- 入力: TSV/CSV（カラム: `日付`, `時刻`, `勝ち点`, `順位`）
- 出力: 時系列 CSV (`datetime`, `threshold_points`, `count_leq`) とオプションでグラフ画像
- オプション機能:
  - 年指定（TSVの`日付`に年情報が無い場合の補完）
  - 解析対象の順位をパラメータ化（例: 1000000, 400000, 100000）
  - 欠損値・パースエラーのログ出力
  - プロット時の y 軸反転オプション（視覚化で順位の小さい方を上に表示したい場合）
- 利用用途: ウェブアプリのバックエンドで定期に実行するバッチ、またはユーザーがアップロードした履歴データの解析エンドポイントの基礎となる。

**フロントエンド上での反映（要件補足・匿名スナップショット）:**
- グラフ表示画面では以下を必須で提供する:
  - イベント選択（`events`）
  - 指定順位（例: 500000, 400000, 100000）に対するしきい値時系列ライン
  - 勝ち点ごとのカウント分布（その時刻に勝ち点が X のユーザーが何人いたか）を時間経過で表示
  - 同勝ち点ユーザーの"増減速度"（例: 直近 N 分でのカウント差分）を簡易的に可視化（線グラフやバーチャートで）
- 匿名性が前提のため、個別プレイヤートラッキングUIは不要。ただし、ユーザーが自分のアップロードデータを紐付けて確認する機能は将来的に追加可能。

---


---
次のステップ提案:
1. 上記要件をレビューして承認をもらう
2. Supabase スキーマ（DDL）を作成して実装
3. Next.js プロジェクトをスキャフォールドして最小機能（単票登録、取得、グラフ）を実装
