Z. Notes:
20250819:
I believe I solved my imputed pitcher problems. In short, I was filling missings with 0s for all players. This was correct except for imp_p and imp_b. These should have been filled with 1s because these players are imputed. Fixing this and retraining the pulls model on 2024 cleared up this issue and my imputed pitchers now test well.

20250624:
Steamer running infinitely
I was having this issue with Steamer running too long and never moving files over to the proper folder. I believe this is because there was a .cr file in my downloads unrelated to the current Steamer runner (I think the last steamer run just broke). The code checks for there being no such files before stopping, so it never got the chance to stop. Clearing out my downloads fixed this.

20250411:
Added bullpen id
I was able to extract relief pitcher ID numbers from URLs on the depth charts. I also added id to historic bullpen files with a merge with roster. This left some missings, but these wouldn't have merged on name (as we are doing currently) anyway. Also, some bullpens didn't have corresponding roster files, but this seems to be because there weren't games that day for that team.

20250407:
Confirmed Starters functionality not working
Funnily enough, I had this same bug exactly one year ago today and totally forgot. I'm guessing it's broken in the code, and I reinstalled it, so probably became a problem again. Players are always read in as confirmed starters. I added an integer function int() to ensure proper handling in lineup_importer.py.

20250119:
Pulls - Imputed Pitchers
I noticed that I was struggling with my imputed pitcher projections. This hasn't always been true, but it's been the case for months. They stay in too long. I realized that this is likely because of my data. Imputation flags were determined each PA and since pitchers PAs increase throughout a game, by the latter parts of the game, pitchers who started off with imputation flags no longer had them. The sample of pitchers who had imputation flags late in the game was small and basically just first time starters. I created a new variable imp_adj (or imp_p_either) that is status coming into the game. This seems to have addressed my pull concerns.

20250117: 
Pulls
I swappped to a system of assigning relief pitchers only 1) when the starter was pulled or 2) at the start of the inning.
This was done to avoid the random shuffling of relief pitchers each PA which prevented realistic inning-specific damage counters (like hits allowed that inning)
It would have worked for starting pitchers, but been wonky for relievers.

20241229:
Sportsbook Review Odds
I noticed some peculiar odds today. Teams favored by unreasonable margins for no apparent reason. I believe Sportsbook Review will, on occasion, update lines past the start of the game, so we might have some from the 7th inning or something. I switched to choosing the opening lines. I'm not sure these will be ideal either but they shouldn't be unreasonable. They just might not account for lineup changes.

20241224:
Imputed Pitcher Pulls
I've been noticing stronger-than-expected performance among pitchers with imputation flags = 1. This, of course, could occur for two reasons: imputed stats are too good or these pitchers have different leashes that the existing pull model is not accounting for. It's almost certainly exclusively the first one because the pull model should incorporate short leashes via IP_start, but I added an imputation flag to the pull model to hopefully get these guys out of there a little earlier and nerf 'em. Tweaks to pitcher imputations should probably still take place though.

20240907:
Solvers
Switching from the default PuLP solver (CBC) to GLPK (which I conda installed) had significant speed benefits for optimization. I was able to cut off an estimated 60% of runtime. If there are no repercussions to this, it'll be swell.

20240624:
Domes
Noticed Texas was getting really high totals in hot weather. Makes sense - model doesn't recognize it's a retractable roof. I'm now treating all domed games as 70 degrees.
This isn't a perfect solution because of how the ball flies closed vs. open, but it's not bad for now. Might be worth revisiting in the offseason.

20240619:
Parallel create_matchup_files
After some changes to the weather data and models, this function breaks when run in parallel. I am not sure why. I either get a pickling error or a complete crash. I have decided to matchup file creation sequentially for now. I wasn't getting a significant time savings anyway. Further research might be helpful, but isn't a high priority. I believe the dataset is just too big now to run in parallel.

20240407:
Minimum Starters
I noticed that pydfs's minimum starter constraint was not working at all, and upon further investigation into the player objects created by reading in the csv, I identified that they were always read in as starters. I had to go into the pydfs code, create a method to parse booleans, and use that. So lineup_import.py has been modified by me. 

20240403:
Deprecating Scraper API
I was using Scraper API to help assist with scraping Sportsbook Review. I got an email saying my trial was ending. Turns out they weren't doing anything for that particular scrape. Simply removing that step allows the code to work fine. Glad I didn't pay for it!

20240331:
Updated DKTEAM from WAS to WSH in Team Map
DraftKings files seem to have switched Washington's abbreviation from WAS to WSH. I believe this is DraftKings' doing, not my own, but I'm not 100%.
I believe this started at the start of the 2024 season.
This caused 2024 contest guides to exclude games with the Nationals as the away team.
Consequently, these simulations were run, but players could not be selected from these games.
I have fixed, to the best of my knowledge, all of the affected contest guides. I don't believe any other files were affected.
A quick search reveals that the only merges on DKTEAM were in Contest Guides.ipynb, so I'm optimistic that this is the only change needed.
I am not anticipating any further issues arising from this, but I'm noting it just in case.
It is perhaps worth noting that any Nationals team aggregations (let's say of player projections) could have two abbreviations. 