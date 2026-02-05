import sys
import os
import load_data
import calculations


def main(year):

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

    month_means = calculations.calculate_station_monthly_averages(df)
    exceed = calculations.calculate_days_exceeding_limit(df)

    month_means.to_csv(f"results/pm25/{year}/monthly_means.csv")
    exceed.to_csv(f"results/pm25/{year}/exceed_days.csv")


if __name__ == "__main__":
    year = int(sys.argv[1])
    main(year)
