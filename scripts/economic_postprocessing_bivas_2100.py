# -*- coding: utf-8 -*-

"""
Created on Tue Apr 16 13:31 2019
@author: L.K. Leunge
"""

from pathlib import Path
from statistics import mean

import numpy as np
import numpy_financial as npf
import pandas as pd
from economic_postprocessing_functions import (
    calculate_difference_welfare_costs,
    calculate_distribution_freight,
    calculate_increase_structural_costs,
    calculate_npv,
    calculate_remaining_freight,
    calculate_sailing_costs,
    calculate_welfare_costs,
    read_bivas_input,
    store_bivas_scenarios,
    store_costs_and_npv,
)


def calculate_increase_storage_capacitiy(
    ref_input_path,
    input_path,
    scenario_ref,
    scenario_i,
    scenario_j,
    years,
    reference_year,
):
    # Open reference scenario and scenario worksheets.
    aux_df_ref = pd.read_pickle(
        Path(ref_input_path, (scenario_ref + ".pkl"))
    ).reset_index()
    aux_df_ref.drop(
        aux_df_ref.columns[[4, 6, 7, 8, 9, 10, 11, 12]], axis=1, inplace=True
    )
    aux_df_i = pd.read_pickle(Path(input_path, (scenario_i + ".pkl"))).reset_index()
    aux_df_i.drop(aux_df_i.columns[[4, 6, 7, 8, 9, 10, 11, 12]], axis=1, inplace=True)
    aux_df_j = pd.read_pickle(Path(ref_input_path, (scenario_j + ".pkl"))).reset_index()
    aux_df_j.drop(aux_df_j.columns[[4, 6, 7, 8, 9, 10, 11, 12]], axis=1, inplace=True)

    # Adjust column names.
    aux_df_ref.columns = ["Jaar", "Datum", "Type Vracht", "NSTR", "Totale Vracht"]
    aux_df_i.columns = ["Jaar", "Datum", "Type Vracht", "NSTR", "Totale Vracht"]
    aux_df_j.columns = ["Jaar", "Datum", "Type Vracht", "NSTR", "Totale Vracht"]

    # Extract month and day from datum and reposition the dataFrame.
    aux_df_ref.insert(
        loc=1, column="Maand", value=pd.to_datetime(aux_df_ref["Datum"]).dt.month
    )
    aux_df_ref.insert(
        loc=2, column="Dag", value=pd.to_datetime(aux_df_ref["Datum"]).dt.day
    )
    aux_df_ref.drop("Datum", axis=1, inplace=True)
    aux_df_i.insert(
        loc=1, column="Maand", value=pd.to_datetime(aux_df_i["Datum"]).dt.month
    )
    aux_df_i.insert(loc=2, column="Dag", value=pd.to_datetime(aux_df_i["Datum"]).dt.day)
    aux_df_i.drop("Datum", axis=1, inplace=True)
    aux_df_j.insert(
        loc=1, column="Maand", value=pd.to_datetime(aux_df_j["Datum"]).dt.month
    )
    aux_df_j.insert(loc=2, column="Dag", value=pd.to_datetime(aux_df_j["Datum"]).dt.day)
    aux_df_j.drop("Datum", axis=1, inplace=True)

    yearly_storage_capacity_data = {"Droge bulk": [], "Natte bulk": [], "Container": []}

    for i in years:
        # Group the data per day into droge bulk, natte bulk and container.
        aux_delta_ref = aux_df_ref[(aux_df_ref["Jaar"] == i)].iloc[:, 1:]
        aux_delta_ref = (
            aux_delta_ref.groupby(["Maand", "Dag", "Type Vracht"])["Totale Vracht"]
            .sum()
            .reset_index()
        )
        aux_delta_ref = aux_delta_ref.drop(
            aux_delta_ref[(aux_delta_ref["Type Vracht"] == "Overig")].index
        )
        aux_delta_i = aux_df_i[(aux_df_i["Jaar"] == i)].iloc[:, 1:]
        aux_delta_i = (
            aux_delta_i.groupby(["Maand", "Dag", "Type Vracht"])["Totale Vracht"]
            .sum()
            .reset_index()
        )
        aux_delta_i = aux_delta_i.drop(
            aux_delta_i[(aux_delta_i["Type Vracht"] == "Overig")].index
        )

        # Calculate the difference in total freight between the reference scenario and the scenario.
        delta = aux_delta_ref.iloc[:, :3]
        delta["Delta Totale Vracht"] = (
            aux_delta_ref["Totale Vracht"] - aux_delta_i["Totale Vracht"]
        )

        # For droge bulk, natte bulk and container.
        for key in yearly_storage_capacity_data:
            # Filter data.
            df = delta[delta["Type Vracht"] == key].reset_index(drop=True)

            # Calculate the cumulative freight with a moving window of 10, 20 and 30 days.
            df["MW10"] = df["Delta Totale Vracht"].rolling(10).sum().fillna(0)
            df["MW20"] = df["Delta Totale Vracht"].rolling(20).sum().fillna(0)
            df["MW30"] = df["Delta Totale Vracht"].rolling(30).sum().fillna(0)

            # Store yearly data [daily max, 10 days max, 20 days max, 30 days max].
            yearly_storage_capacity_data[key].append(
                [
                    df["Delta Totale Vracht"].min(),
                    df["MW10"].min(),
                    df["MW20"].min(),
                    df["MW30"].min(),
                ]
            )

    # Reference year data.
    reference_year_storage_capacity_data = {
        "Droge bulk": [],
        "Natte bulk": [],
        "Container": [],
    }

    # Group the data per day into droge bulk, natte bulk and container.
    aux_delta_ref = aux_df_ref[(aux_df_ref["Jaar"] == reference_year)].iloc[:, 1:]
    aux_delta_ref = (
        aux_delta_ref.groupby(["Maand", "Dag", "Type Vracht"])["Totale Vracht"]
        .sum()
        .reset_index()
    )
    aux_delta_ref = aux_delta_ref.drop(
        aux_delta_ref[(aux_delta_ref["Type Vracht"] == "Overig")].index
    )
    aux_delta_j = aux_df_j[(aux_df_j["Jaar"] == reference_year)].iloc[:, 1:]
    aux_delta_j = (
        aux_delta_j.groupby(["Maand", "Dag", "Type Vracht"])["Totale Vracht"]
        .sum()
        .reset_index()
    )
    aux_delta_j = aux_delta_j.drop(
        aux_delta_j[(aux_delta_j["Type Vracht"] == "Overig")].index
    )

    # Calculate the difference in total freight between the reference scenario and the scenario.
    delta = aux_delta_ref.iloc[:, :3]
    delta["Delta Totale Vracht"] = (
        aux_delta_ref["Totale Vracht"] - aux_delta_j["Totale Vracht"]
    )

    # For droge bulk, natte bulk and container.
    for key in yearly_storage_capacity_data:
        # Filter data.
        df = delta[delta["Type Vracht"] == key].reset_index(drop=True)

        # Calculate the cumulative freight with a moving window of 10, 20 and 30 days.
        df["MW10"] = df["Delta Totale Vracht"].rolling(10).sum().fillna(0)
        df["MW20"] = df["Delta Totale Vracht"].rolling(20).sum().fillna(0)
        df["MW30"] = df["Delta Totale Vracht"].rolling(30).sum().fillna(0)

        # Store yearly data [daily max, 10 days max, 20 days max, 30 days max].
        reference_year_storage_capacity_data[key].append(
            [
                df["Delta Totale Vracht"].min(),
                df["MW10"].min(),
                df["MW20"].min(),
                df["MW30"].min(),
            ]
        )

    # Determine for natte bulk, droge bulk and container the required increase in storage capacity for the Low, Average, and High scenarios.
    increase_storage_capacity = {"Droge bulk": [], "Natte bulk": [], "Container": []}

    # For droge bulk, natte bulk and container.
    for key in increase_storage_capacity:
        # Subtract reference year values.
        delta_yearly_storage_capacity_data = np.array(
            yearly_storage_capacity_data[key]
        ) - np.array(reference_year_storage_capacity_data[key][0])
        delta_yearly_storage_capacity_data[
            delta_yearly_storage_capacity_data > -0.001
        ] = 0.0

        # Low storage scenario.
        increase_storage_capacity[key].append(
            mean(sorted([i[1] for i in delta_yearly_storage_capacity_data])[:3])
        )

        # Average storage scenario.
        increase_storage_capacity[key].append(
            mean(sorted([i[-1] for i in delta_yearly_storage_capacity_data])[:3])
        )

        # High storage scenario.
        increase_storage_capacity[key].append(
            min([i[-1] for i in delta_yearly_storage_capacity_data])
        )

    return increase_storage_capacity


def main():
    # Input and output paths.
    input_path = Path(
        "C:/Users/mes/OneDrive - Stichting Deltares/Documents/Projecten/Deltaprogramma Zoetwater/Scheepvaart/Ruwe data"
    )
    ref_input_path = Path(
        "C:/Users/mes/OneDrive - Stichting Deltares/Documents/Projecten/Deltaprogramma Zoetwater/Scheepvaart/Ruwe data"
    )
    output_path = Path(
        "C:/Users/mes/OneDrive - Stichting Deltares/Documents/Projecten/Deltaprogramma Zoetwater/Scheepvaart/Figures/1916/Figures_2100"
    )

    # Filenames.
    file_name_1 = "BIVAS_resultaten_Pilot 2018.xlsx"
    file_name_2 = "BIVAS_resultaten_Pilot 2018 (infeasible).xlsx"
    file_name_3 = (
        "BIVAS_resultaten_Pilot 2018 (infeasible met minimum van 3 dagen).xlsx"
    )

    # File paths.
    file_path_1 = input_path.joinpath(file_name_1)
    file_path_2 = input_path.joinpath(file_name_2)
    file_path_3 = input_path.joinpath(file_name_3)
    file_path_4 = ref_input_path.joinpath(file_name_1)
    file_path_5 = ref_input_path.joinpath(file_name_2)
    file_path_6 = ref_input_path.joinpath(file_name_3)

    # Reference scenario and year.
    reference = "REF2017BP18"
    reference_year = 1916

    # Scenarios.
    scenarios = ["D2085BP18", "R2085BP18", "S2085BP18", "W2085BP18"]
    ref_scenarios = ["D2050BP18", "R2050BP18", "S2050BP18", "W2050BP18"]
    scenario_year = 2100
    storage_scenarios = ["Laag", "Middel", "Hoog"]

    # Historical time vector (final year of series + 1).
    t = range(1974, 2004)

    # Future time vector.
    future_time = range(2018, scenario_year)

    """ General Input Parameters """

    # Price conversion parameters.
    price_conversion = {
        "2015_to_2017": 1.017,
        "2014_to_2017": 1.023,
        "2012_to_2017": 1.059,
    }

    # Variable storage costs (EUR(2017)).
    storage_costs = {"bulk": 5.2, "container": 11.44}

    # Variable sailing costs (EUR(2014)).
    sailing_costs = {
        "bulk_landbouw": 13.42,
        "bulk_voeding_en_vee": 9.75,
        "bulk_mineralen": 9.88,
        "bulk_aardolie": 16.26,
        "bulk_ertsen": 9.29,
        "bulk_staal": 12.93,
        "bulk_bouwmaterialen": 7.07,
        "bulk_meststoffen": 14.04,
        "bulk_chemische_producten": 13.28,
        "bulk_goederen": 17.56,
        "container": 19.42,
    }

    # Costs per tonkm (EUR(2017)).
    tonkm_costs = {
        "bulk_road": (1.64 / 27) * price_conversion["2015_to_2017"],
        "bulk_train": (16.27 / 2700) * price_conversion["2015_to_2017"],
        "container_road": (1.39 / 27) * price_conversion["2015_to_2017"],
        "container_train": (17.19 / 750) * price_conversion["2015_to_2017"],
    }

    # Infrastructural storage costs/ton per year (EUR(2017)).
    infrastructural_storage_costs = {
        "Droge bulk": 28.09,
        "Natte bulk": 52.55,
        "Container": 89.85,
    }

    # Road and train transport costs/ton per year (EUR(2017)).
    road_transport_costs = {
        "Droge bulk": 17.81,
        "Natte bulk": 17.81,
        "Container": 14.15,
    }

    train_transport_costs = {"Droge bulk": 2.66, "Natte bulk": 2.66, "Container": 36.34}

    # Price elasticities.
    price_elasticities = {
        "landbouw": -0.79,
        "voeding_en_vee": -0.84,
        "mineralen": -0.35,
        "aardolie": -0.42,
        "ertsen": -0.41,
        "staal": -0.75,
        "bouwmaterialen": -0.78,
        "meststoffen": -0.75,
        "chemische_producten": -0.86,
        "goederen": -0.84,
        "leeg": -0.84,
        "container": -0.57,
    }

    # Storage vs modal shift (Lorelei distributions).
    storage_share = {
        "landbouw": 1.00,
        "voeding_en_vee": 1.00,
        "mineralen": 0.95,
        "aardolie": 0.50,
        "ertsen": 0.95,
        "staal": 0.50,
        "bouwmaterialen": 0.80,
        "meststoffen": 1.00,
        "chemische_producten": 0.50,
        "goederen": 1.00,
        "container": 0.15,
    }

    # Modal shift.
    modal_shift_road = {
        "0 - Landbouw": 1.00,
        "1 - Voeding en vee": 0.89,
        "2 - Mineralen": 0.31,
        "3 - Aardolie": 0.93,
        "4 - Ertsen": 0.31,
        "5 - Staal": 0.47,
        "6 - Bouwmaterialen": 1.00,
        "7 - Meststoffen": 0.53,
        "8 - Chemische prod.": 0.84,
        "9 - Goederen": 0.88,
        "Container": 0.50,
    }

    modal_shift_train = {
        "0 - Landbouw": 0.00,
        "1 - Voeding en vee": 0.00,
        "2 - Mineralen": 0.69,
        "3 - Aardolie": 0.14,
        "4 - Ertsen": 0.69,
        "5 - Staal": 0.24,
        "6 - Bouwmaterialen": 0.00,
        "7 - Meststoffen": 0.33,
        "8 - Chemische prod.": 0.01,
        "9 - Goederen": 0.00,
        "Container": 0.50,
    }

    # Distribution domestic and foreign shift.
    shift = 0.5

    # Discount rate.
    discount_rate = 0.045

    """ Read input BIVAS - Heden """

    df_ref = read_bivas_input(file_path_4, file_path_5, file_path_6, reference)

    """ Calculate Sailing Costs - Heden """

    variable_costs_sailing_ref = calculate_sailing_costs(
        df_ref, price_conversion, price_elasticities, reference_year, t
    )

    """ Calculate Remaining Freight Costs - Heden """

    variable_costs_storage_and_sailing_ref, variable_costs_modal_shift_ref = (
        calculate_remaining_freight(
            df_ref,
            storage_costs,
            sailing_costs,
            price_conversion,
            modal_shift_road,
            modal_shift_train,
            tonkm_costs,
            reference_year,
            t,
        )
    )

    """ Calculate Distribution Freight - Heden """

    freight_distribution_ref = calculate_distribution_freight(
        df_ref, modal_shift_road, modal_shift_train
    )

    """ Calculate and plot Total Welfare Costs - Heden """

    data = np.array(
        [
            np.array(variable_costs_sailing_ref)[:, 3],
            np.array(variable_costs_storage_and_sailing_ref)[:, 1],
            np.array(variable_costs_modal_shift_ref)[:, -1],
        ]
    )
    data_labels = [
        "Variabele Kosten - Varen, Inclusief Vraagsubstitutie",
        "Variabele Kosten - Tijdelijke Opslag en Alsnog Varen",
        "Variabele Kosten - Modal Shift",
    ]
    colors = ["navy", "royalblue", "cornflowerblue"]
    calculate_welfare_costs(data, data_labels, colors, t, output_path, "REF2017BP18")

    for i, j in zip(scenarios, ref_scenarios):

        """Read input BIVAS - Scenario 2100 (30 years time series, excluding the reference year 1916)"""

        df_i = read_bivas_input(file_path_1, file_path_2, file_path_3, i)

        """ Read input BIVAS - Scenario 2050 (100 years time series, including the reference year 1916) """

        df_i_year = read_bivas_input(file_path_4, file_path_5, file_path_6, j)

        """ Calculate Sailing Costs - Scenario 2100 (scaled with respect to the reference year 1916 from the Scenario 2050 time series) """

        variable_costs_sailing_i = []

        for k in t:
            # Collect data per year and normalize with respect to the reference year.
            aux_delta = df_i[(df_i["Jaartal"] == k)].iloc[:, :3]
            aux_delta["Totale Vaarkosten [EUR (2017)]"] = (
                df_i[(df_i["Jaartal"] == k)].iloc[:, [0, 7]].drop("Jaartal", axis=1)
                - df_i_year[(df_i_year["Jaartal"] == reference_year)]
                .iloc[:, [0, 7]]
                .set_index(aux_delta.index)
                .drop("Jaartal", axis=1)
            ) * price_conversion["2014_to_2017"]

            # Sort the collected data into the categories: bulk and container.
            delta = (
                aux_delta.iloc[10:, :]
                .groupby(["NSTR"])["Totale Vaarkosten [EUR (2017)]"]
                .sum()
                .reset_index()
            )
            delta["Kosten/ton [EUR (2014)]"] = pd.Series(
                list(
                    df_i[
                        (df_i["Jaartal"] == k)
                        & (
                            (df_i["Type Vracht"] == "Droge bulk")
                            | (df_i["Type Vracht"] == "Natte bulk")
                            | (df_i["Type Vracht"] == "Overig")
                        )
                    ]
                    .groupby(["NSTR"])["Totale Vaarkosten"]
                    .sum()
                    / df_i[
                        (df_i["Jaartal"] == k)
                        & (
                            (df_i["Type Vracht"] == "Droge bulk")
                            | (df_i["Type Vracht"] == "Natte bulk")
                            | (df_i["Type Vracht"] == "Overig")
                        )
                    ]
                    .groupby(["NSTR"])["Totale Vracht"]
                    .sum()
                ),
                index=delta.index,
            )
            delta["Kosten/ton Referentie Jaar [EUR (2014)]"] = pd.Series(
                list(
                    df_i_year[
                        (df_i_year["Jaartal"] == reference_year)
                        & (
                            (df_i_year["Type Vracht"] == "Droge bulk")
                            | (df_i_year["Type Vracht"] == "Natte bulk")
                            | (df_i_year["Type Vracht"] == "Overig")
                        )
                    ]
                    .groupby(["NSTR"])["Totale Vaarkosten"]
                    .sum()
                    / df_i_year[
                        (df_i_year["Jaartal"] == reference_year)
                        & (
                            (df_i_year["Type Vracht"] == "Droge bulk")
                            | (df_i_year["Type Vracht"] == "Natte bulk")
                            | (df_i_year["Type Vracht"] == "Overig")
                        )
                    ]
                    .groupby(["NSTR"])["Totale Vracht"]
                    .sum()
                ),
                index=delta.index,
            )
            delta.insert(loc=0, column="Type Vracht", value="Bulk")
            delta = delta.append(
                pd.Series(
                    [
                        "Container",
                        "All",
                        aux_delta.iloc[:10, :]["Totale Vaarkosten [EUR (2017)]"].sum(),
                        df_i[
                            (df_i["Jaartal"] == k)
                            & (df_i["Type Vracht"] == "Container")
                        ]["Totale Vaarkosten"].sum()
                        / df_i[
                            (df_i["Jaartal"] == k)
                            & (df_i["Type Vracht"] == "Container")
                        ]["Totale Vracht"].sum(),
                        df_i_year[
                            (df_i_year["Jaartal"] == reference_year)
                            & (df_i_year["Type Vracht"] == "Container")
                        ]["Totale Vaarkosten"].sum()
                        / df_i_year[
                            (df_i_year["Jaartal"] == reference_year)
                            & (df_i_year["Type Vracht"] == "Container")
                        ]["Totale Vracht"].sum(),
                    ],
                    index=delta.columns,
                ),
                ignore_index=True,
            )
            delta[
                ["Kosten/ton [EUR (2014)]", "Kosten/ton Referentie Jaar [EUR (2014)]"]
            ] = delta[
                ["Kosten/ton [EUR (2014)]", "Kosten/ton Referentie Jaar [EUR (2014)]"]
            ].replace(
                np.inf, 0
            )

            # Calculate the relative price increase and the associated decrease in demand according to the price elasticity.
            delta["Relatieve Prijsstijging"] = (
                (
                    delta["Kosten/ton [EUR (2014)]"]
                    / delta["Kosten/ton Referentie Jaar [EUR (2014)]"]
                )
                - 1
            ).fillna(0)
            delta["Vraagafname"] = delta["Relatieve Prijsstijging"] * pd.Series(
                price_elasticities
            ).reset_index(drop=True)
            delta["Vraagafname"] = np.where(
                delta["Vraagafname"] < -0.5, -0.5, delta["Vraagafname"]
            )

            # Calculate the decrease of the sailing costs of the decrease in demand, assuming a proportional relation with the decrease in demand.
            delta["Kostenvermindering [EUR (2017)]"] = (
                delta["Totale Vaarkosten [EUR (2017)]"] * delta["Vraagafname"]
            )
            delta["Gecorrigeerde Vaarkosten [EUR (2017)]"] = (
                delta["Totale Vaarkosten [EUR (2017)]"]
                + delta["Totale Vaarkosten [EUR (2017)]"] * delta["Vraagafname"]
            )

            # Calculate consumer surplus effect of the decrease in demand.
            delta["Effect Consumentensurplus [EUR (2017)]"] = (
                delta["Totale Vaarkosten [EUR (2017)]"] * delta["Vraagafname"] * 0.5
            )

            # Calculate welfare effect.
            delta["Uiteindelijke Vaarkosten [EUR (2017)]"] = (
                delta["Totale Vaarkosten [EUR (2017)]"]
                + delta["Kostenvermindering [EUR (2017)]"]
                - delta["Effect Consumentensurplus [EUR (2017)]"]
            )
            variable_costs_sailing_i.append(
                [
                    list(
                        delta.groupby(["Type Vracht"])[
                            "Gecorrigeerde Vaarkosten [EUR (2017)]"
                        ]
                        .sum()
                        .values
                    ),
                    list(
                        delta.groupby(["Type Vracht"])[
                            "Effect Consumentensurplus [EUR (2017)]"
                        ]
                        .sum()
                        .values
                    ),
                    list(
                        delta.groupby(["Type Vracht"])[
                            "Uiteindelijke Vaarkosten [EUR (2017)]"
                        ]
                        .sum()
                        .values
                    ),
                    delta["Uiteindelijke Vaarkosten [EUR (2017)]"].sum(),
                ]
            )

        """ Calculate Remaining Freight Costs - Scenario 2100 (scaled with respect to the reference year 1916 from the Scenario 2050 time series) """

        variable_costs_storage_and_sailing_i = []
        variable_costs_modal_shift_i = []

        for k in t:
            # Collect data per year and normalize with respect to the reference year.
            aux_delta = df_i[(df_i["Jaartal"] == k)].iloc[:, :3]
            aux_delta[
                [
                    "Achtergebleven Vracht [Ton]",
                    "Achtergebleven Vracht Na 3 Dagen [Ton]",
                ]
            ] = df_i[(df_i["Jaartal"] == k)].iloc[:, 12:14] - df_i_year[
                (df_i_year["Jaartal"] == reference_year)
            ].iloc[
                :, 12:14
            ].set_index(
                aux_delta.index
            )

            # Sort the collected data into the categories: bulk and container.
            delta = (
                aux_delta.iloc[10:-1, :]
                .groupby(["NSTR"])[
                    "Achtergebleven Vracht [Ton]",
                    "Achtergebleven Vracht Na 3 Dagen [Ton]",
                ]
                .sum()
                .reset_index()
            )  # Ecorys leaves out 'Leeg (geen lading)'.
            delta["Gemiddelde Tonkm/ton"] = pd.Series(
                list(
                    df_i[
                        (df_i["Jaartal"] == k)
                        & (
                            (df_i["Type Vracht"] == "Droge bulk")
                            | (df_i["Type Vracht"] == "Natte bulk")
                            | (df_i["Type Vracht"] == "Overig")
                        )
                    ]
                    .groupby(["NSTR"])["Gemiddelde Tonkm/ton"]
                    .mean()[:-1]
                ),
                index=delta.index,
            )
            delta.insert(loc=0, column="Type Vracht", value="Bulk")
            delta = delta.append(
                pd.Series(
                    [
                        "Container",
                        "All",
                        aux_delta.iloc[:10, :]["Achtergebleven Vracht [Ton]"].sum(),
                        aux_delta.iloc[:10, :][
                            "Achtergebleven Vracht Na 3 Dagen [Ton]"
                        ].sum(),
                        df_i[
                            (df_i["Jaartal"] == k)
                            & (df_i["Type Vracht"] == "Container")
                        ]["Gemiddelde Tonkm/ton"].mean(),
                    ],
                    index=delta.columns,
                ),
                ignore_index=True,
            )

            # Calculate the variable storage and sailing costs of the freight that has not been transported after 3 days with respect to the reference year.
            delta["Opgeslagen Vracht [Ton]"] = (
                delta["Achtergebleven Vracht [Ton]"]
                - delta["Achtergebleven Vracht Na 3 Dagen [Ton]"]
            )
            delta["Variabele Opslagkosten [EUR (2017)]"] = np.where(
                delta["Type Vracht"] == "Bulk",
                delta["Opgeslagen Vracht [Ton]"] * storage_costs["bulk"],
                delta["Opgeslagen Vracht [Ton]"] * storage_costs["container"],
            )
            delta["Variabele Vaarkosten [EUR (2017)]"] = (
                delta["Opgeslagen Vracht [Ton]"]
                * pd.Series(sailing_costs).reset_index(drop=True)
                * price_conversion["2014_to_2017"]
            )

            # Calculate the model shift of the freight that has not been transported within 3 days.
            delta["Modal Shift Weg [Ton]"] = delta[
                "Achtergebleven Vracht Na 3 Dagen [Ton]"
            ] * pd.Series(modal_shift_road).reset_index(
                drop=True
            )  # Ecorys excludes accidentally container freight.
            delta["Modal Shift Weg [Tonkm]"] = (
                delta["Modal Shift Weg [Ton]"] * delta["Gemiddelde Tonkm/ton"]
            )  # Ecorys excludes accidentally container freight.
            delta["Modal Shift Spoor [Ton]"] = delta[
                "Achtergebleven Vracht Na 3 Dagen [Ton]"
            ] * pd.Series(modal_shift_train).reset_index(drop=True)
            delta["Modal Shift Spoor [Tonkm]"] = (
                delta["Modal Shift Spoor [Ton]"] * delta["Gemiddelde Tonkm/ton"]
            )

            # Calculate the model shift of the freight that has been transported within 3 days.
            costs_road_bulk = np.where(
                delta["Type Vracht"] == "Bulk",
                delta["Modal Shift Weg [Tonkm]"] * tonkm_costs["bulk_road"],
                0,
            ).sum()
            costs_road_container = np.where(
                delta["Type Vracht"] == "Container",
                delta["Modal Shift Weg [Tonkm]"] * tonkm_costs["container_road"],
                0,
            ).sum()
            costs_train_bulk = np.where(
                delta["Type Vracht"] == "Bulk",
                delta["Modal Shift Spoor [Tonkm]"] * tonkm_costs["bulk_train"],
                0,
            ).sum()
            costs_train_container = np.where(
                delta["Type Vracht"] == "Container",
                delta["Modal Shift Spoor [Tonkm]"] * tonkm_costs["container_train"],
                0,
            ).sum()

            # Calculate variable costs storage + sailing and modal shift.
            delta["Totale Kosten Tijdelijke Opslag"] = (
                delta["Variabele Opslagkosten [EUR (2017)]"]
                + delta["Variabele Vaarkosten [EUR (2017)]"]
            )
            variable_costs_storage_and_sailing_i.append(
                [
                    list(
                        delta.groupby(["Type Vracht"])[
                            "Totale Kosten Tijdelijke Opslag"
                        ]
                        .sum()
                        .values
                    ),
                    delta["Totale Kosten Tijdelijke Opslag"].sum(),
                ]
            )
            variable_costs_modal_shift_i.append(
                [
                    costs_road_bulk,
                    costs_road_container,
                    costs_train_bulk,
                    costs_train_container,
                    costs_road_bulk + costs_road_container,
                    costs_train_bulk + costs_train_container,
                    costs_road_bulk
                    + costs_road_container
                    + costs_train_bulk
                    + costs_train_container,
                ]
            )

        """ Calculate Distribution Freight - Scenario 2100 """

        freight_distribution_i = calculate_distribution_freight(
            df_i, modal_shift_road, modal_shift_train
        )

        """ Calculate Structural Costs Increase - Scenario 2100 """

        increase_storage_capacity = calculate_increase_storage_capacitiy(
            ref_input_path, input_path, reference, i, j, t, reference_year
        )
        (
            total_costs_storage_capacity,
            total_costs_road_capacity,
            total_costs_train_capacity,
        ) = calculate_increase_structural_costs(
            df_i,
            increase_storage_capacity,
            t,
            reference_year,
            storage_share,
            modal_shift_road,
            modal_shift_train,
            infrastructural_storage_costs,
            road_transport_costs,
            train_transport_costs,
            storage_scenarios,
        )

        """ Calculate and plot Total Welfare Costs - Scenario 2100 """

        # For each storage scenario [low, average, high].
        for k in range(len(storage_scenarios)):
            data = np.array(
                [
                    np.array(variable_costs_sailing_i)[:, 3],
                    np.array(variable_costs_storage_and_sailing_i)[:, 1],
                    np.array(variable_costs_modal_shift_i)[:, -1],
                    [total_costs_storage_capacity[k]] * len(t),
                    [total_costs_road_capacity[k]] * len(t),
                    [total_costs_train_capacity[k]] * len(t),
                ]
            )
            data_labels = [
                "Variabele Kosten - Varen, Inclusief Vraagsubstitutie",
                "Variabele Kosten - Tijdelijke Opslag en Alsnog Varen",
                "Variabele Kosten - Modal Shift",
                "Structurele Kosten - Toename Opslagcapaciteit",
                "Structurele Kosten - Toename Wegcapaciteit",
                "Structurele Kosten - Toename Spoorcapaciteit",
            ]
            colors = [
                "navy",
                "royalblue",
                "cornflowerblue",
                "lightsteelblue",
                "slategrey",
                "orange",
            ]
            calculate_welfare_costs(
                data,
                data_labels,
                colors,
                t,
                output_path,
                i,
                storage_scenario=storage_scenarios[k],
            )

        """ Calculate and plot difference Total Welfare Costs - Heden and Total Welfare Costs - Scenario 2100 """

        # Calculate delta variable costs.
        delta_variabele_costs_sailing = [
            k[3] - l[3]
            for k, l in zip(variable_costs_sailing_i, variable_costs_sailing_ref)
        ]
        delta_variable_costs_storage_and_sailing = [
            k[1] - l[1]
            for k, l in zip(
                variable_costs_storage_and_sailing_i,
                variable_costs_storage_and_sailing_ref,
            )
        ]
        delta_variable_costs_modal_shift = [
            k[-1] - l[-1]
            for k, l in zip(
                variable_costs_modal_shift_i, variable_costs_modal_shift_ref
            )
        ]
        calculate_difference_welfare_costs(
            storage_scenarios,
            delta_variabele_costs_sailing,
            delta_variable_costs_storage_and_sailing,
            delta_variable_costs_modal_shift,
            total_costs_storage_capacity,
            total_costs_road_capacity,
            total_costs_train_capacity,
            t,
            output_path,
            i,
        )

        """ Calculate the Net Present Value """

        npv = calculate_npv(
            storage_scenarios,
            variable_costs_sailing_ref,
            variable_costs_storage_and_sailing_ref,
            variable_costs_modal_shift_ref,
            variable_costs_sailing_i,
            variable_costs_storage_and_sailing_i,
            variable_costs_modal_shift_i,
            total_costs_storage_capacity,
            total_costs_road_capacity,
            total_costs_train_capacity,
            future_time,
            shift,
            discount_rate,
        )

        """ Store Data """

        store_bivas_scenarios(
            output_path,
            i,
            df_ref,
            df_i,
            freight_distribution_ref,
            freight_distribution_i,
        )
        store_costs_and_npv(
            output_path,
            i,
            t,
            variable_costs_sailing_ref,
            variable_costs_storage_and_sailing_ref,
            variable_costs_modal_shift_ref,
            variable_costs_sailing_i,
            variable_costs_storage_and_sailing_i,
            variable_costs_modal_shift_i,
            storage_scenarios,
            total_costs_storage_capacity,
            total_costs_road_capacity,
            total_costs_train_capacity,
            delta_variabele_costs_sailing,
            delta_variable_costs_storage_and_sailing,
            delta_variable_costs_modal_shift,
            scenario_year,
            npv,
        )


if __name__ == "__main__":
    main()
