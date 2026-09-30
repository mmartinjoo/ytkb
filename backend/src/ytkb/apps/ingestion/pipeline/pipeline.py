from ytkb.apps.ingestion.pipeline.steps.step import Step, StepEnum


class Pipeline():
    steps: dict[str, Step] = {}
    
    def __init__(self, steps: list[Step]):
        for step in steps:
            self.steps[step.name] = step
    
    def get_step(self, name: str) -> Step:
        try:
            return self.steps[name]
        except KeyError as exc:
            raise ValueError(f"invalid step name: {name}")