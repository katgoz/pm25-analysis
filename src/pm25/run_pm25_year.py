import sys
import os
import load_data
import calculations
import argparse
import yaml


def main(year, config_path):
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    chosen_cities = cfg.get("cities", [])

    pm25_cfg = cfg.get("pm25", {})
    limit = pm25_cfg.get("exceedance_limit", 15)

    gios_archive_url = "https://powietrze.gios.gov.pl/pjp/archives/downloadFile/"
    gios_id = load_data.find_gios_pm25_info(year)

    os.makedirs(f"results/pm25/{year}", exist_ok=True)

    dfs = load_data.load_pm25_data(
        [year],
        gios_archive_url,
        {year: gios_id}
    )

    metadata_df = load_data.load_metadata()
    old_codes, cities, provinces = load_data.get_old_station_codes(metadata_df)

    dfs = load_data.clean_pm25_data(dfs)
    dfs = load_data.replace_old_codes(dfs, old_codes)
    dfs = load_data.correct_dates(dfs)

    df = load_data.merge_dataframes(dfs, cities, provinces)

    #srednie dzienne dla wybranych miast (i stacji)
    daily_means = calculations.calculate_daily_station_averages(df)
    daily_means.columns = daily_means.columns.droplevel("Wojewodztwo")
    daily_means_by_chosen_city = daily_means.loc[:, daily_means.columns.get_level_values("Miejscowosc").isin(chosen_cities)]

    #liczba dni z przekroczeniami na miasto - do tabeli przekroczeń per rok/miasto
    exceed_city = calculations.calculate_days_exceeding_limit(df, limit = limit)
    exceed_city_result = exceed_city.T.groupby(level="Miejscowosc").sum().T
    
    daily_means_by_chosen_city.to_csv(f"results/pm25/{year}/daily_means.csv")
    exceed_city_result.to_csv(f"results/pm25/{year}/exceedance_days.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    main(args.year, args.config)
