from dotenv import load_dotenv
from etl.graphs import GraphNeo4j

load_dotenv()


def neo4j_merge_nodes(graph_neo4j: GraphNeo4j) -> None:
    with graph_neo4j.get_db_driver() as driver:
        num_athlete_consolidated = graph_neo4j.consolidate_node_athlete(driver)
        num_team_consolidated = graph_neo4j.consolidate_node_team(driver)
        print(
            f"{num_athlete_consolidated} athletes and ",
            f"{num_team_consolidated} teams consolidated",
        )


def post_process():
    graph_data = GraphNeo4j()
    neo4j_merge_nodes(graph_data)


if __name__ == "__main__":
    post_process()
