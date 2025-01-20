import pandas as pd
import numpy as np

class CarrierRecommendationModel:

    _instance = None 

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, logger):
        if not hasattr(self, "initialized"):  # Ensure __init__ runs only once
            self.logger = logger
            self.initialized = True

    def _transport_eff_m(self, avg_day, max_day, min_day, count_requests):
        if pd.isna(avg_day):
            return 0
        elif min_day == max_day and isinstance(avg_day, float):
            return 5
        else:
            raw_transport_eff = max(0, 5 - (avg_day / max_day) * 5)
            scaling_factor = 1 - round(1 / (1 + round(np.exp(-(count_requests - 10)))), 3)
            teff = raw_transport_eff - raw_transport_eff * scaling_factor

            if avg_day < 2 and count_requests < 6:
                return teff * 0.3
            return teff

    def _cost_eff_m(self, estimated_cost, max_cost, min_cost):
        if pd.isna(estimated_cost):
            return 0
        elif min_cost == max_cost and isinstance(estimated_cost, float):
            return 5
        else:
            raw_cost_eff = max(0, 10 - (estimated_cost / max_cost) * 10)
            return max(0, raw_cost_eff)

    def _reliability_m(self, on_time, late_delivery, count_requests):
        if (on_time + late_delivery) == 0 or pd.isna(late_delivery) or pd.isna(on_time):
            return 0

        raw_reliability = (on_time / (on_time + late_delivery) * 5)
        scale_factor = 1 - round(1 / (1 + np.exp(-(count_requests - 3))), 3)
        return raw_reliability - raw_reliability * scale_factor

    def _categorize_intensity_dynamic(self, cscore, scores):
        if scores.empty:
            return "Cold"

        low_threshold = np.percentile(scores, 40)
        high_threshold = np.percentile(scores, 80)

        if cscore > high_threshold:
            return "Hot"
        elif cscore > low_threshold:
            return "Warm"
        else:
            return "Cold"

    def _normalize_text(self, text):
        if isinstance(text, str):
            return text.lower().strip().replace("é", "e")
        return text

    def recommend_carriers(self, carrierT, pickup_city, destination_city):
        try:
            carrierT[["Pickup City", "Destination City"]] = carrierT[["Pickup City", "Destination City"]].fillna('')

            recommended_carriers = carrierT[carrierT['Pickup City'].str.lower().isin(pickup_city.lower().replace(",", '').split()) &
                                            carrierT['Destination City'].str.lower().isin(destination_city.lower().replace(",", '').split())]

            if recommended_carriers.empty:
                raise ValueError("No carriers found for the specified locations.")

            pickup_city = recommended_carriers['Pickup City'].iloc[0]
            destination_city = recommended_carriers['Destination City'].iloc[0]

            recommended_carriers['Transport Eff. Score'] = recommended_carriers.apply(
                lambda row: self._transport_eff_m(row['Avg. Delivery Day'],
                                                 recommended_carriers['Avg. Delivery Day'].max(),
                                                 recommended_carriers['Avg. Delivery Day'].min(),
                                                 row['CountRequest']), axis=1)

            recommended_carriers['Reliability Score'] = recommended_carriers.apply(
                lambda row: self._reliability_m(row['On-time'], row['Late Delivery'], row['CountRequest']), axis=1)

            recommended_carriers['Cost Eff. Score'] = recommended_carriers.apply(
                lambda row: self._cost_eff_m(row['Estimated Amount'],
                                            recommended_carriers['Estimated Amount'].max(),
                                            recommended_carriers['Estimated Amount'].min()), axis=1)

            recommended_carriers = recommended_carriers.drop(columns=["Avg. Cost Per Km", "Transport Requests"], errors='ignore')

            recommended_carriers['CScore'] = (
                recommended_carriers['Transport Eff. Score'] +
                recommended_carriers['Reliability Score'] +
                recommended_carriers['Cost Eff. Score']
            )

            recommended_carriers = recommended_carriers.sort_values(by='CScore', ascending=False)
            recommended_carriers = recommended_carriers.drop_duplicates(subset='Carrier Name', keep='first')

            try:
                recommended_carriers['Lead Score'] = recommended_carriers.apply(
                    lambda row: self._categorize_intensity_dynamic(row['CScore'], recommended_carriers['CScore']),
                    axis=1)
            except Exception as e:
                self.logger.error(f"Lead Score Error: {e}")

            self.logger.info(recommended_carriers['Carrier Name'])
            return recommended_carriers, pickup_city, destination_city

        except Exception as e:
            self.logger.error(f"Recommendation Error: {e}")
            raise
