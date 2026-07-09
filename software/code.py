from state import StateMachine
from state_startup import StartupState
from state_badge import BadgeState

machine = StateMachine()
machine.add_state(StartupState())
machine.add_state(BadgeState())

machine.go_to_state("startup")

while True:
    machine.update()
