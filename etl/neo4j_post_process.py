import networkx as nx
from dotenv import load_dotenv
from graphs import GraphNeo4j, GraphNetworkx

load_dotenv()


def neo4j_merge_nodes(graph_neo4j: GraphNeo4j) -> None:
    with graph_neo4j.get_db_driver() as driver:
        num_athlete_consolidated = graph_neo4j.consolidate_node_athlete(driver)
        num_team_consolidated = graph_neo4j.consolidate_node_team(driver)
        print(
            f"{num_athlete_consolidated} athletes and ",
            f"{num_team_consolidated} teams consolidated",
        )


def detect_community_agent_athlete(graph_networkx: GraphNetworkx) -> None:
    community_agent_athlete = nx.community.louvain_communities(
        graph_networkx.graph, seed=123
    )
    for community_id, community_member in enumerate(community_agent_athlete):
        if len(community_member) < 10:
            continue
        print(f"community {community_id} has {len(community_member)} members")
        graph_community = GraphNetworkx(
            graph_name=f"community_{community_id}",
            graph_content=nx.induced_subgraph(graph_networkx.graph, community_member),
        )
        graph_community.draw_graph()


def post_process():
    graph_data = GraphNeo4j()
    neo4j_merge_nodes(graph_data)


if __name__ == "__main__":
    post_process()
