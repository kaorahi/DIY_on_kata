#!/usr/bin/env python3

# Naive MCTS in basic Python

# Note:
# "move" is a pair of "player" and "location",
# e.g., ['B', 'Q16'] or ['W', 'D3'].

import math
import sys

####################################################
# node

def make_node():
    node = {
        'visits': 0,
        'child_by_location': {},  # dict
        'policy_by_location': None,
        'black_winrate': None,
    }
    return node

####################################################
# playout

def playout(root, moves_before_root, player, nnet):
    leaf, moves, ancestors = _descend_to_leaf(root, player)
    leaf_eval = nnet.evaluate(moves_before_root + moves)
    _expand_leaf(leaf, leaf_eval)
    _update_ancestors(ancestors, leaf_eval)
    return [leaf, moves, ancestors]

def _descend_to_leaf(root, player):
    node = root
    next_player = player
    moves = []
    ancestors = []
    while _is_expanded(node):
        # select
        location = _select_location(node, next_player)
        move = [next_player, location]
        # record
        moves.append(move)
        ancestors.append(node)
        # update
        node = _get_child(node, location)
        next_player = opponent(next_player)
    leaf = node
    return [leaf, moves, ancestors]

def _expand_leaf(leaf, leaf_eval):
    leaf['policy_by_location'] = leaf_eval['policy_by_location']
    leaf['black_winrate'] = leaf_eval['black_winrate']
    leaf['visits'] = 1

def _update_ancestors(ancestors, leaf_eval):
    for node in ancestors:
        node['visits'] += 1
        delta = leaf_eval['black_winrate'] - node['black_winrate']
        node['black_winrate'] += delta / node['visits']

####################################################
# node selection

def _select_location(node, player):
    priority = lambda location: _mcts_priority(node, player, location)
    locations = node['policy_by_location'].keys()
    selected_location = max(locations, key=priority)
    return selected_location

def _mcts_priority(node, player, location):
    # constants
    c_puct = 1.0
    value_for_unexpanded_move = 0.0
    # policy
    policy_by_location = node['policy_by_location']
    p = policy_by_location[location]
    # visits & value
    child = find_child(node, location)
    if child:
        n = child['visits']
        v = winrate_for_player(child['black_winrate'], player)
    else:
        n = 0
        v = value_for_unexpanded_move
    # priority
    c = c_puct * math.sqrt(node['visits'])
    puct = v + c * p / (n + 1)
    return puct

####################################################
# analysis

def best_next_location(node):
    sorted_locations = sorted_next_locations(node)
    if sorted_locations:
        return sorted_locations[0]
    else:
        return None

def sorted_next_locations(node):
    # sort children by visits
    criterion = lambda location: find_child(node, location)['visits']
    locations = node['child_by_location'].keys()
    sorted_locations = sorted(locations, key=criterion, reverse=True)
    return sorted_locations

def principal_variation(root, location):
    child = find_child(root, location)
    child_pv = _principal_variation_from_node(child)
    return [location] + child_pv

def _principal_variation_from_node(node):
    pv = []
    while _has_child(node):
        best_location = best_next_location(node)
        pv.append(best_location)
        node = find_child(node, best_location)
    return pv

####################################################
# node manipulation

def find_child(node, location):
    child_by_location = node['child_by_location']
    child = child_by_location.get(location)
    return child

def _get_child(node, location):
    child = find_child(node, location)
    if child is None:
        child = make_node()
        child_by_location = node['child_by_location']
        child_by_location[location] = child
    return child

def _has_child(node):
    has_child = bool(node['child_by_location'])
    return has_child

def _is_expanded(node):
    expanded = bool(node['policy_by_location'])
    return expanded

def loggable(node):
    # trim too long items
    child_locations = list(node['child_by_location'].keys())
    children_text = f"SNIP!({','.join(child_locations)})"
    policy_text = f"SNIP!({len(node['policy_by_location'])})"
    mask = {
        'child_by_location': children_text,
        'policy_by_location': policy_text,
    }
    trimmed_node = node | mask
    return trimmed_node

####################################################
# flip

def opponent(player):
    if player == 'B':
        return 'W'
    else:
        return 'B'

def winrate_for_player(black_winrate, player):
    if player == 'B':
        return black_winrate
    else:
        return 1.0 - black_winrate

####################################################
# (example)
# ./mcts.py /PATH/TO/katago analysis -model /PATH/TO/model.bin.gz -config /PATH/TO/analysis.cfg -override-config logDir=,logFile=/dev/null 2> /dev/null

if __name__ == '__main__':
    from neuralnet import NeuralNet
    katago_command = sys.argv[1:]
    moves_before_root = [
        ['B', 'Q16'], ['W', 'D4'], ['B', 'Q4'], ['W', 'D16'], ['B', 'Q10'],
    ]
    player = 'W'
    root = make_node()
    nnet = NeuralNet(katago_command)
    # See KataGo's document for the query paremeters.
    # https://github.com/lightvector/KataGo/blob/master/docs/Analysis_Engine.md
    nnet.set_query_paremeter(rules='japanese', komi=6.5)
    for t in range(10):
        leaf, moves, ancestors = playout(root, moves_before_root, player, nnet)
        print(root['visits'], moves, leaf['black_winrate'])
    print('root', loggable(root))
    for location, child in root['child_by_location'].items():
        print(location, loggable(child))
