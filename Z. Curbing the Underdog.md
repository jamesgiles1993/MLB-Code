Curbing the Underdog

Observation: My model overwhelmingly favors underdog bets

Problem: This may reflect a bias in the model's outputs

Hypothesis 1. Naivety Bias
My projections are biased toward the mean. If I tend to predict similar outcomes for the best and worst teams, the model would typically prefer the greater payout for betting underdogs
Test: Compare model score differentials to actual score differentials
Finding: Varies, but models generally predict similarly differentiated scores

Hypothesis 2. Model Inaccuracy
My projections are less accurate than Vegas's. Even with similar outcome distributions, I'm likely to underrate good teams and overrate bad ones, causing the model to prefer underdog bets
Test: Compare model favorite win% and runs scored by teams
Finding: I predict at least as accurately as Vegas

Hypothesis 3. Vegas Inaccuracy
Hypothesis 2 in reverse. Vegas's projections are less accurate than mine. As such, they tend to underrate good teams and overrate bad ones, causing my model to prefer the side with the higher payout
Test: Compare model favorite win% and runs scored by teams
Finding: We're pretty comparable. Come on. This was never going to be it.

Hypothesis 4. Math
An underdog bias is a mathematical inevitability
Let's imagine two identical models. The favorite determined by Model 1 (Vegas) will always have the greater win probability. Model 2 (me) even with the same distribution, would not guarantee the same.
Test: Determine underdog/favorite bet rates for identical models
Finding: This is definitely true, but doesn't explain all of the discrepancy. 


Conclusion:
Possible that what I'm seeing is a combination of accuracy differences and some sort of Bayes nonsense, not necessarily any sort of inherent biases.