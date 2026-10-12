"""Measured stage boundaries, never simulated progress percentages."""
import time


class StageTimeline:
    def __init__(self,clock=time.monotonic):
        self.clock=clock
        self.started=None
        self.stages=[]

    def enter(self,name):
        current=self.clock()
        if self.started is None:self.started=current
        if self.stages and self.stages[-1]['duration_seconds'] is None:
            self.stages[-1]['duration_seconds']=round(current-self.stages[-1]['started_monotonic'],3)
        self.stages.append({'name':name,'started_monotonic':current,'duration_seconds':None})

    def report(self):
        current=self.clock()
        return {'elapsed_seconds':round(current-(self.started if self.started is not None else current),3),'stages':[dict(stage) for stage in self.stages],'measurement':'monotonic event boundaries'}
