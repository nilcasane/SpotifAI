from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from spotifai.tools.spotify_tools import search_tracks, get_track_analysis
from spotifai.models import MusicSearchPlan, DiscoveryResult


@CrewBase
class DiscoveryCrew():
    """Discovery crew"""

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
    def query_interpreter(self) -> Agent:
        return Agent(
            config=self.agents_config["query_interpreter"], # type: ignore[index]
            verbose=True,
            tools=[],
            max_iter=2,
            allow_delegation=False,
            llm=self.llm_local,
        )

    @agent
    def music_searcher(self) -> Agent:
        return Agent(
            config=self.agents_config['music_searcher'], # type: ignore[index]
            verbose=True,
            tools=[search_tracks],
            max_iter=2,
            llm=self.llm_local
        )

    @agent
    def technical_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['technical_analyst'], # type: ignore[index]
            verbose=True,
            tools=[get_track_analysis],
            llm=self.llm_local
        )

    @task
    def plan_music_search_task(self) -> Task:
        return Task(
            config=self.tasks_config["plan_music_search_task"], # type: ignore[index]
            output_pydantic=MusicSearchPlan,
        )

    @task
    def search_tracks_task(self) -> Task:
        return Task(
            config=self.tasks_config["search_tracks_task"], # type: ignore[index]
            context=[self.plan_music_search_task()],
            output_pydantic=DiscoveryResult,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Discovery crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            tracing=False,
        )
