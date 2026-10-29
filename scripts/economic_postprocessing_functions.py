# -*- coding: utf-8 -*-

"""
Created on Tue Apr 16 13:31 2019
@author: L.K. Leunge
"""

from matplotlib.ticker import FuncFormatter
from openpyxl import load_workbook
from openpyxl.styles import Font
from pathlib import Path
from statistics import mean
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import numpy_financial as npf


# Formulas in section3.2 and 3.3
def calculate_sailing_costs(
    df, price_conversion, price_elasticities, reference_year, t
):
    variable_costs_sailing = []

    for i in t:
        # Collect data per year and normalize with respect to the reference year (#section3.2 - formulas to calculate 'Jaarlijkse totale kosten' en 'Jaarlijkse totale kosten per ton').
        aux_delta = df[(df["Jaartal"] == i)].iloc[:, [0, 1, 2]]
        aux_delta["Totale Vaarkosten [EUR (2017)]"] = (
            df[(df["Jaartal"] == i)].iloc[:, [0, 7]].drop("Jaartal", axis=1)
            - df[(df["Jaartal"] == reference_year)]
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
                df[
                    (df["Jaartal"] == i)
                    & (
                        (df["Type Vracht"] == "Droge bulk")
                        | (df["Type Vracht"] == "Natte bulk")
                        | (df["Type Vracht"] == "Overig")
                    )
                ]
                .groupby(["NSTR"])["Totale Vaarkosten"]
                .sum()
                / df[
                    (df["Jaartal"] == i)
                    & (
                        (df["Type Vracht"] == "Droge bulk")
                        | (df["Type Vracht"] == "Natte bulk")
                        | (df["Type Vracht"] == "Overig")
                    )
                ]
                .groupby(["NSTR"])["Totale Vracht"]
                .sum()
            ),
            index=delta.index,
        )

        delta["Kosten/ton Referentie Jaar [EUR (2014)]"] = pd.Series(
            list(
                df[
                    (df["Jaartal"] == reference_year)
                    & (
                        (df["Type Vracht"] == "Droge bulk")
                        | (df["Type Vracht"] == "Natte bulk")
                        | (df["Type Vracht"] == "Overig")
                    )
                ]
                .groupby(["NSTR"])["Totale Vaarkosten"]
                .sum()
                / df[
                    (df["Jaartal"] == reference_year)
                    & (
                        (df["Type Vracht"] == "Droge bulk")
                        | (df["Type Vracht"] == "Natte bulk")
                        | (df["Type Vracht"] == "Overig")
                    )
                ]
                .groupby(["NSTR"])["Totale Vracht"]
                .sum()
            ),
            index=delta.index,
        )

        delta.insert(loc=0, column="Type Vracht", value="Bulk")

        container_row = pd.DataFrame(
            [
                [
                    "Container",
                    "All",
                    aux_delta.iloc[:10, :]["Totale Vaarkosten [EUR (2017)]"].sum(),
                    (
                        df[(df["Jaartal"] == i) & (df["Type Vracht"] == "Container")][
                            "Totale Vaarkosten"
                        ].sum()
                        / df[(df["Jaartal"] == i) & (df["Type Vracht"] == "Container")][
                            "Totale Vracht"
                        ].sum()
                    ),
                    (
                        df[
                            (df["Jaartal"] == reference_year)
                            & (df["Type Vracht"] == "Container")
                        ]["Totale Vaarkosten"].sum()
                        / df[
                            (df["Jaartal"] == reference_year)
                            & (df["Type Vracht"] == "Container")
                        ]["Totale Vracht"].sum()
                    ),
                ]
            ],
            columns=delta.columns,
        )

        delta = pd.concat([delta, container_row], ignore_index=True)
        delta[
            ["Kosten/ton [EUR (2014)]", "Kosten/ton Referentie Jaar [EUR (2014)]"]
        ] = delta[
            ["Kosten/ton [EUR (2014)]", "Kosten/ton Referentie Jaar [EUR (2014)]"]
        ].replace(
            np.inf, 0
        )

        # Calculate the relative price increase and the associated decrease in demand according to the price elasticity (#section3.2 - formula to calculate 'Vraagafname').
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

        # Calculate the decrease of the sailing costs of the decrease in demand, assuming a proportional relation with the decrease in demand (#section3.2 - formula to calculate 'Kostenvermindering').
        delta["Kostenvermindering [EUR (2017)]"] = (
            delta["Totale Vaarkosten [EUR (2017)]"] * delta["Vraagafname"]
        )
        delta["Gecorrigeerde Vaarkosten [EUR (2017)]"] = (
            delta["Totale Vaarkosten [EUR (2017)]"]
            + delta["Totale Vaarkosten [EUR (2017)]"] * delta["Vraagafname"]
        )

        # Calculate consumer surplus effect of the decrease in demand (#section3.2 - formula to calculate 'Effect consumentensurplus').
        delta["Effect Consumentensurplus [EUR (2017)]"] = (
            delta["Totale Vaarkosten [EUR (2017)]"] * delta["Vraagafname"] * 0.5
        )

        # Calculate welfare effect (#section3.3 - formula to calculate 'Totale jaarlijkse vaarkosten').
        delta["Uiteindelijke Vaarkosten [EUR (2017)]"] = (
            delta["Totale Vaarkosten [EUR (2017)]"]
            + delta["Kostenvermindering [EUR (2017)]"]
            - delta["Effect Consumentensurplus [EUR (2017)]"]
        )
        variable_costs_sailing.append(
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

    return variable_costs_sailing


# Formulas in section 4.2 and 4.3
def calculate_remaining_freight(
    df,
    storage_costs,
    sailing_costs,
    price_conversion,
    modal_shift_road,
    modal_shift_train,
    tonkm_costs,
    reference_year,
    t,
):
    variable_costs_storage_and_sailing = []
    variable_costs_modal_shift = []

    for i in t:
        # Collect data per year and normalize with Respect to the reference year.
        aux_delta = df.loc[(df["Jaartal"] == i), df.columns[:3]]
        aux_delta[
            ["Achtergebleven Vracht [Ton]", "Achtergebleven Vracht Na 3 Dagen [Ton]"]
        ] = df[(df["Jaartal"] == i)].iloc[:, 12:14] - df[
            (df["Jaartal"] == reference_year)
        ].iloc[
            :, 12:14
        ].set_index(
            aux_delta.index
        )

        # Sort the collected data into the categories: bulk and container (#section4.2 - formula to calculate 'Jaarlijkse achtergebleven vracht' and 'Jaarlijkse achtergebleven vracht na 3 dagen').
        delta = (
            aux_delta.iloc[10:-1, :]
            .groupby(["NSTR"])[
                [
                    "Achtergebleven Vracht [Ton]",
                    "Achtergebleven Vracht Na 3 Dagen [Ton]",
                ]
            ]
            .sum()
            .reset_index()
        )
        delta["Gemiddelde Tonkm/ton"] = pd.Series(
            list(
                df[
                    (df["Jaartal"] == i)
                    & (
                        (df["Type Vracht"] == "Droge bulk")
                        | (df["Type Vracht"] == "Natte bulk")
                        | (df["Type Vracht"] == "Overig")
                    )
                ]
                .groupby(["NSTR"])["Gemiddelde Tonkm/ton"]
                .mean()[:-1]
            ),
            index=delta.index,
        )
        delta.insert(loc=0, column="Type Vracht", value="Bulk")
        container_row = pd.DataFrame(
            [
                [
                    "Container",
                    "All",
                    aux_delta.iloc[:10, :]["Achtergebleven Vracht [Ton]"].sum(),
                    aux_delta.iloc[:10, :][
                        "Achtergebleven Vracht Na 3 Dagen [Ton]"
                    ].sum(),
                    df[(df["Jaartal"] == i) & (df["Type Vracht"] == "Container")][
                        "Gemiddelde Tonkm/ton"
                    ].mean(),
                ]
            ],
            columns=delta.columns,
        )

        delta = pd.concat([delta, container_row], ignore_index=True)

        # Calculate the variable storage and sailing costs of the freight that has not been transported after 3 days with respect to the reference year (#section4.2 - formula to calculate 'Tijdelijk opgeslagen vracht').
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

        # Calculate the model shift of the freight that has not been transported within 3 days (#section4.2 - formula to calculate 'Modal Shift).
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

        # Calculate the costs the model shift of the freight that has been transported within 3 days (#section4.2 - formula to calculate 'Modal shift kosten).
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

        # Calculate variable costs storage + sailing and modal shift (#section4.3 - formula to calculate 'Totale jaarlijkse extra transportkosten').
        delta["Totale Kosten Tijdelijke Opslag"] = (
            delta["Variabele Opslagkosten [EUR (2017)]"]
            + delta["Variabele Vaarkosten [EUR (2017)]"]
        )
        variable_costs_storage_and_sailing.append(
            [
                list(
                    delta.groupby(["Type Vracht"])["Totale Kosten Tijdelijke Opslag"]
                    .sum()
                    .values
                ),
                delta["Totale Kosten Tijdelijke Opslag"].sum(),
            ]
        )
        variable_costs_modal_shift.append(
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

    return variable_costs_storage_and_sailing, variable_costs_modal_shift


# Formulas in section5.2 'Dagelijkse totale vracht' and 'MA'
def calculate_increase_storage_capacity(
    input_path, scenario_ref, scenario_i, years, reference_year
):
    # Open reference scenario and scenario worksheets.
    aux_df_ref = pd.read_csv(Path(input_path, (scenario_ref + ".csv")), index_col=[0, 1, 2, 3]).reset_index()
    aux_df_ref.drop(
        aux_df_ref.columns[[4, 6, 7, 8, 9, 10, 11, 12]], axis=1, inplace=True
    )
    aux_df_i = pd.read_csv(Path(input_path, (scenario_i + ".csv")), index_col=[0, 1, 2, 3]).reset_index()
    aux_df_i.drop(aux_df_i.columns[[4, 6, 7, 8, 9, 10, 11, 12]], axis=1, inplace=True)

    # Adjust column names.
    aux_df_ref.columns = ["Jaar", "Datum", "Type Vracht", "NSTR", "Totale Vracht"]
    aux_df_i.columns = ["Jaar", "Datum", "Type Vracht", "NSTR", "Totale Vracht"]

    # Extract month and day from datum and reposition the DataFrame.
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

    yearly_data_ref = []
    yearly_data_i = []

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
        yearly_data_ref.append(aux_delta_ref)
        yearly_data_i.append(aux_delta_i)

    yearly_storage_capacity_data = {"Droge bulk": [], "Natte bulk": [], "Container": []}

    for i in range(len(years)):
        # Extract data associated to the reference year.
        reference_year_ref = yearly_data_ref[years.index(reference_year)]
        reference_year_i = yearly_data_i[years.index(reference_year)]

        # Normalize the yearly data with respect to the reference year and calculate the difference between the reference scenario and the scenario.
        delta = aux_delta_ref.iloc[:, :3]
        delta["Delta"] = (
            yearly_data_ref[i].iloc[:, -1] - reference_year_ref.iloc[:, -1]
        ) - (yearly_data_i[i].iloc[:, -1] - reference_year_i.iloc[:, -1])

        # For droge bulk, natte bulk and container.
        for key in yearly_storage_capacity_data:
            # Filter data.
            df = delta[delta["Type Vracht"] == key].reset_index(drop=True)

            # Calculate the cumulative freight with a moving window of 10, 20 and 30 days.
            df["MW10"] = df["Delta"].rolling(10).sum().fillna(0)
            df["MW20"] = df["Delta"].rolling(20).sum().fillna(0)
            df["MW30"] = df["Delta"].rolling(30).sum().fillna(0)

            # Store yearly data [daily max, 10 days max, 20 days max, 30 days max].
            yearly_storage_capacity_data[key].append(
                [
                    df["Delta"].min(),
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
        delta_yearly_storage_capacity_data = np.array(yearly_storage_capacity_data[key])
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

    return increase_storage_capacity, yearly_storage_capacity_data


# Formulas in section5.2 and 5.3
def calculate_increase_structural_costs(
    df,
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
):
    # Determine for natte bulk, droge bulk and container the share of the freight that will be stored and transported by road and train.
    share_stored_freight = {
        "Droge bulk": 0,
        "Natte bulk": 0,
        "Container": storage_share["container"],
    }
    share_road_transport = {
        "Droge bulk": 0,
        "Natte bulk": 0,
        "Container": (1 - storage_share["container"]) * modal_shift_road["Container"],
    }
    share_train_transport = {
        "Droge bulk": 0,
        "Natte bulk": 0,
        "Container": (1 - storage_share["container"]) * modal_shift_train["Container"],
    }

    # For droge bulk, natte bulk and container.
    for key in share_stored_freight:
        if any([key == "Droge bulk", key == "Natte bulk"]):
            yearly_data = []

            for i in t:
                # Collect data per year and normalize with respect to the reference year (#section5.2 - formulas to calculate 'Jaarlijkse achtergebleven vracht' en 'Gemiddelde jaarlijks achtergebleven vracht').
                aux_delta = df[(df["Jaartal"] == i)].iloc[:, :3]
                aux_delta[
                    [
                        "Achtergebleven Vracht [Ton]",
                        "Achtergebleven Vracht Na 3 Dagen [Ton]",
                    ]
                ] = df[(df["Jaartal"] == i)].iloc[:, 12:14] - df[
                    (df["Jaartal"] == reference_year)
                ].iloc[
                    :, 12:14
                ].set_index(
                    aux_delta.index
                )

                # Filter data.
                aux_df = aux_delta[aux_delta["Type Vracht"] == key].reset_index(
                    drop=True
                )
                yearly_data.append(
                    aux_df["Achtergebleven Vracht [Ton]"].values.tolist()
                )

            # Calculate per sector the yearly average remaining freight.
            yearly_average_remaining_freight = [
                sum(i) / len(i) for i in zip(*yearly_data)
            ]

            # Calculate the share of freight that is being stored and transported by road and train (#section5.2 - formulas to calculate 'Aandeel opslagcapaciteit' en 'Aandeel transportcapaciteit').
            share_stored_freight[key] = sum(
                [
                    i * j
                    for i, j in zip(
                        yearly_average_remaining_freight,
                        [storage_share[k] for k in storage_share][:-1],
                    )
                ]
            ) / sum(yearly_average_remaining_freight)
            share_road_transport[key] = sum(
                [
                    i * (1 - j) * k
                    for i, j, k in zip(
                        yearly_average_remaining_freight,
                        [storage_share[l] for l in storage_share][:-1],
                        [modal_shift_road[l] for l in modal_shift_road][:-1],
                    )
                ]
            ) / sum(yearly_average_remaining_freight)
            share_train_transport[key] = sum(
                [
                    i * (1 - j) * k
                    for i, j, k in zip(
                        yearly_average_remaining_freight,
                        [storage_share[l] for l in storage_share][:-1],
                        [modal_shift_train[l] for l in modal_shift_train][:-1],
                    )
                ]
            ) / sum(yearly_average_remaining_freight)

    # Determine for natte bulk, droge bulk and container the costs associated to the increase in the storage and modal shift capacities.
    costs_storage_capacity = {"Droge bulk": 0, "Natte bulk": 0, "Container": 0}
    costs_road_capacity = {"Droge bulk": 0, "Natte bulk": 0, "Container": 0}
    costs_train_capacity = {"Droge bulk": 0, "Natte bulk": 0, "Container": 0}

    # section5.2 - formulas to calculate 'Kosten opslagcapaciteit' and 'Kosten transportcapaciteit'
    for key in costs_storage_capacity:
        costs_storage_capacity[key] = [
            i * share_stored_freight[key] * infrastructural_storage_costs[key]
            for i in increase_storage_capacity[key]
        ]
        costs_road_capacity[key] = [
            i * share_road_transport[key] * road_transport_costs[key]
            for i in increase_storage_capacity[key]
        ]
        costs_train_capacity[key] = [
            i * share_train_transport[key] * train_transport_costs[key]
            for i in increase_storage_capacity[key]
        ]

    # Determine the total costs associated to the increase in the storage and modal shift capacities fot the Low, Average and High scenarios (section5.3 - formula to calculate 'Totale structurele kosten').
    total_costs_storage_capacity = []
    total_costs_road_capacity = []
    total_costs_train_capacity = []

    for i in range(len(storage_scenarios)):
        total_costs_storage_capacity.append(
            sum([costs_storage_capacity[j][i] for j in costs_storage_capacity]) * -1
        )
        total_costs_road_capacity.append(
            sum([costs_road_capacity[j][i] for j in costs_road_capacity]) * -1
        )
        total_costs_train_capacity.append(
            sum([costs_train_capacity[j][i] for j in costs_train_capacity]) * -1
        )

    return (
        total_costs_storage_capacity,
        total_costs_road_capacity,
        total_costs_train_capacity,
    )


# Generates output files
def store_bivas_scenarios(
    output_path,
    scenario,
    df_ref,
    df_i,
    freight_distribution_ref,
    freight_distribution_i,
):
    # Store BIVAS output of reference scenario and scenario.
    with pd.ExcelWriter(
        output_path.joinpath(f"data_scenario_{scenario}.xlsx")
    ) as writer:
        df_ref.iloc[:, :-1].to_excel(
            writer,
            sheet_name="Output BIVAS REF2017BP18",
            header=False,
            index=False,
            startrow=1,
            engine="openpyxl",
        )
        df_i.iloc[:, :-1].to_excel(
            writer,
            sheet_name="Output BIVAS " + scenario,
            header=False,
            index=False,
            startrow=1,
            engine="openpyxl",
        )

        wb = writer.book
        for col_num, value in enumerate(
            [
                "Jaar",
                "Type Vracht",
                "NSTR",
                "Vaarbewegingen [-]",
                "Totale Vracht [Ton]",
                "Totale TEU [TEU]",
                "Reistijd [min]",
                "Totale Vaarkosten [EUR(2014)]",
                "Variabele Vaarkosten [EUR(2014)]",
                "Vaste Vaarkosten [EUR(2014)]",
                "Afstand [km]",
                "Totale Tonkm [Tonkm]",
                "Achtergebleven Vracht [Ton]",
                "Achtergebleven Vracht Na 3 Dagen [Ton]",
            ]
        ):
            writer.sheets["Output BIVAS REF2017BP18"].cell(
                row=1, column=col_num + 1
            ).value = value
            writer.sheets["Output BIVAS REF2017BP18"].cell(
                row=1, column=col_num + 1
            ).font = Font(bold=True)
            writer.sheets["Output BIVAS " + scenario].cell(
                row=1, column=col_num + 1
            ).value = value
            writer.sheets["Output BIVAS " + scenario].cell(
                row=1, column=col_num + 1
            ).font = Font(bold=True)

        freight_distribution_ref.to_excel(
            writer,
            sheet_name="Vracht Verdeling REF2017BP18",
            index=False,
            engine="openpyxl",
        )
        freight_distribution_i.to_excel(
            writer,
            sheet_name="Vracht Verdeling " + scenario,
            index=False,
            engine="openpyxl",
        )

        for col_num, value in enumerate(
            [
                "Jaar",
                "Type Vracht",
                "NSTR",
                "Direct Vervoerd [Ton]",
                "Tijdelijk Opgeslagen [Ton]",
                "Vervoerd Over Weg [Ton]",
                "Vervoerd Over Spoor [Ton]",
                "Restant [Ton]",
                "Totaal Vervoerd [Ton]",
            ]
        ):
            writer.sheets["Vracht Verdeling REF2017BP18"].cell(
                row=1, column=col_num + 1
            ).value = value
            writer.sheets["Vracht Verdeling REF2017BP18"].cell(
                row=1, column=col_num + 1
            ).font = Font(bold=True)
            writer.sheets["Vracht Verdeling " + scenario].cell(
                row=1, column=col_num + 1
            ).value = value
            writer.sheets["Vracht Verdeling " + scenario].cell(
                row=1, column=col_num + 1
            ).font = Font(bold=True)


# Generates output figures
def calculate_welfare_costs(
    data, data_labels, colors, t, output_path, scenario, storage_scenario=None
):
    # Take negative and positive data apart and cumulate.
    cumulated_data = get_cumulated_array(data, min=0)
    cumulated_data_neg = get_cumulated_array(data, max=0)

    # Re-merge negative and positive cumulative data.
    cumulated_data[data < 0] = cumulated_data_neg[data < 0]
    data_stack = cumulated_data

    formatter = FuncFormatter(millions)
    figsize = [10, 5]
    fig, ax = plt.subplots(1, 1, figsize=figsize)

    for i in range(len(data)):
        ax.bar(
            x=t,
            height=data[i],
            bottom=data_stack[i],
            color=colors[i],
            label=data_labels[i],
        )

    ax.set_xlabel("Years", labelpad=7)
    ax.set_ylabel("Costs in Millions [EUR (2017)]")
    ax.set_xticks(np.arange(t[0], t[-1] + 1, 5))
    ax.set_xticklabels(
        ["{:d}".format(i) for i in np.arange(t[0], t[-1] + 1, 5)], rotation=90
    )
    ax.yaxis.set_major_formatter(formatter)
    ax.set_title("Totale Welvaartskosten Scenario " + scenario)
    plt.legend(
        bbox_to_anchor=(0.5, -0.4),
        loc="center",
        ncol=1 if len(data) == 3 else 2,
        frameon=False,
    )
    plt.tight_layout()
    plt.show()
    # if not storage_scenario:
    #     plt.savefig(output_path.joinpath(f'totale_welvaartskosten_scenario_{scenario}.jpg'))
    #     plt.savefig(output_path.joinpath(f'totale_welvaartskosten_scenario_{scenario}.pdf'))
    # else:
    #     plt.savefig(output_path.joinpath(f'totale_welvaartskosten_scenario_{scenario}_{storage_scenario}.jpg'))
    #     plt.savefig(output_path.joinpath(f'totale_welvaartskosten_scenario_{scenario}_{storage_scenario}.pdf'))

    plt.close()


def get_cumulated_array(data, **kwargs):
    cum = data.clip(**kwargs)
    cum = np.cumsum(cum, axis=0)
    array = np.zeros(np.shape(data))
    array[1:] = cum[:-1]
    return array


def millions(x, pos):
    return "{:.0f}".format(x * 1e-6)


# Reads data and scenario from the other script 'economic_postprocessing_bivas_2050'
def read_bivas_input(file_path_1, file_path_2, file_path_3, reference):
    # Open reference worksheet.
    df = pd.read_excel(open(file_path_1, "rb"), sheet_name=reference).reset_index(
        drop=True
    )

    # Add totale vracht niet vervoerd.
    aux_df_1 = pd.read_excel(open(file_path_2, "rb"), sheet_name=reference).reset_index(
        drop=True
    )
    df["Niet Vervoerd"] = aux_df_1.drop(
        aux_df_1[
            (
                (aux_df_1["Unnamed: 2"] == "Leeg (geen lading)")
                & (aux_df_1["Unnamed: 1"] != "Overig")
            )
            | (
                (aux_df_1["Unnamed: 1"] == "Overig")
                & (aux_df_1["Unnamed: 2"] != "Leeg (geen lading)")
            )
        ].index
    )["Totale Vracht (ton)"].values

    # Add totale vracht niet vervoerd na 3 dagen.
    aux_df_2 = pd.read_excel(open(file_path_3, "rb"), sheet_name=reference).reset_index(
        drop=True
    )
    df["Niet Vervoerd Na 3 Dagen"] = aux_df_2.drop(
        aux_df_2[
            (
                (aux_df_2["Unnamed: 2"] == "Leeg (geen lading)")
                & (aux_df_2["Unnamed: 1"] != "Overig")
            )
            | (
                (aux_df_2["Unnamed: 1"] == "Overig")
                & (aux_df_2["Unnamed: 2"] != "Leeg (geen lading)")
            )
        ].index
    )["Totale Vracht (ton)"].values

    # Adjust column names.
    df.columns = [
        "Jaartal",
        "Type Vracht",
        "NSTR",
        "Vaarbewegingen",
        "Totale Vracht",
        "Totale TEU",
        "Reistijd",
        "Totale Vaarkosten",
        "Variabele Vaarkosten",
        "Vaste Vaarkosten",
        "Afstand",
        "Totale Tonkm",
        "Achtergebleven Ton",
        "Achtergebleven Ton Na 3 Dagen",
    ]

    # Calculate averaged tonkm/ton.
    df["Gemiddelde Tonkm/ton"] = df["Totale Tonkm"] / df["Totale Vracht"]
    df["Gemiddelde Tonkm/ton"].fillna(0, inplace=True)

    return df


# Part of generating total values for output
def calculate_distribution_freight(df, modal_shift_road, modal_shift_train):
    # Collect data per year.
    aux_df = df.iloc[:, [0, 1, 2, 4, 12, 13]]
    aux_df = pd.concat(
        [
            aux_df,
            pd.DataFrame(
                {
                    "Direct Vervoerd": (
                        aux_df["Totale Vracht"] - aux_df["Achtergebleven Ton"]
                    ).tolist(),
                    "Tijdelijk Opgeslagen": (
                        aux_df["Achtergebleven Ton"]
                        - aux_df["Achtergebleven Ton Na 3 Dagen"]
                    ).tolist(),
                    "Vervoerd Over Weg": list(np.zeros(len(aux_df.index))),
                    "Vervoerd Over Spoor": list(np.zeros(len(aux_df.index))),
                }
            ),
        ],
        axis=1,
    )

    for key in modal_shift_road:
        if key != "Container":
            aux_df["Vervoerd Over Weg"] = np.where(
                ((aux_df["Type Vracht"] != "Container") & (aux_df["NSTR"] == key)),
                aux_df["Achtergebleven Ton Na 3 Dagen"] * modal_shift_road[key],
                aux_df["Vervoerd Over Weg"],
            )

            aux_df["Vervoerd Over Spoor"] = np.where(
                ((aux_df["Type Vracht"] != "Container") & (aux_df["NSTR"] == key)),
                aux_df["Achtergebleven Ton Na 3 Dagen"] * modal_shift_train[key],
                aux_df["Vervoerd Over Spoor"],
            )

        else:
            aux_df["Vervoerd Over Weg"] = np.where(
                aux_df["Type Vracht"] == "Container",
                aux_df["Achtergebleven Ton Na 3 Dagen"] * modal_shift_road[key],
                aux_df["Vervoerd Over Weg"],
            )
            aux_df["Vervoerd Over Spoor"] = np.where(
                aux_df["Type Vracht"] == "Container",
                aux_df["Achtergebleven Ton Na 3 Dagen"] * modal_shift_train[key],
                aux_df["Vervoerd Over Spoor"],
            )

    aux_df["Restant"] = aux_df["Achtergebleven Ton Na 3 Dagen"] - (
        aux_df["Vervoerd Over Weg"] + aux_df["Vervoerd Over Spoor"]
    )
    aux_df.drop(
        columns=["Achtergebleven Ton", "Achtergebleven Ton Na 3 Dagen"], inplace=True
    )
    freight_distribution = aux_df[
        [
            "Jaartal",
            "Type Vracht",
            "NSTR",
            "Direct Vervoerd",
            "Tijdelijk Opgeslagen",
            "Vervoerd Over Weg",
            "Vervoerd Over Spoor",
            "Restant",
            "Totale Vracht",
        ]
    ]

    return freight_distribution


# Part of generating total values for output
def calculate_npv(
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
):
    npv = []

    # For each scenario [Low, Average, High].
    for j in range(len(storage_scenarios)):
        # Calculate the yearly costs over the period 2018 - ...
        data_ref = np.array(
            [
                mean(np.array(variable_costs_sailing_ref, dtype='object')[:, 3]),
                mean(np.array(variable_costs_storage_and_sailing_ref, dtype='object')[:, 1]),
                mean(np.array(variable_costs_modal_shift_ref, dtype='object')[:, -1]),
                0,
                0,
                0,
            ]
        )

        data_i = np.array(
            [
                mean(np.array(variable_costs_sailing_i, dtype='object')[:, 3]),
                mean(np.array(variable_costs_storage_and_sailing_i, dtype='object')[:, 1]),
                mean(np.array(variable_costs_modal_shift_i, dtype='object')[:, -1]),
                total_costs_storage_capacity[j],
                total_costs_road_capacity[j],
                total_costs_train_capacity[j],
            ]
        )

        data = np.array([data_ref])

        for k in range(len(future_time)):
            data = np.concatenate(
                [
                    data,
                    np.array(
                        [
                            data[k]
                            + (data_i - data_ref)
                            / (np.ones(len(data_ref)) * len(future_time))
                        ]
                    ),
                ]
            )

        # Cummulated domistic yearly costs over the period 2018 - ...
        cumulated_data = np.sum(data, axis=1) * shift

        # Calculate the net present value [EUR (2017)].
        npv.append(npf.npv(discount_rate, cumulated_data))

    return npv


# Generates total values for output
def store_costs_and_npv(
    output_path,
    scenario,
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
):
    # Store variable costs for reference scenario.
    wb = load_workbook(filename=output_path.joinpath(f"data_scenario_{scenario}.xlsx"))
    ws = wb.create_sheet()
    ws.title = "Variabele Kosten REF2017BP18"
    ws.append(
        [
            "Jaar",
            "Gecorrigeerde Vaarkosten Bulk [EUR(2017)]",
            "Gecorrigeerde Vaarkosten Containers [EUR(2017)]",
            "Consumentensurplus Bulk [EUR(2017)]",
            "Consumentensurplus Containers [EUR(2017)]",
            "Totale Vaarkosten Bulk [EUR(2017)]",
            "Totale Vaarkosten Containers [EUR(2017)]",
            "Totale Vaarkosten [EUR(2017)]",
            "Tijdelijk Opslag en Alsnog Varen Bulk [EUR(2017)]",
            "Tijdelijk Opslag en Alsnog Varen Containers [EUR(2017)]",
            "Totale Tijdelijk Opslag en Alsnog Varen [EUR(2017)]",
            "Modal Shift Weg Transport Bulk [EUR(2017)]",
            "Modal Shift Weg Transport Containers [EUR(2017)]",
            "Modal Shift Spoor Transport Bulk [EUR(2017)]",
            "Modal Shift Spoor Transport Containers [EUR(2017)]",
            "Totale Modal Shift Weg Transport [EUR(2017)]",
            "Totale Modal Shift Spoor Transport [EUR(2017)]",
            "Totale Modal Shift [EUR(2017)]",
        ]
    )

    for i in range(len(t)):
        ws.append(
            [
                t[i],
                variable_costs_sailing_ref[i][0][0],
                variable_costs_sailing_ref[i][0][1],
                variable_costs_sailing_ref[i][1][0],
                variable_costs_sailing_ref[i][1][1],
                variable_costs_sailing_ref[i][2][0],
                variable_costs_sailing_ref[i][2][1],
                variable_costs_sailing_ref[i][3],
                variable_costs_storage_and_sailing_ref[i][0][0],
                variable_costs_storage_and_sailing_ref[i][0][1],
                variable_costs_storage_and_sailing_ref[i][1],
                variable_costs_modal_shift_ref[i][0],
                variable_costs_modal_shift_ref[i][1],
                variable_costs_modal_shift_ref[i][2],
                variable_costs_modal_shift_ref[i][3],
                variable_costs_modal_shift_ref[i][4],
                variable_costs_modal_shift_ref[i][5],
                variable_costs_modal_shift_ref[i][6],
            ]
        )

    # Store variable costs for scenario.
    ws = wb.create_sheet()
    ws.title = "Variabele Kosten " + scenario
    ws.append(
        [
            "Jaar",
            "Gecorrigeerde Vaarkosten Bulk [EUR(2017)]",
            "Gecorrigeerde Vaarkosten Containers [EUR(2017)]",
            "Consumentensurplus Bulk [EUR(2017)]",
            "Consumentensurplus Containers [EUR(2017)]",
            "Totale Vaarkosten Bulk [EUR(2017)]",
            "Totale Vaarkosten Containers [EUR(2017)]",
            "Totale Vaarkosten [EUR(2017)]",
            "Tijdelijk Opslag en Alsnog Varen Bulk [EUR(2017)]",
            "Tijdelijk Opslag en Alsnog Varen Containers [EUR(2017)]",
            "Totale Tijdelijk Opslag en Alsnog Varen [EUR(2017)]",
            "Modal Shift Weg Transport Bulk [EUR(2017)]",
            "Modal Shift Weg Transport Containers [EUR(2017)]",
            "Modal Shift Spoor Transport Bulk [EUR(2017)]",
            "Modal Shift Spoor Transport Containers [EUR(2017)]",
            "Totale Modal Shift Weg Transport [EUR(2017)]",
            "Totale Modal Shift Spoor Transport [EUR(2017)]",
            "Totale Modal Shift [EUR(2017)]",
        ]
    )

    for i in range(len(t)):
        ws.append(
            [
                t[i],
                variable_costs_sailing_i[i][0][0],
                variable_costs_sailing_i[i][0][1],
                variable_costs_sailing_i[i][1][0],
                variable_costs_sailing_i[i][1][1],
                variable_costs_sailing_i[i][2][0],
                variable_costs_sailing_i[i][2][1],
                variable_costs_sailing_i[i][3],
                variable_costs_storage_and_sailing_i[i][0][0],
                variable_costs_storage_and_sailing_i[i][0][1],
                variable_costs_storage_and_sailing_i[i][1],
                variable_costs_modal_shift_i[i][0],
                variable_costs_modal_shift_i[i][1],
                variable_costs_modal_shift_i[i][2],
                variable_costs_modal_shift_i[i][3],
                variable_costs_modal_shift_i[i][4],
                variable_costs_modal_shift_i[i][5],
                variable_costs_modal_shift_i[i][6],
            ]
        )

    # Store structural costs for scenario.
    ws = wb.create_sheet()
    ws.title = "Structurele Kosten " + scenario
    ws.append(
        [
            "Opslagscenario",
            "Opslagcapaciteit [EUR(2017)]",
            "Wegcapaciteit [EUR(2017)]",
            "Spoorcapaciteit [EUR(2017)]",
        ]
    )

    for i in range(len(storage_scenarios)):
        ws.append(
            [
                storage_scenarios[i],
                total_costs_storage_capacity[i],
                total_costs_road_capacity[i],
                total_costs_train_capacity[i],
            ]
        )

    # Store delta variable costs.
    ws = wb.create_sheet()
    ws.title = "Delta Variabele Kosten"
    ws.append(
        [
            "Jaar",
            "Totale Vaarkosten [EUR(2017)]",
            "Tijdelijk Opslag en Alsnog Varen[EUR(2017)]",
            "Modal Shift [EUR(2017)]",
        ]
    )

    for i in range(len(t)):
        ws.append(
            [
                t[i],
                delta_variabele_costs_sailing[i],
                delta_variable_costs_storage_and_sailing[i],
                delta_variable_costs_modal_shift[i],
            ]
        )

    # Store net present value.
    ws = wb.create_sheet()
    ws.title = "Netto Contante Waarde"
    ws.append(["Scenario Jaar", "Opslagscenario", "Netto Contante Waarde [EUR(2017)]"])

    for i in range(len(storage_scenarios)):
        ws.append([scenario_year, storage_scenarios[i], npv[i]])

    # Save workbook.
    wb.save(filename=output_path.joinpath(f"data_scenario_{scenario}.xlsx"))

    # Generating plots in which ranking is used


def calculate_difference_welfare_costs(
    storage_scenarios,
    delta_variabele_costs_sailing,
    delta_variable_costs_storage_and_sailing,
    delta_variable_costs_modal_shift,
    total_costs_storage_capacity,
    total_costs_road_capacity,
    total_costs_train_capacity,
    t,
    output_path,
    scenario,
):
    # For each storage scenario [low, average, high].
    for i in range(len(storage_scenarios)):
        # Get ranking index of the sum of delta_welfare_effect, delta_variable_costs_storage_and_sailing and delta_variable_costs_modal_shift.
        sort_index = np.argsort(
            [
                sum(j)
                for j in zip(
                    delta_variabele_costs_sailing,
                    delta_variable_costs_storage_and_sailing,
                    delta_variable_costs_modal_shift,
                )
            ]
        )[::-1]

        # Rank delta_welfare_effect, delta_variable_costs_storage_and_sailing and delta_variable_costs_modal_shift according to ranking index.
        data = np.array(
            [
                [delta_variabele_costs_sailing[j] for j in sort_index],
                [delta_variable_costs_storage_and_sailing[j] for j in sort_index],
                [delta_variable_costs_modal_shift[j] for j in sort_index],
                [total_costs_storage_capacity[i]] * len(t),
                [total_costs_road_capacity[i]] * len(t),
                [total_costs_train_capacity[i]] * len(t),
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

        # Take negative and positive data apart and cumulate.
        cumulated_data = get_cumulated_array(data, min=0)
        cumulated_data_neg = get_cumulated_array(data, max=0)

        # Re-merge negative and positive cumulative data.
        cumulated_data[data < 0] = cumulated_data_neg[data < 0]
        data_stack = cumulated_data

        formatter = FuncFormatter(millions)
        figsize = [10, 5]
        fig, ax = plt.subplots(1, 1, figsize=figsize)

        for j in range(len(data)):
            ax.bar(
                x=t,
                height=data[j],
                bottom=data_stack[j],
                color=colors[j],
                label=data_labels[j],
            )

        ax.set_xlabel("Years", labelpad=7)
        ax.set_ylabel("Costs in Millions [EUR (2017)]")
        ax.set_xticks(np.arange(t[0], t[-1] + 1, 5))
        ax.set_xticklabels(["{:d}".format(j) for j in np.arange(0, len(t), 5)])
        ax.yaxis.set_major_formatter(formatter)
        ax.set_title("Verschil Welvaartskosten REF2017BP18 en Scenario " + scenario)
        plt.legend(bbox_to_anchor=(0.5, -0.4), loc="center", ncol=2, frameon=False)
        plt.tight_layout()
        plt.show()
        # plt.savefig(output_path.joinpath(f'delta_welvaartskosten_scenario_{scenario}_{storage_scenarios[i]}.jpg'))
        # plt.savefig(output_path.joinpath(f'delta_welvaartskosten_scenario_{scenario}_{storage_scenarios[i]}.pdf'))
        plt.close()
