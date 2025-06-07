import os
import pandas as pd
from ast import literal_eval
from dotenv import load_dotenv
from etl.graphs import GraphNeo4j
from pandas.core.common import flatten

load_dotenv()


def update_graph_athletes(graph: GraphNeo4j, athlete_list: list) -> None:
    print(f"{len(athlete_list)} athletes")
    with graph.get_db_driver() as driver:
        for athlete_name in athlete_list:
            check_player_exists = graph.match_node_athlete(athlete_name, driver)
            if not check_player_exists:
                graph.add_node_athlete(athlete_name, driver)


def update_graph_agents(graph: GraphNeo4j, agent_list: list) -> None:
    print(f"{len(agent_list)} agents")
    with graph.get_db_driver() as driver:
        for agent_name in agent_list:
            graph.add_node_agent(agent_name, driver)


def update_graph_athletes_agents(
    graph: GraphNeo4j, athlete_list: list, agent_list: list[list]
) -> None:
    assert len(athlete_list) == len(agent_list)
    num_relations = sum([len(agents) for agents in agent_list])
    print(f"{num_relations} agent -> athlete relations")
    with graph.get_db_driver() as driver:
        for athlete_name, agent_names in zip(athlete_list, agent_list):
            graph.add_edge_agent_athlete(athlete_name, agent_names, driver)


def update_graph_from_df(athlete_agents_df: pd.DataFrame) -> None:
    graph_data = GraphNeo4j()
    # Add Node: athletes
    all_athletes = athlete_agents_df["Player"]
    update_graph_athletes(graph_data, all_athletes)
    # Add Node: agents
    all_agents = athlete_agents_df["Agents"]
    all_agents_unique = set(flatten(all_agents))
    update_graph_agents(graph_data, all_agents_unique)
    # Add Relation: (agent) - [represent] -> (athlete)
    update_graph_athletes_agents(graph_data, all_athletes, all_agents)


if __name__ == "__main__":
    nba_agents_df = pd.read_csv(
        f"data/nba_agents_2025-03-22.csv",
        converters={"Agents": literal_eval},
    )
    update_graph_from_df(nba_agents_df)
