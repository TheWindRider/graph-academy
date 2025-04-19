from pydantic import BaseModel
from typing import List

class Node(BaseModel):
    id: int
    label: str
    name: str

class Edge(BaseModel):
    from_node_id: int
    to_node_id: int
    relation_type: str

class Athlete(Node):
    name_short: str

class Team(Node):
    name_short: str

class Game(Node):
    date: str

class AthleteStats(BaseModel):
    stats_name: str
    stats_value: int | float
class AthleteCompeteIn(Edge):
    stats: list[AthleteStats]

class AthleteCompeteFor(Edge):
    date: str
    jersey: int

class TeamCompeteIn(Edge):
    home_or_away: str
    is_winner: bool

class GraphSports(BaseModel):
    athletes: List[Athlete]
    teams: List[Team]
    game: Game
    athlete_compete_in_game: List[AthleteCompeteIn]
    athlete_compete_for_team: List[AthleteCompeteFor]
    team_compete_in_game: List[TeamCompeteIn]
