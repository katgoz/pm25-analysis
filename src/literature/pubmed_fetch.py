import argparse
import csv
import yaml
from pathlib import Path
import pandas as pd
from Bio import Entrez
import matplotlib.pyplot as plt
from Bio import Medline
import re

def clean(text):
    text = text.lower()
    text = re.sub(r"\W+", "_", text)
    return text.strip("_")


def build_query(cfg: dict, year: str):
    keyword = cfg["pubmed"]["keyword"]

    return f'{keyword} AND "{year}"[PDAT]'



def fetch_limited_records(query: str, limit: int, batch_size: int = 200):
    """
    Pobiera tylko pierwsze `limit` rekordów i zwraca pełny Count z PubMed.
    """

    handle = Entrez.esearch(
        db="pubmed",
        term=query,
        usehistory="y",
        retmax=limit,
        sort="pmid"
    )


    results = Entrez.read(handle)
    handle.close()
    id_list = results["IdList"]

    total_count = int(results["Count"])
    webenv = results["WebEnv"]
    query_key = results["QueryKey"]

    to_download = min(limit, total_count)

    records_all = []

    for start in range(0, to_download, batch_size):
        handle = Entrez.efetch(
            db="pubmed",
            rettype="medline",
            retmode="text",
            retstart=start,
            retmax=min(batch_size, to_download - start),
            webenv=webenv,
            query_key=query_key
        )

        records = Medline.parse(handle)
        records_all.extend(list(records))
        handle.close()

    return records_all, total_count, id_list




def save_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader() #nazwy kolumn
        writer.writerows(rows)


def save_summary_by_year(path: Path, year: str, total_found: int):
    rows = [{"year": year, "count": total_found,}]

    save_csv(path, rows, ["year", "count"])


def save_top_journals(path: Path, articles, top_n=10):
    journal_counts = {}

    for a in articles:
        journal = a["journal"]
        if journal:
            journal_counts[journal] = journal_counts.get(journal, 0) + 1

    sorted_counts = sorted(journal_counts.items(), key=lambda x: (-x[1], x[0]))

    rows = [
        {"journal": j, "count": c}
        for j, c in sorted_counts[:top_n]
    ]

    save_csv(path, rows, ["journal", "count"])


#w ramach pobranego limitu - total_papers=limit
def plot_top_journals(path: Path, top_csv: Path, total_papers: int):
    df = pd.read_csv(top_csv)
    if df.empty:
        return

    top_sum = df["count"].sum()
    other = total_papers - top_sum

    if other > 0:
        df.loc[len(df)] = ["Other", other]

    path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(10, 5))
    plt.bar(df["journal"], df["count"])
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Number of papers")
    plt.title("Top journals (+ Other)")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()


def record_to_article_dict(r: dict, year: str) -> dict:
    """
    Zamienia rekord MEDLINE -> słownik CSV. Wydzielone do testów pytest
    """
    return {
        "pmid": r.get("PMID", ""),
        "title": r.get("TI", ""),
        "journal": r.get("JT", ""),
        "year": year,
        "authors": "; ".join(r.get("AU", [])),
        "abstract": r.get("AB", "")
    }

def fetch_records_by_id_list(id_list, batch_size=200):
    records_all = []

    for start in range(0, len(id_list), batch_size):
        batch = id_list[start:start + batch_size]

        handle = Entrez.efetch(
            db="pubmed",
            rettype="medline",
            retmode="text",
            id=",".join(batch)
        )

        records = Medline.parse(handle)
        records_all.extend(list(records))
        handle.close()

    return records_all

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", required=True)
    parser.add_argument("--config", required=True)

    args = parser.parse_args()

    with open(args.config) as f:
        cfg = yaml.safe_load(f)

    email = cfg["pubmed"]["entrez_email"]
    if not email:
        raise ValueError("entrez_email must not be empty")
    Entrez.email = email

    batch_size = cfg["pubmed"].get("batch_size", 200)
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")

    top_journals = cfg["pubmed"].get("top_journals", 10)
    if top_journals <= 0:
        raise ValueError("top_journals must be > 0")

    year = args.year
    if not year.isdigit() or len(year) != 4:
        raise ValueError("year must be a 4-digit number, e.g. 2020")

    query = build_query(cfg, year)

    limit = cfg["pubmed"].get("limit", 1000)

    keyword = cfg["pubmed"]["keyword"]
    safe_keyword = clean(keyword)

    snapshot_dir = Path("results/pubmed_snapshots")
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    snapshot_path = snapshot_dir / f"{safe_keyword}_{year}_{limit}.txt"

    if limit <= 0:
        raise ValueError("limit must be > 0")

    outdir = Path(f"results/literature/{year}")

    if snapshot_path.exists():
        with open(snapshot_path) as f:
            lines = [line.strip() for line in f]

        header = lines[0]
        if header.startswith("# total_count="):
            total_found = int(header.split("=")[1])
            id_list = lines[1:]
        else:
            id_list = lines
            total_found = len(id_list)
        records = fetch_records_by_id_list(id_list, batch_size=batch_size)

    else:
        records, total_found, id_list = fetch_limited_records(query, limit=limit, batch_size=batch_size)

        with open(snapshot_path, "w") as f:
            f.write(f"# total_count={total_found}\n")
            for pmid in id_list:
               f.write(pmid + "\n")


    articles = []
    for r in records:
        articles.append(record_to_article_dict(r, year))
    articles = sorted(articles, key=lambda x: x["pmid"])


    # wszystkie wyniki
    save_csv(outdir / "pubmed_papers.csv", articles, ["pmid", "title", "year", "journal", "authors", "abstract"])

    # ile w tym roku - jedno pole po query po roku
    save_summary_by_year(outdir / "summary_by_year.csv", year, total_found)


    save_top_journals(outdir / "top_journals.csv", articles, top_n=top_journals)

    # wykres ile w roku artykułów topowych czasopism i ile pozostałych
    plot_top_journals(outdir / "papers_by_journal.png", outdir / "top_journals.csv", len(articles))


if __name__ == "__main__":
    main()
