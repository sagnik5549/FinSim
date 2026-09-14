import urllib.request
import json

# Create game
req = urllib.request.Request(
    'http://localhost:8000/api/game/new',
    data=json.dumps({'player_name': 'TestPlayer2'}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST',
)
resp = urllib.request.urlopen(req)
data = json.loads(resp.read())
game_id = data['game_id']
print(f"Game ID: {game_id}")

# Get state
req = urllib.request.Request(f'http://localhost:8000/api/game/state/{game_id}')
resp = urllib.request.urlopen(req)
state = json.loads(resp.read())
print(f"Status: {state['status']}, Day: {state['time']['career_day']}, Hour: {state['time']['game_hour']}, Market: {state['time']['market_status']}")
print(f"Portfolio: {state['financials']['total_value_cr']} Cr")
assert state['status'] == 'ACTIVE'
assert state['time']['market_status'] == 'OPEN'

# Advance 1 hour
req = urllib.request.Request(
    'http://localhost:8000/api/game/advance-hours',
    data=json.dumps({'game_id': game_id, 'hours': 1}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST',
)
resp = urllib.request.urlopen(req)
adv = json.loads(resp.read())
print(f"After advance: Day {adv['time']['career_day']}, Hour {adv['time']['game_hour']}, Market {adv['time']['market_status']}")
assert adv['time']['game_hour'] == 10

# Buy a stock
req = urllib.request.Request(
    'http://localhost:8000/api/trade/buy',
    data=json.dumps({'game_id': game_id, 'symbol': 'APXT', 'quantity': 1000}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST',
)
resp = urllib.request.urlopen(req)
trade = json.loads(resp.read())
print("Buy: " + trade['message'].replace('\u20b9', 'INR') + ", Success: " + str(trade['success']))
assert trade['success'] is True

# Get portfolio
req = urllib.request.Request(f'http://localhost:8000/api/portfolio/{game_id}')
resp = urllib.request.urlopen(req)
portfolio = json.loads(resp.read())
print(f"Portfolio has {len(portfolio['holdings'])} holdings")

# Get career
req = urllib.request.Request(f'http://localhost:8000/api/career/{game_id}')
resp = urllib.request.urlopen(req)
career = json.loads(resp.read())
print(f"Career: Level {career['career']['level']}, Role: {career['career']['role']}")
assert career['career']['level'] == 1
assert career['leave']['annual_allowance'] == 60

print("ALL API TESTS PASSED")
