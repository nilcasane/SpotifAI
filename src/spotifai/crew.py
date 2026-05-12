from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from spotifai.tools.spotify_tools import search_tracks, create_playlist

@CrewBase
class Spotifai():
    """SpotifAI crew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    agents: list[BaseAgent]
    tasks: list[Task]

llm_local = LLM(
    model="ollama/llama3.2",
    base_url="http://localhost:11434" # Port per defecte de Llama3
)
    @agent
    def music_searcher(self) -> Agent:
        return Agent(
            config=self.agents_config['music_searcher'], # type: ignore[index]
            verbose=True,
            tools=[search_tracks],
            llm=llm_local # Llama3.2
)
        )

    @agent
    def technical_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['technical_analyst'], # type: ignore[index]
            verbose=True,
            llm=llm_local # Llama3.2
)
        )

    @agent
    def playlist_manager(self) -> Agent:
        return Agent(
            config=self.agents_config['playlist_manager'], # type: ignore[index]
            verbose=True,
            tools=[create_playlist],
            llm=llm_local # Llama3.2
)
        )

    @task
    def search_tracks_task(self) -> Task:
        return Task(
            config=self.tasks_config["search_tracks_task"],
        )

    #@task
    #def analyze_tracks_task(self) -> Task:
    #    return Task(config=self.tasks_config["analyze_tracks_task"])

    @task
    def create_playlist_task(self) -> Task:
        return Task(config=self.tasks_config["create_playlist_task"])

    @crew
    def crew(self) -> Crew:
        """Creates the Spotifai crew"""
        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
