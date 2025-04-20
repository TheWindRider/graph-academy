import os
import json
import glob
from datetime import date, timedelta
from dotenv import load_dotenv
from graphs import GraphNeo4j
from models import GraphSports

load_dotenv()


def build_graph(graph_db: GraphNeo4j, graph_pydantic_sports: GraphSports):
    with graph_db.get_db_driver() as driver:
        graph_db.add_nodes_pydantic(graph_pydantic_sports, driver)
        graph_db.add_edges_pydantic(graph_pydantic_sports, driver)


def generate_graph_from_json(process_date: str, game_id: str = "*") -> None:
    graph_data = GraphNeo4j()

    for file_path in glob.glob(f"data/{process_date}/{game_id}.json"):
        if os.path.basename(file_path).split(".")[0] == "raw_events":
            continue
        print(f"processing {file_path}")
        with open(file_path, "r") as input_file:
            input_data = json.load(input_file)
        pydantic_data = GraphSports.model_validate(input_data)
        build_graph(graph_data, pydantic_data)


if __name__ == "__main__":
    yesterday = date.today() - timedelta(days=1)
    graph_sports = generate_graph_from_json(process_date=str(yesterday))
