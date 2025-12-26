# TODO: Smart Street Light Project Updates

## Tasks to Complete
- [x] Modify `read_sensor_data` function in backend.py to implement automatic control for lights 1-3 based on LDR readings (turn on when dark, off when bright)
- [x] Ensure light 4 remains in sensor fault mode (lux=-1, voltage=0, current=0)
- [x] Update GPIO control in `read_sensor_data` to set relay states automatically for lights 1-3
- [x] Verify manual control via buttons still works, but automatic takes precedence
- [ ] Test the system to ensure real-time updates on webpage

## Notes
- LDR pins: 5,6,13,19 for lights 1-4
- Relay pins: 17,18,27,22 for lights 1-4
- Threshold: Use digital LDR value (0=dark -> ON, 1=bright -> OFF)
- Light 4 always sensor fault
