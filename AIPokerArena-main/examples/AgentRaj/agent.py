"""A first-week agent using only conditionals and the public API."""

from arena import Call, Check, Fold, RaiseTo
import random


class MyFirstKuhnAgent:

    def new_match(self, context):
        # Include player_id so identical agents do not share the same random stream.
        self.rng = random.Random(f"{context.seed}:{context.player_id}")

    def act(self, observation, legal_actions):
        card = observation.toy_private_card


####################################################################################

        # King takes care of Table Options 3,6,9,12
        if card == "K":

            #! Player 0 - Decision 1 - Check or Bet - Table Option 3
            # This occurs when the round starts (no previous actions)
            if observation.seat == 0 and len(observation.action_history) == 0:  

                randNum = self.rng.random()

                #50% Bet
                if randNum < 0.50:
                    for action in legal_actions:
                        if isinstance(action, RaiseTo):
                            return action

                #50% Check
                else:
                    for action in legal_actions:
                        if isinstance(action, Check):
                            return action
                

            # Player 1 - Either Decision 2 or Decision 3
            elif observation.seat == 1 and len(observation.action_history) == 1:   
                first_action = observation.action_history[0].action

                #! Player 1 - Decision 2 - Check or Bet - Table Option 6
                # This occurs if Player 0 chose to Check
                if isinstance(first_action, Check):                    
                    
                    randNum = self.rng.random()

                    #90% Bet
                    if randNum < 0.90:
                        for action in legal_actions:
                            if isinstance(action, RaiseTo):
                                return action
    
                    #10% Check
                    else:
                        for action in legal_actions:
                            if isinstance(action, Check):
                                return action


                #! Player 1 - Decision 3 - Call or Fold - Table Option 9
                # This occurs if Player 0 chose to Bet
                elif isinstance(first_action, RaiseTo):

                    #100% Call
                    for action in legal_actions:
                        if isinstance(action, Call):
                            return action


            #! Player 0 - Decision 4 - Call or Fold - Table Option 12
            # This occurs if Player 0 chose to Check then Player 1 chose to Bet
            elif observation.seat == 0 and len(observation.action_history) == 2:    

                #100% Call
                for action in legal_actions:
                    if isinstance(action,Call):
                        return action


####################################################################################

        # Queen takes care of Table Options 2,5,8,11
        if card == "Q":

            #! Player 0 - Decision 1 - Check or Bet - Table Option 2
            # This occurs when the round starts (no previous actions)
            if observation.seat == 0 and len(observation.action_history) == 0:  

                #100% Check
                for action in legal_actions:
                    if isinstance(action, Check):
                        return action
                

            # Player 1 - Either Decision 2 or Decision 3
            elif observation.seat == 1 and len(observation.action_history) == 1:   
                first_action = observation.action_history[0].action

                #! Player 1 - Decision 2 - Check or Bet - Table Option 5
                # This occurs if Player 0 chose to Check
                if isinstance(first_action, Check):                    

                    #100% Check
                    for action in legal_actions:
                        if isinstance(action, Check):
                            return action


                #! Player 1 - Decision 3 - Call or Fold - table Option 8
                # This occurs if Player 0 chose to Bet
                elif isinstance(first_action, RaiseTo):

                    randNum = self.rng.random()

                    #40% Fold
                    if randNum < 0.40:
                        for action in legal_actions:
                            if isinstance(action, Fold):
                                return action

                    #60% Call
                    else:
                        for action in legal_actions:
                            if isinstance(action, Call):
                                return action


            #! Player 0 - Decision 4 - Call or Fold - Table Option 11
            # This occurs if Player 0 chose to Check then Player 1 chose to Bet
            elif observation.seat == 0 and len(observation.action_history) == 2:    

                randNum = self.rng.random()

                #20% Fold
                if randNum < 0.20:
                    for action in legal_actions:
                        if isinstance(action, Fold):
                            return action

                #80% Call
                else:
                    for action in legal_actions:
                        if isinstance(action,Call):
                            return action


####################################################################################

        # Jack takes care of Table Options 1,4,7,10
        if card == "J":

            #! Player 0 - Decision 1 - Check or Bet - Table Option 1
            # This occurs when the round starts (no previous actions)
            if observation.seat == 0 and len(observation.action_history) == 0:  

                randNum = self.rng.random()

                #75% Check
                if randNum < 0.75:
                    for action in legal_actions:
                        if isinstance(action, Check):
                            return action

                #25% Bet
                else:
                    for action in legal_actions:
                        if isinstance(action, RaiseTo):
                            return action

            # ? Player 1 - Either Decision 2 or Decision 3
            elif observation.seat == 1 and len(observation.action_history) == 1:   
                first_action = observation.action_history[0].action

                #! Player 1 - Decision 2 - Check or Bet - Table Option 4
                # This occurs if Player 0 chose to Check
                if isinstance(first_action, Check):                    

                    randNum = self.rng.random()

                    #25% Bet
                    if randNum < 0.25:
                        for action in legal_actions:
                            if isinstance(action, RaiseTo):
                                return action

                    #75% Check
                    else:
                        for action in legal_actions:
                            if isinstance(action, Check):
                                return action


                #! Player 1 - Decision 3 - Call or Fold - Table Option 7
                # This occurs if Player 0 chose to Bet
                elif isinstance(first_action, RaiseTo):

                    randNum = self.rng.random()

                    #80% Fold
                    if randNum < 0.80:
                        for action in legal_actions:
                            if isinstance(action, Fold):
                                return action

                    #20% Call
                    else:
                        for action in legal_actions:
                            if isinstance(action, Call):
                                return action


            #! Player 0 - Decision 4 - Call or Fold - Table Option 10
            # This occurs if Player 0 chose to Check then Player 1 chose to Bet
            elif observation.seat == 0 and len(observation.action_history) == 2:    

                randNum = self.rng.random()

                #60% Fold
                if randNum < 0.60:
                    for action in legal_actions:
                        if isinstance(action, Fold):
                            return action

                #40% Call
                else:
                    for action in legal_actions:
                        if isinstance(action,Call):
                            return action


        # If something goes wrong with the decisions, it just plays the first
        # legal action as a failsafe
        return legal_actions[0]


def create_agent():
    return MyFirstKuhnAgent()
