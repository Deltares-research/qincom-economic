# -*- coding: utf-8 -*-

"""
Created on Tue Apr 16 13:31 2019
@author: L.K. Leunge
"""
from economic_postprocessing_functions_mediaan import read_bivas_input, calculate_sailing_costs, calculate_remaining_freight, calculate_distribution_freight, calculate_difference_welfare_costs, calculate_increase_storage_capacitiy, calculate_welfare_costs, calculate_increase_structural_costs, calculate_npv, store_bivas_scenarios, store_costs_and_npv
from pathlib import Path
from pathlib import Path
import numpy as np
import numpy_financial as npf

def main():
    # Input and output paths.
    input_path = Path('C:/Users/mes/OneDrive - Stichting Deltares/Documents/Projecten/Deltaprogramma Zoetwater/Scheepvaart/Ruwe data')
    output_path = Path('C:/Users/mes/OneDrive - Stichting Deltares/Documents/Projecten/Deltaprogramma Zoetwater/Scheepvaart/Figures/Median/Figures_2050')

    # Filenames.
    file_name_1 = 'BIVAS_resultaten_Pilot 2018.xlsx'
    file_name_2 = 'BIVAS_resultaten_Pilot 2018 (infeasible).xlsx'
    file_name_3 = 'BIVAS_resultaten_Pilot 2018 (infeasible met minimum van 3 dagen).xlsx'

    # File paths.
    file_path_1 = input_path.joinpath(file_name_1)
    file_path_2 = input_path.joinpath(file_name_2)
    file_path_3 = input_path.joinpath(file_name_3)

    # Scenarios.
    scenarios = ['D2050BP18', 'R2050BP18', 'S2050BP18', 'W2050BP18']
    scenario_year = 2050
    storage_scenarios = ['Laag', 'Middel', 'Hoog']

    # Historical time vector (final year of series + 1).
    t = range(1911, 2012)

    # Future time vector.
    future_time = range(2018, scenario_year)

    # Reference Scenario.
    reference = 'REF2017BP18'

    """ General Input Parameters """

    # Price conversion parameters.
    price_conversion = {'2015_to_2017': 1.017,
                        '2014_to_2017': 1.023,
                        '2012_to_2017': 1.059}

    # Variable storage costs (EUR(2017)).
    storage_costs = {'bulk': 5.2,
                     'container': 11.44}

    # Variable sailing costs (EUR(2014)).
    sailing_costs = {'bulk_landbouw': 13.42,
                     'bulk_voeding_en_vee': 9.75,
                     'bulk_mineralen': 9.88,
                     'bulk_aardolie': 16.26,
                     'bulk_ertsen': 9.29,
                     'bulk_staal': 12.93,
                     'bulk_bouwmaterialen': 7.07,
                     'bulk_meststoffen': 14.04,
                     'bulk_chemische_producten': 13.28,
                     'bulk_goederen': 17.56,
                     'container': 19.42}

    # Costs per tonkm (EUR(2017)).
    tonkm_costs = {'bulk_road': (1.64 / 27) * price_conversion['2015_to_2017'],
                   'bulk_train': (16.27 / 2700) * price_conversion['2015_to_2017'],
                   'container_road': (1.39 / 27) * price_conversion['2015_to_2017'],
                   'container_train': (17.19 / 750) * price_conversion['2015_to_2017']}

    # Infrastructural storage costs/ton per year (EUR(2017)).
    infrastructural_storage_costs = {'Droge bulk': 28.09,
                                     'Natte bulk': 52.55,
                                     'Container': 89.85}

    # Road and train transport costs/ton per year (EUR(2017)).
    road_transport_costs = {'Droge bulk': 17.81,
                            'Natte bulk': 17.81,
                            'Container': 14.15}

    train_transport_costs = {'Droge bulk': 2.66,
                             'Natte bulk': 2.66,
                             'Container': 36.34}

    # Price elasticities.
    price_elasticities = {'landbouw': -0.79,
                          'voeding_en_vee': -0.84,
                          'mineralen': -0.35,
                          'aardolie': -0.42,
                          'ertsen': -0.41,
                          'staal': -0.75,
                          'bouwmaterialen': -0.78,
                          'meststoffen': -0.75,
                          'chemische_producten': -0.86,
                          'goederen': -0.84,
                          'leeg': -0.84,
                          'container': -0.57}

    # Storage vs modal shift (Lorelei distributions).
    storage_share = {'landbouw': 1.00,
                     'voeding_en_vee': 1.00,
                     'mineralen': 0.95,
                     'aardolie': 0.50,
                     'ertsen': 0.95,
                     'staal': 0.50,
                     'bouwmaterialen': 0.80,
                     'meststoffen': 1.00,
                     'chemische_producten': 0.50,
                     'goederen': 1.00,
                     'container': 0.15}

    # Modal shift.
    modal_shift_road = {'0 - Landbouw': 1.00,
                        '1 - Voeding en vee': 0.89,
                        '2 - Mineralen': 0.31,
                        '3 - Aardolie': 0.93,
                        '4 - Ertsen': 0.31,
                        '5 - Staal': 0.47,
                        '6 - Bouwmaterialen': 1.00,
                        '7 - Meststoffen': 0.53,
                        '8 - Chemische prod.': 0.84,
                        '9 - Goederen': 0.88,
                        'Container': 0.50}

    modal_shift_train = {'0 - Landbouw': 0.00,
                         '1 - Voeding en vee': 0.00,
                         '2 - Mineralen': 0.69,
                         '3 - Aardolie': 0.07,
                         '4 - Ertsen': 0.69,
                         '5 - Staal': 0.24,
                         '6 - Bouwmaterialen': 0.00,
                         '7 - Meststoffen': 0.33,
                         '8 - Chemische prod.': 0.01,
                         '9 - Goederen': 0.00,
                         'Container': 0.50}

    # Distribution domestic and foreign shift.
    shift = 0.5

    # Discount rate.
    discount_rate = 0.045

    """ Read input BIVAS - Heden """

    df_ref = read_bivas_input(file_path_1, file_path_2, file_path_3, reference)

    """ Calculate Sailing Costs - Heden """

    variable_costs_sailing_ref = calculate_sailing_costs(df_ref, price_conversion, price_elasticities, t)

    """ Calculate Remaining Freight Costs - Heden """

    variable_costs_storage_and_sailing_ref, variable_costs_modal_shift_ref = calculate_remaining_freight(df_ref, storage_costs, sailing_costs, price_conversion, modal_shift_road, modal_shift_train, tonkm_costs, t)

    """ Calculate Distribution Freight - Heden """

    freight_distribution_ref = calculate_distribution_freight(df_ref, modal_shift_road, modal_shift_train)

    """ Calculate and plot Total Welfare Costs - Heden """

    data = np.array([np.array(variable_costs_sailing_ref)[:, 3], np.array(variable_costs_storage_and_sailing_ref)[:, 1], np.array(variable_costs_modal_shift_ref)[:, -1]])
    data_labels = ['Variabele kosten - Varen, inclusief vraagsubstitutie', 'Variabele kosten - Tijdelijke opslag en alsnog varen', 'Variabele kosten - Modal shift']
    colors = ['navy', 'royalblue', 'cornflowerblue']
    calculate_welfare_costs(data, data_labels, colors, t, output_path, 'REF2017BP18')

    for i in scenarios:

        """ Read input BIVAS - Scenario 2050 """

        df_i = read_bivas_input(file_path_1, file_path_2, file_path_3, i)

        """ Calculate Sailing Costs - Scenario 2050 """

        variable_costs_sailing_i = calculate_sailing_costs(df_i, price_conversion, price_elasticities, t)

        """ Calculate Remaining Freight - Scenario 2050 """

        variable_costs_storage_and_sailing_i, variable_costs_modal_shift_i = calculate_remaining_freight(df_i, storage_costs, sailing_costs, price_conversion, modal_shift_road, modal_shift_train, tonkm_costs, t)

        """ Calculate Distribution Freight Costs - Scenario 2050 """

        freight_distribution_i = calculate_distribution_freight(df_i, modal_shift_road, modal_shift_train)

        """ Calculate Structural Costs Increase - Scenario 2050 """

        increase_storage_capacity, increase_yearly_storage_capacity = calculate_increase_storage_capacitiy(input_path, reference, i, t)
        total_costs_storage_capacity, total_costs_road_capacity, total_costs_train_capacity = calculate_increase_structural_costs(df_i, increase_storage_capacity, t, storage_share, modal_shift_road, modal_shift_train, infrastructural_storage_costs, road_transport_costs, train_transport_costs, storage_scenarios)

        """ Calculate and plot Total Welfare Costs - Scenario 2050 """

        # For each storage scenario [Low, Average, High].
        for j in range(len(storage_scenarios)):
            data = np.array([np.array(variable_costs_sailing_i)[:, 3], np.array(variable_costs_storage_and_sailing_i)[:, 1], np.array(variable_costs_modal_shift_i)[:, -1], [total_costs_storage_capacity[j]] * len(t), [total_costs_road_capacity[j]] * len(t), [total_costs_train_capacity[j]] * len(t)])
            data_labels = ['Variabele kosten - Varen, inclusief vraagsubstitutie', 'Variabele kosten - Tijdelijke opslag en alsnog varen', 'Variabele kosten - Modal shift', 'Structurele kosten - Toename opslagcapaciteit', 'Structurele kosten - Toename wegcapaciteit', 'Structurele kosten - Toename spoorcapaciteit']
            colors = ['navy', 'royalblue', 'cornflowerblue', 'lightsteelblue', 'slategrey', 'orange']
            calculate_welfare_costs(data, data_labels, colors, t, output_path, i, storage_scenario=storage_scenarios[j])

        """ Calculate and plot difference Total Welfare Costs - Heden and Total Welfare Costs - Scenario 2050 """

        delta_variabele_costs_sailing = [j[3] - k[3] for j, k in zip(variable_costs_sailing_i, variable_costs_sailing_ref)]
        delta_variable_costs_storage_and_sailing = [j[1] - k[1] for j, k in zip(variable_costs_storage_and_sailing_i, variable_costs_storage_and_sailing_ref)]
        delta_variable_costs_modal_shift = [j[-1] - k[-1] for j, k in zip(variable_costs_modal_shift_i, variable_costs_modal_shift_ref)]
        calculate_difference_welfare_costs(storage_scenarios, delta_variabele_costs_sailing, delta_variable_costs_storage_and_sailing, delta_variable_costs_modal_shift, total_costs_storage_capacity, total_costs_road_capacity, total_costs_train_capacity, t, output_path, i)

        """ Calculate the Net Present Value """

        npv = calculate_npv(storage_scenarios, variable_costs_sailing_ref, variable_costs_storage_and_sailing_ref, variable_costs_modal_shift_ref, variable_costs_sailing_i, variable_costs_storage_and_sailing_i, variable_costs_modal_shift_i, total_costs_storage_capacity, total_costs_road_capacity, total_costs_train_capacity, future_time, shift, discount_rate)

        """ Store Data """

        store_bivas_scenarios(output_path, i, df_ref, df_i, freight_distribution_ref, freight_distribution_i)
        store_costs_and_npv(output_path, i, t, variable_costs_sailing_ref, variable_costs_storage_and_sailing_ref, variable_costs_modal_shift_ref, variable_costs_sailing_i, variable_costs_storage_and_sailing_i, variable_costs_modal_shift_i, storage_scenarios, total_costs_storage_capacity, total_costs_road_capacity, total_costs_train_capacity, delta_variabele_costs_sailing, delta_variable_costs_storage_and_sailing, delta_variable_costs_modal_shift, scenario_year, npv)

if __name__ == '__main__':
    main()
