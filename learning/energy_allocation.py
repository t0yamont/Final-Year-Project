"""Hand-checkable discrete exercise; costs are invented, not physical lap times."""
from functools import lru_cache
from itertools import product
import json

# Each segment costs either its base duration or base duration minus one benefit.
# Action 1 consumes one abstract energy token; action 0 consumes none.
BASE_TIMES = (10, 10, 10)
SAVINGS = (1, 4, 2)
BUDGET = 2


def exhaustive():
    candidates = []
    for actions in product((0, 1), repeat=len(BASE_TIMES)):
        if sum(actions) <= BUDGET:
            cost = sum(base - gain * action for base, gain, action in zip(BASE_TIMES, SAVINGS, actions))
            candidates.append((cost, actions))
    return min(candidates)


def dynamic_programming():
    @lru_cache(None)
    def value(segment, energy):
        if segment == len(BASE_TIMES):
            return 0, ()
        options = []
        for action in (0, 1):
            if action <= energy:
                future, tail = value(segment + 1, energy - action)
                options.append((BASE_TIMES[segment] - SAVINGS[segment] * action + future,
                                (action,) + tail))
        return min(options)
    return value(0, BUDGET)


if __name__ == "__main__":
    dp, brute = dynamic_programming(), exhaustive()
    assert dp == brute == (24, (0, 1, 1))
    print(json.dumps({"provenance": "invented_discrete_educational_costs", "dp": dp,
                      "exhaustive": brute, "agreement": True}, indent=2))
