import networkx as nx
from itertools import combinations
from etl.graphs import GraphNeo4j, GraphNetworkx
from etl.neo4j_to_networkx import convert_agent_athlete_neo4j_networkx


def detect_community_agent_athlete(graph_networkx: GraphNetworkx) -> None:
    community_agent_athlete: list[set] = nx.community.louvain_communities(
        graph_networkx.graph
    )
    community_agent_athlete_large = [
        community_member
        for community_member in community_agent_athlete
        if len(community_member) >= 10
    ]
    print(f"{len(community_agent_athlete_large)} large (>10) communities")

    community_pairs = combinations(community_agent_athlete_large, 2)
    for pair_id, (community_1, community_2) in enumerate(community_pairs):
        community_union = community_1.union(community_2)
        graph_community = GraphNetworkx(
            graph_name=f"louvain_community_pair_{pair_id}",
            graph_content=nx.subgraph(graph_networkx.graph, community_union),
        )
        if nx.is_connected(graph_community.graph):
            agent_athlete_bridge = nx.minimum_edge_cut(graph_community.graph)
            print(
                f"community pair {pair_id} with",
                f"{len(community_1)} + {len(community_2)} = {len(community_union)} members,",
                f"bridged by {agent_athlete_bridge}",
            )
            graph_community.draw_graph()


def analyze():
    graph_neo4j = GraphNeo4j()
    graph_networkx = convert_agent_athlete_neo4j_networkx(graph_neo4j)
    detect_community_agent_athlete(graph_networkx)


if __name__ == "__main__":
    analyze()
