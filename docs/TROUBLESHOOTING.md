# Troubleshooting Guide

Common issues and solutions for WLED Effects.

## Installation Issues

### Integration Not Appearing

**Problem**: WLED Effects doesn't show in integration list

**Solutions**:
- Restart Home Assistant after installation
- Check `custom_components/wled_context_effects/` exists
- Verify `manifest.json` is present and valid
- Check logs: Settings → System → Logs

### WLED Device Not Found

**Problem**: Can't select WLED device during setup

**Solutions**:
- Install and configure WLED integration first
- Verify WLED device is online (ping IP address)
- Check WLED firmware version (need 0.14.0+)
- Try manual IP address entry

## Effect Issues

### Effect Not Starting

**Problem**: Effect switch turns on but nothing happens

**Solutions**:
1. Check WLED device is responsive
2. Verify WLED isn't in another mode
3. Check brightness is above 0
4. Review logs for errors
5. Try restarting the effect

```yaml
# Restart effect
service: button.press
target:
  entity_id: button.wled_effects_<name>_restart
```

### Effect Looks Wrong

**Problem**: Effect displays incorrectly

**Solutions**:
- Check LED count configuration
- Verify color format (R,G,B, 0-255)
- Test with default configuration
- Check `reverse_direction` setting
- Verify WLED segment configuration

### Effect is Laggy

**Problem**: Animations are choppy or slow

**Solutions**:
- Check network latency to WLED device
- Reduce update rate for complex effects
- Verify WLED device isn't overloaded
- Check Home Assistant CPU usage
- Simplify effect configuration

```yaml
# Monitor performance
sensor.wled_effects_<name>_frame_rate
sensor.wled_effects_<name>_latency
```

## State-Reactive Issues

### State Not Affecting Effect

**Problem**: Effect doesn't react to state changes

**Solutions**:
1. Verify `state_entity` exists and is available
2. Check `state_min` and `state_max` are correct
3. Verify state value is numeric
4. Check `state_controls` parameter
5. Review effect documentation for state support

### Effect Updates Too Slowly

**Problem**: Effect lags behind state changes

**Solutions**:
- Set `transition_mode` to `instant`
- Reduce `smoothing_factor`
- Check state entity update frequency
- Verify network isn't congested

### Effect Updates Too Rapidly

**Problem**: Effect is jittery or flickering

**Solutions**:
- Set `transition_mode` to `smooth`
- Increase `smoothing_factor`
- Add delay to state entity updates
- Use `blend_mode: average` for multi-input

## Configuration Issues

### Parameter Not Accepting Value

**Problem**: Configuration parameter rejects value

**Solutions**:
- Check parameter range (min/max)
- Verify data type (number vs string)
- Use correct format (e.g., "R,G,B" for colors)
- Check effect documentation for valid values

### Configuration Resets

**Problem**: Configuration changes don't persist

**Solutions**:
- Use number/select entities, not direct config
- Restart Home Assistant after config changes
- Check for automation overriding settings
- Verify configuration entry isn't corrupted

## Performance Issues

### High CPU Usage

**Problem**: Home Assistant CPU usage high

**Solutions**:
- Reduce number of active effects
- Increase effect update intervals
- Disable unused state monitoring
- Check for automation loops
- Review logs for errors

### Network Congestion

**Problem**: WLED device becoming unresponsive

**Solutions**:
- Reduce effect update frequency
- Check network bandwidth
- Verify WLED device isn't overwhelmed
- Use rate limiting (automatic in integration)

## Error Messages

### "Connection Failed"

**Cause**: Can't reach WLED device

**Solutions**:
- Verify WLED device IP address
- Check network connectivity
- Ping WLED device
- Restart WLED device
- Check firewall settings

### "Effect Not Found"

**Cause**: Effect type doesn't exist

**Solutions**:
- Check effect name spelling
- Verify effect is registered
- Restart Home Assistant
- Check custom effect files

### "Configuration Error"

**Cause**: Invalid configuration

**Solutions**:
- Review configuration format
- Check required parameters
- Verify parameter types
- Use effect documentation

### "State Entity Unavailable"

**Cause**: Monitored entity is unavailable

**Solutions**:
- Verify entity exists
- Check entity availability
- Remove `state_entity` for standalone mode
- Use fallback configuration

## Device-Specific Issues

### ESP8266 vs ESP32

**ESP8266**:
- Lower LED count limit (~250)
- Slower processing
- Use simpler effects

**ESP32**:
- Higher LED count (500+)
- Faster processing
- All effects work well

### Firmware Compatibility

**Minimum**: WLED 0.14.0

**Recommended**: Latest stable release

**Issues with older firmware**:
- Update WLED firmware
- Check changelog for breaking changes
- Test with basic effects first

## Diagnostic Tools

### Check Effect Status

```yaml
# View current status
sensor.wled_effects_<name>_status

# View performance
sensor.wled_effects_<name>_frame_rate
sensor.wled_effects_<name>_latency
sensor.wled_effects_<name>_error_rate
```

### Enable Debug Logging

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.wled_context_effects: debug
```

### Test WLED Connectivity

```yaml
# Test service call
service: wled.effect
target:
  entity_id: light.wled_device
data:
  effect: "Solid"
```

## Common Automation Issues

### Effect Doesn't Turn Off

**Problem**: Effect stays on when automation should turn it off

**Solutions**:
- Check automation mode (restart, single, parallel)
- Verify entity_id is correct
- Check for competing automations
- Add explicit turn_off action

### Multiple Effects Fighting

**Problem**: Multiple effects activating simultaneously

**Solutions**:
- Use automation modes properly
- Add conditions to prevent conflicts
- Turn off other effects explicitly
- Use scenes for coordinated control

## Getting Help

If problems persist:

1. **Check logs**: Settings → System → Logs
2. **Search issues**: [GitHub Issues](https://github.com/tamaygz/hacs-wledext-effects/issues)
3. **Ask community**: [GitHub Discussions](https://github.com/tamaygz/hacs-wledext-effects/discussions)
4. **Report bug**: Include logs, configuration, WLED version

### Bug Report Template

```markdown
**Environment**:
- Home Assistant version: 
- WLED Effects version: 
- WLED firmware version: 
- WLED device: ESP8266/ESP32
- LED count: 

**Issue**:
[Describe the problem]

**Configuration**:
```yaml
[Your effect configuration]
```

**Logs**:
```
[Relevant log entries]
```

**Steps to Reproduce**:
1. 
2. 
3. 
```

---

**Last Updated**: January 2026
