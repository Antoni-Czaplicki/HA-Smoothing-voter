"""Smoothing Voter Sensor Group for Home Assistant."""

from __future__ import annotations

import logging
from typing import Any

# Import SensorGroup and related logic from group integration
# pylint: disable-next=hass-component-root-import
from homeassistant.components.group.sensor import SensorGroup
from homeassistant.components.sensor import UNIT_CONVERTERS
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ENTITIES,
    CONF_NAME,
    CONF_SMOOTHING_THRESHOLD,
    CONF_VOTER_THRESHOLD,
)

_LOGGER = logging.getLogger(__name__)


def smoothing_voter(
    inputs, prev_output=None, voter_threshold=0.1, smoothing_threshold=1.0
):
    """Apply the smoothing voter algorithm to a list of inputs.

    Args:
        inputs (list): List of numeric inputs.
        prev_output (float, optional): Previous output value for smoothing. Defaults to None.
        voter_threshold (float, optional): Threshold for voter stability. Defaults to 0.1.
        smoothing_threshold (float, optional): Threshold for smoothing based on previous output. Defaults to 1.0.

    Returns:
        tuple: A tuple containing the new value and the calculation type ('median', 'smoothed', or 'none').

    """
    n = len(inputs)
    if n < 3:
        raise ValueError("Smoothing voter requires at least three inputs.")
    sorted_inputs = sorted(inputs)
    m = (n + 1) // 2
    for i in range(n - m + 1):
        subset = sorted_inputs[i : i + m]
        if max(subset) - min(subset) <= voter_threshold:
            # Found a stable median subset
            return subset[m // 2], "median"
    if prev_output is None:
        # Fallback median if no stable subset found and no prev output
        return sorted_inputs[n // 2], "median"
    closest_input = min(inputs, key=lambda x: abs(x - prev_output))
    if abs(closest_input - prev_output) <= smoothing_threshold:
        # Smoothed value based on prev_output
        return closest_input, "smoothed"
    # None found
    return None, "none"


class SmoothingVoterSensorGroup(SensorGroup):
    """A sensor group that calculates its state using the smoothing voter algorithm."""

    def __init__(
        self,
        hass: HomeAssistant,
        unique_id: str | None,
        name: str,
        entity_ids: list[str],
        ignore_non_numeric: bool,
        voter_threshold: float,
        smoothing_threshold: float,
    ) -> None:
        """Initialize the sensor group."""
        super().__init__(
            hass,
            unique_id,
            name,
            entity_ids,
            ignore_non_numeric,
            "mean",  # Not used, but required by base class signature
            None,
            None,
            None,
        )
        self._voter_threshold = voter_threshold
        self._smoothing_threshold = smoothing_threshold
        self._prev_output = None
        self._calculation_type = "none"

    @property
    def should_poll(self) -> bool:
        """Disable polling."""
        return False

    def async_update_group_state(self) -> None:
        """Update group state using smoothing_voter instead of standard aggregation."""
        valid_state_entities = self._get_valid_entities()
        self.calculate_state_attributes(valid_state_entities)

        sensor_values = []
        any_valid = False

        for entity_id in self._entity_ids:
            if (state := self.hass.states.get(entity_id)) is not None:
                try:
                    numeric_state = float(state.state)
                    uom = state.attributes.get("unit_of_measurement")
                    # Convert to native unit if possible
                    if (
                        self._valid_units
                        and uom in self._valid_units
                        and self._can_convert
                    ):
                        numeric_state = UNIT_CONVERTERS[self.device_class].convert(
                            numeric_state, uom, self.native_unit_of_measurement
                        )
                    sensor_values.append(numeric_state)
                    any_valid = True
                except (ValueError, KeyError):
                    # Non-numeric or incompatible state, skip
                    continue

        self._attr_available = any_valid and len(sensor_values) >= 3

        if not self._attr_available:
            self._attr_native_value = None
            self._calculation_type = "none"
            return

        try:
            new_val, calc_type = smoothing_voter(
                sensor_values,
                self._prev_output,
                self._voter_threshold,
                self._smoothing_threshold,
            )
            self._attr_native_value = new_val
            self._calculation_type = calc_type
            if new_val is not None:
                self._prev_output = new_val
        except ValueError:
            # Not enough inputs
            self._attr_native_value = None
            self._calculation_type = "none"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor, including calculation type."""
        return {
            **super().extra_state_attributes,
            "calculation_type": self._calculation_type,
        }


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the Smoothing Voter sensor group."""
    name = config_entry.options.get(CONF_NAME)
    entities = config_entry.options.get(CONF_ENTITIES, [])
    voter_threshold = config_entry.options.get(CONF_VOTER_THRESHOLD, 0.1)
    smoothing_threshold = config_entry.options.get(CONF_SMOOTHING_THRESHOLD, 1.0)

    ignore_non_numeric = True
    unique_id = config_entry.entry_id

    async_add_entities(
        [
            SmoothingVoterSensorGroup(
                hass,
                unique_id,
                name,
                entities,
                ignore_non_numeric,
                voter_threshold,
                smoothing_threshold,
            )
        ],
        True,
    )
