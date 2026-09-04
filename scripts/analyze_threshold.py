import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def parse_args():
    p = argparse.ArgumentParser(description='Analyze points threshold for target rank from TSV')
    p.add_argument('--tsv', default=str(DATA_DIR / 'Jイベレート変動.tsv'))
    p.add_argument('--year', type=int, default=datetime.now().year)
    p.add_argument('--target-rank', type=int, default=1000000, help='Target rank (e.g. 1000000)')
    p.add_argument('--out', default=None, help='CSV output path')
    p.add_argument('--plot', action='store_true', help='Save simple plot of threshold over time')
    return p.parse_args()


def make_dt(row, year):
    try:
        m, d = map(int, str(row['日付']).split('/'))
        h, mi = map(int, str(row['時刻']).split(':'))
        return datetime(year, m, d, h, mi)
    except Exception:
        return None


def compute_threshold(df, target_rank):
    # group by datetime and compute highest points among rows with rank <= target_rank
    rows = []
    for dt, g in df.groupby('datetime'):
        leq = g[g['順位'] <= target_rank]
        if leq.empty:
            threshold = None
            count = 0
        else:
            threshold = int(leq['勝ち点'].max())
            count = int(len(leq))
        rows.append({'datetime': dt, 'threshold_points': threshold, 'count_leq': count})
    out = pd.DataFrame(rows).sort_values('datetime').reset_index(drop=True)
    return out


def main():
    args = parse_args()
    tsv_path = Path(args.tsv)
    if not tsv_path.exists():
        print('TSV not found:', tsv_path)
        return

    df = pd.read_csv(tsv_path, sep='\t')
    expected_cols = ['日付', '時刻', '勝ち点', '順位']
    if not all(c in df.columns for c in expected_cols):
        print('TSV columns missing. Found:', df.columns.tolist())
        return

    df = df[expected_cols].copy()
    df['datetime'] = df.apply(lambda r: make_dt(r, args.year), axis=1)
    df = df.dropna(subset=['datetime']).sort_values('datetime').reset_index(drop=True)

    # Ensure numeric
    df['勝ち点'] = pd.to_numeric(df['勝ち点'], errors='coerce')
    df['順位'] = pd.to_numeric(df['順位'], errors='coerce')
    df = df.dropna(subset=['勝ち点', '順位'])

    out = compute_threshold(df, args.target_rank)

    out_path = Path(args.out) if args.out else OUTPUT_DIR / f'threshold_{args.target_rank}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    out.to_csv(out_path, index=False)
    print('Threshold CSV written to', out_path)

    if args.plot:
        try:
            import matplotlib.pyplot as plt
            plt.figure(figsize=(10,4))
            plt.plot(out['datetime'], out['threshold_points'], marker='o')
            plt.title(f'Points threshold for rank <= {args.target_rank}')
            plt.xlabel('datetime')
            plt.ylabel('points')
            plt.grid(True)
            png = OUTPUT_DIR / f'threshold_plot_{args.target_rank}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
            plt.tight_layout()
            plt.savefig(png, dpi=150)
            print('Plot saved to', png)
        except Exception as e:
            print('Plot failed:', e)


if __name__ == '__main__':
    main()
