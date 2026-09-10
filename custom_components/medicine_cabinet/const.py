"""Constants for the Medicine Cabinet integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "medicine_cabinet"

PLATFORMS = ["sensor", "calendar"]

STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = f"{DOMAIN}.cabinet"

# Config / options keys
CONF_EXPIRY_WARNING_DAYS = "expiry_warning_days"
CONF_LOW_STOCK_DEFAULT = "low_stock_default"
CONF_NOTIFY_EXPIRED = "notify_expired"
CONF_NOTIFY_LOW_STOCK = "notify_low_stock"

DEFAULT_EXPIRY_WARNING_DAYS = 30
DEFAULT_LOW_STOCK_DEFAULT = 1
DEFAULT_NOTIFY_EXPIRED = True
DEFAULT_NOTIFY_LOW_STOCK = True

UPDATE_INTERVAL = timedelta(hours=1)

# Medication field keys (as stored)
ATTR_ID = "id"
ATTR_NAME = "name"
ATTR_QUANTITY = "quantity"
ATTR_UNIT = "unit"
ATTR_EXPIRATION_DATE = "expiration_date"
ATTR_PURPOSE = "purpose"
ATTR_CATEGORY = "category"
ATTR_MINIMUM_QUANTITY = "minimum_quantity"
ATTR_LOCATION = "location"
ATTR_NOTES = "notes"

# Derived attributes
ATTR_DAYS_UNTIL_EXPIRATION = "days_until_expiration"
ATTR_IS_EXPIRED = "is_expired"
ATTR_IS_EXPIRING_SOON = "is_expiring_soon"
ATTR_IS_LOW_STOCK = "is_low_stock"

# Service names
SERVICE_ADD_MEDICATION = "add_medication"
SERVICE_UPDATE_MEDICATION = "update_medication"
SERVICE_REMOVE_MEDICATION = "remove_medication"
SERVICE_CONSUME = "consume"
SERVICE_RESTOCK = "restock"

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_MEDICATION_ID = "medication_id"
ATTR_AMOUNT = "amount"

EVENT_EXPIRED = f"{DOMAIN}_expired"
EVENT_EXPIRING_SOON = f"{DOMAIN}_expiring_soon"
EVENT_LOW_STOCK = f"{DOMAIN}_low_stock"

MANUFACTURER = "Medicine Cabinet Tracker"
