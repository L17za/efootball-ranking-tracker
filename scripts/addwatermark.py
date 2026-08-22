import matplotlib.pyplot as plt

def add_watermark(
    ax=None, 
    text="＠L17za", 
    fontsize=40, 
    color='gray', 
    alpha=0.15, 
    rotation=30, 
    ha='center', 
    va='center'
):
    """
    MatplotlibのAxesに対して透かし（ウォーターマーク）を追加する関数
    """
    if ax is None:
        ax = plt.gca()
        
    # グラフの中央（0.5, 0.5）に大きな斜め文字を表示
    ax.text(
        0.5, 0.5, text,
        transform=ax.transAxes,
        fontsize=fontsize,
        color=color,
        alpha=alpha,
        rotation=rotation,
        ha=ha,
        va=va,
        fontweight='bold',
        zorder=10  # グラフ要素の上に載せる場合は高めの値を設定
    )