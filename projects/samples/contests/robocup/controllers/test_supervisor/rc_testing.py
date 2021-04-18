from abc import ABC, abstractmethod
from controller import Supervisor

import numpy as np

POS_ABS_TOL = 0.03 # [m]

VALID_STATES = ["INITIAL","READY","SET","PLAYING","FINISH"]

def target_to_def_name(target):
    return target.upper().replace(" ","_")

class StatusInformation:
    def __init__(self, system_time, simulated_time, gc_status):
        self.system_time = system_time
        self.simulated_time = simulated_time
        self._state_starts = {}
        self.gc_status = None
        self._updateGC(system_time, simulated_time, gc_status)

    def update(self, system_time, simulated_time, gc_status):
        self.system_time = system_time
        self.simulated_time = simulated_time
        self._updateGC(system_time, simulated_time, gc_status)

    def getFormattedTime(self):
        return "[{:08.3f}|{:08.3f}]".format(self.system_time, self.simulated_time)

    def getGameState(self):
        if self.gc_status is None:
            return None
        return self.gc_status.game_state.split("_")[1]

    def getStateStart(self, state, clock_type):
        state_start = self._state_starts.get(state)
        if state_start is None:
            return -1
        return self._state_starts[state][clock_type]

    def _updateGC(self, system_time, simulated_time, gc_status):
        if gc_status is not None:
            update_start = (self.gc_status is None or
                            gc_status.game_state != self.gc_status.game_state)
            if update_start:
                state = gc_status.game_state.split("_")[1]
                self._state_starts[state] = {
                    "System" : system_time,
                    "Simulated" : simulated_time
                }
        self.gc_status = gc_status

class TimeSpecification(ABC):
    @abstractmethod
    def isActive(self, status):
        pass

    @abstractmethod
    def isFinished(self, status):
        pass

    def getCurrentTime(self, status):
        offset = 0.0
        if self._state is not None:
            offset = status.getStateStart(self._state, self._clock_type)
            if offset < 0:
                return -1
        if self._clock_type == "Simulated":
            return status.simulated_time - offset
        elif self._clock_type == "System":
            return status.system_time - offset
        raise RuntimeError(f"Unexpected value for _clock_type: {self._clock_type}")

    def buildFromDictionary(properties):
       t = properties["time"]
       clock_type = properties.get("clock_type", "Simulated")
       state = properties.get("state")
       if clock_type not in ["Simulated", "System"]:
           raise RuntimeError(f"clock_type: '{clock_type}' unknown")
       if isinstance(t,float) or isinstance(t,int):
           return TimePoint(t, clock_type, state)
       elif isinstance(t, list):
           if len(t) == 2:
               return TimeInterval(t[0], t[1], clock_type, state)
           raise RuntimeError(f"Invalid size for time: {len(t)}")
       raise RuntimeError("Invalid type for time")

class TimeInterval(TimeSpecification):
    def __init__(self, start, end, clock_type, state):
       self._start = start
       self._end = end
       self._clock_type = clock_type
       if state is not None and state not in VALID_STATES:
           raise RuntimeError("Invalid state: {state}")
       self._state = state

    def isActive(self, status):
        t = self.getCurrentTime(status)
        return t > self._start and t <= self._end

    def isFinished(self, status):
        t = self.getCurrentTime(status)
        return t > self._end

class TimePoint(TimeSpecification):
    def __init__(self, t, clock_type, state):
       self._t = t
       self._clock_type = clock_type
       if state is not None and state not in VALID_STATES:
           raise RuntimeError("Invalid state: {state}")
       self._state = state

    def isActive(self, status):
        t = self.getCurrentTime(status)
        return t > self._t

    def isFinished(self, status):
        t = self.getCurrentTime(status)
        return t > self._t

    def __str__(self):
        return f"t:{self._t}, clock_type:{self._clock_type}, state: {self._state}"

class Test:
    def __init__(self, name, target = None, position = None, rotation = None,
                 state = None, penalty = None, yellow_cards = None):
        self._name = name
        self._target = target
        self._position = position
        self._rotation = rotation
        self._state = state
        self._penalty = penalty
        self._yellow_cards = yellow_cards
        self._msg = []
        self._success = True

    def perform(self, status, supervisor):
        if self._position is not None:
            self._testTargetPosition(status, supervisor)
        if self._rotation is not None:
            self._testTargetRotation(status, supervisor)
        if self._penalty is not None:
            self._testTargetPenalty(status, supervisor)
        if self._yellow_cards is not None:
            self._testYellowCards(status, supervisor)
        if self._state is not None:
            self._testState(status, supervisor)

    def hasPassed(self):
        return self._success

    def printResult(self):
        if self._success:
            print(f"[PASS] Test {self._name}")
        else:
            print(f"[FAIL] Test {self._name}")
            for m in self._msg:
                print(f"\tCaused by {m}")

    def buildFromDictionary(dic):
        c = Test(dic["name"])
        c._target = dic.get("target")
        c._position = dic.get("position")
        c._rotation = dic.get("rotation")
        c._state = dic.get("state")
        c._penalty = dic.get("penalty")
        c._yellow_cards = dic.get("yellow_cards")
        return c

    def _getTargetGCData(self, status):
        splitted_target = self._target.split(" ")
        if len(splitted_target) != 3:
            raise RuntimeError("Invalid target to get GameController data from")
        team_color = splitted_target[0].upper()
        player_idx = int(splitted_target[2]) - 1
        for i in range(2):
            if status.gc_status.teams[i].team_color == team_color:
                return status.gc_status.teams[i].players[player_idx]
        return None


    def _testTargetPosition(self, status, supervisor):
        if self._target is None:
            raise RuntimeError("{self._name} tests position and has no target")
        def_name = target_to_def_name(self._target)
        target = supervisor.getFromDef(def_name)
        received_pos = target.getField('translation').getSFVec3f()
        if not np.allclose(self._position, received_pos, atol = POS_ABS_TOL):
            failure_msg = f"Position Invalid at {status.getFormattedTime()}: "\
                f"expecting {self._position}, received {received_pos}"
            print(f"Failure in test {self._name}\n\t{failure_msg}")
            self._msg.append(failure_msg)
            self._success = False
            # Each test can only fail once to avoid spamming
            self._position = None

    def _testTargetRotation(self, status, supervisor):
        if self._target is None:
            raise RuntimeError("{self._name} tests position and has no target")
        # TODO Implement of rotation check is currently disabled, to be
        # properly introduced, it will require to be able to compare properly
        # the axis-angle obtained. Moreover, after reset, it does not seem that
        # the robot respects has the exact orientation used in pose

    def _testTargetPenalty(self, status, supervisor):
        if self._target is None:
            raise RuntimeError("{self._name} tests position and has no target")
        gc_data = self._getTargetGCData(status)
        if gc_data.penalty != self._penalty:
            failure_msg = f"Invalid penalty at {status.getFormattedTime()}: "\
                f"for {self._target}: received {gc_data.penalty},"\
                f"expecting {self._penalty}"
            self._msg.append(failure_msg)
            self._penalty = None
            # Each test can only fail once to avoid spamming
            self._success = False

    def _testState(self, status, supervisor):
        received_state = status.getGameState()
        expected_state = self._state
        if expected_state != received_state:
            failure_msg = f"Invalid state at {status.getFormattedTime()}: "\
                f"received {received_state}, expecting {expected_state}"
            self._msg.append(failure_msg)
            self._state = None
            # Each test can only fail once to avoid spamming
            self._success = False

    def _testYellowCards(self, status, supervisor):
        if self._target is None:
            raise RuntimeError("{self._name} tests position and has no target")
        gc_data = self._getTargetGCData(status)
        received = gc_data.number_of_yellow_cards
        if received != self._penalty:
            failure_msg = \
                f"Invalid number of yellow cards at {status.getFormattedTime()}: "\
                f"for {self._target}: received {received},"\
                f"expecting {self._yellow_cards}"
            self._msg.append(failure_msg)
            self._yellow_cards = None
            # Each test can only fail once to avoid spamming
            self._success = False

class Action:

    def __init__(self, target, position = None, force = None, velocity = None):
        self._def_name = target_to_def_name(target)
        self._position = position
        self._force = force
        self._velocity = velocity

    def buildFromDictionary(dic):
        a = Action(dic["target"])
        a._position = dic.get("position")
        a._force = dic.get("force")
        a._velocity = dic.get("velocity")
        return a


    def perform(self, supervisor):
        obj = supervisor.getFromDef(self._def_name)
        obj.resetPhysics()
        if self._position is not None:
            self._setPosition(obj)
        if self._force is not None:
            self._setForce(obj)
        if self._velocity is not None:
            self._setVelocity(obj)

    def _setPosition(self, obj):
        print(f"Setting {self._def_name} to {self._position}")
        obj.getField("translation").setSFVec3f(self._position)

    def _setForce(self, obj):
        obj.addForce(self._force)

    def _setVelocity(self, obj):
        obj.setVelocity(self._velocity)



class Event:
    def __init__(self, time_spec, tests=[], actions=[], done=False):
        self._time_spec = time_spec
        self._tests = tests
        self._actions = actions
        self._done = done

    def isActive(self, status):
        return self._time_spec.isActive(status)

    def isFinished(self, status):
        #TODO an event might also been 'finished' if all tests have failed and
        # no action is there
        return self._time_spec.isFinished(status)

    """
    Applies tests and *afterwards* apply actions
    """
    def perform(self, status, supervisor):
        for c in self._tests:
            c.perform(status, supervisor)
        for a in self._actions:
            a.perform(supervisor)

    def getNbTests(self):
        return len(self._tests)

    """
    Return the number of tests that have not failed. It is the caller
    responsibility to make sure event is finished before calling this function.
    """
    def getNbTestsPassed(self):
        return sum([1 for c in self._tests if c.hasPassed()])

    def printResults(self):
        for c in self._tests:
            c.printResult()

    def buildFromDictionary(dic):
        tests_str = dic.get("tests")
        tests = []
        if tests_str is not None:
            for test_dic in tests_str:
                tests.append(Test.buildFromDictionary(test_dic))
        actions_str = dic.get("actions")
        actions = []
        if actions_str is not None:
            for action_dic in actions_str:
                actions.append(Action.buildFromDictionary(action_dic))
        event = Event(TimeSpecification.buildFromDictionary(dic["timing"]), tests, actions)
        # TODO build actions to add them
        return event


class Scenario:
    def __init__(self, events = []):
        self._waiting_events = events
        self._finished_events = []

    def step(self, status, supervisor):
        finished_events = []
        for i in range(len(self._waiting_events)):
            e = self._waiting_events[i]
            if e.isActive(status):
                e.perform(status, supervisor)
            if e.isFinished(status):
                finished_events.insert(0,i)
        for i in finished_events:
            print(f"{status.getFormattedTime()} Finished treating an event")
            e = self._waiting_events.pop(i)
            e.printResults()
            self._finished_events.append(e)

    def isFinished(self):
        return len(self._waiting_events) == 0

    def getNbTests(self):
        waiting = sum([e.getNbTests() for e in self._waiting_events])
        finished = sum([e.getNbTests() for e in self._finished_events])
        return waiting + finished

    def getNbTestsPassed(self):
        return sum([e.getNbTestsPassed() for e in self._finished_events])

    def printResults(self):
        for e in self._waiting_events:
            e.printResults()
        for e in self._finished_events:
            e.printResults()
        nb_tests = self.getNbTests()
        nb_tests_passed = self.getNbTestsPassed()
        print(f"TEST RESULTS: {nb_tests_passed}/{nb_tests}")

    def buildFromList(event_list):
        s = Scenario()
        for e in event_list:
            s._waiting_events.append(Event.buildFromDictionary(e))
        return s

