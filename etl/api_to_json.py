import os
import json
import requests
from datetime import date
from dotenv import load_dotenv

load_dotenv()


def get_espn_api_scoreboard(event_date: date) -> dict:
    scoreboard_res = requests.get(
        url=os.getenv("ESPN_API_URL"), params={"dates": event_date.strftime("%Y%m%d")}
    )
    assert scoreboard_res.status_code == 200
    return scoreboard_res.json()


def get_news_api_headline(query: str) -> dict:
    headline_res = requests.get(
        headers={"X-Api-Key": os.getenv("NEWS_API_KEY")},
        url=os.getenv("NEWS_API_URL"),
        params={"q": query},
    )
    assert headline_res.status_code == 200
    return headline_res.json()


def is_event_completed(event_doc: dict) -> bool:
    result_games = event_doc["competitions"]
    if len(result_games) > 1:
        print(f"Unexpected number of games: {len(result_games)}")
    return result_games[0]["status"]["type"]["completed"]


def extract_events(scoreboard_doc: dict) -> list:
    sports_events = scoreboard_doc["events"]
    if len(sports_events) > 1:
        print(f"Multiple events: {len(sports_events)}")
    sports_events_completed = list(filter(is_event_completed, sports_events))
    if len(sports_events_completed) < len(sports_events):
        print(f"{len(sports_events_completed)} of {len(sports_events)} games finished")
    return sports_events_completed


if __name__ == "__main__":
    sports_news = get_news_api_headline(query="trade")

    file_name = "test/raw_news.json"
    with open(file_name, mode="w") as file_io:
        json.dump(sports_news, file_io, indent=2)
