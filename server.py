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

    if path.exists(json_url):
        return json.load(open(json_url))

    formula = parser(formula_string)

    # Dump
    dfa = formula.to_automaton()
    graph = dfa.to_graphviz()
    graph.render("./formulas/" + formula_filename + ".dot")

    import subprocess
    subprocess.run(["dot", "-Txdot_json", "./formulas/" + formula_filename + ".dot",
                    "-o", "./formulas/" + formula_filename + ".json"])

    return json.load(open(json_url))


app.run()
