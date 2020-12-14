#!/usr/bin/python3

import os
import sys
from networkx.readwrite import json_graph
import networkx as nx
import flask
from flask import jsonify, request, json
import hashlib
from flloat.parser.ldlf import LDLfParser
from PySimpleAutomata.automata_IO import dfa_to_json, dfa_dot_importer

# parser = LDLfParser()
# formula_string = "<true*; a & b>tt"
# formula = parser(formula_string)        # returns a LDLfFormula

# print(formula)                          # prints "<((true)* ; (a & b))>(tt)"
# print(formula.find_labels())            # prints {a, b}

# dfa = formula.to_automaton()
# graph = dfa.to_graphviz()
# graph.render("./my-automaton")

# dot_graph = nx.nx_pydot.read_dot("./my-automaton")

app = flask.Flask(__name__)
app.config["DEBUG"] = True


@app.route('/', methods=['GET'])
def home():
    print("FORMULA: ", request.args.get('formula'))

    parser = LDLfParser()
    formula_string = request.args.get('formula')
    formula = parser(formula_string)

    formula_filename = hashlib.md5(formula_string.encode('ascii')).hexdigest()

    # Dump
    dfa = formula.to_automaton()
    graph = dfa.to_graphviz()
    graph.render("./formulas/" + formula_filename + ".dot")

    import subprocess
    subprocess.run(["dot", "-Txdot_json", "./formulas/" + formula_filename + ".dot",
                    "-o", "./formulas/" + formula_filename + ".json"])

    SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
    json_url = os.path.join(SITE_ROOT, "formulas", formula_filename + ".json")

    return json.load(open(json_url))


app.run()
