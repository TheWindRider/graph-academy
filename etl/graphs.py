import os
import networkx as nx
import pygraphviz as pgv
from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver

load_dotenv()


class GraphNeo4j:
    def __init__(self):
        self.neo4j_uri = os.getenv("NEO4J_URL")
        self.neo4j_auth = (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
        with self.get_db_driver() as driver:
            driver.verify_connectivity()

    def get_db_driver(self) -> Driver:
        return GraphDatabase.driver(uri=self.neo4j_uri, auth=self.neo4j_auth)

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


class GraphNetworkx:
    def __init__(self, graph_name: str = "", graph_content: nx.Graph | None = None):
        self.graph = nx.Graph() if graph_content is None else graph_content
        self.name = graph_name

    def __str__(self):
        num_nodes = self.graph.number_of_nodes()
        num_edges = self.graph.number_of_edges()
        return f"Graph with {num_nodes} nodes and {num_edges} edges"

    def draw_graph(self) -> None:
        agraph: pgv.AGraph = nx.nx_agraph.to_agraph(self.graph)
        agraph.draw(f"../test/{self.name}.png", prog="circo")

    def add_edges(self, edge_list: list) -> None:
        self.graph.add_edges_from(edge_list)
