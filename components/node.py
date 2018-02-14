__author__ = 'N. Avisse'
__email__ = 'nicolas.avisse@gmail.com'

from pynsim import Node


class SurfaceReservoir(Node):
    """
    A general surface reservoir node
    """

    eta_pipe = 0.5  # household network efficiency
    eta = 0.5   # irrigation efficiency
    rf = 0.3    # return flows
    CroppingIntensity = 1  #1.12  # cropping intensity (WB, 2001)
    sediment_pct = 0.001  # sediment per water quantity [ratio]

    _properties = {'storage': None,
                   'inflow': None,
                   'outflow': None,
                   'evaporation': None,
                   'demand': None,  # demand at the reservoir!
                   'deficit': None,  # deficit at the reservoir
                   'inflow_tot': None,
                   'inflow_deficit': None,
                   'wadi_losses': None}

    def __init__(self, name, x, y, idx, capacity=0, area_storage=list(), service_year=1970, end_year=None,
                 use=None, manager=None, initial_storage=0, nre_forecast=list(), crop_demand_forecast=list(),
                 inhabitants=0, inflow_forecast=list(), storage_forecast=list(), **kwargs):
        super(SurfaceReservoir, self).__init__(name, x, y, **kwargs)
        self.idx = idx
        self.capacity = capacity
        self.area_storage = area_storage
        self.year_start = service_year
        self.year_end = end_year
        self.use = use
        self.manager = manager
        self.storage_ini = initial_storage
        self.nre_forecast = nre_forecast
        self.crop_demand_forecast = crop_demand_forecast
        self.inhabitants = inhabitants
        self.inflow_forecast = inflow_forecast
        self.storage_forecast = storage_forecast
        self.storage = None  # already defined in _properties
        self.inflow = None   # already defined in _properties
        self.outflow = None  # already defined in _properties
        self.evaporation = None  # already defined in _properties
        self.demand = None   # already defined in _properties
        self.deficit = None  # already defined in _properties
        self.inflow_tot = None  # already defined in _properties
        self.inflow_deficit = None  # already defined in _properties
        self.wadi_losses = None  # already defined in _properties
        self.active = 0      # 0: not built yet / 1: built and active / 2: destroyed or abandoned
        # sediments in 1983, but capacity in 1983 estimated from 2000 remote sensing observation
        if service_year < 1983:
            self.sediments = self.sediment_pct * sum(inflow_forecast) / len(inflow_forecast) * 12 * \
                             (1983 - service_year)
            self.capacity -= self.sediments
        else:
            self.sediments = None

    def __repr__(self):
        return "%s(name=%s, x=%s, y=%s, capacity in 1983=%s MCM, created in %s, destroyed in %s)"\
               % (self.__class__.__name__, self.name, self.x, self.y, self.capacity, self.year_start, self.year_end)

    def current_upstream_reservoirs(self):
        """
        Returns upstream reservoirs at a given time (relative after Jan 1983)
        """
        cur_us_reservoirs = []
        res_tmp = [us_n for us_n in self.upstream_nodes if us_n.component_type == 'SurfaceReservoir']
        # while there remains upstream reservoirs not taken into account
        while len(res_tmp) > 0:
            # dam built and active?
            if res_tmp[0].active == 1:
                cur_us_reservoirs.append(res_tmp[0])
            else:
                for us_r in res_tmp[0].upstream_nodes:
                    if us_r.component_type == 'SurfaceReservoir':
                        # only wadi because canal not built if reservoir not built
                        link = self.network.get_link('RS_' + str(us_r.idx) + '-' + str(res_tmp[0].idx))
                        if link is not None:  # if the wadi exists
                            res_tmp.append(us_r)
            res_tmp.remove(res_tmp[0])
        return cur_us_reservoirs

    def all_current_upstream_reservoirs(self):
        """
        Returns all upstream reservoirs in the network for a given time (relative after Jan 1983)
        """
        all_cur_us_reservoirs = []
        cur_us_res_tmp = [us_res for us_res in self.current_upstream_reservoirs()]
        # while there remains upstream reservoirs not taken into account
        while len(cur_us_res_tmp) > 0:
            cur_res_tmp = cur_us_res_tmp
            cur_us_res_tmp = []
            for res in cur_res_tmp:
                # sorting us to ds
                if res in all_cur_us_reservoirs:
                    all_cur_us_reservoirs.remove(res)
                all_cur_us_reservoirs.insert(0, res)
                for us_res in res.current_upstream_reservoirs():
                    cur_us_res_tmp.append(us_res)
        return all_cur_us_reservoirs

    def all_upstream_reservoirs(self):
        """
        Returns all upstream reservoirs in the network
        """
        all_us_reservoirs = []
        us_res_tmp = [us_n for us_n in self.upstream_nodes if us_n.component_type == 'SurfaceReservoir']
        # while there remains upstream reservoirs not taken into account
        while len(us_res_tmp) > 0:
            res_tmp = us_res_tmp
            us_res_tmp = []
            for res in res_tmp:
                # sorting us to ds
                if res in all_us_reservoirs:
                    all_us_reservoirs.remove(res)
                all_us_reservoirs.insert(0, res)
                for us_n in res.upstream_nodes:
                    if us_n.component_type == 'SurfaceReservoir':
                        us_res_tmp.append(us_n)
        return all_us_reservoirs

    def setup(self, timestamp):
        """
        At each timestep, inflows and demand are initialized
        """
        # if (float(timestamp) - 3) / 12 == 2018 - 1983:     # test efficiency for future scenarios
        #     self.eta += 0.1
        self.inflow = self.inflow_forecast[timestamp]
        self.demand = self.crop_demand_forecast[timestamp] * self.CroppingIntensity / self.eta + \
            self.inhabitants * 5 / 1e6 / self.eta_pipe
        # assumption: dams built and destroyed in April
        # if (float(timestamp) - 3) / 12 == 2018 - 1983:     # test rehabilitation for future scenarios
        #     self.active = 1
        #     self.year_end = 2222
        if (float(timestamp) - 3) / 12 == self.year_start - 1983:    # reservoir just created
            self.active = 1
            self.storage_ini = 0
            self.sediments = self.sediment_pct * self.inflow
            self.capacity -= self.sediment_pct * self.inflow
        elif (float(timestamp) - 3) / 12 > self.year_start - 1983:   # reservoir already created
            # for dams already built for the first timestamp
            if timestamp == 0:
                self.active = 1
                self.storage = self.storage_ini
            # index in the storage area relation -> evaporation
            id_s = [s / 100.0 * self.capacity >= self.storage for s in range(0, 101, 2)].index(True)
            self.evaporation = min(self.storage, self.area_storage[id_s] * self.nre_forecast[timestamp] / 1000)  # [MCM]
            self.storage_ini = self.storage - self.evaporation
            # sediments
            if (timestamp - 3) / 12 < self.year_end - 1983 or self.year_end != self.year_end:  # reservoir still active
                self.sediments += self.sediment_pct * self.inflow
                self.capacity -= self.sediment_pct * self.inflow
            else:  # dam destroyed or abandoned
                self.active = 2
        # Wahda reservoir
        if len(self.storage_forecast) > 0:  # storage objective
            self.storage = self.storage_forecast[timestamp]
            # ===================================================================================
            # CONFIDENTIAL DATA (numbers given in this section are false values)
            # TODO replace this data
            pct_abstractions = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # [%]
            self.demand += pct_abstractions[timestamp % 12] / 100.0 * 0  # % of yearly amount
            # ===================================================================================


class Aquifer(Node):
    """
    Class for a global aquifer under the YRB
    """

    eta = 0.7  # irrigation efficiency
    rf = 0.3    # return flows
    wadi_rf = 0.75  # return flows from the wadis

    _properties = {'outflow': None,
                   'demand': None,
                   'deficit': None,
                   'inflow': None}

    def __init__(self, name, x=0, y=0, hist_bf=0, trigger=100, min_bf=0, crop_demand_forecast=list(), **kwargs):
        super(Aquifer, self).__init__(name, x, y, **kwargs)
        self.hist_bf = hist_bf  # base flow [hm3]
        self.trigger = trigger  # trigger under which GW decreases [hm3]
        self.min_bf = min_bf    # min GW flow [hm3]
        self.crop_demand_forecast = crop_demand_forecast
        self.outflow = None     # already defined in _properties
        self.demand = None      # already defined in _properties
        self.deficit = None     # already defined in _properties
        self.inflow = None      # already defined in _properties
        self.inflow_tot = None
        self.demand_average = [hist_bf + 0 * m for m in range(0, 2*12)]  # average to consider a transit time
        self.inflow_average = [hist_bf + 0 * m for m in range(0, 2*12)]  # average to consider a transit time
        self.outflow_1 = None   # release at time t-1

    def __repr__(self):
        return "%s(name=%s, x=%s, y=%s, hist_GW_flow=%s MCM, trigger=%s MCM, min_flow=%s MCM)" \
               % (self.__class__.__name__, self.name, self.x, self.y, self.hist_bf, self.trigger, self.min_bf)

    def setup(self, timestamp):
        """
        At each timestep, demand is initialized
        """
        # if (float(timestamp) - 3) / 12 == 2018 - 1983:     # test efficiency for future scenarios
        #     self.eta += 0.1
        # average demand and inflow
        if len(self.crop_demand_forecast) > 0:  # if there is pumping from the aquifer
            self.demand_average[timestamp % len(self.demand_average)] = self.crop_demand_forecast[timestamp] / self.eta
            self.inflow_average[timestamp % len(self.inflow_average)] = 0

        # release at t-1
        if timestamp > 0:
            self.outflow_1 = self.outflow
        else:
            self.outflow_1 = self.hist_bf


class Outlet(Node):
    """
    Outlet of the YRB
    """

    _properties = {'inflow': None,
                   'inflow_tot': None,
                   'alpha': None,  # to KAC
                   'beta': None}   # to Israel and the Jordan River

    def __init__(self, name, x, y, inflow_forecast=list(), **kwargs):
        super(Outlet, self).__init__(name, x, y, **kwargs)
        self.inflow_forecast = inflow_forecast
        self.inflow = None  # already defined in _properties
        self.inflow_tot = None  # already defined in _properties
        self.alpha = None  # already defined in properties
        self.beta = None  # already defined in properties

    def setup(self, timestamp):
        """
        At each timestep, inflows are initialized
        """
        self.inflow = self.inflow_forecast[timestamp]

    def current_upstream_reservoirs(self):
        """
        Returns upstream reservoirs at a given time
        """
        cur_us_reservoirs = []
        res_tmp = [us_n for us_n in self.upstream_nodes if us_n.component_type == 'SurfaceReservoir']
        # while there remains upstream reservoirs not taken into account
        while len(res_tmp) > 0:
            # dam built and active?
            if res_tmp[0].active == 1:
                cur_us_reservoirs.append(res_tmp[0])
            else:
                for us_r in res_tmp[0].upstream_nodes:
                    if us_r.component_type == 'SurfaceReservoir':
                        # only wadi because canal not built if reservoir not built
                        link = self.network.get_link('RS_' + str(us_r.idx) + '-' + str(res_tmp[0].idx))
                        if link is not None:  # if the wadi exists
                            res_tmp.append(us_r)
            res_tmp.remove(res_tmp[0])
        return cur_us_reservoirs
