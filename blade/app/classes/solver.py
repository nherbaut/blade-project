# coding: utf-8

from . import bdd
import numpy as np
from app.classes.topsis import topsis
from app.classes.bdd import Bdd


class Solver:
    """Solver object is responsible of doing calculations to find the best alternative when requirements are provided."""

    def __init__(self, weights, requirements):
        """Initialize the object by creating a new solving session using user requirements and preferences
        
        Arguments:
            weights {[array[int]]} -- [User preferences]
            requirements {[array[(int, int)]]} -- [User requirements]
        """
        self.bdd = Bdd()
        self.new(weights, requirements, False)

    def __del__(self):
        """Disconnects from bdd and destroy the bdd object when called"""

        self.bdd.disconnect()
        del self.bdd

    def new(self, weights, requirements, save):
        """Initialize a new solving session, and retrieve attributes from BDD
        
        Arguments:
            weights {[int[]]} -- [User preferences]
            requirements {[(int, int)[]]} -- [User requirements]
        """
        self.alternatives_values = []
        self.abst_attrs_values = []

        self.abst_attrs_values = self.bdd.get_abst_labels_values()
        self.alternatives_attrs, self.costs, self.types = self.get_attributes_metadata()
        self.alternatives = self.bdd.get_alternatives()
        self.weights = weights
        self.requirements = requirements
        self.update_costs_with_reqs()

        self.results = {
            'disqualified': [],
            'considered': [],
            'optimum_id': None
        }

        if save:
            self.save_results()

    def update_costs_with_reqs(self):
        """Update default costs using values selected by the user"""
        for i in range(len(self.types)):
            if self.types[i] == "boolean":
                self.costs[i] = int(self.requirements[i][1])

    def save_results(self):
        """Save results in database"""

        self.bdd.save_results(self.alternatives, self.requirements, self.weights, self.costs, self.results)

    def get_attributes_metadata(self):
        """Get attr labels list costs, and related types in BDD and returns them as a tuple of arrays
        
        Returns:
            [(str[], int[])] -- [Tuple of arrays containing labels costs and datatypes]
        """
        labels = []
        costs = []
        types = []

        attr_meta = self.bdd.get_attributes_metadata()
        for a in attr_meta:
            labels.append(a["name"])
            costs.append(a["defaultCost"])
            types.append(a["type"])

        return labels, costs, types

    def format_value(self, value):
        """Converts litteral value of alternatives attributes to numerical using correspondance array
        
        Arguments:
            value {[lambda]} -- [Value to convert (if needed)]
        
        Returns:
            [float] -- [Converted value]
        """
        for attr in self.abst_attrs_values:
            if attr["name"] == value:
                return attr["value"]
        return value

    def gen_alternatives_values_array(self):
        """Retrieves all values from alternatives attributes and store them in an array for TOPSIS algorithm"""

        for b in self.results["considered"]:
            alternative = []
            for p in self.alternatives_attrs:
                alternative.append(self.format_value(b["consideredAttributes"][p]["value"]))

            self.alternatives_values.append(alternative)

    def filter_unsuitable_alternatives(self):
        """Fetch requirements to eliminate unsuitable alternatives"""

        for b in self.alternatives:
            qualified = True

            for i in range(0, len(self.requirements)):
                if self.requirements[i][0]:
                    prop = b["consideredAttributes"][self.alternatives_attrs[i]]
                    print("prop", prop)
                    if self.costs[i]:
                        if self.format_value(prop["value"]) < self.requirements[i][1]:
                            qualified = False
                            break
                    else:
                        if self.format_value(prop["value"]) > self.requirements[i][1]:
                            qualified = False
                            break

            if qualified:
                self.results["considered"].append(b)
            else:
                self.results["disqualified"].append(b)

    def return_topsis_res(self, scores=[]):
        """Display results in CLI"""
        res = ""
        if self.results["optimum_id"] is None:
            res += "Alternatives cannot be ranked if weights are null or considered alternatives identical on chosen requirements.\n"
            res += "However, blockchains have been filtered according to your requirements.\n"
            res += "Suitable alternatives: \n"
            for a in self.results["considered"]:
                res += "- %s" % (a["name"] + " (" + a["infoAttributes"]["consensusAlgorithm"] + ")\n")
        else:
            res += "Considered alternatives: \n"
            for a in self.results["considered"]:
                res += "- %s" % (a["name"] + " (" + a["infoAttributes"]["consensusAlgorithm"] + ")\n")

            res += "Disqualified alternatives: \n"
            for a in self.results["disqualified"]:
                res += "- %s" % (a["name"] + " (" + a["infoAttributes"]["consensusAlgorithm"] + ")\n")

            best_altr = self.results["considered"][self.results["optimum_id"]]
            res += "Best solution: %s" % (
                        best_altr["name"] + " (" + best_altr["infoAttributes"]["consensusAlgorithm"] + ")\n")
            res += "Scores: %s \n" % scores
        
        return {
                "success": True,
                "msg": res
        }

    def solve(self):
        """Executes the 2-step solving process : filter unsuitable alternatives, then run TOPSIS to find the best alternative"""

        self.filter_unsuitable_alternatives()

        if len(self.results["considered"]) == 1:
            return {
                "success": True,
                "msg": "Only one alternative is compatible with your input: " + self.results["considered"][0]
            }
        elif len(self.results["considered"]) > 1:
            try:
                self.gen_alternatives_values_array()
            
                if(sum(abs(x) for x in self.weights) > 0):
                    decision = topsis(self.alternatives_values, self.weights, self.costs)
                    decision.calc()

                    self.results['optimum_id'] = decision.optimum_choice
                
                    return self.return_topsis_res(decision.C)

                return self.return_topsis_res()
            except:
                return {
                    "error": True,
                    "msg": "An unexpected error happened. Please copy your generated YAML file and send it to one of the researcher in charge of the project. Thanks!"
                }
        else:
            return {
                "success": True,
                "msg": "No alternative compatible with this input. Please change your requirements and retry."
            }
