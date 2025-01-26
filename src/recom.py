import pandas as pd
import numpy as np
from utils.helpers import *
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
        # Handle empty scores gracefully
        if scores.empty or len(scores) < 2:
            return "Cold"
        
        # Calculate dynamic thresholds
        mid_low_threshold = np.percentile(scores, 50)  # Median
        mid_threshold = np.percentile(scores, 75)  # Top 25%
        high_threshold = np.percentile(scores, 90)  # Top 10%
        very_high_threshold = np.percentile(scores, 95)  # Top 5%

        # Categorize based on dynamic thresholds
        if cscore >= very_high_threshold:
            return "Very Hot"  # Top 5%
        elif cscore >= high_threshold:
            return "Hot"  # Top 10%
        elif cscore >= mid_threshold:
            return "Warm"  # Top 25%
        elif cscore >= mid_low_threshold:
            return "Moderate"  # Median to 25th percentile
        else:
            return "Cold"  # Below 25%


    def _normalize_text(self, text):
        if isinstance(text, str):
            return text.lower().strip().replace("é", "e")
        return text

    def recommend_carriers(self, carrierT: pd.DataFrame, pickup_city : str, destination_city : str,pickup_province : str, dropoff_province :str):
        try:
            carrierT[["Pickup City", "Destination City","Pickup State/Province", "Destination State/Province"]] = carrierT[["Pickup City", "Destination City","Pickup State/Province", "Destination State/Province"]].fillna('')
            
            #city level matching
            carrierT[["Pickup City", "Destination City", "Pickup State/Province", "Destination State/Province"]] = \
            carrierT[["Pickup City", "Destination City", "Pickup State/Province", "Destination State/Province"]].applymap(self._normalize_text)

                # Initialize an empty list to store final recommended carriers
            recommended_carriers = pd.DataFrame()

            # First match: City-level matching (both pickup and destination cities must match)
            city_level_carriers = carrierT[
                (carrierT['Pickup City'] == self._normalize_text(pickup_city)) &
                (carrierT['Destination City'] == self._normalize_text(destination_city))
            ]
            city_level_carriers['matching_score'] = 5  # High score for exact city match
            recommended_carriers = pd.concat([recommended_carriers, city_level_carriers], ignore_index=True)

            # Exclude carriers already matched in the city-level or partial city-level matches
            remaining_carriers = carrierT[~carrierT['Carrier Name'].isin(recommended_carriers['Carrier Name'])]
            remaining_carriers.fillna(0, inplace=True)  # Fill missing values with 0
            # Second match: State-level matching (pickup and dropoff provinces must match)
            state_level_carriers = remaining_carriers[
                (remaining_carriers['Pickup State/Province'] == self._normalize_text(pickup_province)) &
                (remaining_carriers['Destination State/Province'] == self._normalize_text(dropoff_province))
            ]
            
            state_level_carriers = state_level_carriers.groupby('Carrier Name').agg({
                    'Pickup City': 'first',  # Assuming the Pickup City is the same for each carrier
                    'Pickup State/Province': 'first',  # Assuming the Pickup State/Province is the same for each carrier
                    'Pickup Country': 'first',  # Assuming the Pickup Country is the same for each carrier
                    'Destination City': 'first',  # Assuming the Destination City is the same for each carrier
                    'Destination State/Province': 'first',  # Assuming the Destination State/Province is the same for each carrier
                    'Destination Country': 'first',  # Assuming the Destination Country is the same for each carrier
                    'Transport Requests': 'sum',  # Total transport requests for each carrier
                    'Avg. Cost Per Km': 'mean',  # Average cost per km for each carrier
                    'Estimated Amount': 'mean',  # Average estimated amount for each carrier
                    'Avg. Delivery Day': 'mean',  # Average delivery day for each carrier
                    'On-time': 'mean',  # Average on-time percentage for each carrier
                    'Late Delivery': 'mean',  # Average late delivery percentage for each carrier
                    'CountRequest': 'sum'  # Total requests count for each carrier
                }).reset_index()
            state_level_carriers['matching_score'] = -5  # Low score for state-level match
            recommended_carriers = pd.concat([recommended_carriers, state_level_carriers], ignore_index=True)
            # Drop duplicates to ensure no carrier is added more than once
            recommended_carriers = recommended_carriers.drop_duplicates(subset='Carrier Name', keep='first')

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
                recommended_carriers['Cost Eff. Score'] + 
                recommended_carriers['matching_score']
            )

            recommended_carriers = recommended_carriers.sort_values(by='CScore', ascending=False)
            recommended_carriers = recommended_carriers.drop_duplicates(subset='Carrier Name', keep='first')
            
            try:
                recommended_carriers['Lead Score'] = recommended_carriers.apply(
                    lambda row: self._categorize_intensity_dynamic(row['CScore'], recommended_carriers['CScore']),
                    axis=1)
            except Exception as e:
                self.logger.error(f"Lead Score Error: {e}")


            self.logger.info(recommended_carriers[['Carrier Name','CScore']])
            return recommended_carriers[:14].sort_values(by='CScore', ascending=True)

        except Exception as e:
            self.logger.error(f"Recommendation Error: {e}")
            raise
