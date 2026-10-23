"""A first-week agent using only conditionals and the public API."""

from arena import Call, Check, Fold, RaiseTo


class MyFirstKuhnAgent:
    def act(self, observation, legal_actions):
        card = observation.toy_private_card

        if card == "K":
            for action in legal_actions:
                if isinstance(action, (RaiseTo, Call)):
                    return action

        if card == "J":
            for action in legal_actions:
                if isinstance(action, (Check, Fold)):
                    return action

        for action in legal_actions:
            if isinstance(action, (Check, Call)):
                return action

        return legal_actions[0]


def create_agent():
    return MyFirstKuhnAgent()
