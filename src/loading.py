"""Cleans the race CSVs and shapes them into the tables of the normalised schema.

Same logic as data_loading.ipynb, in a form init_db.py can run from the command line.
"""
import os

import numpy as np
import pandas as pd
from psycopg2 import sql
from psycopg2.extras import execute_values

AWARDS = ["general", "points", "king of the mountains", "young rider", "best team"]


def read_clean_data(data_path):
    """Reads the three CSVs and applies the two known data fixes."""
    riders = pd.read_csv(os.path.join(data_path, "riders.csv"))
    results = pd.read_csv(os.path.join(data_path, "individual_results.csv"))
    exits = pd.read_csv(os.path.join(data_path, "exits.csv"))

    riders["dob"] = pd.to_datetime(riders["dob"])
    results["day"] = pd.to_datetime(results["day"])

    # Aleksandr Vlasov is Russian but raced as a neutral, so his country is blank in the source
    riders["rider_country_code"] = riders["rider_country_code"].fillna("RUS")
    riders["rider_country_name"] = riders["rider_country_name"].fillna("Russian Federation")

    # Two riders share rank 108 on 18 Jul 2025; the published result places bib 197 at 109
    results.loc[
        (results["day"] == pd.Timestamp("2025-07-18")) & (results["rider"] == 197),
        "rank",
    ] = 109

    return riders, results, exits


def build_tables(riders, results, exits):
    """Returns {table name: DataFrame} in foreign-key insertion order."""
    countries = pd.concat([
        riders[["rider_country_code", "rider_country_name"]].set_axis(["iso", "name"], axis=1),
        riders[["team_country_code", "team_country_name"]].set_axis(["iso", "name"], axis=1),
        results[["start_country_code", "start_country_name"]].set_axis(["iso", "name"], axis=1),
        results[["finish_country_code", "finish_country_name"]].set_axis(["iso", "name"], axis=1),
    ], ignore_index=True).drop_duplicates().reset_index(drop=True)

    teams = (
        riders[["team", "team_country_code"]]
        .set_axis(["name", "country"], axis=1)
        .drop_duplicates()
        .reset_index(drop=True)
    )

    riders_table = riders[["bib", "rider_name", "dob", "team", "rider_country_code"]].set_axis(
        ["bib_num", "name", "dob", "team", "country"], axis=1
    )

    locations = pd.concat([
        results[["start_location", "start_country_code"]].set_axis(["name", "country"], axis=1),
        results[["finish_location", "finish_country_code"]].set_axis(["name", "country"], axis=1),
    ], ignore_index=True).drop_duplicates().reset_index(drop=True)

    stages = (
        results[["day", "start_location", "finish_location", "length", "type"]]
        .set_axis(["date", "start_location", "end_location", "dist_covered", "type"], axis=1)
        .drop_duplicates()
        .sort_values(by="date", ascending=True)
        .reset_index(drop=True)
    )
    # Stage ids are numbered in date order
    stages.insert(0, "id", np.arange(1, len(stages) + 1))

    stage_results = results.merge(stages[["date", "id"]], left_on="day", right_on="date", validate="many_to_one")
    stage_results = stage_results[["rider", "id", "rank", "time", "bonus", "penalty"]].set_axis(
        ["rider_bib", "stage_id", "rank", "finish_time", "time_bonus", "time_penalty"], axis=1
    )

    rider_exits = exits[["bib", "stage", "reason"]].set_axis(["rider_bib", "stage_id", "reason"], axis=1)
    awards = pd.DataFrame({"name": AWARDS})

    return {
        "countries": countries,
        "teams": teams,
        "riders": riders_table,
        "locations": locations,
        "stages": stages,
        "stage_results": stage_results,
        "rider_exits": rider_exits,
        "awards": awards,
    }


def validate_tables(tables):
    """Checks the keys and the rules the schema cannot enforce before anything is inserted."""
    keys = {
        "countries": ["iso"], "teams": ["name"], "riders": ["bib_num"], "locations": ["name"], "stages": ["id"],
        "stage_results": ["rider_bib", "stage_id"], "rider_exits": ["rider_bib"], "awards": ["name"],
    }
    for name, key in keys.items():
        assert not tables[name].duplicated(key).any(), f"Duplicate key in {name}"
        assert not tables[name].isna().any().any(), f"Missing values in {name}"

    results, exits = tables["stage_results"], tables["rider_exits"]
    assert not results.duplicated(["stage_id", "rank"]).any(), "Duplicate rank within a stage"
    assert tables["teams"]["name"].isin(tables["riders"]["team"]).all(), "A team has no riders"

    used = pd.concat([tables["stages"]["start_location"], tables["stages"]["end_location"]])
    assert tables["locations"]["name"].isin(used).all(), "A location is not used by any stage"

    # If a rider exits at stage S, no result may exist for S or any later stage
    both = results.merge(exits, on="rider_bib", suffixes=("_result", "_exit"))
    assert (both["stage_id_result"] < both["stage_id_exit"]).all(), "A result exists at or after an exit"


def insert_tables(cursor, tables):
    for name, df in tables.items():
        query = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
            sql.Identifier(name),
            sql.SQL(", ").join(map(sql.Identifier, df.columns)),
        )
        execute_values(cursor, query.as_string(cursor), list(df.itertuples(index=False, name=None)))
        print(f"Inserted {len(df)} rows into {name}")
