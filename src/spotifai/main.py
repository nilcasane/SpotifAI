#!/usr/bin/env python
from pathlib import Path
import json
import sys

from crewai.flow import Flow

from spotifai.flows.spotifai_flow import SpotifAIFlow


def kickoff(crewai_trigger_payload: dict | None = None):
    """Instantiate and run the SpotifAI Flow.

    If `crewai_trigger_payload` is provided it will be forwarded to the
    Flow's @start() method (this matches the pattern used by CrewAI flows).
    """
    flow = SpotifAIFlow()
    if crewai_trigger_payload:
        return flow.kickoff({"crewai_trigger_payload": crewai_trigger_payload})

    # Default quick-run payload for local testing
    return flow.kickoff({"crewai_trigger_payload": {"user_request": "Queen"}})


def plot():
    flow = SpotifAIFlow()
    flow.plot()


def run_with_trigger():
    """Run the flow with a trigger payload passed on the command line.

    Usage: python -m spotifai.main run_with_trigger '{"user_request": "Chill workout"}'
    """
    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    return kickoff(trigger_payload)


if __name__ == "__main__":
    kickoff()
