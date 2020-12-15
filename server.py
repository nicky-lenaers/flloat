#!/usr/bin/python3

import os
from os import path
import flask
from flask import request, json
import hashlib
from flloat.parser.ldlf import LDLfParser

app = flask.Flask(__name__)
app.config["DEBUG"] = True


@app.route('/', methods=['GET'])
def home():
    parser = LDLfParser()
    formula_string = request.args.get('formula')
    formula_filename = hashlib.md5(formula_string.encode('ascii')).hexdigest()
    SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
    json_url = os.path.join(SITE_ROOT, "formulas", formula_filename + ".json")
    graph_url = os.path.join(SITE_ROOT, "formulas", formula_filename + ".dot")

    if path.exists(json_url) and path.exists(graph_url):
        return {
            "asDOT": open(graph_url).read(),
            "asJSON": json.load(open(json_url))
        }

    formula = parser(formula_string)

    # Dump
    dfa = formula.to_automaton()
    graph = dfa.to_graphviz()
    graph.render(graph_url)

    import subprocess
    subprocess.run(["dot", "-Txdot_json", graph_url,
                    "-o", "./formulas/" + formula_filename + ".json"])

    return {
        "asDOT": open(graph_url).read(),
        "asJSON": json.load(open(json_url))
    }


app.run()
