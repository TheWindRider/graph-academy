import os
import json
import glob
from datetime import date, timedelta
from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver
from models import (
    GraphSports,
    AthleteCompeteIn,
    AthleteCompeteFor,
    TeamCompeteIn,
    Node,
    Edge,
)

load_dotenv()


class GraphNeo4j:
    def __init__(self):
        self.neo4j_uri = os.getenv("NEO4J_URL")
        self.neo4j_auth = (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
        with GraphDatabase.driver(uri=self.neo4j_uri, auth=self.neo4j_auth) as driver:
            driver.verify_connectivity()

    def generate_query_params(self, entity_attributes: dict) -> str:
        node_params = [
            f"{attribute}: ${attribute}" for attribute in entity_attributes.keys()
        ]
        return "{" + ", ".join(node_params) + "}"

    def merge_node(self, node_pydantic: Node, neo4j_driver: Driver):
        node_attributes = node_pydantic.model_dump()
        node_label = node_attributes.pop("label")
        node_property = self.generate_query_params(node_attributes)
        node_query = f"MERGE (n:{node_label} {node_property})"
        neo4j_driver.execute_query(
            query_=node_query,
            parameters_=node_attributes,
            database_="neo4j",
        )

    def merge_edge(self, edge_pydantic: Edge, neo4j_driver: Driver):
        edge_attributes = edge_pydantic.model_dump()
        edge_label = edge_attributes.pop("relation_type")
        node_from = edge_attributes.pop("from_node_id")
        node_to = edge_attributes.pop("to_node_id")
        # customized for different edge types
        if isinstance(edge_pydantic, AthleteCompeteIn):
            edge_attributes = {}
            for athlete_stats in edge_pydantic.stats:
                edge_attributes[athlete_stats.stats_name] = athlete_stats.stats_value
            edge_property = self.generate_query_params(edge_attributes)
            edge_query = (
                f"MATCH (a:athlete), (g:game)\n"
                f"WHERE a.id = {node_from} AND g.id = {node_to}\n"
                f"MERGE (a)-[:{edge_label} {edge_property}]->(g)"
            )
        elif isinstance(edge_pydantic, AthleteCompeteFor):
            edge_query = (
                f"MATCH (a:athlete), (t:team)\n"
                f"WHERE a.id = {node_from} AND t.id = {node_to}\n"
                f"MERGE (a)-[e:{edge_label}]->(t)\n"
                f"ON CREATE SET e.jersey = $jersey, e.first_date = $date\n"
                f"ON MATCH SET e.last_date = $date\n"
            )
        elif isinstance(edge_pydantic, TeamCompeteIn):
            edge_property = self.generate_query_params(edge_attributes)
            edge_query = (
                f"MATCH (t:team), (g:game)\n"
                f"WHERE t.id = {node_from} AND g.id = {node_to}\n"
                f"MERGE (t)-[:{edge_label} {edge_property}]->(g)"
            )
        neo4j_driver.execute_query(
            query_=edge_query,
            parameters_=edge_attributes,
            database_="neo4j",
        )

    def add_nodes(self, graph_pydantic_sports: GraphSports, neo4j_driver: Driver):
        # Game
        self.merge_node(graph_pydantic_sports.game, neo4j_driver)
        # Athletes
        for athlete in graph_pydantic_sports.athletes:
            self.merge_node(athlete, neo4j_driver)
        # Teams
        for team in graph_pydantic_sports.teams:
            self.merge_node(team, neo4j_driver)

    def add_edges(self, graph_pydantic_sports: GraphSports, neo4j_driver: Driver):
        # Athlete -> Game
        for athlete_game in graph_pydantic_sports.athlete_compete_in_game:
            self.merge_edge(athlete_game, neo4j_driver)
        # Athlete -> Team
        for athlete_team in graph_pydantic_sports.athlete_compete_for_team:
            self.merge_edge(athlete_team, neo4j_driver)
        # Team -> Game
        for team_game in graph_pydantic_sports.team_compete_in_game:
            self.merge_edge(team_game, neo4j_driver)

    def build_graph(self, graph_pydantic_sports: GraphSports):
        with GraphDatabase.driver(uri=self.neo4j_uri, auth=self.neo4j_auth) as driver:
            self.add_nodes(graph_pydantic_sports, driver)
            self.add_edges(graph_pydantic_sports, driver)


def generate_graph_from_json(process_date: str, game_id: str = "*") -> None:
    graph_data = GraphNeo4j()

    for file_path in glob.glob(f"data/{process_date}/{game_id}.json"):
        if os.path.basename(file_path).split(".")[0] == "raw_events":
            continue
        print(f"processing {file_path}")
        with open(file_path, "r") as input_file:
            input_data = json.load(input_file)
        pydantic_data = GraphSports.model_validate(input_data)
        graph_data.build_graph(pydantic_data)


if __name__ == "__main__":
    yesterday = date.today() - timedelta(days=1)
    graph_sports = generate_graph_from_json(process_date=str(yesterday))
