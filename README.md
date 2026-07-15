# KMU26 physical AUV ROS 2 package

`hit25_auv_ros2` starts the vehicle sensors, MAVROS, localization, and joystick control.

The default launch behavior is unchanged: `joy2mavros` publishes directly to
`/mavros/rc/override`. When it is used with `kmu26_pinger_homing`, start the stack with the
dedicated mux input and idle release enabled:

```bash
ros2 launch hit25_auv_ros2 localization_test.launch.py \
  joy_rc_output_topic:=/control/joystick/rc_override \
  joy_release_when_idle:=true
```

The Pinger Homing Web GUI supplies these two arguments automatically. Idle joystick samples then
publish `CHAN_RELEASE`; deliberate joystick axis movement publishes active PWM and takes priority
over autonomous pinger RC in `rc_override_mux`. Arming and mode buttons continue to call the normal
MAVROS services.

Test the mux-input contract after building:

```bash
colcon test --packages-select hit25_auv_ros2 --ctest-args -R joy2mavros_mux_input
```
