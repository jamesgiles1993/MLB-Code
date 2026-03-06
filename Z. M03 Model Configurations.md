The Baseball Robot tends to predict close games. This result is robust to changes in:
    Parameters
        With and without WFX inputs
        With and without score and score-differential inputs
    Model Infrasture
        Layers
        Nodes
        Voting status
        Learning rate
        Activation function
        Batch size
    Model Count/Purpose:
        1 Model
            Kitchen Sink: All inputs, including WFX
            Interacted Outputs: No WFX in the model, WFX multiplied in post to calculate rates
        2 Models
            Interacted Inputs: First model predicts without weather. Second predicts with model 1 outputs and WFX interactions.
            Split: First model predicts without weather. Second predicts with model 1 outputs and WFX separately.
        3 Models
            Splitting out vs. safe: A binary for out/safe, a model for out, a model for safe

Despite the persistence of this problem, I'd like to record a bit about what I learned from prior tests to better plan for future ones. 


Model Count/Purpose:
    Baseline: Just player inputs/game states. No WFX.
        Still biased toward underdogs, but less so than with WFX
    1 Model
        Kitchen Sink: All inputs, including WFX
            Performs well overall but struggles with venues
        Interacted Outputs: No WFX in the model, WFX multiplied in post to calculate rates
            Seemingly decent at maintaining differences between teams, but still biased. Struggles with venues.
    2 Models
        Interacted Inputs: First model predicts without weather. Second predicts with model 1 outputs and WFX interactions.
            Decent with venues. Don't like that it treats poor and strong hitters the same in terms of how much WFX affect them.
        Split: First model predicts without weather. Second predicts with model 1 outputs and WFX separately.
            Decent with venues. Not super different from interacted inputs, but in theory, should allow for different effects by batter/pitcher quality, which is nice.
    3 Models
        Splitting out vs. safe: A binary for out/safe, a model for out, a model for safe
            Nice in theory. Complex to upkeep. Little to no benefit over simpler infrastucture.


Theory:
    WFX matter substantially for scores and over/unders, but should have less impact on how often the model prefers a favorite vs. an underdog. If a model without WFX still heavily favors the underdog, we can isolate the problem a little better.

Test Model:
    Single Model
    No WFX
    No score or score/differential inputs
    Max pareto-optimal standard deviation model

Evaluations:
    Do I predict underdogs/favorites roughly evenly for MLs?
        Figure 1A 
    Are my victory margins consistent with reality?
        Figure 2D

If variance is achieved, this would support theory that problem is largely in WFX/score inputs/voting
If it's still not achieved, this would suggest that it's caused largely by bad individual projections.



    
    
You will always prefer underdogs systemically. 


Let's assume two highly-similar models (perhaps just different seeds) that predict the correct winner of a baseball game on average 58% of the time.
If well-calibrated, on average, favorites will be assigned a 58% chance to win in both models.
However, Robot's favorites may not be Vegas's favorites. As such, there may be some Robot underdogs in Vegas's favorites.
Because of this, Robot will assign less than a 58% chance on average for Vegas's favorites to win.
This will lead to systemic underprediction. 