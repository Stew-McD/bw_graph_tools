import pytest
from bw2data import Database, Method
from bw2data.tests import bw2test

from bw_graph_tools import GraphTraversal


@pytest.fixture
@bw2test
def init_database_no_loops():
    biosphere = Database("biosphere")
    biosphere.register()
    biosphere.write(
        {
            ("biosphere", "CO2"): {
                "categories": ["things"],
                "exchanges": [],
                "name": "an emission",
                "type": "emission",
                "unit": "kg",
            }
        }
    )

    db = Database("test")
    db.register()
    db.write(
        {
            ("test", "A"): {
                "name": "A",
                "exchanges": [
                    {"input": ("test", "A"), "amount": -1.0, "type": "production"},
                    {"input": ("test", "B"), "amount": -1.0, "type": "technosphere"},
                ],
            },
            ("test", "B"): {
                "name": "B",
                "exchanges": [
                    {"input": ("test", "B"), "amount": -2.0, "type": "production"},
                    {"input": ("test", "C"), "amount": 1.0, "type": "technosphere"},
                ],
            },
            ("test", "C"): {
                "name": "C",
                "exchanges": [
                    {"input": ("test", "C"), "amount": 1.0, "type": "production"},
                    {"input": ("test", "D"), "amount": -1.0, "type": "technosphere"},
                ],
            },
            ("test", "D"): {
                "name": "D",
                "exchanges": [
                    {"input": ("test", "D"), "amount": -1.0, "type": "production"},
                    {
                        "input": ("biosphere", "CO2"),
                        "amount": -1.0,
                        "type": "biosphere",
                    },
                ],
            },
        }
    )

    method = Method(("a method",))
    method.register()
    method.write([(("biosphere", "CO2"), 1)])

    return db, biosphere, method


def test_single_activity_graph_traversal_no_loop(init_database_no_loops):
    nodes_expected = {
        -1: {"amount": 1, "cum": -0.5, "ind": 0},
        ("test", "C"): {"amount": 0.5, "cum": -0.5, "ind": 0},
        ("test", "D"): {"amount": -0.5, "cum": -0.5, "ind": 0},
        ("biosphere", "CO2"): {"amount": -0.5, "cum": -0.5, "ind": -0.5},
        ("test", "A"): {"amount": -1.0, "cum": -0.5, "ind": 0},
        ("test", "B"): {"amount": -1.0, "cum": -0.5, "ind": 0},
    }
    edges_expected = [
        {
            "to": -1,
            "from": ("test", "A"),
            "amount": -1,
            "exc_amount": -1,
            "impact": -0.5,
        },
        {
            "to": ("test", "A"),
            "from": ("test", "B"),
            "amount": -1.0,
            "exc_amount": 1.0,
            "impact": -0.5,
        },
        {
            "to": ("test", "B"),
            "from": ("test", "C"),
            "amount": 0.5,
            "exc_amount": -0.5,
            "impact": -0.5,
        },
        {
            "to": ("test", "C"),
            "from": ("test", "D"),
            "amount": -0.5,
            "exc_amount": -1.0,
            "impact": -0.5,
        },
        {
            "to": ("test", "D"),
            "from": ("biosphere", "CO2"),
            "amount": -0.5,
            "exc_amount": 1.0,
            "impact": -0.5,
        },
    ]

    act = [a for a in Database("test") if a._data["name"] == "A"][0]
    demand = {act: -1}

    gt = GraphTraversal(use_keys=True, include_biosphere=True, importance_first=True)
    actual = gt.calculate(demand, ("a method",))
    assert actual["nodes"] == nodes_expected
    assert actual["edges"] == edges_expected

    # test depth first traversal
    gt.traverse = gt.traverse_depth_first
    actual = gt.calculate(demand, ("a method",))
    assert actual["nodes"] == nodes_expected
    assert actual["edges"] == edges_expected

    # test include_biosphere = False
    gt.traverse = gt.traverse_importance_first
    gt.include_biosphere = False
    actual = gt.calculate(demand, ("a method",))
    nodes_expected = {
        k: v for k, v in nodes_expected.items() if k == -1 or k[0] != "biosphere"
    }
    nodes_expected[("test", "D")]["ind"] = -0.5
    edges_expected = [
        e for e in edges_expected if e["from"] == -1 or e["from"][0] != "biosphere"
    ]
    assert actual["nodes"] == nodes_expected
    assert actual["edges"] == edges_expected

    # test use_keys = False
    gt.use_keys = False
    actual = gt.calculate(demand, ("a method",))
    nodes_expected = {
        gt.lca.activity_dict.get(k, -1): v for k, v in nodes_expected.items()
    }
    for e in edges_expected:
        e["to"] = gt.lca.activity_dict.get(e["to"], -1)
        e["from"] = gt.lca.activity_dict.get(e["from"], -1)
    assert actual["nodes"] == nodes_expected
    assert actual["edges"] == edges_expected


def test_multi_activity_graph_traversal_no_loop(init_database_no_loops):
    nodes_expected = {
        -1: {"amount": 1, "cum": -1.5, "ind": 0},
        ("test", "C"): {"amount": 0.5, "cum": -0.5, "ind": 0},
        ("test", "D"): {"amount": -1.5, "cum": -1.5, "ind": 0},
        ("biosphere", "CO2"): {"amount": -1.5, "cum": -1.5, "ind": -1.5},
        ("test", "A"): {"amount": -1.0, "cum": -0.5, "ind": 0},
        ("test", "B"): {"amount": -1.0, "cum": -0.5, "ind": 0},
    }
    edges_expected = [
        {
            "to": -1,
            "from": ("test", "A"),
            "amount": -1,
            "exc_amount": -1,
            "impact": -0.5,
        },
        {
            "to": -1,
            "from": ("test", "D"),
            "amount": -1,
            "exc_amount": -1,
            "impact": -1.0,
        },
        {
            "to": ("test", "A"),
            "from": ("test", "B"),
            "amount": -1.0,
            "exc_amount": 1.0,
            "impact": -0.5,
        },
        {
            "to": ("test", "B"),
            "from": ("test", "C"),
            "amount": 0.5,
            "exc_amount": -0.5,
            "impact": -0.5,
        },
        {
            "to": ("test", "C"),
            "from": ("test", "D"),
            "amount": -0.5,
            "exc_amount": -1.0,
            "impact": -0.5,
        },
        {
            "to": ("test", "D"),
            "from": ("biosphere", "CO2"),
            "amount": -0.5,
            "exc_amount": 1.0,
            "impact": -0.5,
        },
        {
            "to": ("test", "D"),
            "from": ("biosphere", "CO2"),
            "amount": -1.0,
            "exc_amount": 1.0,
            "impact": -1.0,
        },
    ]

    A = [a for a in Database("test") if a._data["name"] == "A"][0]
    D = [a for a in Database("test") if a._data["name"] == "D"][0]
    demand = {A: -1, D: -1}

    gt = GraphTraversal(use_keys=True, include_biosphere=True, importance_first=True)
    actual = gt.calculate(demand, ("a method",))
    assert actual["nodes"] == nodes_expected
    assert actual["edges"] == edges_expected

    return


@pytest.fixture
@bw2test
def init_database_incl_loops():
    biosphere = Database("biosphere")
    biosphere.register()
    biosphere.write(
        {
            ("biosphere", "CO2"): {
                "categories": ["things"],
                "exchanges": [],
                "name": "an emission",
                "type": "emission",
                "unit": "kg",
            }
        }
    )

    db = Database("test")
    db.register()
    db.write(
        {
            ("test", "A"): {
                "name": "coal mining",
                "exchanges": [
                    {
                        "input": ("biosphere", "CO2"),
                        "amount": 0.05,
                        "type": "biosphere",
                    },
                    {"input": ("test", "A"), "amount": 1, "type": "production"},
                    {
                        "input": ("test", "E"),
                        "amount": 0.1,
                        "type": "technosphere",
                    },  # hot rolling
                ],
            },
            ("test", "B"): {
                "name": "steel smelting",
                "exchanges": [
                    {"input": ("biosphere", "CO2"), "amount": 1.1, "type": "biosphere"},
                    {"input": ("test", "B"), "amount": 1, "type": "production"},
                    {"input": ("test", "A"), "amount": 1, "type": "technosphere"},
                    {
                        "input": ("test", "C"),
                        "amount": 0.5,
                        "type": "technosphere",
                    },  # electricity
                    {
                        "input": ("test", "D"),
                        "amount": 2,
                        "type": "technosphere",
                    },  # ore mining
                ],
            },
            ("test", "C"): {
                "name": "electricity production",
                "exchanges": [
                    {"input": ("biosphere", "CO2"), "amount": 1, "type": "biosphere"},
                    {"input": ("test", "C"), "amount": 1, "type": "production"},
                    {"input": ("test", "A"), "amount": 1, "type": "technosphere"},
                ],
            },
            ("test", "D"): {
                "name": "iron ore mining",
                "exchanges": [
                    {"input": ("test", "D"), "amount": 1, "type": "production"},
                    {"input": ("test", "C"), "amount": 0.5, "type": "technosphere"},
                    {"input": ("test", "E"), "amount": 0.1, "type": "technosphere"},
                ],
            },
            ("test", "E"): {
                "name": "hot-rolling",
                "exchanges": [
                    {"input": ("biosphere", "CO2"), "amount": 0.1, "type": "biosphere"},
                    {"input": ("test", "E"), "amount": 1, "type": "production"},
                    {"input": ("test", "C"), "amount": 0.5, "type": "technosphere"},
                    {"input": ("test", "B"), "amount": 1, "type": "technosphere"},
                ],
            },
        }
    )

    method = Method(("a method",))
    method.register()
    method.write([(("biosphere", "CO2"), 1)])

    return db, biosphere, method


def test_single_activity_graph_traversal_incl_loop(init_database_incl_loops):
    nodes_expected = {
        # todo
    }
    edges_expected = [
        # todo
    ]

    act = [a for a in Database("test") if a._data["name"] == "hot-rolling"][0]
    demand = {act: 1}

    gt = GraphTraversal(use_keys=True, include_biosphere=True, importance_first=True)
    actual = gt.calculate(demand, ("a method",))
    assert actual["nodes"] == nodes_expected
    assert actual["edges"] == edges_expected
