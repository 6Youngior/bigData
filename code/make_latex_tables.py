"""根据已核对的分析结果生成报告表格与附录。"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "docs" / "tables"
LATEX = TABLES / "latex"
LATEX.mkdir(parents=True, exist_ok=True)


def percent(value: float) -> str:
    return f"{value:+.1%}".replace("%", r"\%")


def amount(value: float) -> str:
    return f"{value / 10000:.1f}"


def command(name: str, value: str) -> str:
    return rf"\newcommand{{\{name}}}{{{value}}}"


def main() -> None:
    quality = pd.read_csv(TABLES / "data_quality.csv").set_index("year")
    categories = pd.read_csv(TABLES / "category_metrics.csv")
    quadrants = pd.read_csv(TABLES / "quadrant_summary.csv").set_index("quadrant")
    comparable = categories[categories.lifecycle.eq("两期动销")]
    q17, q18 = quality.loc[2017], quality.loc[2018]
    values = {
        "SalesSeventeen": amount(q17.classified_revenue),
        "SalesEighteen": amount(q18.classified_revenue),
        "OrdersSeventeen": f"{int(q17.classified_orders):,}",
        "OrdersEighteen": f"{int(q18.classified_orders):,}",
        "SalesGrowth": percent(q18.classified_revenue / q17.classified_revenue - 1),
        "OrderGrowth": percent(q18.classified_orders / q17.classified_orders - 1),
        "AverageGrowth": percent(
            (q18.classified_revenue / q18.classified_orders)
            / (q17.classified_revenue / q17.classified_orders) - 1
        ),
        "MissingShareSeventeen": percent(q17.missing_category_revenue_share).lstrip("+"),
        "MissingShareEighteen": percent(q18.missing_category_revenue_share).lstrip("+"),
        "SmallBaseShare": percent(
            comparable.loc[comparable.small_base.eq(True), "revenue_2018"].sum()
            / q18.classified_revenue
        ).lstrip("+"),
        "CommonRevenueShare": percent(comparable.revenue_2018.sum() / q18.classified_revenue).lstrip("+"),
        "StarIncrementShare": percent(
            (quadrants.loc["明星", "revenue_2018"] - quadrants.loc["明星", "revenue_2017"])
            / (comparable.revenue_2018.sum() - comparable.revenue_2017.sum())
        ).lstrip("+"),
    }
    for name, key in [("Star", "明星"), ("Cow", "金牛"), ("Potential", "潜力"), ("Dog", "瘦狗")]:
        row = quadrants.loc[key]
        values[name + "Count"] = str(int(row.categories))
        values[name + "Sales"] = amount(row.revenue_2018)
        values[name + "Share"] = percent(row.revenue_share_of_classified_2018).lstrip("+")
        values[name + "SalesGrowth"] = percent(row.revenue_growth)
        values[name + "OrderGrowth"] = percent(row.category_order_growth)
    (LATEX / "report_values.tex").write_text(
        "\n".join(command(k, v) for k, v in values.items()) + "\n", encoding="utf-8"
    )

    rows = []
    for key in ("明星", "金牛", "潜力", "瘦狗"):
        row = quadrants.loc[key]
        rows.append(
            f"{key} & {int(row.categories)} & {amount(row.revenue_2018)} & "
            f"{percent(row.revenue_share_of_classified_2018).lstrip('+')} & "
            f"{percent(row.revenue_growth)} & {percent(row.category_order_growth)} & "
            f"{int(row.small_base_categories)} " + r"\\"
        )
    (LATEX / "report_quadrants.tex").write_text(
        "\n".join(rows) + "\n" + r"\bottomrule" + "\n", encoding="utf-8"
    )

    named_examples = (
        "beleza_saude", "relogios_presentes",
        "informatica_acessorios", "artes",
        "utilidades_domesticas", "telefonia",
        "cama_mesa_banho", "cool_stuff",
    )
    rows = []
    for name in named_examples:
        row = comparable.loc[comparable.product_category_name.eq(name)].iloc[0]
        note = r"\textsuperscript{*}" if row.small_base else ""
        rows.append(
            f"{row.quadrant} & {row.category_cn}{note} & "
            f"{amount(row.revenue_2018)} & {percent(row.sales_growth)} & "
            f"{percent(row.order_growth)} & {int(row.orders_2017):,} " + r"\\"
        )
    (LATEX / "report_examples.tex").write_text(
        "\n".join(rows) + "\n" + r"\bottomrule" + "\n", encoding="utf-8"
    )

    audit_rows = [
        ("有效订单数", "eligible_orders_with_items", False),
        ("商品明细行数", "all_item_rows", False),
        ("缺失品类明细行数", "missing_category_item_rows", False),
        ("有品类信息订单数", "classified_orders", False),
        ("有品类信息商品金额／万 BRL", "classified_revenue", True),
    ]
    rows = []
    for label, field, as_amount in audit_rows:
        fmt = amount if as_amount else lambda value: f"{int(value):,}"
        rows.append(f"{label} & {fmt(q17[field])} & {fmt(q18[field])} " + r"\\")
    (LATEX / "report_audit.tex").write_text(
        "\n".join(rows) + "\n" + r"\bottomrule" + "\n", encoding="utf-8"
    )

    rows = []
    for row in categories.loc[~categories.lifecycle.eq("两期动销")].itertuples():
        rows.append(
            f"{row.lifecycle} & {row.category_cn} & {row.revenue_2017:,.0f} & "
            f"{row.revenue_2018:,.0f} & {int(row.orders_2017)} & "
            f"{int(row.orders_2018)} " + r"\\"
        )
    (LATEX / "report_new_exit.tex").write_text(
        "\n".join(rows) + "\n" + r"\bottomrule" + "\n", encoding="utf-8"
    )

    ordering = {"明星": 0, "金牛": 1, "潜力": 2, "瘦狗": 3}
    appendix = comparable.assign(_rank=comparable.quadrant.map(ordering)).sort_values(
        ["_rank", "revenue_2018"], ascending=[True, False]
    )
    lines = [
        r"\begin{longtable}{lp{5.5cm}rrrr}",
        r"\caption{69 个品类的销售额和订单同比}\label{tab:all-categories}\\",
        r"\toprule",
        r"象限 & 品类 & 2017 订单 & 2018 金额／BRL & 销售同比 & 订单同比 \\",
        r"\midrule",
        r"\endfirsthead",
        r"\multicolumn{6}{l}{表 \thetable\ （续）}\\",
        r"\toprule",
        r"象限 & 品类 & 2017 订单 & 2018 金额／BRL & 销售同比 & 订单同比 \\",
        r"\midrule",
        r"\endhead",
    ]
    previous = None
    for row in appendix.itertuples():
        if previous is not None and row.quadrant != previous:
            lines.append(r"\midrule")
        note = r"\textsuperscript{*}" if row.small_base else ""
        category_name = row.category_cn.replace("&", r"\&").replace("%", r"\%")
        lines.append(
            f"{row.quadrant} & {category_name}{note} & {int(row.orders_2017):,} & "
            f"{row.revenue_2018:,.0f} & {percent(row.sales_growth)} & "
            f"{percent(row.order_growth)} " + r"\\"
        )
        previous = row.quadrant
    lines += [r"\bottomrule", r"\end{longtable}"]
    (LATEX / "report_all_categories.tex").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("Wrote report values, audit, quadrant, example, lifecycle and full-category tables")


if __name__ == "__main__":
    main()
