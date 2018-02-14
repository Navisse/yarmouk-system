__author__ = 'N. Avisse'
__email__ = 'nicolas.avisse@gmail.com'

from pynsim import Engine


class SimulationOfSyria(Engine):
    """
    Basic engine to simulate the Yarmouk flow and observed reservoirs storage variations
    """
    name = "Syrian system simulation"

    def run(self):
        # target = Syria
        self.target.manage_water_resources(self.target.network.current_timestep)

class TreatyOfPeace(Engine):
    """
    Basic engine reproducing the 1994 Treaty of Peace between Jordan and Israel
    """
    name = "1994 Treaty of peace"

    def run(self):
        # target = JVA
        self.target.manage_wahda(self.target.network.current_timestep)
        self.target.separate_the_flow(self.target.network.current_timestep)

class ExchangeWithTiberias(Engine):
    """
    Basic engine reproducing the Israeli pumping at Yarmoukeem pool
    """
    name = "Israeli pumping stations"

    def run(self):
        # target = Israel
        self.target.pump_in_yarmoukeem_pool()
        self.target.send_concession_back(self.target.network.current_timestep)
