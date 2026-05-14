#!/usr/bin/env python
import json
import sys

from spotifai.flows.spotifai_flow import SpotifAIFlow

def run_flow(crewai_trigger_payload: dict | None = None):
    flow = SpotifAIFlow()
    if crewai_trigger_payload:
        return flow.kickoff({"crewai_trigger_payload": crewai_trigger_payload})

    # Default quick-run payload for local testing
    return flow.kickoff({"crewai_trigger_payload": {"user_request": "Twenty One Pilots"}})

def kickoff(crewai_trigger_payload: dict | None = None):
    """Console entry point used by `crewai run`."""
    run_flow(crewai_trigger_payload)

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

    run_flow(trigger_payload)

if __name__ == "__main__":
    kickoff()