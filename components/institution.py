__author__ = 'N. Avisse'
__email__ = 'nicolas.avisse@gmail.com'

from pynsim import Institution


class Syria(Institution):
    """
    Syrian decision maker. Class name voluntarily left generic.
    """

    def manage_water_resources(self, timestep):
        wadi_losses = 0
        for n in self.network.nodes:
            if n.component_type == 'SurfaceReservoir':
                n.inflow_tot = n.inflow
                n.wadi_losses = 0
                wadi_losses += n.wadi_losses
                # adding outflow from current upstream reservoirs
                for us_n in n.upstream_nodes:
                    if us_n in n.current_upstream_reservoirs():
                        link = self.network.get_link('RS_' + str(us_n.idx) + '-' + str(n.idx))
                        if link is None:
                            link2 = self.network.get_link('C_' + str(us_n.idx) + '-' + str(n.idx))
                        list_ds_n = [n2 for n2 in us_n.downstream_nodes if n2.component_type == 'SurfaceReservoir']
                        # if both a wadi and a canal come from the upstream reservoir
                        if len(list_ds_n) > 1:
                            # if not wadi then canal to n
                            if link is None:
                                # additional inflow cannot excess the transfer capacity of canal/pipe
                                n.inflow_tot += link2.link_yield * min(link2.max_flow, us_n.outflow)
                                n.wadi_losses += (1 - link2.link_yield) * min(link2.max_flow, us_n.outflow)
                                wadi_losses += (1 - link2.link_yield) * min(link2.max_flow, us_n.outflow)
                            else:
                                list_ds_n.remove(n)
                                ds_n = list_ds_n[0]
                                link2 = self.network.get_link('C_' + str(us_n.idx) + '-' + str(ds_n.idx))
                                # what does not go through the canal goes to the wadi
                                n.inflow_tot += link.link_yield * max(0, us_n.outflow - link2.max_flow)
                                n.wadi_losses += (1 - link.link_yield) * max(0, us_n.outflow - link2.max_flow)
                                wadi_losses += (1 - link.link_yield) * max(0, us_n.outflow - link2.max_flow)
                        # else: only one wadi
                        else:
                            if link is None:
                                link = self.network.get_link('C_' + str(us_n.idx) + '-' + str(n.idx))
                            n.inflow_tot += link.link_yield * us_n.outflow
                            n.wadi_losses += (1 - link.link_yield) * us_n.outflow
                            wadi_losses += (1 - link.link_yield) * us_n.outflow
                    # direct upstream reservoir inactive
                    elif us_n.component_type == 'SurfaceReservoir':
                        link = self.network.get_link('RS_' + str(us_n.idx) + '-' + str(n.idx))
                        # flow can only be diverted through a canal if the reservoir is active
                        if link is not None:
                            n.inflow_tot += us_n.inflow_tot
                if n.name != 'El Wahda':
                    # dams built?
                    if n.active == 0:  # dam not built yet
                        n.deficit = 0  # n.demand
                    elif n.active == 1:  # dam operational
                        s_available = n.storage_ini
                        s_max = n.capacity
                    else:  # reservoir not active anymore
                        s_available = n.storage_ini
                        s_max = n.storage_ini
                    # operational rules
                    if n.active > 0:
                        if n.inflow_tot + s_available - n.demand >= 0:  # In + Si - abs >= 0
                            # demand is met
                            n.deficit = 0  # deficit at the reservoir
                            n.storage = min(s_max, n.inflow_tot + s_available - n.demand)
                            n.outflow = max(0, n.inflow_tot + s_available - n.demand - s_max)
                        else:  # In + Si - abs < 0
                            # demand is not met
                            n.deficit = n.demand - n.inflow_tot - s_available  # deficit at the reservoir
                            n.storage = 0
                            n.outflow = 0

            elif n.component_type == 'Aquifer':
                # demand
                l_d_average = len(n.demand_average)
                n.demand_average[timestep % l_d_average] += sum([us_n.deficit for us_n in n.upstream_nodes])
                n.demand = sum(n.demand_average) / l_d_average
                # only reservoirs upstream anyway
                l_if_average = len(n.inflow_average)
                n.inflow_tot = sum([us_n.rf * (1 - us_n.eta) * us_n.demand for us_n in n.upstream_nodes])
                if n.name == 'GW_Wahda':
                    n.inflow_tot += n.wadi_rf * wadi_losses + n.rf * (1 - n.eta) * n.demand
                n.inflow_average[timestep % l_if_average] += n.inflow_tot
                n.inflow = sum(n.inflow_average) / l_if_average
                # release
                if n.demand - n.inflow <= n.trigger:  # pumping too low to affect the base flow
                    n.outflow = n.hist_bf
                    n.deficit = 0
                    for us_n in n.upstream_nodes:
                        us_n.deficit = 0
                elif n.demand - n.inflow <= n.trigger + n.hist_bf - n.min_bf:
                    # pumping decreases the level of the aquifer
                    n.outflow = n.trigger + n.hist_bf - n.demand + n.inflow
                    n.deficit = 0
                    for us_n in n.upstream_nodes:
                        us_n.deficit = 0
                else:  # minimum base flow
                    n.outflow = n.min_bf
                    n.deficit = n.demand - n.inflow - (n.trigger + n.hist_bf - n.min_bf)
                    us_satisfied_ratio = 1 - n.deficit / n.demand
                    for us_n in n.upstream_nodes:
                        us_n.deficit -= us_n.deficit * us_satisfied_ratio

            elif n.component_type == 'Outlet':
                n.inflow_tot = n.inflow


class JVA(Institution):
    """
    JVA decision maker
    """

    # ===================================================================================
    # CONFIDENTIAL DATA (numbers given in this section are false values)
    # TODO replace this data
    objective_kac = 0  # annual quantity to be send to the KAC
    # monthly transfers as per the 1994 Treaty of Peace between Jordan and Israel
    allocation = [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3]  # total = 25 hm3
    concession = [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0, 0]  # total = 20 hm3
    # flow from Mukheibeh wells
    mukheibeh = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # [hm3]
    # repartition of the KAC annual transfer during the year
    kac_94 = [100, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # [%]
    kac95_07 = [100, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # [%]
    kac08 = [100, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # [%]
    # ===================================================================================

    _properties = {'kac': None}  # available in the KAC

    def __init__(self, name, **kwargs):
        super(JVA, self).__init__(name, **kwargs)
        self.kac = None  # already defined in _properties

    def manage_wahda(self, timestep):
        wahda = self.network.get_node('El Wahda')
        # aquifer deficit
        aq = self.network.get_node('GW_Wahda')
        wahda.inflow_tot += aq.outflow
        diff_min_flow = wahda.inflow_tot - aq.min_bf
        wahda.inflow_tot -= min(diff_min_flow, aq.deficit)
        if wahda.active == 0:  # dam not built yet
            wahda.deficit = 0  # n.demand
        # operational rules
        else:
            # ==================================================================
            # CONFIDENTIAL DATA (numbers given in this section are false values)
            # TODO replace this data
            # Loss in Wahda reservoir
            pct_abstractions = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # [%]
            # % of yearly amount
            wahda.inflow_tot -= min(wahda.inflow_tot - aq.min_bf, pct_abstractions[timestep % 12] / 100.0 * 0)
            # ==================================================================
            if wahda.inflow_tot + wahda.storage_ini - wahda.storage - wahda.demand >= 0:
                # demand and storage objective are met
                wahda.outflow = wahda.inflow_tot + wahda.storage_ini - wahda.storage - wahda.demand
                wahda.deficit = 0
            elif wahda.inflow_tot + wahda.storage_ini - wahda.storage > 0:
                # demand is not satisfied
                wahda.outflow = 0
                wahda.deficit = wahda.demand - (wahda.inflow_tot + wahda.storage_ini - wahda.storage)
            else:
                # storage objective is not met
                wahda.outflow = 0
                wahda.storage = wahda.inflow_tot + wahda.storage_ini
                wahda.deficit = wahda.demand

    def separate_the_flow(self, timestep):
        # flow to Adasiya
        adasiya = self.network.get_node('Adasiya')
        for us_n in adasiya.upstream_nodes:
            if us_n in adasiya.current_upstream_reservoirs():
                link = self.network.get_link('RS_' + str(us_n.idx) + '-0')
                adasiya.inflow_tot += link.link_yield * us_n.outflow
            elif us_n.component_type == 'SurfaceReservoir':
                adasiya.inflow_tot += us_n.inflow_tot
            else:
                adasiya.inflow_tot += us_n.outflow
        # rules from the 1994 Treaty of Peace
        wahda = self.network.get_node('El Wahda')
        israel_share = self.allocation[timestep % 12] + self.concession[timestep % 12]
        if timestep / 12 < 1995 - 1983:
            kac = self.kac_94[timestep % 12] / 100 * self.objective_kac  # hm3
        elif timestep / 12 < 2008 - 1983:
            kac = self.kac95_07[timestep % 12] / 100 * self.objective_kac  # hm3
        else:
            kac = self.kac08[timestep % 12] / 100 * self.objective_kac  # hm3
        if wahda.active == 1:
            # if Wahda built and active and max storage in April
            if timestep % 12 == 3:
                obj_last_year = self.objective_kac
                self.objective_kac = max(55, wahda.storage + sum(self.mukheibeh) - sum(self.allocation)
                                         - sum(self.concession) + 30, obj_last_year - 20)
            # priority 1: allocation and concession for Israel
            # priority 2: KAC
            if adasiya.inflow_tot <= israel_share:
                water_reserve = min(wahda.storage, israel_share - adasiya.inflow_tot)
                wahda.storage -= water_reserve
                wahda.outflow += water_reserve
                adasiya.inflow_tot += water_reserve
                adasiya.alpha = 0
                adasiya.beta = adasiya.inflow_tot
            else:
                if adasiya.inflow_tot - israel_share < kac - self.mukheibeh[timestep % 12]:
                    water_reserve = min(wahda.storage, kac - self.mukheibeh[timestep % 12]
                                        - (adasiya.inflow_tot - israel_share))
                    wahda.storage -= water_reserve
                    wahda.outflow += water_reserve
                    adasiya.inflow_tot += water_reserve
                adasiya.alpha = min(adasiya.inflow_tot - israel_share, kac - self.mukheibeh[timestep % 12])
                adasiya.beta = adasiya.inflow_tot - adasiya.alpha
        else:
            adasiya.beta = min(adasiya.inflow_tot, israel_share)
            adasiya.alpha = min(adasiya.inflow_tot - adasiya.beta, kac - self.mukheibeh[timestep % 12])
            adasiya.beta += adasiya.inflow_tot - adasiya.alpha - adasiya.beta
        self.kac = adasiya.alpha + self.mukheibeh[timestep % 12]


class Israel(Institution):
    """
    Israeli decision maker
    """

    # 3.95 m3/s (in theory 4.5 m3/s)
    pumping_capacity = 3.95 * 86400 * 30 / 1e6
    # ===================================================================================
    # CONFIDENTIAL DATA (numbers given in this section are false values)
    # TODO replace this data
    # monthly transfers as per the 1994 Treaty of Peace between Jordan and Israel
    allocation = [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3]  # total = 25 hm3
    concession = [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0, 0]  # total = 20 hm3
    # monthly transfers leaving Lake Tiberias to go to KAC
    tiberias = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # [hm3]
    # ===================================================================================

    _properties = {'quantity_available': None,   # available for Israel
                   'yarmouk_to_tiberias': None,  # send to Tiberias
                   'loss_to_JordanRiver': None}  # to the Jordan River

    def __init__(self, name, **kwargs):
        super(Israel, self).__init__(name, **kwargs)
        self.quantity_available = None  # already defined in _properties
        self.yarmouk_to_tiberias = None  # already defined in _properties
        self.loss_to_JordanRiver = None  # already defined in _properties
        self.obs_concession = self.concession

    def pump_in_yarmoukeem_pool(self):
        adasiya = self.network.get_node('Adasiya')
        self.yarmouk_to_tiberias = min(self.pumping_capacity, adasiya.beta)
        self.loss_to_JordanRiver = adasiya.beta - self.yarmouk_to_tiberias

    def send_concession_back(self, timestep):
        if self.yarmouk_to_tiberias <= self.allocation[timestep % 12]:
            self.quantity_available = self.yarmouk_to_tiberias
            self.obs_concession[timestep % 12] = 0
        elif self.yarmouk_to_tiberias <= self.allocation[timestep % 12] + self.concession[timestep % 12]:
            self.quantity_available = self.allocation[timestep % 12]
            self.obs_concession[timestep % 12] = self.yarmouk_to_tiberias - self.quantity_available
        else:
            self.quantity_available = self.yarmouk_to_tiberias - self.concession[timestep % 12]
            self.obs_concession[timestep % 12] = self.concession[timestep % 12]
        jva = self.network.get_institution('Jordan Valley Authority')
        jva.kac += max(0, self.tiberias[timestep % 12] + (sum(self.obs_concession) - sum(self.concession)) / 12)
