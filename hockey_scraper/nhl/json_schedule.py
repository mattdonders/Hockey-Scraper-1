"""
This module contains functions to scrape the json schedule for any games or date range
"""

from datetime import datetime, timedelta
import json
import time
import hockey_scraper.utils.shared as shared


def get_schedule(date_from, date_to):
    """
    Scrapes games in date range
    Ex: https://statsapi.web.nhl.com/api/v1/schedule?startDate=2010-10-03&endDate=2011-06-20
    
    :param date_from: scrape from this date
    :param date_to: scrape until this date
    
    :return: raw json of schedule of date range
    """
    page_info = {
        "url": 'https://statsapi.web.nhl.com/api/v1/schedule?startDate={a}&endDate={b}'.format(a=date_from, b=date_to),
        "name": date_from + "_" + date_to,
        "type": "json_schedule",
        "season": shared.get_season(date_from),
    }

    return json.loads(shared.get_file(page_info))


def chunk_schedule_calls(from_date, to_date):
    """
    The schedule endpoint sucks when handling a big date range. So instead I call in increments of n days.
    
    :param date_from: scrape from this date
    :param date_to: scrape until this date

    :return: raw json of schedule of date range
    """
    sched = []
    days_per_call = 100

    from_date = datetime.strptime(from_date, "%Y-%m-%d") 
    to_date = datetime.strptime(to_date, "%Y-%m-%d")
    num_days = (to_date - from_date).days + 1  # +1 since difference is looking for total number of days

    for offset in range(0, num_days, days_per_call):
        f_chunk = datetime.strftime(from_date + timedelta(days=offset), "%Y-%m-%d")

        # We need the min bec. if the chunks are evenly sized this prevents us from overshooting the max
        t_chunk = datetime.strftime(from_date + timedelta(days=min(num_days-1, offset+days_per_call-1)), "%Y-%m-%d")

        chunk_sched = get_schedule(f_chunk, t_chunk)
        sched.append(chunk_sched['dates'])

    return sched


def get_dates(games):
    """
    Given a list game_ids it returns the dates for each game.

    We go from the beginning of the earliest season in the sample to the end of the most recent
    
    :param games: list with game_id's ex: 2016020001
    
    :return: list with game_id and corresponding date for all games
    """
    # TODO: Needed??? Scared to change
    # Convert to str to avoid issues
    games = list(map(str, games))

    # Determine oldest and newest game
    games.sort()

    date_from = '-'.join([games[0][:4], '9', '1']) 
    year_to = games[-1][:4]

    # If the last game is part of the ongoing season then only request the schedule until that day
    # We get strange errors if we don't do it like this
    if year_to == shared.get_season(datetime.strftime(datetime.today(), "%Y-%m-%d")):
        date_to = '-'.join([str(datetime.today().year), str(datetime.today().month), str(datetime.today().day)])
    else:
        date_to = '-'.join([str(int(year_to) + 1), '7', '1'])  # Newest game in sample

    # TODO: Assume true is live here -> Workaround
    schedule = scrape_schedule(date_from, date_to, preseason=True, not_over=True)

    # Only return games we want in range
    games_list = []
    for game in schedule:
        if str(game['game_id']) in games:
            games_list.extend([game])

    return games_list


def scrape_schedule(date_from, date_to, preseason=False, not_over=False):
    """
    Calls getSchedule and scrapes the raw schedule Json
    
    :param date_from: scrape from this date
    :param date_to: scrape until this date
    :param preseason: Boolean indicating whether include preseason games (default if False)
    :param not_over: Boolean indicating whether we scrape games not finished. 
                     Means we relax the requirement of checking if the game is over. 
    
    :return: list with all the game id's
    """
    schedule = []
    schedule_json = chunk_schedule_calls(date_from, date_to)

    for chunk in schedule_json:
        for day in chunk:
            for game in day['games']:
                if game['status']['detailedState'] == 'Final' or not_over:
                    game_id = int(str(game['gamePk'])[5:])

                    if (game_id >= 20000 or preseason) and game_id < 40000:
                        schedule.append({
                                "game_id": game['gamePk'], 
                                 "date": day['date'], 
                                 "start_time": datetime.strptime(game['gameDate'][:-1], "%Y-%m-%dT%H:%M:%S"),
                                 "venue": game['venue'].get('name'),
                                 "home_team": shared.get_team(game['teams']['home']['team']['name'].upper()),
                                 "away_team": shared.get_team(game['teams']['away']['team']['name'].upper()),
                                 "home_score": game['teams']['home'].get("score"),
                                 "away_score": game['teams']['away'].get("score"),
                                 "status": game["status"]["abstractGameState"]
                        })

    return schedule
