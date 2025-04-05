#!/usr/bin/env python3

# Use KataGo's neural network by calling KataGo itself.

# See KataGo's document for the query paremeters.
# https://github.com/lightvector/KataGo/blob/master/docs/Analysis_Engine.md

import subprocess
import sys
import json

class NeuralNet:
    def __init__(self, katago_command):
        self.query_counter = -1
        self.query_id = None
        self.query_parameter = {
            'maxVisits': 1,
            'includePolicy': True,
            'rules': 'tromp-taylor',
            'komi': 7.5,
            'boardXSize': 19,
            'boardYSize': 19,
            'initialStones': [],
        }
        shell = False
        if len(katago_command) == 1:
            shell = True
            katago_command = katago_command[0]
        self.process = subprocess.Popen(
            katago_command,
            shell=shell,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            text=True,
        )
        print(f'(Debug) KataGo command: {katago_command}', file=sys.stderr)

    ###################################################
    # public

    def set_query_paremeter(self, **kwargs):
        self.query_parameter.update(kwargs)

    def evaluate(self, moves):
        self._send_query(moves)
        response = self._receive_response()
        evaluation = self._get_evaluation(response)
        return evaluation

    def location_for_coord(self, coord):
        i, j = coord
        col_name = 'ABCDEFGHJKLMNOPQRST'  # 'I' is skipped.
        w = self.query_parameter['boardXSize']
        row = str(w - i)
        col = col_name[j]
        return col + row

    ###################################################
    # private

    # query

    def _send_query(self, moves):
        query_string = self._build_query(moves)
        print(f'(Debug) Query: {query_string}', file=sys.stderr)
        self.process.stdin.write(query_string + '\n')
        self.process.stdin.flush()

    def _build_query(self, moves):
        self._renew_query_id()
        base_query = {
            'id': self.query_id,
            'moves': moves,
        }
        query = self.query_parameter | base_query
        query_string = json.dumps(query)
        return query_string

    def _renew_query_id(self):
        self.query_counter += 1
        self.query_id = f'ID{self.query_counter}'

    # response

    def _receive_response(self):
        response_string = self.process.stdout.readline()
        response = json.loads(response_string)
        print(f'(Debug) Response: {response | {"policy": "SNIP!"}}', file=sys.stderr)
        self._exit_if_failed(response)
        return response

    def _exit_if_failed(self, response):
        if 'error' in response:
            raise RuntimeError(f"Error in response {response}.")
        if response['id'] != self.query_id:
            raise RuntimeError(f"Unexpected response {response['id']} for query {id_string}.")
        root_info = response['rootInfo']
        if root_info['visits'] != 1:
            raise RuntimeError(f"Unexpected visits ${root_info['visits']}.")

    # evaluation

    def _get_evaluation(self, response):
        policy_list = response['policy']
        policy_by_location = self._get_policy_dict(policy_list)
        root_info = response['rootInfo']
        black_winrate = root_info['rawWinrate']
        black_score = root_info['rawLead']
        evaluation = {
            'policy_by_location': policy_by_location,
            'black_winrate': black_winrate,
            'black_score': black_score,
        }
        return evaluation

    def _get_policy_dict(self, policy_list):
        policy_dict = {
            self._location_for_index(k): p for k, p
            in enumerate(policy_list) if p >= 0.0  # exclude illegal moves
        }
        return policy_dict

    def _location_for_index(self, k):
        w = self.query_parameter['boardXSize']
        h = self.query_parameter['boardYSize']
        if (k >= w * h):
            return 'pass'
        i = k // w
        j = k % w
        return self.location_for_coord([i, j])

####################################################
# (example)
# ./neuralnet.py /PATH/TO/katago analysis -model /PATH/TO/model.bin.gz -config /PATH/TO/analysis.cfg -override-config logDir=,logFile=/dev/null

if __name__ == '__main__':
    katago_command = sys.argv[1:]
    nnet = NeuralNet(katago_command)
    nnet.set_query_paremeter(rules='japanese', komi=6.5)
    moves = [['B', 'P6'], ['W', 'P5']]
    evaluation = nnet.evaluate(moves)
    print('eval', evaluation)
