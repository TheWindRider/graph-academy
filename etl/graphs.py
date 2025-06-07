import os
import networkx as nx
import pygraphviz as pgv
from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver
from etl.models import (
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
        with self.get_db_driver() as driver:
            driver.verify_connectivity()

    def get_db_driver(self) -> Driver:
        return GraphDatabase.driver(uri=self.neo4j_uri, auth=self.neo4j_auth)

    def generate_query_params(self, entity_attributes: dict) -> str:
        node_params = [
            f"{attribute}: ${attribute}" for attribute in entity_attributes.keys()
        ]
        return "{" + ", ".join(node_params) + "}"

    def match_node_athlete(self, full_name: str, neo4j_driver: Driver) -> bool:
        match_query = f"MATCH (a:athlete)\nWHERE a.name = $athlete_name\nRETURN a"
        match_result = neo4j_driver.execute_query(
            query_=match_query,
            parameters_={"athlete_name": full_name},
            database_="neo4j",
        )
        num_match = len(match_result.records)
        if num_match == 0:
            return False
        elif num_match == 1:
            return True
        else:
            print(f"{num_match} matches found: {match_result.records}")
            return False

    def add_node_generic(self, node_pydantic: Node, neo4j_driver: Driver):
        node_attributes = node_pydantic.model_dump()
        node_label = node_attributes.pop("label")
        node_property = self.generate_query_params(node_attributes)
        node_query = f"MERGE (n:{node_label} {node_property})"
        neo4j_driver.execute_query(
            query_=node_query,
            parameters_=node_attributes,
            database_="neo4j",
        )

    def add_node_athlete(self, full_name: str, neo4j_driver: Driver) -> None:
        athlete_property = "{name: $athlete_name}"
        add_query = f"MERGE (n:athlete {athlete_property})"
        neo4j_driver.execute_query(
            query_=add_query,
            parameters_={"athlete_name": full_name},
            database_="neo4j",
        )

    def add_node_agent(self, full_name: str, neo4j_driver: Driver) -> None:
        agent_property = "{name: $agent_name}"
        add_query = f"MERGE (n:agent {agent_property})"
        neo4j_driver.execute_query(
            query_=add_query,
            parameters_={"agent_name": full_name},
            database_="neo4j",
        )

    def consolidate_node_athlete(self, neo4j_driver: Driver) -> int:
        merge_query = """
        MATCH(a1:athlete), (a2:athlete)
        WHERE a1.id IS NULL AND a2.id IS NOT NULL
        AND a1.name = a2.name
        CALL apoc.refactor.mergeNodes([a1,a2]) YIELD node
        RETURN node
        """
        merge_result = neo4j_driver.execute_query(
            query_=merge_query,
            database_="neo4j",
        )
        for node_athlete in merge_result.records:
            print(node_athlete)
        return len(merge_result.records)

    def consolidate_node_team(self, neo4j_driver: Driver) -> int:
        update_query = """
        MATCH (t2:team)<-[c2:compete_for]-(a:athlete)-[c1:compete_for]->(t1:team)
        WHERE upper(t2.name_short) = t2.name_short
        AND t1.name = t2.name
        AND t1.name_short <> t2.name_short
        SET c2.first_date = c1.first_date, c2.last_date = c1.last_date
        """
        merge_query = """
        MATCH(t1:team), (t2:team)
        WHERE upper(t2.name_short) = t2.name_short
        AND t1.name = t2.name
        AND t1.name_short <> t2.name_short
        CALL apoc.refactor.mergeNodes([t1,t2]) YIELD node
        RETURN node
        """
        neo4j_driver.execute_query(
            query_=update_query,
            database_="neo4j",
        )
        merge_result = neo4j_driver.execute_query(
            query_=merge_query,
            database_="neo4j",
        )
        for node_team in merge_result.records:
            print(node_team)
        return len(merge_result.records)

    def add_nodes_pydantic(
        self, graph_pydantic_sports: GraphSports, neo4j_driver: Driver
    ):
        # Game
        self.add_node_generic(graph_pydantic_sports.game, neo4j_driver)
        # Athletes
        for athlete in graph_pydantic_sports.athletes:
            self.add_node_generic(athlete, neo4j_driver)
        # Teams
        for team in graph_pydantic_sports.teams:
            self.add_node_generic(team, neo4j_driver)

    def get_edge_agent_athlete(self, neo4j_driver: Driver) -> dict:
        get_query = """
        MATCH (ag:agent)-[r:represent]->(at:athlete)
        RETURN ag.name AS agent_name, at.name AS athlete_name
        """
        edge_results = neo4j_driver.execute_query(
            query_=get_query,
            database_="neo4j",
        )
        print(f"{len(edge_results.records)} agent-athlete edges")
        return [agent_athlete.data() for agent_athlete in edge_results.records]

    def add_edge_generic(self, edge_pydantic: Edge, neo4j_driver: Driver):
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

    def add_edge_agent_athlete(
        self, athlete_name: str, agent_names: list[str], neo4j_driver: Driver
    ) -> None:
        add_query = """
            MATCH (t:athlete), (g:agent)
            WHERE t.name = $athlete_name AND g.name IN $agent_names
            MERGE (t)<-[:represent]-(g)
        """
        neo4j_driver.execute_query(
            query_=add_query,
            parameters_={"athlete_name": athlete_name, "agent_names": agent_names},
            database_="neo4j",
        )

    def add_edges_pydantic(
        self, graph_pydantic_sports: GraphSports, neo4j_driver: Driver
    ):
        # Athlete -> Game
        for athlete_game in graph_pydantic_sports.athlete_compete_in_game:
            self.add_edge_generic(athlete_game, neo4j_driver)
        # Athlete -> Team
        for athlete_team in graph_pydantic_sports.athlete_compete_for_team:
            self.add_edge_generic(athlete_team, neo4j_driver)
        # Team -> Game
        for team_game in graph_pydantic_sports.team_compete_in_game:
            self.add_edge_generic(team_game, neo4j_driver)


class GraphNetworkx:
    def __init__(self, graph_name: str = "", graph_content: nx.Graph | None = None):
        self.graph = nx.Graph() if graph_content is None else graph_content
        self.name = graph_name

    def __str__(self):
        num_nodes = self.graph.number_of_nodes()
        num_edges = self.graph.number_of_edges()
        return f"Graph with {num_nodes} nodes and {num_edges} edges"

    def draw_graph(self) -> None:
        test_dir = os.path.join(os.path.dirname(__file__), "..", "test")
        agraph: pgv.AGraph = nx.nx_agraph.to_agraph(self.graph)
        agraph.draw(f"{test_dir}/{self.name}.png", prog="fdp")

    def add_edges(self, edge_list: list) -> None:
        self.graph.add_edges_from(edge_list)
