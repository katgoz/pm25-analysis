import argparse
import yaml
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import re
from collections import Counter
import seaborn as sns

def load_exceedance_days(path: Path):
    df = pd.read_csv(path)

    year = df["Data"].iloc[0]
    df = df.set_index("Data")
    df=df.T
    df.index.name = "Miasto"
    df.columns = [year]
    return df

def md_table(df):
    return df.to_markdown()


def load_daily_means(path: Path):
    df = pd.read_csv(path, header=None)

    cities_row = df.iloc[0, 1:]
    stations_row = df.iloc[1, 1:]

    new_cols = []
    new_cols.append("Data")
    for city, station in zip(cities_row, stations_row):
        new_cols.append(f"{city} ({station})")

    df2=df.iloc[3:, :]
    df2.columns=new_cols

    # konwersja typów
    df2["Data"] = pd.to_datetime(df2["Data"])

    for col in df2.columns[1:]:
        df2[col] = pd.to_numeric(df2[col], errors="coerce")

    df2 = df2.set_index("Data")
    df2=df2.T
    return df2


def plot_yearly_heatmaps(data_dict,  outpath: Path):
    n_years = len(data_dict)

    fig, axes = plt.subplots(n_years, 1, figsize=(15, 4 * n_years), sharex=True)

    if n_years == 1:
        axes = [axes]

    # wspólna skala kolorów
    global_min = min(df.min().min() for df in data_dict.values())
    global_max = max(df.max().max() for df in data_dict.values())

    for ax, (year, df) in zip(axes, data_dict.items()): #items: np. (2021, df2021)
        sns.heatmap(
            df,
            cmap="Reds",
            ax=ax,
            vmin=global_min,
            vmax=global_max,
            cbar=True
        )

        # ===== FORMATOWANIE DAT ======
        dates = pd.to_datetime(df.columns)

        # pozycje pierwszego dnia miesiąca
        month_starts = dates[dates.day == 1]
        month_positions = [df.columns.get_loc(d) for d in month_starts]

        ax.set_xticks(month_positions)
        ax.set_xticklabels(month_starts.strftime("%b"), rotation=0)

        ax.set_title(f"PM2.5 daily means – {year}")
        ax.set_ylabel("Stacja")
        ax.set_xlabel("Dzień roku")

    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()


def plot_publication_trend(df, outpath: Path):
    outpath.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(6, 4))

    plt.plot(df["year"], df["papers"], marker="o")

    plt.xlabel("Year")
    plt.ylabel("Number of publications")
    plt.title("Publication trend over time")

    plt.ylim(0, df["papers"].max() * 1.1)

    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()




exclude = {"with","from", "using","study","analysis","effects","effect","associated", "pm25",
    "pollution","health", "during", "between", "particulate", "matter", "based"
}


def extract_top_words(titles, top_n=10):
    words = []

    for t in titles:
        t = str(t).lower()
        found_words = re.findall(r"\S+", t)
        found_words = [w.rstrip(".,;:!?") for w in found_words]

        found_words = [w for w in found_words if len(w) > 3 and w not in exclude]

        words.extend(found_words)

    counter = Counter(words)

    return pd.DataFrame(
        counter.most_common(top_n),
        columns=["word", "count"]
    )



def plot_top_words_side_by_side(df1, df2, year1, year2, outpath: Path):
    outpath.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    axes[0].bar(df1["word"], df1["count"])
    axes[0].set_title(str(year1))
    axes[0].tick_params(axis="x", rotation=45)
    axes[0].set_ylabel("Count")

    axes[1].bar(df2["word"], df2["count"])
    axes[1].set_title(str(year2))
    axes[1].tick_params(axis="x", rotation=45)

    fig.suptitle("Top title words comparison")

    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()


# =====================================================
# MAIN
# =====================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config) as f:
        cfg = yaml.safe_load(f)

    years = sorted(cfg["years"])
    cities = cfg.get("cities", [])
    query = cfg["pubmed"]["keyword"]

    years_str = "_".join(map(str, years))

    report_lines = []
    report_lines.append("# Katarzyna Gozdek - Task 4 Report\n")

    #PM2.5
    #===========Tabel liczby przekroczeń miasto/rok====================
    report_lines.append("## PM2.5 – number of days exceeding PM2.5 limit by city/year\n")

    pm_exceedance_year = []

    for y in years:
        path = Path(f"results/pm25/{y}/exceedance_days.csv")
        pm_exceedance_year.append(load_exceedance_days(path))

    pm_all_years = pd.concat(pm_exceedance_year, axis=1)

    report_lines.append(md_table(pm_all_years))
    report_lines.append("\n")

    #===============Dzienne średnie dla stacji w wybranych miastach =================

    report_lines.append("## PM2.5 – daily means (selected cities)\n")

    years_dict={}
    for y in years:
        df = load_daily_means(Path(f"results/pm25/{y}/daily_means.csv"))
        years_dict[y]=df

    heatmap_path = Path(f"results/report/heatmap_{years_str}.png")
    plot_yearly_heatmaps(years_dict, heatmap_path)

    report_lines.append(f"![PM2.5 heatmap](report/heatmap_{years_str}.png)")
    report_lines.append("\n")



    # LITERATURA
    report_lines.append("## Literature summary\n")

    #==========ile publikacji dla zapytania w danym roku=========
    lit_rows = []

    for y in years:
        summary = pd.read_csv(f"results/literature/{y}/summary_by_year.csv")
        count = int(summary["count"].iloc[0])

        lit_rows.append({
            "year": y,
            "papers": count
        })

    lit_df = pd.DataFrame(lit_rows)

    report_lines.append(f"### Publications per year for query {query}")
    report_lines.append(md_table(lit_df))
    report_lines.append("\n")

    #===========trend liczby publikacji w czasie================

    trend_path = Path(f"results/report/publications_trend_{years_str}.png")
    plot_publication_trend(lit_df, trend_path)

    report_lines.append("### Publication trend")
    report_lines.append(f"![Publication trend](report/publications_trend_{years_str}.png)")

    report_lines.append("\n")

    #=======================top czasopisma=====================

    report_lines.append("### Top journals\n")

    for y in years:
        report_lines.append(f"#### {y}")
        df = pd.read_csv(f"results/literature/{y}/top_journals.csv")
        report_lines.append(md_table(df))
        report_lines.append("\n")

    #=============== wykresy liczby czasopism =============
    report_lines.append("### Papers by journal – plots\n")

    for y in years:
        report_lines.append(f"#### {y}")
        report_lines.append(f"![papers by journal](literature/{y}/papers_by_journal.png)")
        report_lines.append("\n")

    #===============kilka przykładowych tytułów =============
    report_lines.append("### Example papers\n")

    for y in years:
        report_lines.append(f"#### {y}")
        df = pd.read_csv(f"results/literature/{y}/pubmed_papers.csv")

        for title in df["title"].head(5):
            report_lines.append(f"- {title}")

        report_lines.append("\n")


# BONUS – dodatkowa prosta analiza tytułów (top słowa) per rok i wykres porównawczy 2019 vs 2024.
    if len(years) >= 2:
        y1, y2 = years[0], years[-1]

        papers1 = pd.read_csv(f"results/literature/{y1}/pubmed_papers.csv")
        papers2 = pd.read_csv(f"results/literature/{y2}/pubmed_papers.csv")

        df1 = extract_top_words(papers1["title"])
        df2 = extract_top_words(papers2["title"])

        compare_path = Path(f"results/report/top_words_compare_{y1}_{y2}.png")

        plot_top_words_side_by_side(df1, df2, y1, y2, compare_path)

        report_lines.append("## Title word comparison")
        report_lines.append(f"![comparison](report/top_words_compare_{y1}_{y2}.png)")
        report_lines.append("\n")


    out = Path(f"results/report_{years_str}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(report_lines), encoding="utf-8")



if __name__ == "__main__":
    main()
