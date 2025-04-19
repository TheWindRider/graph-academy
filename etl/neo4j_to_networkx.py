from graphs import GraphNeo4j, GraphNetworkx


def neo4j_get_edges_agent_athlete(graph: GraphNeo4j) -> list:
    with graph.get_db_driver() as driver:
        neo4j_edges = graph.get_edge_agent_athlete(driver)
    result_edge_list = [
        (agent_athlete["agent_name"], agent_athlete["athlete_name"])
        for agent_athlete in neo4j_edges
    ]
    return result_edge_list


def convert_agent_athlete_neo4j_networkx(graph_neo4j: GraphNeo4j) -> GraphNetworkx:
    graph_networkx = GraphNetworkx("agent_athlete")
    agent_athlete_edge_list = neo4j_get_edges_agent_athlete(graph_neo4j)
    graph_networkx.add_edges(agent_athlete_edge_list)
    print(graph_networkx)
    return graph_networkx


if __name__ == "__main__":
    graph_neo4j = GraphNeo4j()
    graph_networkx = convert_agent_athlete_neo4j_networkx(graph_neo4j)
