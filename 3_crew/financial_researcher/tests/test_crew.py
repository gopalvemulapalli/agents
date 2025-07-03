import sys
import pytest

pytest.importorskip('crewai', reason='crewai must be installed to run these tests')

# Use relative import for local package
from financial_researcher.crew import ResearchCrew
from crewai import Agent, Task, Crew

@pytest.fixture
def research_crew():
    return ResearchCrew()

def test_agents_exist(research_crew):
    researcher = research_crew.researcher()
    analyst = research_crew.analyst()
    validator = research_crew.validator()
    assert isinstance(researcher, Agent)
    assert isinstance(analyst, Agent)
    assert isinstance(validator, Agent)

def test_tasks_exist(research_crew):
    research_task = research_crew.research_task()
    analysis_task = research_crew.analysis_task()
    validation_task = research_crew.validation_task()
    assert isinstance(research_task, Task)
    assert isinstance(analysis_task, Task)
    assert isinstance(validation_task, Task)

def test_crew_structure(research_crew):
    crew = research_crew.crew()
    assert isinstance(crew, Crew)
    assert hasattr(crew, 'agents1')
    assert hasattr(crew, 'tasks')
    assert crew.process.name == 'sequential' 