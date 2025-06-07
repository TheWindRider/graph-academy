from collections import defaultdict
import os
import json
from datetime import date, timedelta
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from etl.models import (
    GraphSports,
    Game,
    Team,
    Athlete,
    TeamCompeteIn,
    AthleteCompeteFor,
    AthleteCompeteIn,
    AthleteStats,
)


class GraphPydanticManual:
    def __init__(self):
        pass

    def navigate_event_to_competition(self, input_event: dict) -> dict:
        competition = input_event["competitions"]
        if len(competition) > 1:
            print(
                f"{len(competition)} competitions in event {input_event['shortName']}"
            )
        return competition[0]

    def navigate_competition_to_competitors(self, input_competition: dict) -> list:
        competitors = input_competition["competitors"]
        if len(competitors) > 2:
            print(f"{len(competitors)} competitors")
        return competitors

    def navigate_competitor_to_team(self, input_competitor: dict) -> dict:
        return input_competitor["team"]

    def navigate_competitor_to_leaders(self, input_competitor: dict) -> list:
        return input_competitor["leaders"]

    def navigate_leaders_to_athletes(self, input_leaders: list) -> dict:
        athletes = {}
        for input_leader in input_leaders:
            if input_leader["name"] == "rating":
                continue
            leader = input_leader["leaders"]
            if len(leader) > 1:
                print(f"{len(leader)} leaders in {input_leader['name']}")
            athlete = leader[0]["athlete"]
            athletes[athlete["id"]] = athlete
        return athletes

    def navigate_leaders_to_stats(self, input_leaders: list) -> dict:
        stats = defaultdict(list)
        for input_leader in input_leaders:
            if input_leader["name"] == "rating":
                continue
            leader = input_leader["leaders"]
            if len(leader) > 1:
                print(f"{len(leader)} leaders in {input_leader['name']}")
            athlete = leader[0]["athlete"]
            stats[athlete["id"]].append(
                {
                    "stats_name": input_leader["name"],
                    "stats_value": leader[0]["value"],
                }
            )
        return stats

    def extract_game_from_event(self, input_event: dict) -> Game:
        return Game(
            id=input_event["id"],
            label="game",
            name=input_event["name"],
            date=input_event["date"],
        )

    def extract_team_from_team(self, input_team: dict) -> Team:
        return Team(
            id=input_team["id"],
            label="team",
            name=input_team["displayName"],
            name_short=input_team["abbreviation"],
        )

    def extract_athletes_from_athletes(self, input_athletes: dict) -> list[Athlete]:
        return [
            Athlete(
                id=athlete_id,
                label="athlete",
                name=athlete_info["fullName"],
                name_short=athlete_info["shortName"],
            )
            for athlete_id, athlete_info in input_athletes.items()
        ]

    def connect_team_to_game(
        self, input_competitor: dict, input_competition: dict
    ) -> TeamCompeteIn:
        return TeamCompeteIn(
            from_node_id=input_competitor["team"]["id"],
            to_node_id=input_competition["id"],
            relation_type="compete_in",
            home_or_away=input_competitor["homeAway"],
            is_winner=input_competitor["winner"],
        )

    def connect_athletes_to_team(
        self, input_athletes: dict, input_competition: dict, input_team: dict
    ) -> list[AthleteCompeteFor]:
        return [
            AthleteCompeteFor(
                from_node_id=athlete_id,
                to_node_id=input_team["id"],
                relation_type="compete_for",
                date=input_competition["date"],
                jersey=athlete_info["jersey"],
            )
            for athlete_id, athlete_info in input_athletes.items()
        ]

    def connect_athletes_to_game(
        self, input_stats: dict, input_competition: dict
    ) -> list[AthleteCompeteIn]:
        return [
            AthleteCompeteIn(
                from_node_id=athlete_id,
                to_node_id=input_competition["id"],
                relation_type="compete_in",
                stats=[AthleteStats.model_validate(stat) for stat in athlete_stats],
            )
            for athlete_id, athlete_stats in input_stats.items()
        ]

    def transform_graph_pydantic(self, input_event: dict):
        output_game = self.extract_game_from_event(input_event)
        output_teams = []
        output_athletes = []
        output_team_game = []
        output_athlete_team = []
        output_athlete_game = []

        input_competition = self.navigate_event_to_competition(input_event)
        input_competitors = self.navigate_competition_to_competitors(input_competition)
        for input_competitor in input_competitors:
            input_team = self.navigate_competitor_to_team(input_competitor)
            input_leaders = self.navigate_competitor_to_leaders(input_competitor)
            input_athletes = self.navigate_leaders_to_athletes(input_leaders)
            input_stats = self.navigate_leaders_to_stats(input_leaders)
            output_teams.append(self.extract_team_from_team(input_team))
            output_athletes.extend(self.extract_athletes_from_athletes(input_athletes))
            output_team_game.append(
                self.connect_team_to_game(input_competitor, input_competition)
            )
            output_athlete_team.extend(
                self.connect_athletes_to_team(
                    input_athletes, input_competition, input_team
                )
            )
            output_athlete_game.extend(
                self.connect_athletes_to_game(input_stats, input_competition)
            )

        return GraphSports(
            athletes=output_athletes,
            teams=output_teams,
            game=output_game,
            athlete_compete_in_game=output_athlete_game,
            athlete_compete_for_team=output_athlete_team,
            team_compete_in_game=output_team_game,
        )


class GraphPydanticChain:
    def __init__(self, prompt_file_path: str):
        self.llm = ChatOpenAI(model="gpt-4o-2024-08-06", temperature=0)
        with open(prompt_file_path, "r") as prompt_file:
            prompt_str = prompt_file.read()
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", prompt_str),
                (
                    "human",
                    "Use the given format to extract information from the following input: {input}",
                ),
                ("human", "Tip: Make sure to answer in the correct format"),
            ]
        )
        self.chain = self.prompt | self.llm.with_structured_output(schema=GraphSports)

    def transform_graph_pydantic(self, input_doc: dict):
        graph_sports: GraphSports = self.chain.invoke({"input": input_doc})
        assert type(graph_sports) == GraphSports
        return graph_sports


if __name__ == "__main__":
    yesterday = date.today() - timedelta(days=1)
    process_date = "2025-02-21"
    graph_pydantic_manual = GraphPydanticManual()
    # graph_pydantic_chain = GraphPydanticChain("prompts/json_to_graph_sports.md")

    with open(f"data/{process_date}/raw_events.json", "r") as input_file:
        input_data = json.load(input_file)
    for each_input_doc in input_data:
        # graph_data = graph_pydantic_chain.transform_graph_pydantic(each_input_doc)
        graph_data = graph_pydantic_manual.transform_graph_pydantic(each_input_doc)
        game_id = graph_data.game.id
        os.makedirs(f"test/{process_date}", exist_ok=True)
        with open(f"test/{process_date}/{game_id}.json", "w") as output_file:
            json.dump(graph_data.model_dump(), output_file, indent=2)
