"""复现 Olist 数据 2017 年与 2018 年 1—8 月的品类矩阵及核查表。"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "数据"
TABLES = ROOT / "docs" / "tables"
FIGURES = ROOT / "docs" / "figures"
TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

PERIODS = {
    2017: (pd.Timestamp("2017-01-01"), pd.Timestamp("2017-09-01")),
    2018: (pd.Timestamp("2018-01-01"), pd.Timestamp("2018-09-01")),
}
QUADRANTS = ["明星", "金牛", "潜力", "瘦狗"]
COLORS = {"明星": "#147D69", "金牛": "#2D6DA3", "潜力": "#B56B19", "瘦狗": "#A04450"}
# 原始品类翻译表缺少以下两个葡语品类名称。
MANUAL_NAMES = {
    "pc_gamer": "游戏电脑",
    "portateis_cozinha_e_preparadores_de_alimentos": "便携厨房与食品加工电器",
}


def read_sources() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    orders = pd.read_excel(
        DATA / "olist_orders_dataset.xlsx",
        usecols=["order_id", "order_status", "order_purchase_timestamp"],
    )
    items = pd.read_excel(
        DATA / "olist_order_items_dataset.xlsx",
        usecols=["order_id", "order_item_id", "product_id", "price", "freight_value"],
    )
    products = pd.read_excel(
        DATA / "olist_products_dataset.xlsx",
        usecols=["product_id", "product_category_name"],
    )
    translations = pd.read_excel(DATA / "product_category_name_translation.xlsx")
    assert orders.order_id.is_unique and products.product_id.is_unique
    assert not items.duplicated(["order_id", "order_item_id"]).any()
    assert items.price.notna().all() and items.price.gt(0).all()
    assert translations.product_category_name.is_unique
    return orders, items, products, translations


def classify(sales: float, orders: float, sales_base: float, order_base: float) -> str:
    if sales >= sales_base and orders >= order_base:
        return "明星"
    if sales < sales_base and orders >= order_base:
        return "金牛"
    if sales >= sales_base and orders < order_base:
        return "潜力"
    return "瘦狗"


def save_csv(frame: pd.DataFrame, filename: str) -> None:
    frame.to_csv(TABLES / filename, index=False, encoding="utf-8-sig", float_format="%.8f")


def plot_matrix(matrix: pd.DataFrame, sales_base: float, order_base: float) -> None:
    plt.rcParams.update({
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC"],
        "axes.unicode_minus": False,
        "font.size": 9,
        "savefig.dpi": 260,
    })
    fig, ax = plt.subplots(figsize=(7.4, 6.1), facecolor="white")
    fig.subplots_adjust(left=0.13, right=0.97, bottom=0.12, top=0.90)
    x_min, x_max = -1.08, 3.30
    y_min, y_max = -1.08, 3.80
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    visible = matrix[(matrix.sales_growth <= x_max) &
                     (matrix.order_growth <= y_max)].copy()

    # 浅色背景标出四个象限，分界线与点位均使用未经变换的同比数值。
    regions = [
        ("金牛", x_min, sales_base, order_base, y_max),
        ("明星", sales_base, x_max, order_base, y_max),
        ("瘦狗", x_min, sales_base, y_min, order_base),
        ("潜力", sales_base, x_max, y_min, order_base),
    ]
    for name, x0, x1, y0, y1 in regions:
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0,
                               facecolor=COLORS[name], alpha=0.055,
                               edgecolor="none", zorder=0))
    ax.grid(color="#E1E5E7", linewidth=0.65, zorder=1)
    ax.axvline(sales_base, color="#55616B", linewidth=1.1, zorder=2)
    ax.axhline(order_base, color="#55616B", linewidth=1.1, zorder=2)

    max_rev = float(visible.revenue_2018.max())
    for name in QUADRANTS:
        sub = visible[visible.quadrant == name].sort_values("revenue_2018")
        sizes = 25 + 650 * sub.revenue_2018 / max_rev
        ax.scatter(sub.sales_growth, sub.order_growth, s=sizes,
                   facecolor="white", edgecolor=COLORS[name],
                   linewidth=1.3, zorder=3)

    # 大额品类直接在圆圈上标名，其余代表品类用短引线标注。
    inside_names = {"健康美妆": "健康\n美妆", "腕表礼品": "腕表\n礼品",
                    "运动休闲": "运动\n休闲"}
    for name, label in inside_names.items():
        row = visible.loc[visible.category_cn.eq(name)].iloc[0]
        ax.text(row.sales_growth, row.order_growth, label,
                ha="center", va="center", fontsize=8.5, linespacing=0.95,
                fontweight="medium",
                color="#25313A", zorder=6)

    label_positions = {
        "汽车用品": (1.77, 2.82), "母婴用品": (3.02, 1.96),
        "文具": (3.02, 2.96), "电脑及配件": (0.72, 2.08),
        "大众通俗书籍": (0.64, 1.68),
        "家居日用": (2.42, 1.16), "手机通讯": (2.40, 0.79),
        "固定电话": (1.91, -0.34),
        "床品卫浴餐桌用品": (0.28, 1.18),
        "潮流新奇好物": (-0.18, 0.33),
    }
    for name, position in label_positions.items():
        row = visible.loc[visible.category_cn.eq(name)].iloc[0]
        ax.annotate(name, (row.sales_growth, row.order_growth),
                    xytext=position, textcoords="data", ha="center", va="center",
                    fontsize=9.1, color="#28343C", zorder=6,
                    arrowprops={"arrowstyle": "-", "color": "#96A1A7", "lw": 0.65},
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.92, "pad": 1.0})

    x_ticks = [-1, -0.5, 0, 0.5, 1, 1.5, 2, 2.5, 3]
    y_ticks = [-1, -0.5, 0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5]
    ax.set_xticks(x_ticks, [f"{v:.0%}" for v in x_ticks], fontsize=8.7)
    ax.set_yticks(y_ticks, [f"{v:.0%}" for v in y_ticks], fontsize=8.7)
    ax.set_xlabel("销售额同比增长率", fontsize=10.5, labelpad=8)
    ax.set_ylabel("订单量同比增长率", fontsize=10.5, labelpad=8)
    ax.set_title("二级品类经营矩阵", fontsize=13, fontweight="bold", pad=13)
    for spine in ax.spines.values():
        spine.set_color("#87939A")
        spine.set_linewidth(0.75)

    positions = {"金牛": (0.04, 0.94, "left"), "明星": (0.96, 0.94, "right"),
                 "瘦狗": (0.52, 0.04, "right"), "潜力": (0.96, 0.05, "right")}
    for name, (x, y, align) in positions.items():
        title = f"{name}品类"
        ax.text(x, y, title, transform=ax.transAxes,
                ha=align, va="top" if y > 0.5 else "bottom",
                fontsize=11, fontweight="bold", color=COLORS[name], zorder=5,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 2})
    ax.text(sales_base, 0.99, f"销售额基准 {sales_base:+.1%}",
            transform=ax.get_xaxis_transform(), ha="center", va="top",
            fontsize=8.5, color="#4D5962", zorder=5,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.9, "pad": 1.5})
    ax.text(0.985, order_base, f"订单量基准 {order_base:+.1%}",
            transform=ax.get_yaxis_transform(), ha="right", va="bottom",
            fontsize=8.5, color="#4D5962", zorder=5,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.9, "pad": 1.5})

    fig.savefig(FIGURES / "matrix.png", facecolor="white")
    plt.close(fig)


def main() -> None:
    orders, items, products, translations = read_sources()
    known_names = translations.set_index("product_category_name").iloc[:, 1].to_dict()
    known_names.update(MANUAL_NAMES)
    missing_translation = set(products.product_category_name.dropna()) - set(known_names)
    assert not missing_translation, f"Missing translations: {missing_translation}"

    eligible_status = {"delivered", "shipped", "invoiced", "processing", "approved"}
    eligible = orders.loc[orders.order_status.isin(eligible_status),
                          ["order_id", "order_purchase_timestamp"]].copy()
    data = items.merge(eligible, on="order_id", how="inner", validate="many_to_one")
    data = data.merge(products, on="product_id", how="left", validate="many_to_one",
                      indicator=True)
    assert data["_merge"].eq("both").all(), "Some order items have no product record"
    data = data.drop(columns="_merge")
    data["category_cn"] = data.product_category_name.map(known_names)
    assert data.loc[data.product_category_name.notna(), "category_cn"].notna().all()

    period_data = {}
    quality_rows = []
    year_tables = []
    for year, (start, end) in PERIODS.items():
        all_items = data.loc[data.order_purchase_timestamp.ge(start)
                             & data.order_purchase_timestamp.lt(end)].copy()
        named = all_items.loc[all_items.product_category_name.notna()].copy()
        period_data[year] = named
        year_tables.append(
            named.groupby(["product_category_name", "category_cn"], as_index=False)
            .agg(revenue=("price", "sum"), orders=("order_id", "nunique"),
                 items=("price", "size")).assign(year=year)
        )
        quality_rows.append({
            "year": year,
            "eligible_orders_with_items": int(all_items.order_id.nunique()),
            "all_item_rows": len(all_items),
            "missing_category_item_rows": int(all_items.product_category_name.isna().sum()),
            "missing_category_revenue": float(all_items.loc[all_items.product_category_name.isna(), "price"].sum()),
            "missing_category_revenue_share": float(
                all_items.loc[all_items.product_category_name.isna(), "price"].sum()
                / all_items.price.sum()
            ),
            "classified_orders": int(named.order_id.nunique()),
            "classified_revenue": float(named.price.sum()),
            "classified_item_rows": len(named),
        })

    quality = pd.DataFrame(quality_rows)
    save_csv(quality, "data_quality.csv")
    grouped = pd.concat(year_tables, ignore_index=True)
    a = grouped.loc[grouped.year.eq(2017)].drop(columns="year").rename(
        columns={"revenue": "revenue_2017", "orders": "orders_2017", "items": "items_2017"})
    b = grouped.loc[grouped.year.eq(2018)].drop(columns="year").rename(
        columns={"revenue": "revenue_2018", "orders": "orders_2018", "items": "items_2018"})
    full = a.merge(b, on=["product_category_name", "category_cn"], how="outer",
                   validate="one_to_one")
    full["lifecycle"] = np.select(
        [full.revenue_2017.isna(), full.revenue_2018.isna()],
        ["2018新增", "2018退出"], default="两期动销",
    )
    for col in ("revenue_2017", "revenue_2018", "orders_2017", "orders_2018",
                "items_2017", "items_2018"):
        full[col] = full[col].fillna(0)
    matrix = full.loc[full.lifecycle.eq("两期动销")].copy()
    matrix["sales_growth"] = matrix.revenue_2018 / matrix.revenue_2017 - 1
    matrix["order_growth"] = matrix.orders_2018 / matrix.orders_2017 - 1
    matrix["revenue_per_category_order_growth"] = (
        (matrix.revenue_2018 / matrix.orders_2018)
        / (matrix.revenue_2017 / matrix.orders_2017) - 1
    )
    sales_base = (quality.loc[quality.year.eq(2018), "classified_revenue"].iloc[0]
                  / quality.loc[quality.year.eq(2017), "classified_revenue"].iloc[0] - 1)
    order_base = (quality.loc[quality.year.eq(2018), "classified_orders"].iloc[0]
                  / quality.loc[quality.year.eq(2017), "classified_orders"].iloc[0] - 1)
    matrix["quadrant"] = [
        classify(s, o, sales_base, order_base)
        for s, o in zip(matrix.sales_growth, matrix.order_growth)
    ]
    matrix["small_base"] = matrix.orders_2017.lt(30)
    full = full.merge(matrix[["product_category_name", "sales_growth", "order_growth",
                              "revenue_per_category_order_growth", "quadrant",
                              "small_base"]], on="product_category_name", how="left",
                      validate="one_to_one")
    full = full.sort_values(["lifecycle", "revenue_2018"], ascending=[True, False])
    save_csv(full, "category_metrics.csv")

    summary = (
        matrix.groupby("quadrant").agg(
            categories=("product_category_name", "size"),
            revenue_2017=("revenue_2017", "sum"),
            revenue_2018=("revenue_2018", "sum"),
            category_orders_2017=("orders_2017", "sum"),
            category_orders_2018=("orders_2018", "sum"),
            small_base_categories=("small_base", "sum"),
        ).reindex(QUADRANTS).reset_index()
    )
    summary["revenue_growth"] = summary.revenue_2018 / summary.revenue_2017 - 1
    summary["category_order_growth"] = (
        summary.category_orders_2018 / summary.category_orders_2017 - 1)
    summary["revenue_share_of_classified_2018"] = (
        summary.revenue_2018 / quality.loc[quality.year.eq(2018), "classified_revenue"].iloc[0])
    save_csv(summary, "quadrant_summary.csv")

    assert len(matrix) == 69 and full.lifecycle.eq("2018新增").sum() == 3
    assert full.lifecycle.eq("2018退出").sum() == 1
    assert summary.categories.sum() == len(matrix)
    assert np.isclose(full.revenue_2017.sum(), quality.loc[quality.year.eq(2017), "classified_revenue"].iloc[0])
    assert np.isclose(full.revenue_2018.sum(), quality.loc[quality.year.eq(2018), "classified_revenue"].iloc[0])
    assert np.isclose(summary.revenue_2018.sum(), matrix.revenue_2018.sum())
    assert np.allclose(
        1 + matrix.sales_growth,
        (1 + matrix.order_growth) * (1 + matrix.revenue_per_category_order_growth),
    )

    # 2018 年 8 月部分订单在数据截止时尚未送达，另以“仅已送达”订单复算分类。
    delivered_ids = set(orders.loc[orders.order_status.eq("delivered"), "order_id"])
    completed = data.loc[data.order_id.isin(delivered_ids)
                         & data.product_category_name.notna()].copy()
    completed_years = []
    completed_totals = {}
    for year, (start, end) in PERIODS.items():
        part = completed.loc[completed.order_purchase_timestamp.ge(start)
                             & completed.order_purchase_timestamp.lt(end)]
        completed_totals[year] = (part.price.sum(), part.order_id.nunique())
        completed_years.append(
            part.groupby("product_category_name", as_index=False).agg(
                revenue=("price", "sum"), orders=("order_id", "nunique")
            ).assign(year=year)
        )
    d17, d18 = completed_years
    dcompare = d17.drop(columns="year").merge(
        d18.drop(columns="year"), on="product_category_name",
        suffixes=("_2017", "_2018"), validate="one_to_one"
    )
    d_sales_base = completed_totals[2018][0] / completed_totals[2017][0] - 1
    d_order_base = completed_totals[2018][1] / completed_totals[2017][1] - 1
    dcompare["delivered_quadrant"] = [
        classify(r.revenue_2018 / r.revenue_2017 - 1,
                 r.orders_2018 / r.orders_2017 - 1, d_sales_base, d_order_base)
        for r in dcompare.itertuples()
    ]
    sensitivity = matrix[["product_category_name", "category_cn", "quadrant"]].merge(
        dcompare[["product_category_name", "delivered_quadrant"]],
        on="product_category_name", validate="one_to_one"
    )
    sensitivity["same_quadrant"] = sensitivity.quadrant.eq(sensitivity.delivered_quadrant)
    save_csv(sensitivity, "status_sensitivity.csv")

    plot_matrix(matrix, float(sales_base), float(order_base))
    payload = {
        "definition": "Noncancelled active orders, Jan-Aug purchase timestamp, item price excluding freight, nonmissing category",
        "base_sales_growth": float(sales_base),
        "base_order_growth": float(order_base),
        "classifiable_categories_2017": len(a),
        "classifiable_categories_2018": len(b),
        "common_categories": len(matrix),
        "new_categories": int(full.lifecycle.eq("2018新增").sum()),
        "exited_categories": int(full.lifecycle.eq("2018退出").sum()),
        "small_base_categories": int(matrix.small_base.sum()),
        "zero_line_double_positive": int(((matrix.sales_growth >= 0) & (matrix.order_growth >= 0)).sum()),
        "delivered_only_sensitivity": {
            "sales_base": float(d_sales_base),
            "order_base": float(d_order_base),
            "same_quadrant": int(sensitivity.same_quadrant.sum()),
            "total_categories": len(sensitivity),
        },
        "quadrants": {
            row.quadrant: {
                "categories": int(row.categories),
                "revenue_2018": float(row.revenue_2018),
                "revenue_growth": float(row.revenue_growth),
                "category_order_growth": float(row.category_order_growth),
                "revenue_share_of_classified_2018": float(row.revenue_share_of_classified_2018),
            }
            for row in summary.itertuples()
        },
    }
    (TABLES / "analysis_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("\nQUADRANTS\n", summary.to_string(index=False))
    print("\nTOP CATEGORIES\n", matrix.nlargest(15, "revenue_2018")[
        ["category_cn", "quadrant", "revenue_2017", "revenue_2018",
         "orders_2017", "orders_2018", "sales_growth", "order_growth"]
    ].to_string(index=False))


if __name__ == "__main__":
    main()
