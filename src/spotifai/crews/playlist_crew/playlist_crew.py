from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent

from spotifai import tools
from spotifai.tools.spotify_tools import create_playlist, add_tracks_to_playlist
from spotifai.models import PlaylistResult

@CrewBase
class PlaylistCrew():
    """SpotifAI crew"""

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    
    llm_local = LLM(
        model="ollama/llama3.2",
        base_url="http://localhost:11434",
        timeout=120
    )

    @agent
    def playlist_manager(self) -> Agent:
        return Agent(
            config=self.agents_config['playlist_manager'], # type: ignore[index]
            verbose=True,
            max_iter=4,
            allow_delegation=False,
            llm=self.llm_local
        )

    @task
    def create_playlist_task(self) -> Task:
        return Task(
            config=self.tasks_config["create_playlist_task"], # type: ignore[index]
            tools=[create_playlist],
            output_pydantic=PlaylistResult,
        )

    @task
    def add_tracks_task(self) -> Task:
        return Task(
            config=self.tasks_config["add_tracks_task"], # type: ignore[index]
            context=[self.create_playlist_task()],
            tools=[add_tracks_to_playlist],
            output_pydantic=PlaylistResult,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Playlist crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            tracing=False,
        )
