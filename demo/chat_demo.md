# Telegram Bot Demo

## Sample messages (translated from Polish)

### Scenario 1:
User wants to add a new workout to the database, and the bot guides them through the process.

### User
```
Add a new workout: swimming, 1600m, 35min, 133 bpm, RPE 7.
```

### Bot
```
Analyzing your message...
Analyzing your data...

Here's your workout:

Date: 2026-04-01
Discipline: Swimming
Time: 35 min
Distance: 1.6 km
RPE: 7
HR: 133
Notes:

Is everything correct?
```
### User
```
Notes: 1000m continuous, 6x100m
```

### Bot
```
Making corrections...
Corrected! New data:

Date: 2026-04-01
Discipline: Swimming
Time: 35 min
Distance: 1.6 km
RPE: 7
HR: 133
Notes: 1000m continuous, 6x100m

Is everything correct now?
```
### User
``` 
Yes
``` 

**Note:** The same action can be acomplished by sending a screenshot of the workout from Garmin Connect or Strava. The bot will extract the data and add it to the database. The user can then edit the workout details if needed.

### Scenario 2: 
User asks about this weeks trainings, and the bot provides an analysis based on recent workouts.
### User
```
What did I train this week?
```

### Bot
```
I'm analyzing your message...
I'm analyzing your training history...

This week, you focused on building your running and swimming volume, completing three runs (19.5 km) and one heavy swim. Your intensity is appropriate, although "parkrun" at RPE 7 suggests a too-fast pace, which should be more controlled during this base-building period. You lack consistency in your cycling training, which is critical in preparing for the 1/2 IM. Use low-RPE workouts to improve your technique, and save the heavier workouts for specific pace blocks. Focus on consistency on the bike to avoid endurance deficits before Malbork.

Statistics (2026-03-30 – 2026-04-02):
Swim: 35 min (1.6 km)
Run: 118 min (13.55 km)
Gym: 37 min
Total time: 190 min
Average RPE: 5.0
```

### Scenario 3:
User asks for a weekend training plan, and the bot creates a plan based on recent workouts.

### User
```
Prepare a weekend plan.
```

### Bot
```
I'm analyzing your message...
I'm preparing a training plan...

You're in a strong cycle; yesterday's double was demanding. Considering recovery before the next microcycle:

Friday (April 3): Active Recovery / Mobility
- Discipline: Stretching and mobilization (home/gym)
- Time: 40 min
- Intensity: RPE 2 (very low)
- Goal: Muscle relaxation after the last two weeks, preparation for a solid weekend.

Saturday (April 4): Building Aerobic Power (Cycling)
- Discipline: Cycling (road – avoid open areas due to 20 km/h winds)
- Time: 120 min
- Distance: approx. 40-45 km
- Intensity: RPE 5 (steady, moderate pace, avoid peak G-forces)
- Note: Due to the wind, choose a more sheltered/forest route.

Sunday (April 5): Running Strength and Technique
- Discipline: Running (Cross/City) + Swimming
- Run: 50 min, approx. 8-9 km (RPE 6, include 5 x 30s jogs to improve technique)
- Swimming: 45 min (approx. 1.8 - 2.0 km) – easy swimming with an emphasis on extended water holding. - Intensity: RPE 6

Fitness is built through patience, not overtraining. Stick to your plan; the wind on Saturday isn't an excuse, but rather a part of building your "triathlete character." Get to work!