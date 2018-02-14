__author__ = 'N. Avisse'
__email__ = 'nicolas.avisse@gmail.com'

from pynsim import Link


class RiverSection(Link):
    """
    Simple link type with a max and min flow value and a yield
    """
    _properties = {'min_flow': None,
                   'max_flow': None}

    def __init__(self, name, start_node, end_node, link_yield=0.5, **kwargs):
        super(RiverSection, self).__init__(name, start_node, end_node, **kwargs)
        self.link_yield = link_yield


class Canal(Link):
    """
    Simple link type with a max and min flow value and a yield
    """
    # max flow from Manning-Strickler
    _properties = {'min_flow': None,
                   'max_flow': 1,
                   'link_yield': 0.5}


class UndergroundTransfer(Link):
    """
    Simple Link for transfer from GW to outlet
    """
    pass
