import os
import requests
import pandas as pd
from datetime import date
from dotenv import load_dotenv

load_dotenv()


def get_nba_agents_table() -> pd.DataFrame:
    nba_agents_html = requests.get(os.getenv("NBA_AGENTS_URL")).content
    nba_agents_dfs = pd.read_html(nba_agents_html)
    assert len(nba_agents_dfs) == 1
    nba_agents_df = nba_agents_dfs[0]
    expected_columns = [
        "Player",
        "Current AAV",
        "Agency",
        "Agent",
        "Agent.1",
        "Agent.2",
        "Agent.3",
    ]
    if set(nba_agents_df.columns) != set(expected_columns):
        print(f"Unexpected columns: {nba_agents_df.columns}")
    return nba_agents_df


def process_nba_agents_table(raw_table: pd.DataFrame) -> pd.DataFrame:
    processed_table = raw_table.copy(deep=True)
    processed_table = processed_table[processed_table["Current AAV"] != "$0"]
    processed_table["Player"] = processed_table["Player"].apply(
        lambda name: " ".join(name.split(" ")[0:-1])
    )
    processed_table["Team"] = processed_table["Player"].apply(
        lambda name: name.split(" ")[-1]
    )
    processed_table["Agents"] = processed_table[
        ["Agency", "Agent", "Agent.1", "Agent.2", "Agent.3"]
    ].apply(lambda row: [agent for agent in row.values if not pd.isna(agent)], axis=1)
    processed_table["Agents_Count"] = processed_table["Agents"].apply(
        lambda agents: len(agents) > 0
    )
    processed_table = processed_table[processed_table["Agents_Count"] > 0]
    return processed_table[["Player", "Agents"]]


if __name__ == "__main__":
    nba_agents_raw = get_nba_agents_table()
    nba_agents_processed = process_nba_agents_table(nba_agents_raw)

    file_name = f"data/nba_agents_{date.today()}.csv"
    nba_agents_processed.to_csv(file_name)
