import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 透かしモジュールを同じフォルダから読み込み
from addwatermark import add_watermark

# ==========================================
# パス設定（GitHub Actions対応）
# ==========================================
BASE_DIR = Path(__file__).resolve().parent.parent   # リポジトリルート
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

TSV_PATH = DATA_DIR / "Jイベレート変動.tsv"

# ==========================================
# 時刻設定（JSTのnaive datetimeとして扱う）
# ==========================================
JST = timezone(timedelta(hours=9))   # now() を取るときだけ使用

# すべて timezone を付けない（naive）で統一
PLOT_START_TIME = datetime(2026, 8, 21, 11, 0)
PLOT_END_TIME   = datetime(2026, 8, 24, 10, 55)
CURRENT_TIME    = datetime.now(JST).replace(tzinfo=None)   # ← 重要：naiveにする

print(f"TSVを読み込みます: {TSV_PATH}")
df = pd.read_csv(TSV_PATH, sep='\t')
df.columns = ['日付', '時間', '勝ち点', '順位']

def make_dt(row):
    try:
        m, d = map(int, str(row['日付']).split('/'))
        h, mi = map(int, str(row['時間']).split(':'))
        # timezone を付けない（naive）
        return datetime(2026, m, d, h, mi)
    except:
        return None

df['datetime'] = df.apply(make_dt, axis=1)
df = df.dropna(subset=['datetime']).sort_values('datetime').reset_index(drop=True)

# ==========================================
# 頻出レート抽出
# ==========================================
top_n = 10
frequent_rates = df['勝ち点'].value_counts().head(top_n).index.tolist()
ordered_rates = sorted(frequent_rates)

print(f"頻出レート Top {top_n}: {frequent_rates}")

all_frequent_df = df[df['勝ち点'].isin(frequent_rates)]
overall_start_dt = all_frequent_df['datetime'].min()
overall_end_dt   = all_frequent_df['datetime'].max()

plot_span_df = df[
    (df['datetime'] >= overall_start_dt) &
    (df['datetime'] <= overall_end_dt) &
    (df['datetime'] <= PLOT_END_TIME)
].copy()

# ==========================================
# グラフ描画
# ==========================================
plt.figure(figsize=(14, 8))

# フォント設定（GitHub Actions用に Noto Sans CJK を優先）
plt.rcParams['font.family'] = [
    'Noto Sans CJK JP',
    'Yu Gothic',
    'Meiryo',
    'MS Gothic',
    'Hiragino Sans',
    'DejaVu Sans'
]

colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b',
          '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

latest_summary_lines = ["【各系列の最新データ】"]
latest_rows = []

for idx, rate in enumerate(ordered_rates):
    c = colors[idx % len(colors)]
    rate_df = plot_span_df[plot_span_df['勝ち点'] == rate]
    if rate_df.empty:
        continue

    plt.plot(
        rate_df['datetime'],
        rate_df['順位'],
        marker='o',
        linestyle='-',
        linewidth=1.5,
        markersize=5,
        color=c,
        label=f'勝ち点 {rate} (件数: {len(rate_df)})'
    )

    last_row = rate_df.iloc[-1]
    latest_rows.append({
        'rate': rate,
        'dt': last_row['datetime'],
        'rank': last_row['順位'],
    })

latest_rows = sorted(latest_rows, key=lambda x: x['rate'])
for row in latest_rows:
    latest_summary_lines.append(
        f"・勝ち点 {row['rate']} : 時刻 {row['dt'].strftime('%m/%d %H:%M')} / 順位 {row['rank']:,.0f}位"
    )

ax = plt.gca()

# サマリー注釈
summary_text = "\n".join(latest_summary_lines)
plt.annotate(
    summary_text,
    xy=(0.02, 0.95),
    xycoords='axes fraction',
    fontsize=10,
    verticalalignment='top',
    bbox=dict(boxstyle='round,pad=0.6', facecolor='white', edgecolor='#666666', alpha=0.9)
)

# 40万位ライン
ax.axhline(y=400000, color='crimson', linestyle='--', linewidth=1.8, label='目標 40万位ボーダー')

# 現在時刻ライン
if PLOT_START_TIME <= CURRENT_TIME <= PLOT_END_TIME:
    ax.axvline(
        x=CURRENT_TIME,
        color='darkslategray',
        linestyle=':',
        linewidth=1.6,
        alpha=0.8,
        label=f'現在時刻 {CURRENT_TIME.strftime("%m/%d %H:%M")}'
    )

min_rank = plot_span_df['順位'].min()
ax.set_ylim(bottom=min_rank * 0.9, top=420000)
ax.set_xlim(PLOT_START_TIME, PLOT_END_TIME)

ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
plt.xticks(rotation=45)
ax.yaxis.set_major_formatter('{x:,.0f}')

plt.title(
    f'頻出勝ち点における順位推移（40万位ボーダー基準）',
    fontsize=13,
    fontweight='bold',
    pad=15
)
plt.xlabel('日時')
plt.ylabel('順位 (上が40万位ボーダーに接近)')
plt.grid(True, linestyle='--', alpha=0.6)
plt.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))

# 透かしを追加
add_watermark(
    ax=ax,
    text="＠L17za",
    fontsize=50,
    color='gray',
    alpha=0.15,
    rotation=25
)

plt.tight_layout()

# ==========================================
# 保存（plt.show() は書かない）
# ==========================================
output_png = OUTPUT_DIR / f"frequent_rates_{datetime.now(JST).strftime('%Y%m%d_%H%M%S')}.png"
plt.savefig(output_png, dpi=300, bbox_inches='tight')
print(f"グラフを保存しました: {output_png}")