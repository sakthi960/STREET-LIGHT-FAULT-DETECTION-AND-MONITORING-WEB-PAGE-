# TODO: Fix Automatic Light Control Based on LDR Sensor

## Steps to Complete
- [x] Modify read_sensor_data() in backend.py to read actual lux value from GPIO pin (assuming digital: 0 for dark, 1 for light)
- [x] Update update_light_data() in backend.py to read the actual relay state from GPIO pins to sync software state with hardware state
- [x] Ensure manual control still works and is not overridden by automatic logic (manual control updates GPIO and state, automatic is hardware-based)
- [x] Test the changes by running the server and verifying status updates in dark conditions
