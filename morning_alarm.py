from datetime import datetime, timezone, timedelta

import hassapi as hass


class MorningAlarm(hass.Hass):
    def initialize(self):
        self.running_dimmer = False
        self.location = self.get_entity("device_tracker.pixel_7_pro")
        self.dor_bad = self.get_entity("binary_sensor.dor_bad_contact")
        self.dor_bad.listen_state(self.activity)
        self.next_alarm = self.get_entity("sensor.pixel_7_pro_next_alarm")
        self.next_alarm.listen_state(self.alarm_set)


    def reset(self):
        self.log("Restarting")
        self.restart_app("morning_alarm")


    def alarm_set(self, entity, attribute, old_alarm, new_alarm, kwargs):

        if self.location.is_state("home"):
            self.log("IM HOME")
        else:
            self.log("not home... cancelling.")
            self.reset()

        if new_alarm != "unavailable":
            alarm_time = datetime.fromisoformat(new_alarm)
            delta = alarm_time - timedelta(minutes=30)
            self.log("delta: ", delta)
            delta2 = delta + timedelta(minutes=15)
            self.log("delta2: ", delta2)
            self.kjokken_lys_dimmer = self.run_every(
                    self.run_dimmer, 
                    delta, 
                    10, 
                    which="light.kjokken",
                    stop_at=180
            ) 
            self.stue_lys_timer= self.run_every(
                    self.run_dimmer, 
                    delta2, 
                    30, 
                    which="light.dimmer_stue_spotlights",
                    stop_at=60
            ) 
        else:
            self.log("Alarm unset... cancelling.")
            self.reset()
        

    def run_dimmer(self, kwargs):
        which = kwargs.get("which")
        stop_at = kwargs.get("stop_at")
        light_state = self.get_state(which)
        if self.running_dimmer == False and light_state == "on":
            if which == "lights.dimmer_stue_spotlights":
                self.log("Light already on, cancelling")
                self.reset()
        self.running_dimmer = True

        brightness = self.get_state(which, "brightness")
        if brightness == None:
            brightness= 0
        brightness += 2

        self.call_service(
            "light/turn_on", 
            entity_id = which, 
            brightness = brightness,
        )
        if brightness >= stop_at:
            match which:
                case  "light.kjokken":
                    self.cancel_timer(self.kjokken_lys_dimmer)
                    return
                case  "light.dimmer_stue_spotlights":
                    self.cancel_timer(self.stue_lys_timer)
                    return

    
    def activity(self, entity, attribute, old_state, new_state, kwargs):
        if self.running_dimmer == True and new_state == "on":
            self.log("Someones up... cancelling")
            self.reset()

