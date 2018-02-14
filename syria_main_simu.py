__author__ = 'N. Avisse'
__email__ = 'nicolas.avisse@gmail.com'


from pynsim import Network, Simulator

from components.node import SurfaceReservoir, Aquifer, Outlet
from components.link import RiverSection, Canal, UndergroundTransfer
from components.institution import Syria, JVA, Israel
from engines.twr_management import SimulationOfSyria, TreatyOfPeace, ExchangeWithTiberias

import pandas as pd

# Source file for the analysis
source_file = 'reservoirs_1983.xlsx'
results_file = 'results_1983.xlsx'
test_future = 1

# PERSIANN rainfall
eff_precip = pd.read_excel('data/precip83-16_v7.xlsx', sheetname='calib_for_cwr')
contributive_weighted_precip = pd.read_excel('data/'+source_file, sheetname='rainfall', skiprows=[0], parse_cols='C:W')
# Test for future?
if test_future==1:
    eff_precip2 = pd.read_excel('data/precip83-16_v7.xlsx', sheetname='calib_for_cwr', skiprows=range(1,1+279),
                                skip_footer=6)
    eff_precip = [eff_precip, eff_precip2]
    eff_precip = pd.concat(eff_precip, ignore_index=True)
    contributive_weighted_precip2 = pd.read_excel('data/'+source_file, sheetname='rainfall',
                                                  skiprows=[0]+range(2,2+279), skip_footer=6, parse_cols='C:W')
    contributive_weighted_precip = [contributive_weighted_precip, contributive_weighted_precip2]
    contributive_weighted_precip = pd.concat(contributive_weighted_precip, ignore_index=True)

# area-storage relations
A_S = pd.read_excel('data/'+source_file, sheetname='evaporation', skiprows=[0])

# Evaporation at Wahda (CONFIDENTIAL DATA)
# TODO replace this data
evaporation = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # [mm]

# Crops
crops = ['olive', 'citrus', 'tomato', 'apple', 'cherry', 'eggplant', 'lettuce', 'cauliflower', 'forage']

# CWR
cwr = dict()
for c in crops:
    cwr[c] = pd.read_excel('data/'+source_file, sheetname=c, skiprows=[0])

# Irrigation deficit
irr_def = 0.4

# Inflows [natural flow GR2M]
flows = pd.read_excel('data/'+source_file, sheetname='inflows', skiprows=[0, 1], parse_cols='A:W')
# Test for future?
if test_future==1:
    flows2 = pd.read_excel('data/' + source_file, sheetname='inflows', skiprows=[0, 1]+range(3,3+279), skip_footer=6,
                           parse_cols='A:W')
    flows = [flows, flows2]
    flows = pd.concat(flows, ignore_index=True)
T = len(flows)

# Wahda storage constrained (CONFIDENTIAL DATA)
# TODO fill the excel sheet
wahda_storage = pd.read_excel('data/'+source_file, sheetname='storage', skiprows=[0], parse_cols='A:C')
# Test for future?
if test_future==1:
    wahda_storage = pd.read_excel('data/' + source_file, sheetname='storage', skiprows=[0], parse_cols='E:G')
wahda_storage = wahda_storage['El Wahda']

# Nodes
reservoirs = pd.read_excel('data/'+source_file, skip_footer=17)  # ignoring dams < 1 MCM
Res = {}
for i, dam in enumerate(reservoirs.name):
    # storage constraint only for El Wahda
    if reservoirs.idx[i] == 1:
        storage_constraint_i = wahda_storage
    else:
        storage_constraint_i = list()

    # Net Reservoir Evaporation [mm]
    nre_i = list()

    # irrigation
    if reservoirs.use[i] != 'Farming':
        # crop irrigation requirements
        cir_i = [0 for m in flows.Month]  # hm3
        # nre
        for k, m in enumerate(flows.Month):
            nre_i.append(evaporation[k % 12] - contributive_weighted_precip[dam][k])  # [mm]
    else:
        # abstractions from reservoir i
        i_r = cwr['olive'].idx.tolist().index(reservoirs.idx[i])
        # crop irrigation requirements
        cir_i = list()  # [hm3]

        for k, m in enumerate(flows.Month):
            # nre
            nre_i.append(evaporation[k % 12] - contributive_weighted_precip[dam][k])  # [mm]
            if flows.Year[k] < 1984:
                cir_i.append(sum([cwr[c]['area_1984'][i_r]
                                  * max(0, cwr[c][m][i_r] * (1 - irr_def) - eff_precip[dam][k]) / 1e9
                                  for c in crops]))
            elif flows.Year[k] < 1998:
                cir_i.append(sum([(int(1998-flows.Year[k]) * cwr[c]['area_1984'][i_r]
                                   + int(flows.Year[k]-1984) * cwr[c]['area_1998'][i_r]) / (1998-1984)
                                  * max(0, cwr[c][m][i_r] * (1 - irr_def) - eff_precip[dam][k]) / 1e9
                                  for c in crops]))
            elif 1983 + k / 12 < 2006:
                cir_i.append(sum([(int(2006-flows.Year[k]) * cwr[c]['area_1998'][i_r]
                                   + int(flows.Year[k]-1998) * 2 * cwr[c]['area_1998'][i_r]) / (2006-1998)
                                  * max(0, cwr[c][m][i_r] * (1 - irr_def) - eff_precip[dam][k]) / 1e9
                                  for c in crops]))
            elif 1983 + k / 12 < 2014:
                cir_i.append(sum([(int(2014-flows.Year[k]) * 2 * cwr[c]['area_1998'][i_r]
                                   + int(flows.Year[k]-2006) * cwr[c]['area_2014'][i_r]) / (2014-2006)
                                  * max(0, cwr[c][m][i_r] * (1 - irr_def) - eff_precip[dam][k]) / 1e9
                                  for c in crops]))
            else:
                cir_i.append(sum([cwr[c]['area_2014'][i_r]
                                  * max(0, cwr[c][m][i_r] * (1 - irr_def) - eff_precip[dam][k]) / 1e9
                                  for c in crops]))

    # household consumption
    if reservoirs.inhabitants[i] == reservoirs.inhabitants[i]:
        pop = reservoirs.inhabitants[i]
    else:
        pop = 0

    Res[reservoirs.idx[i]] = SurfaceReservoir(name=dam, x=reservoirs.east[i], y=reservoirs.north[i],
                                              idx=reservoirs.idx[i], capacity=reservoirs.capacity[i],
                                              area_storage=A_S[dam], service_year=reservoirs.year[i],
                                              end_year=reservoirs.end_year[i], use=reservoirs.use[i],
                                              manager=reservoirs.manager[i], initial_storage=0.8*reservoirs.capacity[i],
                                              nre_forecast = nre_i, crop_demand_forecast=cir_i, inhabitants=pop,
                                              inflow_forecast=flows[dam], storage_forecast=storage_constraint_i)

gwr = []  # [hm3]
gw_r = cwr['olive'].idx.tolist().index(0)
for k, m in enumerate(flows.Month):
    if flows.Year[k] < 1984:
        gwr.append(sum([cwr[c]['area_1984'][gw_r] * max(0, cwr[c][m][gw_r] * (1 - irr_def) - eff_precip['YRB'][k]) / 1e9
                        for c in crops]))
    elif flows.Year[k] < 1998:
        gwr.append(sum([(int(1998 - flows.Year[k]) * cwr[c]['area_1984'][gw_r]
                         + int(flows.Year[k] - 1984) * cwr[c]['area_1998'][gw_r]) / (1998 - 1984)
                        * max(0, cwr[c][m][gw_r] * (1 - irr_def) - eff_precip['YRB'][k]) / 1e9
                        for c in crops]))
    elif 1983 + k / 12 < 2006:
        gwr.append(sum([(int(2006-flows.Year[k]) * cwr[c]['area_1998'][gw_r]
                         + int(flows.Year[k]-1998) * 2 * cwr[c]['area_1998'][gw_r]) / (2006-1998)
                        * max(0, cwr[c][m][gw_r] * (1 - irr_def) - eff_precip['YRB'][k]) / 1e9
                        for c in crops]))
    elif 1983 + k / 12 < 2014:
        gwr.append(sum([(int(2014-flows.Year[k]) * 2 * cwr[c]['area_1998'][gw_r]
                         + int(flows.Year[k]-2006) * cwr[c]['area_2014'][gw_r]) / (2014-2006)
                        * max(0, cwr[c][m][gw_r] * (1 - irr_def) - eff_precip['YRB'][k]) / 1e9
                        for c in crops]))
    else:  # elif 1983 + k / 12 < 2018:  # test for future scenarios
        gwr.append(sum([cwr[c]['area_2014'][gw_r] * max(0, cwr[c][m][gw_r] * (1 - irr_def) - eff_precip['YRB'][k]) / 1e9
                        for c in crops]))
    # elif 1983 + k / 12 == 2018:
    #     gwr.append(sum([cwr[c]['area_2014'][gw_r] * 0.9 * max(0, cwr[c][m][gw_r] * (1 - irr_def) - eff_precip['YRB'][k])
    #                     / 1e9 for c in crops]))
    # elif 1983 + k / 12 == 2019:
    #     gwr.append(sum([cwr[c]['area_2014'][gw_r] * 0.8 * max(0, cwr[c][m][gw_r] * (1 - irr_def) - eff_precip['YRB'][k])
    #                     / 1e9 for c in crops]))
    # else:
    #     gwr.append(sum([cwr[c]['area_2014'][gw_r] * 0.7 * max(0, cwr[c][m][gw_r] * (1 - irr_def) - eff_precip['YRB'][k])
    #                     / 1e9 for c in crops]))

Groundwater_W = Aquifer(name='GW_Wahda', x=0, y=0, hist_bf=7, trigger=14.75, min_bf=0.3, crop_demand_forecast=gwr)

Groundwater_Ad = Aquifer(name='GW_Adasiya', x=0, y=0, hist_bf=2)

Ad = Outlet(name='Adasiya', x=0, y=0, inflow_forecast=flows['Adasiya'])

# Links
W = dict()  # Wadis                     Res -> Res/Ad
C = dict()  # Canals                    Res -> Res
U = dict()  # Underground transfers     GW -> Wah/Ad
for i, idx in enumerate(reservoirs.idx):
    # Transfers  with GW
    if idx == 1:
        U[0] = UndergroundTransfer('GW_to_Ad', Groundwater_Ad, Ad)
        U[1] = UndergroundTransfer('GW_to_W', Groundwater_W, Res[1])
    else:
        U[idx] = UndergroundTransfer(str(idx)+'_to_GW', Res[idx], Groundwater_W)

    # Wadis
    idx_W_ds = reservoirs.river[i]  # index of downstream node from a wadi
    if idx_W_ds == idx_W_ds:
        if idx_W_ds != 0:
            W[idx] = RiverSection('RS_' + str(idx) + '-' + str(int(idx_W_ds)), Res[idx], Res[idx_W_ds])
        elif idx == 1:
            W[idx] = RiverSection(name='RS_' + str(idx) + '-' + str(int(idx_W_ds)), start_node=Res[idx], end_node=Ad,
                                  link_yield=1)
        else:
            W[idx] = RiverSection('RS_' + str(idx) + '-' + str(int(idx_W_ds)), Res[idx], Ad)

    # Canals
    idx_C_ds = reservoirs.canal[i]  # index of downstream node from a canal
    if idx_C_ds == idx_C_ds:
        C[idx] = Canal('C_'+str(idx)+'-'+str(int(idx_C_ds)), Res[idx], Res[idx_C_ds])

# Institution
Jordan_gvt = JVA('Jordan Valley Authority')
Syria_gvt = Syria('MAAR')
Israel_gvt = Israel('Israel')

# Network
nodes = [Ad]
us_nodes_tmp = Ad.upstream_nodes
while len(us_nodes_tmp) > 0:
    nodes_tmp = list(us_nodes_tmp)
    us_nodes_tmp = []
    for n in nodes_tmp:
        if n in nodes:
            nodes.remove(n)
        nodes.insert(0, n)  # sorting from us to ds
        for us_n in n.upstream_nodes:
            us_nodes_tmp.append(us_n)

n_YRB = Network('Yarmouk_reservoirs_network')
for us_n in nodes:
    n_YRB.add_node(us_n)

for idx in reservoirs.idx:
    if idx in W.keys():
        n_YRB.add_link(W[idx])
    if idx in C.keys():
        n_YRB.add_link(C[idx])
    if idx in U.keys():
        n_YRB.add_link(U[idx])
n_YRB.add_institutions(Jordan_gvt, Israel_gvt, Syria_gvt)

# Simulator object that will be run
s = Simulator(network=n_YRB)

# Timesteps of the simulator
t = range(0, T)  # months
s.set_timesteps(t)

# Engines
reservoirs_management = SimulationOfSyria(target=Syria_gvt)
treaty = TreatyOfPeace(target=Jordan_gvt)
pumping = ExchangeWithTiberias(target=Israel_gvt)
s.add_engine(reservoirs_management)
# if test alpha & beta possibilities
s.add_engine(treaty)
s.add_engine(pumping)

# Simulation
s.start()

# Create a Pandas Excel writer using XlsxWriter as the engine
writer = pd.ExcelWriter('results/'+results_file, engine='xlsxwriter')
for id_a, agent in enumerate(s.network.nodes + s.network.institutions):
    for H_data in agent.get_properties().keys():
        # History
        H = agent.get_history(H_data)
        # Create a Pandas dataframe from the data
        H_df = pd.DataFrame({agent.name: H})
        # Convert the dataframe to an XlsxWriter Excel object
        if id_a == 0:
            H_df.to_excel(writer, sheet_name=H_data, startcol=id_a)
        else:
            H_df.to_excel(writer, sheet_name=H_data, index=False, startcol=id_a+1)

# Close the Pandas Excel writer and output the Excel file.
writer.save()
