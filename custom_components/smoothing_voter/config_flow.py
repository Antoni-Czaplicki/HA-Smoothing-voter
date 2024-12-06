"""Config flow for Smoothing voter integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector
from homeassistant.helpers.entity_registry import async_validate_entity_ids

from .const import (
    CONF_ENTITIES,
    CONF_SMOOTHING_THRESHOLD,
    CONF_VOTER_THRESHOLD,
    DEFAULT_NAME,
    DEFAULT_SMOOTHING_THRESHOLD,
    DEFAULT_VOTER_THRESHOLD,
    DOMAIN,
)


class SmoothingVoterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smoothing voter."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            # Check if user selected at least three entities
            if len(user_input[CONF_ENTITIES]) >= 3:
                registry = self.hass.helpers.entity_registry.async_get()
                entities = async_validate_entity_ids(
                    registry, user_input[CONF_ENTITIES]
                )

                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={},
                    options={
                        CONF_ENTITIES: entities,
                        CONF_VOTER_THRESHOLD: user_input[CONF_VOTER_THRESHOLD],
                        CONF_SMOOTHING_THRESHOLD: user_input[CONF_SMOOTHING_THRESHOLD],
                        CONF_NAME: user_input[CONF_NAME],
                    },
                )
            errors["base"] = "not_enough_entities"

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): selector.TextSelector(),
                vol.Required(CONF_ENTITIES): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "number", "input_number"], multiple=True
                    )
                ),
                vol.Optional(
                    CONF_VOTER_THRESHOLD, default=DEFAULT_VOTER_THRESHOLD
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_SMOOTHING_THRESHOLD, default=DEFAULT_SMOOTHING_THRESHOLD
                ): vol.Coerce(float),
            }
        )

        # If validation failed, show the form again with errors
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_import(self, user_input):
        """Import from configuration.yaml if needed."""
        # This just calls the user step logic; you could also add YAML-specific handling.
        return await self.async_step_user(user_input)

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return SmoothingVoterOptionsFlow(config_entry)


class SmoothingVoterOptionsFlow(config_entries.OptionsFlow):
    """Handle an options flow for Smoothing voter."""

    def __init__(self, config_entry) -> None:
        """Initialize the options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}
        if user_input is not None:
            # Validate at least three entities again
            if len(user_input[CONF_ENTITIES]) >= 3:
                registry = self.hass.helpers.entity_registry.async_get()
                entities = async_validate_entity_ids(
                    registry, user_input[CONF_ENTITIES]
                )
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_ENTITIES: entities,
                        CONF_VOTER_THRESHOLD: user_input[CONF_VOTER_THRESHOLD],
                        CONF_SMOOTHING_THRESHOLD: user_input[CONF_SMOOTHING_THRESHOLD],
                        CONF_NAME: user_input[CONF_NAME],
                    },
                )
            errors["base"] = "not_enough_entities"

        # Pre-fill form fields with current options
        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_NAME, default=options.get(CONF_NAME, DEFAULT_NAME)
                ): selector.TextSelector(),
                vol.Required(
                    CONF_ENTITIES, default=options.get(CONF_ENTITIES, [])
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "number", "input_number"], multiple=True
                    )
                ),
                vol.Optional(
                    CONF_VOTER_THRESHOLD,
                    default=options.get(CONF_VOTER_THRESHOLD, DEFAULT_VOTER_THRESHOLD),
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_SMOOTHING_THRESHOLD,
                    default=options.get(
                        CONF_SMOOTHING_THRESHOLD, DEFAULT_SMOOTHING_THRESHOLD
                    ),
                ): vol.Coerce(float),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
