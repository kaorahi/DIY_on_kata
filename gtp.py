#!/usr/bin/env python3

# Minimal GTP engine

# (cf.) https://www.lysator.liu.se/~gunnar/gtp/gtp2-spec-draft2/gtp2-spec.html

import sys
import time
import select

from mcts import (
    make_node, playout,
    best_next_location, sorted_next_locations, principal_variation,
    find_child, loggable, opponent, winrate_for_player,
)
from neuralnet import NeuralNet

####################################################
# initialize

# constants
protocol_version = '2'
name = 'DIY_on_kata'
version = '0.0.0'

# states
move_history = []
nnet = None
genmove_sec = 1

# automatic flush
sys.stdout.reconfigure(line_buffering=True)

####################################################
# main loop

def start_gtp(katago_command):
    global nnet
    nnet = NeuralNet(katago_command)
    print('GTP ready', file=sys.stderr)
    run_gtp()

def run_gtp():
    for line in sys.stdin:
        gtp_id, command, args = parse(line)
        if command is None:  # ignore empty lines
            continue
        execute(gtp_id, command, args)
        if command == 'quit':
            break

####################################################
# subroutines for run_gtp

def parse(line):
    gtp_id = ''
    a = line.strip().split()
    if not a:
        return [None, None, None]
    if a[0].isdigit():
        gtp_id = a.pop(0)
    command, *args = a or ['']
    return [gtp_id, command, args]

def execute(gtp_id, command, args):
    success, result, follow_up = handle(command, args)
    response = build_response(gtp_id, success, result)
    print(response)
    follow_up_maybe(follow_up)
    print()  # newline

def handle(command, args):
    handler = command_table.get(command, handle_unknown_command)
    try:
        success, result, *follow_up = handler(*args)
    except (TypeError):
        success = False
        result = 'syntax error'
        follow_up = []
    return [success, result, follow_up]

def build_response(gtp_id, success, result):
    header_by_success = {True: '=', False: '?'}
    header = header_by_success[bool(success)]
    response = f'{header}{gtp_id} {result}'
    return response

def follow_up_maybe(follow_up):
    if follow_up:
        func, *args = follow_up
        func(*args)

####################################################
# command handlers

def handle_protocol_version():
    success = True
    result = protocol_version
    return [success, result]

def handle_name():
    success = True
    result = name
    return [success, result]

def handle_version():
    success = True
    result = version
    return [success, result]

def handle_known_command(command_name):
    success = True
    result = bool_text(command_name in command_table)
    return [success, result]

def handle_list_commands():
    success = True
    result = '\n'.join(command_table.keys())
    return [success, result]

def handle_quit():
    success = True
    result = ''
    return [success, result]

def handle_boardsize(size_text):
    result = ''
    try:
        size = int(size_text)
        success = size >= 2 and size <= 19
        if success:
            nnet.set_query_paremeter(boardXSize=size, boardYSize=size)
        else:
            result = 'unacceptable size'
    except (ValueError, TypeError):
        success = False
    return [success, result]

def handle_clear_board():
    move_history.clear()
    set_handicap_locations([])
    success = True
    result = ''
    return [success, result]

def handle_komi(komi_text):
    result = ''
    try:
        new_komi = float(komi_text)
        is_half_int = (2 * new_komi == int(2 * new_komi))
        success = is_half_int
        if success:
            nnet.set_query_paremeter(komi=new_komi)
        else:
            result = f'unacceptable komi "{komi_text}"'
    except (ValueError, TypeError):
        success = False
    return [success, result]

def handle_play(color, vertex):
    # fixme: need error check
    play(color, vertex)
    success = True
    result = ''
    return [success, result]

def handle_genmove(color):
    # setup
    stop_time = time.time() + genmove_sec
    root = make_node()
    player = color.upper()
    # playout
    while time.time() < stop_time or root['visits'] < 1:
        playout(root, move_history, player, nnet)
    # play
    best_location = best_next_location(root)
    play(player, best_location)
    # return
    success = True
    result = best_location
    return [success, result]

def handle_undo():
    success = bool(move_history)
    if success:
        move_history.pop(-1)
        result = ''
    else:
        result = 'cannot undo'
    return [success, result]

def handle_lz_analyze(*args):
    player, interval = decode_analyze_args(args)
    success = (interval >= 0)
    if success:
        result = ''
        follow_up = [lz_analyze, player, interval]
        return [success, result] + follow_up
    else:
        result = 'syntax error'
        return [success, result]

def handle_time_settings(main_time, byo_yomi_time, byo_yomi_stones):
    # effect
    global genmove_sec
    time1 = int(main_time) / 400
    time2 = int(byo_yomi_time) / int(byo_yomi_stones) * 0.9
    genmove_sec = max(time1, time2)
    # output
    success = True
    result = ''
    return [success, result]

def handle_fixed_handicap(number_of_stones_text):
    k = int(number_of_stones_text)
    success = 0 < k and k <= 9 and not move_history
    if success:
        locations = fixed_handicap_locations(k)
        set_handicap_locations(locations)
        result = ' '.join(locations)
    else:
        result = ''
    return [success, result]

def handle_unknown_command(*args):
    success = False
    result = 'unknown command'
    return [success, result]

####################################################
# command table

command_table = {
    # Required
    'protocol_version': handle_protocol_version,
    'name':             handle_name,
    'version':          handle_version,
    'known_command':    handle_known_command,
    'list_commands':    handle_list_commands,
    'quit':             handle_quit,
    'boardsize':        handle_boardsize,
    'clear_board':      handle_clear_board,
    'komi':             handle_komi,
    'play':             handle_play,
    'genmove':          handle_genmove,
    # For Lizzie
    'undo':             handle_undo,
    'lz-analyze':       handle_lz_analyze,
    'time_settings':    handle_time_settings,
    'fixed_handicap':   handle_fixed_handicap,
}

####################################################
# play

def play(color, vertex):
    player = color.upper()
    location = vertex.upper()
    if location == 'PASS':
        location = 'pass'
    move = [player, location]
    move_history.append(move)

####################################################
# analyze

def decode_analyze_args(args):
    # reused logic in TamaGo's _decode_analyze_arg
    player = next_player()
    interval = 0
    error_interval = -1.0
    args = [s.upper() for s in args]
    try:
        if args[0] in ['B', 'W']:
            player = args.pop(0)
        if args[0] in 'INTERVAL':
            args.pop(0)
        if args[0].isdigit():
            interval = int(args.pop(0)) / 100
    except (IndexError, ValueError):
        interval = error_interval
    if args:
        interval = error_interval
    return [player, interval]

def lz_analyze(player, interval):
    root = make_node()
    next_message_time = -1
    while not stdin_has_data():
        playout(root, move_history, player, nnet)
        if time.time() > next_message_time:
            print(lz_analyze_message(root))
            next_message_time = time.time() + interval

def lz_analyze_message(root):
    info_list = [
        lz_analyze_info(order, location, root)
        for order, location in enumerate(sorted_next_locations(root))
    ]
    return ' '.join(info_list)

def lz_analyze_info(order, location, root):
    child = find_child(root, location)
    visits = child['visits']
    black_winrate = child['black_winrate']
    player = next_player()
    winrate = winrate_for_player(black_winrate, player)
    prior = root['policy_by_location'][location]
    pv = ' '.join(principal_variation(root, location))
    message = ' '.join([
        'info',
        f'move {location}',
        f'visits {visits}',
        f'winrate {lz_integerize(winrate)}',
        f'prior {lz_integerize(prior)}',
        f'order {order}',
        f'pv {pv}'
    ])
    return message

def lz_integerize(x):
    return round(x * 10000)

####################################################
# handicap stones

def set_handicap_locations(locations):
    stones = [['B', loc] for loc in locations]
    nnet.set_query_paremeter(initialStones=stones)

# (ref.)
# http://www.lysator.liu.se/~gunnar/gtp/gtp2-spec-draft2/gtp2-spec.html#sec:fixed-handicap-placement

# Imported from add_handicap_stones in LizGoban.

def fixed_handicap_locations(number_of_stones):
    board_size = nnet.query_parameter['boardXSize']
    if board_size > 12:
        i1 = 3
    else:
        i1 = 2
    i2 = board_size // 2
    i3 = board_size - 1 - i1
    corners = [[i1, i3], [i3, i1], [i3, i3], [i1, i1]]
    edges = [[i2, i3], [i2, i1], [i1, i2], [i3, i2]]
    center = [i2, i2]
    all_stars = corners + edges + [center]
    stars = all_stars[:number_of_stones]
    locations = [nnet.location_for_coord(coord) for coord in stars]
    if number_of_stones in [5, 7]:
        center_location = nnet.location_for_coord(center)
        locations[-1] = center_location
    return locations

####################################################
# misc.

def bool_text(val):
    ret = {True: 'true', False: 'false'}
    return ret(bool(val))

def next_player():
    if not move_history:
        return 'B'
    player, location = move_history[-1]
    return opponent(player)

def stdin_has_data():
    rlist, _, _ = select.select([sys.stdin], [], [], 0)
    return bool(rlist)

####################################################
# (example)
# echo 'play B D4\ngenmove W' | ./gtp.py /PATH/TO/katago analysis -model /PATH/TO/model.bin.gz -config /PATH/TO/analysis.cfg -override-config logDir=,logFile=/dev/null 2> /dev/null
# (echo 'lz-analyze 20'; sleep 3) | ./gtp.py /PATH/TO/katago analysis -model /PATH/TO/model.bin.gz -config /PATH/TO/analysis.cfg -override-config logDir=,logFile=/dev/null 2> /dev/null

if __name__ == '__main__':
    katago_command = sys.argv[1:]
    start_gtp(katago_command)
