# -*- coding: utf-8 -*-

import pytest
from wireviz.wireviz import parse
from wireviz.wv_dataclasses import Group
from wireviz.wv_harness import Harness


def test_group_dataclass_defaults():
    g = Group(name="unit_a")
    assert g.name == "unit_a"
    assert g.label == "unit_a"
    assert g.style is None
    assert g.color is None
    assert g.bgcolor is None
    assert g.members == []


def test_group_dataclass_custom():
    g = Group(
        name="unit_b",
        label="Custom Label",
        style=["dashed", "rounded"],
        color="#336699",
        bgcolor="#F4F7F9",
        members=["J1", "J2"],
    )
    assert g.label == "Custom Label"
    assert g.style == "dashed,rounded"
    assert g.color.html == "#336699"
    assert g.bgcolor.html == "#F4F7F9"
    assert g.members == ["J1", "J2"]


def test_group_parsing_and_subgraph_generation():
    yaml_content = """
connectors:
  J1:
    type: 4-pin
    pinlabels: [VCC, GND, TX, RX]
  J2:
    type: 2-pin
    pinlabels: [PWR+, PWR-]
  Sensor_In:
    type: 4-pin
    pinlabels: [VCC, GND, TX, RX]

cables:
  W1:
    colors: [RD, BK, WH, GN]

connections:
  -
    - J1: [1, 2, 3, 4]
    - W1: [1, 2, 3, 4]
    - Sensor_In: [1, 2, 3, 4]

groups:
  autopilot:
    label: "Autopilot Unit"
    style: dashed
    color: "#336699"
    bgcolor: "#F4F7F9"
    members: [J1, J2]
"""
    harness: Harness = parse(yaml_content, return_types="harness")
    assert "autopilot" in harness.groups
    group = harness.groups["autopilot"]
    assert group.label == "Autopilot Unit"
    assert group.style == "dashed"
    assert group.color.html == "#336699"
    assert group.bgcolor.html == "#F4F7F9"
    assert group.members == ["J1", "J2"]

    dot_graph = harness.create_graph()
    source = dot_graph.source
    assert "subgraph cluster_autopilot" in source
    assert 'label="Autopilot Unit"' in source
    assert 'bgcolor="#F4F7F9"' in source
    assert 'color="#336699"' in source
    assert "style=dashed" in source


def test_group_unknown_member_raises_value_error():
    yaml_content = """
connectors:
  J1:
    pincount: 2
groups:
  autopilot:
    members: [J1, TypoConnector]
"""
    with pytest.raises(ValueError) as excinfo:
        parse(yaml_content, return_types="harness")
    assert "Group 'autopilot' references unknown member 'TypoConnector'." in str(excinfo.value)


def test_backward_compatibility_no_groups():
    yaml_content = """
connectors:
  X1:
    pincount: 2
  X2:
    pincount: 2
cables:
  W1:
    wirecount: 2
connections:
  -
    - X1: [1, 2]
    - W1: [1, 2]
    - X2: [1, 2]
"""
    harness: Harness = parse(yaml_content, return_types="harness")
    assert harness.groups == {}
    dot_graph = harness.create_graph()
    assert "cluster_" not in dot_graph.source
