#!/usr/bin/python3

# import requests
# import json
import json
import sys
from networkx.readwrite import json_graph
import networkx as nx
import jsons
import flask
from flask import jsonify

from flloat.parser.ldlf import LDLfParser

parser = LDLfParser()
formula_string = "<true*; a & b>tt"
formula = parser(formula_string)        # returns a LDLfFormula

# print(formula)                          # prints "<((true)* ; (a & b))>(tt)"
# print(formula.find_labels())            # prints {a, b}

dfa = formula.to_automaton()

graph = dfa.to_graphviz()
graph.render("./my-automaton")

dot_graph = nx.nx_pydot.read_dot("./my-automaton")

app = flask.Flask(__name__)
app.config["DEBUG"] = True


@app.route('/', methods=['GET'])
def home():
    # TODO: first dump the graph, then transform it to JSON and send it here using: https://stackoverflow.com/questions/40262441/how-to-transform-a-dot-graph-to-json-graph
    return json.dumps(json_graph.node_link_data(dot_graph))
    # json.dumps(json_graph.node_link_data(dot_graph))
    # return jsonify(dfa)


app.run()
