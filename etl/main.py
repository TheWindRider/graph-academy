import glob
import os
import sys
import json
from datetime import date, timedelta
from dotenv import load_dotenv

from models import GraphSports
from api_to_json import get_espn_api_scoreboard, extract_events
from json_to_pydantic import GraphPydanticManual
from pydantic_to_neo4j import GraphNeo4j

load_dotenv()

if __name__ == "__main__":
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    yesterday = date.today() - timedelta(days=1)
    sports_neo4j_data = GraphNeo4j()

    # Read from ESPN API and write to JSON document
    sports_scoreboard = get_espn_api_scoreboard(yesterday)
    sports_events = extract_events(sports_scoreboard)
    if len(sports_events) == 0:
        sys.exit()
    file_name_raw_json = f"{data_dir}/{yesterday}/raw_events.json"
    os.makedirs(os.path.dirname(file_name_raw_json), exist_ok=True)
    with open(file_name_raw_json, mode="w") as file_io:
        json.dump(sports_events, file_io, indent=2)

    # Read from raw JSON document and extract data per Pydantic
    # file_name_prompt = f"{file_dir}/prompts/json_to_graph_sports.md"
    graph_pydantic_manual = GraphPydanticManual()
    with open(file_name_raw_json, "r") as file_raw_json:
        sports_events = json.load(file_raw_json)
    for sports_doc in sports_events:
        sports_graph_data = graph_pydantic_manual.transform_graph_pydantic(sports_doc)
        game_id = sports_graph_data.game.id
        file_name_graph = f"{data_dir}/{yesterday}/{game_id}.json"
        with open(file_name_graph, "w") as file_graph:
            json.dump(sports_graph_data.model_dump(), file_graph, indent=2)

    # Read from Pydantic JSON document and write to Neo4J graph DB
    file_name_graph = f"{data_dir}/{yesterday}/*.json"
    for file_path in glob.glob(file_name_graph):
        if os.path.basename(file_path).split(".")[0] == "raw_events":
            continue
        print(f"processing {file_path}")
        with open(file_path, "r") as input_file:
            sports_pydantic_data = json.load(input_file)
        sports_graph_data = GraphSports.model_validate(sports_pydantic_data)
        sports_neo4j_data.build_graph(sports_graph_data)
